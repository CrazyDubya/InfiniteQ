"""
FastAPI routes for the InfiniteQ planning harness.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from app.models.schema import (
    CreateSessionRequest,
    CreateSessionResponse,
    AnswerRequest,
    AnswerResponse,
    FinishResponse
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
    Create a new planning session.

    Args:
        request: Session creation request

    Returns:
        Session ID and first questions
    """
    try:
        # Create session
        session = _session_manager.create_session(
            idea=request.idea,
            mode=request.mode
        )

        # Generate first questions
        first_questions = _question_engine.generate_questions(
            idea_brief=session.idea_brief,
            plan_state=session.plan_state,
            coverage=session.coverage,
            recent_qa=[],
            round_number=0
        )

        return CreateSessionResponse(
            session_id=session.session_id,
            first_questions=first_questions,
            coverage=session.coverage
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
async def finish_session(session_id: str):
    """
    Finish the session and generate final plan.

    Args:
        session_id: Session identifier

    Returns:
        Final JSON plan and markdown brief
    """
    try:
        # Get session
        session = _session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Synthesize final plan
        final_plan, markdown_brief = _plan_synthesizer.synthesize(
            plan_state=session.plan_state,
            idea_brief=session.idea_brief
        )

        # Mark session as completed
        _session_manager.complete_session(session_id)

        return FinishResponse(
            json_plan=final_plan,
            markdown_brief=markdown_brief
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session finish failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """
    Get session status.

    Args:
        session_id: Session identifier

    Returns:
        Session metadata
    """
    try:
        session = _session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return {
            "session_id": session.session_id,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "completed": session.completed,
            "qa_count": len(session.qa_history),
            "coverage": session.coverage.model_dump()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
