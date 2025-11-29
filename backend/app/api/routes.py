"""
FastAPI routes for the InfiniteQ planning harness.
Version 0.2: Adds thread management endpoints.
"""
import os
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.models.schema import (
    CreateSessionRequest,
    CreateSessionResponse,
    AnswerRequest,
    AnswerResponse,
    FinishRequest,
    FinishResponse,
    # v0.2 Thread API models
    CreateThreadRequest,
    CreateThreadResponse,
    ListThreadsResponse,
    UpdateThreadRequest,
    ThreadAnswerRequest,
    ThreadAnswerResponse,
    SubmitReflectionRequest,
    SubmitReflectionResponse,
)
from app.services.session_manager import SessionManager
from app.services.question_engine import QuestionEngine
from app.services.plan_reducer import PlanReducer
from app.services.plan_synthesizer import PlanSynthesizer
from app.services.reflection_service import ReflectionService

logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_SESSION = os.environ.get("RATE_LIMIT_SESSION", "10/minute")
RATE_LIMIT_LLM = os.environ.get("RATE_LIMIT_LLM", "30/minute")
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


# Dependency injection will be handled by main.py
_session_manager: SessionManager = None
_question_engine: QuestionEngine = None
_plan_reducer: PlanReducer = None
_plan_synthesizer: PlanSynthesizer = None
_reflection_service: ReflectionService = None


def init_routes(
    session_manager: SessionManager,
    question_engine: QuestionEngine,
    plan_reducer: PlanReducer,
    plan_synthesizer: PlanSynthesizer,
    reflection_service: ReflectionService
):
    """Initialize route dependencies."""
    global _session_manager, _question_engine, _plan_reducer, _plan_synthesizer, _reflection_service
    _session_manager = session_manager
    _question_engine = question_engine
    _plan_reducer = plan_reducer
    _plan_synthesizer = plan_synthesizer
    _reflection_service = reflection_service


def _filter_plan_chunks_by_view(chunks: list, view_profile) -> list:
    """
    Filter plan chunks by view profile visibility (v0.2).

    Args:
        chunks: List of PlanChunk objects
        view_profile: ViewProfile enum

    Returns:
        Filtered list of chunks
    """
    from app.models.schema import ViewProfile, Visibility

    if not chunks:
        return []

    # Define visibility mapping for each view
    visibility_map = {
        ViewProfile.BUILDER: {Visibility.INTERNAL_ONLY, Visibility.TEAM, Visibility.AGENT_ONLY},
        ViewProfile.STAKEHOLDER: {Visibility.TEAM, Visibility.STAKEHOLDER, Visibility.DECK_FRIENDLY},
        ViewProfile.INVESTOR: {Visibility.STAKEHOLDER, Visibility.DECK_FRIENDLY},
        ViewProfile.AGENT_SPEC: {Visibility.AGENT_ONLY, Visibility.TEAM}
    }

    allowed_visibilities = visibility_map.get(view_profile, {Visibility.TEAM})

    # Filter chunks
    filtered = [
        chunk for chunk in chunks
        if not chunk.parked and chunk.visibility in allowed_visibilities
    ]

    return filtered


@router.post("/session", response_model=CreateSessionResponse)
@limiter.limit(RATE_LIMIT_SESSION)
async def create_session(request: CreateSessionRequest, req: Request):
    """
    Create a new planning session (v0.2: with profiles and initial thread).

    Args:
        request: Session creation request
        req: FastAPI request object (for rate limiting)

    Returns:
        Session ID, initial thread ID, and first questions
    """
    try:
        # Create session (automatically creates initial thread)
        session = _session_manager.create_session(
            idea=request.idea,
            mode=request.mode,
            project_profile=request.project_profile,
            persona_profile=request.persona_profile
        )

        # Get the initial thread
        if not session.active_thread_id or session.active_thread_id not in session.threads:
            raise ValueError("Initial thread not created")

        initial_thread = session.threads[session.active_thread_id]

        # Generate first questions for the initial thread
        first_questions = _question_engine.generate_questions(
            idea_brief=session.idea_brief,
            plan_state=session.plan_state,
            coverage=initial_thread.coverage,
            recent_qa=[],
            round_number=0,
            # v0.2: Pass profiles and thread context
            project_profile=session.project_profile,
            persona_profile=session.persona_profile,
            thread_type=initial_thread.type,
            plan_notes=initial_thread.notes,
            phase_coverage=initial_thread.phase_coverage
        )

        # Store questions for retrieval when answers are submitted
        _session_manager.store_pending_questions(
            session_id=session.session_id,
            thread_id=initial_thread.id,
            questions=first_questions
        )

        return CreateSessionResponse(
            session_id=session.session_id,
            thread_id=initial_thread.id,
            first_questions=first_questions,
            coverage=initial_thread.coverage,
            project_profile=session.project_profile,
            persona_profile=session.persona_profile
        )

    except Exception as e:
        logger.error(f"Session creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/answer", response_model=AnswerResponse)
