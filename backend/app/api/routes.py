"""
FastAPI routes for the InfiniteQ planning harness.
Version 0.2: Adds thread management endpoints.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
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
)
from app.services.session_manager import SessionManager
from app.services.question_engine import QuestionEngine
from app.services.plan_reducer import PlanReducer
from app.services.plan_synthesizer import PlanSynthesizer

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency injection will be handled by main.py
_session_manager: SessionManager = None
_question_engine: QuestionEngine = None
_plan_reducer: PlanReducer = None
_plan_synthesizer: PlanSynthesizer = None


def init_routes(
    session_manager: SessionManager,
    question_engine: QuestionEngine,
    plan_reducer: PlanReducer,
    plan_synthesizer: PlanSynthesizer
):
    """Initialize route dependencies."""
    global _session_manager, _question_engine, _plan_reducer, _plan_synthesizer
    _session_manager = session_manager
    _question_engine = question_engine
    _plan_reducer = plan_reducer
    _plan_synthesizer = plan_synthesizer


@router.post("/session", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    Create a new planning session (v0.2: with profiles and initial thread).

    Args:
        request: Session creation request

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
            round_number=0
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
async def submit_answers(session_id: str, request: AnswerRequest):
    """
    Submit answers and get next questions.

    Args:
        session_id: Session identifier
        request: Answer submission request

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

        # Get the questions that were answered
        # (In a real implementation, we'd store these; here we'll need to handle this differently)
        # For now, we'll skip validation and just process the answers

        # Update plan based on answers
        # We need the original questions - in production, store these in session
        # For now, create dummy questions from answer IDs
        questions = []  # Would be retrieved from session state

        # Update plan state
        updated_plan = _plan_reducer.update_plan(
            plan_state=session.plan_state,
            questions=questions,
            answers=request.answers
        )

        # Update coverage
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

        # Generate next questions
        round_number = len(session.qa_history) // 3  # Rough round estimation
        next_questions = _question_engine.generate_questions(
            idea_brief=session.idea_brief,
            plan_state=updated_plan,
            coverage=updated_coverage,
            recent_qa=session.qa_history[-5:],
            round_number=round_number
        )

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
async def finish_session(session_id: str, request: FinishRequest):
    """
    Finish the session and generate final plan (v0.2: with view profile and execution bundle).

    Args:
        session_id: Session identifier
        request: Finish request with view profile

    Returns:
        Final JSON plan, markdown brief, and optional execution bundle
    """
    try:
        # Get session
        session = _session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Synthesize final plan with view profile
        final_plan, markdown_brief = _plan_synthesizer.synthesize(
            plan_state=session.plan_state,
            idea_brief=session.idea_brief
        )

        # TODO v0.2: Generate execution bundle if requested
        execution_bundle = None
        if request.include_execution_bundle:
            # Will implement in PlanSynthesizer v0.2
            pass

        # TODO v0.2: Filter plan chunks by view profile
        plan_chunks = session.plan_chunks

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
            round_number=0
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
async def submit_thread_answers(session_id: str, thread_id: str, request: ThreadAnswerRequest):
    """
    Submit answers to a specific thread (v0.2).

    Args:
        session_id: Session identifier
        thread_id: Thread identifier
        request: Answer request

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

        # TODO v0.2: Get original questions (would be stored in thread state)
        # For now, we'll work without validation
        questions = []

        # Update plan state (thread-aware)
        updated_plan = _plan_reducer.update_plan(
            plan_state=session.plan_state,
            questions=questions,
            answers=request.answers
        )

        # Update thread coverage
        updated_thread_coverage = _plan_reducer.update_coverage(
            coverage=thread.coverage,
            questions=questions,
            answers=request.answers
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
        if _session_manager.should_inject_reflection(thread):
            # TODO v0.2: Generate reflection question
            pass

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
            round_number=round_number
        )

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
