"""
Session Manager: manages interview sessions and state.
Version 0.2: Adds support for threads, profiles, and modes.
Version 0.3: Adds pluggable storage backends (in-memory or Redis).
"""
import uuid
import logging
import threading
from datetime import datetime
from functools import wraps
from typing import Optional, List, Dict
from app.models.schema import (
    SessionData,
    IdeaBrief,
    PlanState,
    CoverageMap,
    QAPair,
    Question,
    Answer,
    # v0.2 additions
    ProjectProfile,
    PersonaProfile,
    ThreadState,
    ThreadType,
    Mode,
    PlanNote
)
from app.services.vultr_client import VultrClient
from app.services.model_registry import ModelRegistry
from app.services.session_storage import SessionStorage, create_storage
from app.prompts.templates import (
    IDEA_NORMALIZATION_SYSTEM,
    format_idea_normalization_prompt
)

logger = logging.getLogger(__name__)


def _synchronized(method):
    """
    Serialize a mutating SessionManager method on the session it targets.

    Every mutator is a read-modify-write cycle (load, mutate, save). Without
    this, two requests touching the same session can interleave and one of them
    silently loses its update. The lock is reentrant so a locked method may
    call another one.

    Note: this serializes requests within one process. Running several server
    processes against the same file/Redis store would need an external lock.
    """
    @wraps(method)
    def wrapper(self, session_id, *args, **kwargs):
        with self._lock_for(session_id):
            return method(self, session_id, *args, **kwargs)

    return wrapper


def aggregate_global_coverage(threads: Dict[str, ThreadState]) -> CoverageMap:
    """
    Aggregate per-thread coverage into the session-level (global) map.

    Each dimension takes the highest score reached by any thread. Coverage is a
    "how well is this dimension understood" score and each thread is a focused
    exploration of one area, so per dimension the best thread wins rather than
    the average: creating another (still empty) thread must never lower global
    coverage, and answering a question can only raise it.

    Args:
        threads: Thread states keyed by thread id (all of them, active or parked)

    Returns:
        Global coverage map
    """
    aggregated = {field: 0.0 for field in CoverageMap.model_fields}

    for thread in threads.values():
        for field, score in thread.coverage.model_dump().items():
            if score > aggregated[field]:
                aggregated[field] = score

    return CoverageMap(**aggregated)


