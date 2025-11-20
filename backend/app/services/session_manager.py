"""
Session Manager: manages interview sessions and state.
"""
import uuid
import logging
from datetime import datetime
from typing import Dict, Optional, List
from app.models.schema import (
    SessionData,
    IdeaBrief,
    PlanState,
    CoverageMap,
    QAPair,
    Question,
    Answer
)
from app.services.vultr_client import VultrClient
from app.services.model_registry import ModelRegistry
from app.prompts.templates import (
    IDEA_NORMALIZATION_SYSTEM,
    format_idea_normalization_prompt
)

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages interview sessions.
    Handles session creation, state persistence, and lifecycle.
    """

    def __init__(
        self,
        vultr_client: VultrClient,
        model_registry: ModelRegistry
    ):
        """
        Initialize session manager.

        Args:
            vultr_client: Vultr API client
            model_registry: Model registry
        """
        self.client = vultr_client
        self.registry = model_registry
        self.sessions: Dict[str, SessionData] = {}

    def create_session(self, idea: str, mode: str = "software") -> SessionData:
        """
        Create a new interview session.

        Args:
            idea: User's initial idea
            mode: Project mode (software, story, process, etc.)

        Returns:
            New session data
        """
        try:
            # Generate session ID
            session_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()

            # Normalize the idea
            idea_brief = self._normalize_idea(idea, mode)

            # Create session
            session = SessionData(
                session_id=session_id,
                idea_brief=idea_brief,
                plan_state=PlanState(),
                coverage=CoverageMap(),
                qa_history=[],
                created_at=timestamp,
                updated_at=timestamp,
                completed=False
            )

            # Initialize plan metadata
            session.plan_state.meta.title = idea_brief.normalized_summary[:100]
            session.plan_state.meta.type = idea_brief.inferred_type
            session.plan_state.problem.summary = idea_brief.normalized_summary

            # Store session
            self.sessions[session_id] = session

            logger.info(f"Created session {session_id}")
            return session

        except Exception as e:
            logger.error(f"Session creation failed: {e}", exc_info=True)
            raise

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None
        """
        return self.sessions.get(session_id)

    def update_session(
        self,
        session_id: str,
        questions: List[Question],
        answers: List[Answer],
        plan_state: PlanState,
        coverage: CoverageMap
    ) -> SessionData:
        """
        Update session with new Q&A and state.

        Args:
            session_id: Session identifier
            questions: Questions that were asked
            answers: User's answers
            plan_state: Updated plan state
            coverage: Updated coverage

        Returns:
            Updated session
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Add Q&A to history
        question_map = {q.id: q for q in questions}
        for answer in answers:
            question = question_map.get(answer.question_id)
            if question:
                session.qa_history.append(QAPair(
                    question=question,
                    answer=answer
                ))

        # Update state
        session.plan_state = plan_state
        session.coverage = coverage
        session.updated_at = datetime.utcnow().isoformat()

        # Keep Q&A history manageable (last 20 pairs)
        if len(session.qa_history) > 20:
            session.qa_history = session.qa_history[-20:]

        logger.info(f"Updated session {session_id}")
        return session

    def complete_session(self, session_id: str) -> SessionData:
        """
        Mark session as completed.

        Args:
            session_id: Session identifier

        Returns:
            Completed session
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.completed = True
        session.updated_at = datetime.utcnow().isoformat()

        logger.info(f"Completed session {session_id}")
        return session

    def _normalize_idea(self, idea: str, mode: str) -> IdeaBrief:
        """
        Normalize user's raw idea into structured brief.

        Args:
            idea: Raw idea text
            mode: Project mode

        Returns:
            Normalized idea brief
        """
        try:
            # Use a strategy model for normalization
            models = self.registry.pick_strategy_models(k=1)
            if not models:
                raise ValueError("No models available for normalization")

            model = models[0]

            user_prompt = format_idea_normalization_prompt(idea, mode)

            messages = [
                {"role": "system", "content": IDEA_NORMALIZATION_SYSTEM},
                {"role": "user", "content": user_prompt}
            ]

            result = self.client.chat_completion_json(
                model=model,
                messages=messages,
                temperature=0.5,
                max_tokens=1000
            )

            # Create IdeaBrief
            return IdeaBrief(
                raw_input=idea,
                normalized_summary=result.get("normalized_summary", idea),
                inferred_type=result.get("inferred_type", mode),
                key_entities=result.get("key_entities", []),
                initial_scope=result.get("initial_scope", "")
            )

        except Exception as e:
            logger.error(f"Idea normalization failed: {e}")
            # Fallback to minimal brief
            return IdeaBrief(
                raw_input=idea,
                normalized_summary=idea,
                inferred_type=mode,
                key_entities=[],
                initial_scope=""
            )

    def list_sessions(self) -> List[str]:
        """
        List all session IDs.

        Returns:
            List of session IDs
        """
        return list(self.sessions.keys())

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session {session_id}")
            return True
        return False