@limiter.limit(RATE_LIMIT_LLM)
async def submit_answers(session_id: str, request: AnswerRequest, req: Request):
    """
    Submit answers and get next questions.

    Args:
        session_id: Session identifier
        request: Answer submission request
        req: FastAPI request object (for rate limiting)

    Returns:
        Next questions and updated coverage
    """
    try:
        # Get session
        session = _session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.completed:
            raise HTTPException(status_code=400, detail="Session already completed")

        # Retrieve pending questions from storage
        questions = _session_manager.get_pending_questions(session_id, thread_id=None)

        # Update plan state with actual questions
        updated_plan = _plan_reducer.update_plan(
            plan_state=session.plan_state,
            questions=questions,
            answers=request.answers,
            project_profile=session.project_profile
        )

        # Update coverage with actual questions
        updated_coverage = _plan_reducer.update_coverage(
            coverage=session.coverage,
            questions=questions,
            answers=request.answers
        )

        # Update session
        session = _session_manager.update_session(
            session_id=session_id,
            questions=questions,
            answers=request.answers,
            plan_state=updated_plan,
            coverage=updated_coverage
        )

        # Clear pending questions since they've been answered
        _session_manager.clear_pending_questions(session_id, thread_id=None)

        # Generate next questions
        round_number = len(session.qa_history) // 3  # Rough round estimation
        next_questions = _question_engine.generate_questions(
            idea_brief=session.idea_brief,
            plan_state=updated_plan,
            coverage=updated_coverage,
            recent_qa=session.qa_history[-5:],
            round_number=round_number,
            project_profile=session.project_profile,
            persona_profile=session.persona_profile
        )

        # Store the new questions for the next answer round
        _session_manager.store_pending_questions(session_id, thread_id=None, questions=next_questions)

        return AnswerResponse(
            next_questions=next_questions,
            coverage=updated_coverage,
            plan_preview=updated_plan.model_dump()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Answer submission failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/finish", response_model=FinishResponse)
@limiter.limit(RATE_LIMIT_SESSION)
async def finish_session(session_id: str, request: FinishRequest, req: Request):
    """
    Finish the session and generate final plan (v0.2: with view profile and execution bundle).

    Args:
        session_id: Session identifier
        request: Finish request with view profile
        req: FastAPI request object (for rate limiting)

    Returns:
        Final JSON plan, markdown brief, and optional execution bundle
    """
    try:
        # Get session
        session = _session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Synthesize final plan with view profile and execution bundle
        final_plan, markdown_brief, execution_bundle = _plan_synthesizer.synthesize(
            plan_state=session.plan_state,
            idea_brief=session.idea_brief,
            view_profile=request.view_profile,
            project_profile=session.project_profile,
            include_execution_bundle=request.include_execution_bundle
        )

        # v0.2: Filter plan chunks by view profile
        plan_chunks = _filter_plan_chunks_by_view(session.plan_chunks, request.view_profile)

        # Mark session as completed
        _session_manager.complete_session(session_id)

        return FinishResponse(
            json_plan=final_plan,
            markdown_brief=markdown_brief,
            execution_bundle=execution_bundle,
            plan_chunks=plan_chunks
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session finish failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Thread Management Endpoints (v0.2)
# ============================================================================

@router.post("/session/{session_id}/threads", response_model=CreateThreadResponse)
async def create_thread(session_id: str, request: CreateThreadRequest):
    """
    Create a new thread in a session.

    Args:
        session_id: Session identifier
        request: Thread creation request

    Returns:
        Created thread and initial questions
    """
    try:
        # Create thread
        thread = _session_manager.create_thread(
            session_id=session_id,
            thread_type=request.type,
            title=request.title,
            root_prompt=request.root_prompt
        )

        # Generate first questions for this thread
        session = _session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        first_questions = _question_engine.generate_questions(
            idea_brief=session.idea_brief,
            plan_state=session.plan_state,
            coverage=thread.coverage,
            recent_qa=[],
            round_number=0,
            # v0.2: Pass profiles and thread context
            project_profile=session.project_profile,
            persona_profile=session.persona_profile,
            thread_type=thread.type,
            plan_notes=thread.notes,
            phase_coverage=thread.phase_coverage
        )

        # Store questions for retrieval when answers are submitted
        _session_manager.store_pending_questions(
            session_id=session_id,
            thread_id=thread.id,
            questions=first_questions
        )

        return CreateThreadResponse(
            thread=thread,
            first_questions=first_questions
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Thread creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/threads", response_model=ListThreadsResponse)
async def list_threads(session_id: str):
    """
    List all threads in a session.

    Args:
        session_id: Session identifier

    Returns:
        List of threads and active thread ID
    """
    try:
        session = _session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        threads = _session_manager.list_threads(session_id)

        return ListThreadsResponse(
            threads=threads,
            active_thread_id=session.active_thread_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Thread listing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/session/{session_id}/threads/{thread_id}")
async def update_thread(session_id: str, thread_id: str, request: UpdateThreadRequest):
    """
    Update thread metadata.

    Args:
        session_id: Session identifier
        thread_id: Thread identifier
        request: Update request

    Returns:
        Updated thread
    """
    try:
        thread = _session_manager.update_thread(
            session_id=session_id,
            thread_id=thread_id,
            title=request.title,
            active=request.active
        )

        return thread

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Thread update failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/threads/{thread_id}/activate")
async def activate_thread(session_id: str, thread_id: str):
    """
    Set a thread as the active thread.

    Args:
        session_id: Session identifier
        thread_id: Thread identifier

    Returns:
        Success message
    """
    try:
        _session_manager.set_active_thread(session_id, thread_id)
        return {"message": "Thread activated", "thread_id": thread_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Thread activation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/threads/{thread_id}/answer", response_model=ThreadAnswerResponse)
@limiter.limit(RATE_LIMIT_LLM)
async def submit_thread_answers(session_id: str, thread_id: str, request: ThreadAnswerRequest, req: Request):
    """
    Submit answers to a specific thread (v0.2).

    Args:
        session_id: Session identifier
        thread_id: Thread identifier
        request: Answer request
        req: FastAPI request object (for rate limiting)

    Returns:
        Next questions, coverage, and optional reflection prompt
    """
    try:
        # Get session and thread
        session = _session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        thread = _session_manager.get_thread(session_id, thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        if session.completed:
            raise HTTPException(status_code=400, detail="Session already completed")

        # Retrieve pending questions for this thread
        questions = _session_manager.get_pending_questions(session_id, thread_id)

        # Update plan state (thread-aware)
        updated_plan = _plan_reducer.update_plan(
            plan_state=session.plan_state,
            questions=questions,
            answers=request.answers,
            # v0.2: Pass thread context and notes
            thread_id=thread_id,
            plan_notes=thread.notes,
            project_profile=session.project_profile
        )

        # Update thread coverage (with phase support)
        updated_thread_coverage = _plan_reducer.update_coverage(
            coverage=thread.coverage,
            questions=questions,
            answers=request.answers,
            phase_coverage=thread.phase_coverage  # v0.2: Update phase coverage in-place
        )

        # Update thread with answers
        _session_manager.update_thread_after_answers(
            session_id=session_id,
            thread_id=thread_id,
            questions=questions,
            answers=request.answers
        )

        # Check if reflection is needed
        reflection_prompt = None
        thread_refreshed = _session_manager.get_thread(session_id, thread_id)  # Get updated state
        if thread_refreshed and _reflection_service.should_inject_reflection(thread_refreshed):
            # Generate reflection question
            reflection_prompt = _reflection_service.generate_reflection_question(
                thread=thread_refreshed,
                project_context=session.idea_brief.normalized_summary
            )
            logger.info(f"Injecting reflection prompt for thread {thread_id}")

        # Update global coverage (aggregate across threads)
        # TODO v0.2: Implement proper aggregation
        updated_global_coverage = session.coverage

        # Generate next questions for this thread
        round_number = thread.questions_asked // 3
        next_questions = _question_engine.generate_questions(
            idea_brief=session.idea_brief,
            plan_state=updated_plan,
            coverage=updated_thread_coverage,
            recent_qa=thread.qa_history[-5:],
            round_number=round_number,
            # v0.2: Full context with profiles, thread, notes, and phases
            project_profile=session.project_profile,
            persona_profile=session.persona_profile,
            thread_type=thread_refreshed.type if thread_refreshed else thread.type,
            plan_notes=thread_refreshed.notes if thread_refreshed else thread.notes,
            phase_coverage=thread_refreshed.phase_coverage if thread_refreshed else thread.phase_coverage
        )

        # Clear pending questions and store the new ones
        _session_manager.clear_pending_questions(session_id, thread_id)
        _session_manager.store_pending_questions(session_id, thread_id, next_questions)

        return ThreadAnswerResponse(
            next_questions=next_questions,
            thread_coverage=updated_thread_coverage,
            phase_coverage=thread.phase_coverage,
            global_coverage=updated_global_coverage,
            reflection_prompt=reflection_prompt
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Thread answer submission failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/threads/{thread_id}/reflect", response_model=SubmitReflectionResponse)
async def submit_reflection(session_id: str, thread_id: str, request: SubmitReflectionRequest):
    """
    Submit a reflection for a thread (v0.2).

    Args:
        session_id: Session identifier
        thread_id: Thread identifier
        request: Validated reflection request with text field

    Returns:
        Created PlanNote
    """
    try:
        # Get session and thread
        session = _session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        thread = _session_manager.get_thread(session_id, thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Create plan note (validation already done by Pydantic)
        plan_note = _reflection_service.create_plan_note(
            thread_id=thread_id,
            index_in_thread=thread.questions_asked,
            raw_reflection=request.text.strip(),
            thread_type=thread.type,
            project_profile=session.project_profile.model_dump()
        )

        # Add note to session
        _session_manager.add_plan_note(
            session_id=session_id,
            thread_id=thread_id,
            raw=plan_note.raw,
            distilled=plan_note.distilled,
            tags=plan_note.tags
        )

        logger.info(f"Reflection captured for thread {thread_id}: {len(plan_note.tags)} tags")

        return SubmitReflectionResponse(note=plan_note)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reflection submission failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/threads/{thread_id}/insights")
async def get_thread_insights(session_id: str, thread_id: str):
    """
    Get insights extracted from thread reflections.

    Args:
        session_id: Session identifier
        thread_id: Thread identifier

    Returns:
        Summary of insights from reflections
    """
    try:
        thread = _session_manager.get_thread(session_id, thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        insights_summary = _reflection_service.extract_insights_from_notes(
            notes=thread.notes
        )

        return {
            "thread_id": thread_id,
            "note_count": len(thread.notes),
            "insights": insights_summary,
            "notes": [note.model_dump() for note in thread.notes]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Insights retrieval failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """
    Get session status (v0.2: includes thread information).

    Args:
        session_id: Session identifier

    Returns:
        Session metadata with thread summary
    """
    try:
        session = _session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Calculate thread summary
        thread_summary = [
            {
                "id": thread.id,
                "title": thread.title,
                "type": thread.type.value,
                "questions_asked": thread.questions_asked,
                "active": thread.active,
                "coverage_avg": sum(thread.coverage.model_dump().values()) / 9
            }
            for thread in session.threads.values()
        ]

        return {
            "session_id": session.session_id,
            "mode": session.mode.value,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "completed": session.completed,
            "qa_count": len(session.qa_history),  # Legacy
            "coverage": session.coverage.model_dump(),
            "project_profile": session.project_profile.model_dump(),
            "persona_profile": session.persona_profile.model_dump(),
            "active_thread_id": session.active_thread_id,
            "thread_count": len(session.threads),
            "threads": thread_summary
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