class SessionManager:
    """
    Manages interview sessions (v0.2: with threads and profiles).
    Handles session creation, state persistence, and lifecycle.
    v0.3: Uses pluggable storage backends (in-memory or Redis).
    """

    def __init__(
        self,
        vultr_client: VultrClient,
        model_registry: ModelRegistry,
        storage: Optional[SessionStorage] = None
    ):
        """
        Initialize session manager.

        Args:
            vultr_client: Vultr API client
            model_registry: Model registry
            storage: Session storage backend (defaults to env-configured storage)
        """
        self.client = vultr_client
        self.registry = model_registry
        self.storage = storage or create_storage()
        # One reentrant lock per session, guarding the read-modify-write cycle
        # of every mutation below.
        self._session_locks: Dict[str, threading.RLock] = {}
        self._session_locks_guard = threading.Lock()

    def _lock_for(self, session_id: str) -> threading.RLock:
        """Get (or create) the mutation lock for a session."""
        with self._session_locks_guard:
            lock = self._session_locks.get(session_id)
            if lock is None:
                lock = threading.RLock()
                self._session_locks[session_id] = lock
            return lock

    def create_session(
        self,
        idea: str,
        mode: Mode = Mode.KICKOFF,
        project_profile: Optional[ProjectProfile] = None,
        persona_profile: Optional[PersonaProfile] = None
    ) -> SessionData:
        """
        Create a new interview session (v0.2: with profiles).

        Args:
            idea: User's initial idea
            mode: Interview mode
            project_profile: Project profile (defaults if not provided)
            persona_profile: Persona profile (defaults if not provided)

        Returns:
            New session data
        """
        try:
            # Generate session ID
            session_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()

            # Normalize the idea
            idea_brief = self._normalize_idea(idea, str(mode.value))

            # Use provided profiles or defaults
            if project_profile is None:
                project_profile = ProjectProfile()
            if persona_profile is None:
                persona_profile = PersonaProfile()

            # Create session
            session = SessionData(
                session_id=session_id,
                idea_brief=idea_brief,
                plan_state=PlanState(),
                coverage=CoverageMap(),
                qa_history=[],
                project_profile=project_profile,
                persona_profile=persona_profile,
                threads={},
                mode=mode,
                created_at=timestamp,
                updated_at=timestamp,
                completed=False
            )

            # Initialize plan metadata
            session.plan_state.meta.title = idea_brief.normalized_summary[:100]
            session.plan_state.meta.type = idea_brief.inferred_type
            session.plan_state.problem.summary = idea_brief.normalized_summary

            # Create initial thread based on mode
            initial_thread = self._create_initial_thread(session, mode)
            session.threads[initial_thread.id] = initial_thread
            session.active_thread_id = initial_thread.id

            # Global coverage is derived from the threads, so keep the
            # invariant true from the start.
            session.coverage = aggregate_global_coverage(session.threads)

            # Store session
            self.storage.save(session_id, session)

            logger.info(f"Created session {session_id} with mode {mode.value}")
            return session

        except Exception as e:
            logger.error(f"Session creation failed: {e}", exc_info=True)
            raise

    def _create_initial_thread(
        self,
        session: SessionData,
        mode: Mode
    ) -> ThreadState:
        """
        Create the initial thread for a session.

        Args:
            session: Session data
            mode: Interview mode

        Returns:
            Initial thread state
        """
        timestamp = datetime.utcnow().isoformat()
        thread_id = str(uuid.uuid4())

        # Determine thread type and title based on mode
        if mode == Mode.KICKOFF:
            thread_type = ThreadType.KICKOFF
            title = "Kickoff: Core Planning"
            root_prompt = session.idea_brief.normalized_summary
        elif mode == Mode.SANITY_CHECK:
            thread_type = ThreadType.SANITY_CHECK
            title = "Sanity Check: Review & Validate"
            root_prompt = f"Reviewing: {session.idea_brief.normalized_summary}"
        else:  # DEEP_DIVE
            thread_type = ThreadType.ARCHITECTURE  # Default deep dive
            title = "Deep Dive: Architecture"
            root_prompt = session.idea_brief.normalized_summary

        return ThreadState(
            id=thread_id,
            session_id=session.session_id,
            type=thread_type,
            title=title,
            root_prompt=root_prompt,
            created_at=timestamp,
            last_updated=timestamp
        )

    @_synchronized
    def create_thread(
        self,
        session_id: str,
        thread_type: ThreadType,
        title: str,
        root_prompt: str = ""
    ) -> ThreadState:
        """
        Create a new thread in a session.

        Args:
            session_id: Session identifier
            thread_type: Type of thread
            title: Thread title
            root_prompt: Initial prompt/context for thread

        Returns:
            New thread state
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        timestamp = datetime.utcnow().isoformat()
        thread_id = str(uuid.uuid4())

        thread = ThreadState(
            id=thread_id,
            session_id=session_id,
            type=thread_type,
            title=title,
            root_prompt=root_prompt or session.idea_brief.normalized_summary,
            created_at=timestamp,
            last_updated=timestamp
        )

        session.threads[thread_id] = thread
        session.updated_at = timestamp

        # Persist changes
        self.storage.save(session_id, session)

        logger.info(f"Created thread {thread_id} in session {session_id}")
        return thread

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Get session by ID from the configured storage backend.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None
        """
        return self.storage.get(session_id)

    def get_thread(self, session_id: str, thread_id: str) -> Optional[ThreadState]:
        """
        Get a thread by ID.

        Args:
            session_id: Session identifier
            thread_id: Thread identifier

        Returns:
            Thread state or None
        """
        session = self.get_session(session_id)
        if not session:
            return None
        return session.threads.get(thread_id)

    @_synchronized
    def set_active_thread(self, session_id: str, thread_id: str) -> SessionData:
        """
        Set the active thread for a session.

        Args:
            session_id: Session identifier
            thread_id: Thread identifier

        Returns:
            Updated session
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if thread_id not in session.threads:
            raise ValueError(f"Thread {thread_id} not found in session")

        session.active_thread_id = thread_id
        session.updated_at = datetime.utcnow().isoformat()

        # Persist changes
        self.storage.save(session_id, session)

        logger.info(f"Set active thread to {thread_id} in session {session_id}")
        return session

    @_synchronized
    def update_thread(
        self,
        session_id: str,
        thread_id: str,
        title: Optional[str] = None,
        active: Optional[bool] = None
    ) -> ThreadState:
        """
        Update thread metadata.

        Args:
            session_id: Session identifier
            thread_id: Thread identifier
            title: New title (optional)
            active: Active status (optional)

        Returns:
            Updated thread
        """
        session = self.storage.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        thread = session.threads.get(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")

        if title is not None:
            thread.title = title
        if active is not None:
            thread.active = active

        thread.last_updated = datetime.utcnow().isoformat()

        # Persist changes
        self.storage.save(session_id, session)

        logger.info(f"Updated thread {thread_id}")
        return thread

    @_synchronized
    def update_session(
        self,
        session_id: str,
        questions: List[Question],
        answers: List[Answer],
        plan_state: PlanState,
        coverage: CoverageMap
    ) -> SessionData:
        """
        Update session with new Q&A and state (legacy v0.1 method).

        Args:
            session_id: Session identifier
            questions: Questions that were asked
            answers: User's answers
            plan_state: Updated plan state
            coverage: Updated coverage

        Returns:
            Updated session
        """
        session = self.storage.get(session_id)
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

        self.storage.save(session_id, session)

        logger.info(f"Updated session {session_id}")
        return session

    @_synchronized
    def update_thread_after_answers(
        self,
        session_id: str,
        thread_id: str,
        questions: List[Question],
        answers: List[Answer],
        plan_state: Optional[PlanState] = None,
        coverage: Optional[CoverageMap] = None
    ) -> ThreadState:
        """
        Record answers for a thread and persist everything they produced (v0.2).

        This is the single write path for answering questions inside a thread:
        it stores the new Q&A pairs, saves the updated plan state and thread
        coverage, and recomputes global coverage from every thread. All of it is
        persisted so the next request builds on it instead of restarting from
        zero.

        Args:
            session_id: Session identifier
            thread_id: Thread identifier
            questions: Questions that were presented for answering (all of them
                count as asked, whether or not the caller answered each one)
            answers: User's answers
            plan_state: Plan state updated from these answers (optional)
            coverage: Thread coverage updated from these answers (optional)

        Returns:
            Updated thread
        """
        session = self.storage.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        thread = session.threads.get(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")

        # Add Q&A to the thread's own history, and to the session's bounded
        # recent-activity log (what /status and the legacy answer endpoint read).
        question_map = {q.id: q for q in questions}
        for answer in answers:
            question = question_map.get(answer.question_id)
            if question:
                pair = QAPair(question=question, answer=answer)
                thread.qa_history.append(pair)
                session.qa_history.append(pair)

        # Persist the state these answers produced, so the next round (and the
        # final synthesis) sees it.
        if plan_state is not None:
            session.plan_state = plan_state
        if coverage is not None:
            thread.coverage = coverage

        timestamp = datetime.utcnow().isoformat()

        # Update counters
        thread.questions_asked += len(questions)
        thread.questions_since_reflection += len(questions)
        thread.last_updated = timestamp

        # Keep histories manageable (last 30 pairs per thread, 20 per session)
        if len(thread.qa_history) > 30:
            thread.qa_history = thread.qa_history[-30:]
        if len(session.qa_history) > 20:
            session.qa_history = session.qa_history[-20:]

        # Global coverage is derived from every thread, so work done in one
        # thread is not discarded when another one answers.
        session.coverage = aggregate_global_coverage(session.threads)
        session.updated_at = timestamp

        # Persist changes
        self.storage.save(session_id, session)

        logger.info(f"Recorded {len(answers)} answers on thread {thread_id} "
                    f"(coverage: {thread.coverage.model_dump()})")

        return thread

    # NOTE: reflection scheduling lives in ReflectionService (which owns the
    # trigger policy) - there is deliberately no second copy here.

    @_synchronized
    def add_plan_note(
        self,
        session_id: str,
        thread_id: str,
        raw: str,
        distilled: str,
        tags: List[str]
    ) -> PlanNote:
        """
        Add a plan note to a thread.

        Args:
            session_id: Session identifier
            thread_id: Thread identifier
            raw: Raw user reflection
            distilled: LLM summary
            tags: Tags for the note

        Returns:
            Created plan note
        """
        session = self.storage.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        thread = session.threads.get(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")

        note = PlanNote(
            id=str(uuid.uuid4()),
            thread_id=thread_id,
            index_in_thread=thread.questions_asked,
            raw=raw,
            distilled=distilled,
            tags=tags
        )

        thread.notes.append(note)
        thread.questions_since_reflection = 0  # Reset counter
        thread.last_updated = datetime.utcnow().isoformat()

        # Persist changes
        self.storage.save(session_id, session)

        logger.info(f"Added plan note to thread {thread_id}")
        return note

    @_synchronized
    def complete_session(self, session_id: str) -> SessionData:
        """
        Mark session as completed.

        Args:
            session_id: Session identifier

        Returns:
            Completed session
        """
        session = self.storage.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.completed = True
        session.updated_at = datetime.utcnow().isoformat()

        self.storage.save(session_id, session)

        logger.info(f"Completed session {session_id}")
        return session

    @_synchronized
    def store_pending_questions(
        self,
        session_id: str,
        thread_id: Optional[str],
        questions: List
    ) -> None:
        """
        Store pending questions for later retrieval when answers are submitted.

        Args:
            session_id: Session identifier
            thread_id: Thread identifier (None for legacy session-level storage)
            questions: List of Question objects to store
        """
        session = self.storage.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if thread_id:
            thread = session.threads.get(thread_id)
            if not thread:
                raise ValueError(f"Thread {thread_id} not found")
            thread.pending_questions = questions
            thread.last_updated = datetime.utcnow().isoformat()
            logger.debug(f"Stored {len(questions)} pending questions for thread {thread_id}")
        else:
            # Legacy session-level storage
            session.pending_questions = questions
            session.updated_at = datetime.utcnow().isoformat()
            logger.debug(f"Stored {len(questions)} pending questions for session {session_id}")

        # Persist changes
        self.storage.save(session_id, session)

    def get_pending_questions(
        self,
        session_id: str,
        thread_id: Optional[str] = None
    ) -> List:
        """
        Retrieve pending questions for a session or thread.

        Args:
            session_id: Session identifier
            thread_id: Thread identifier (None for legacy session-level storage)

        Returns:
            List of pending Question objects
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if thread_id:
            thread = self.get_thread(session_id, thread_id)
            if not thread:
                raise ValueError(f"Thread {thread_id} not found")
            return thread.pending_questions
        else:
            # Legacy session-level storage
            return session.pending_questions

    @_synchronized
    def clear_pending_questions(
        self,
        session_id: str,
        thread_id: Optional[str] = None
    ) -> None:
        """
        Clear pending questions after they've been answered.

        Args:
            session_id: Session identifier
            thread_id: Thread identifier (None for legacy session-level storage)
        """
        session = self.storage.get(session_id)
        if not session:
            return

        if thread_id:
            thread = session.threads.get(thread_id)
            if thread:
                thread.pending_questions = []
        else:
            session.pending_questions = []

        # Persist changes
        self.storage.save(session_id, session)

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
        return self.storage.list_ids()

    def list_threads(self, session_id: str) -> List[ThreadState]:
        """
        List all threads in a session.

        Args:
            session_id: Session identifier

        Returns:
            List of thread states
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        return list(session.threads.values())

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from the configured storage backend.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        deleted = self.storage.delete(session_id)
        if deleted:
            with self._session_locks_guard:
                self._session_locks.pop(session_id, None)
            logger.info(f"Deleted session {session_id}")
        return deleted
