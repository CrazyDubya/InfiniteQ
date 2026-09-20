"""
Tests for the robustness fixes: model categorization, HTTP retries,
deterministic reflection triggers, and per-session write locking.
"""
import threading

import pytest

from app.models.schema import (
    Answer,
    CoverageKey,
    CoverageMap,
    IdeaBrief,
    QAPair,
    Question,
    QuestionOption,
    SessionData,
    ThreadState,
    ThreadType,
)
from app.services.model_registry import ModelRegistry
from app.services.reflection_service import ReflectionService
from app.services.session_manager import SessionManager
from app.services.session_storage import FileStorage
from app.services.vultr_client import VultrClient

NOW = "2024-01-01T00:00:00"
THREAD_ID = "thread-1"


class StubModelClient:
    """Minimal stand-in for VultrClient (no network)."""

    def __init__(self, models=None, error=None):
        self._models = models or []
        self._error = error

    def list_models(self):
        if self._error:
            raise RuntimeError(self._error)
        return list(self._models)

    def chat_completion_json(self, model, messages, **kwargs):
        return {}


def _registry(client=None):
    return ModelRegistry(client or StubModelClient())


class TestModelCategorization:
    """MODEL_PATTERNS are regexes and must actually be applied as such."""

    @pytest.mark.parametrize("model_id,expected", [
        ("deepseek-r1-distill-qwen-32b", "reasoning"),
        ("qwen3-think-8b", "reasoning"),          # requires "qwen.*think"
        ("qwen2.5-coder-32b-instruct", "code_tech"),
        ("deepseek-coder-v2", "code_tech"),       # requires "deepseek.*coder"
        ("llama-3.3-70b-instruct-fp8", "synthesis"),
        ("llama-3.1-70b-instruct", "synthesis"),
        ("kimi-k2-instruct", "synthesis"),
        ("mystery-model-7b", "general"),
    ])
    def test_models_land_in_the_right_role(self, model_id, expected):
        assert _registry()._categorize_model(model_id).value == expected


class TestModelDiscoveryFailure:
    """A bad API key must be visible, not masked by silent fallbacks."""

    def test_failure_is_recorded_and_fallbacks_are_used(self):
        registry = _registry(StubModelClient(error="401 Unauthorized"))

        models = registry.discover_models()

        assert models, "expected hardcoded fallback models"
        assert registry.discovery_error and "401" in registry.discovery_error

    def test_success_clears_the_error(self):
        registry = _registry(StubModelClient(models=[{"id": "llama-3.3-70b-instruct-fp8"}]))

        registry.discover_models()

        assert registry.discovery_error is None

    def test_health_reports_a_degraded_registry(self, client, monkeypatch):
        import app.main as main

        registry = _registry(StubModelClient(error="401 Unauthorized"))
        registry.discover_models()
        monkeypatch.setattr(main, "model_registry", registry)

        payload = client.get("/health").json()

        assert payload["status"] == "degraded"
        assert "401" in payload["model_discovery_error"]


class TestHttpRetryConfiguration:
    """Retries must cover the POST calls they were written for."""

    def test_chat_completions_are_retried(self):
        session = VultrClient(api_key="test-key").session

        retries = session.get_adapter("https://api.vultrinference.com/v1").max_retries

        # urllib3 defaults to idempotent methods only, which excludes POST.
        assert "POST" in retries.allowed_methods
        assert 429 in retries.status_forcelist
        assert 500 in retries.status_forcelist
        assert retries.total >= 1


def _question(question_id):
    return Question(
        id=question_id,
        coverage_key=CoverageKey.FEATURES,
        priority=0.5,
        text="What matters most?",
        options=[QuestionOption(id="A", text="Option A", effect="narrow")],
    )


def _pair(question_id="Q1", free_text="A thorough answer with real context."):
    return QAPair(
        question=_question(question_id),
        answer=Answer(question_id=question_id, choice_id="A", free_text=free_text),
    )


def _thread(questions_since_reflection, qa_history=(), coverage=None):
    return ThreadState(
        id=THREAD_ID,
        session_id="s1",
        type=ThreadType.KICKOFF,
        title="Kickoff",
        questions_since_reflection=questions_since_reflection,
        qa_history=list(qa_history),
        coverage=coverage or CoverageMap(),
        created_at=NOW,
        last_updated=NOW,
    )


class TestReflectionTriggers:
    """Triggering is deterministic, so the same thread always answers the same."""

    @pytest.fixture
    def service(self):
        return ReflectionService(StubModelClient(), _registry())

    def test_too_early(self, service):
        assert service.should_inject_reflection(_thread(2)) is False

    def test_max_interval_forces_reflection(self, service):
        assert service.should_inject_reflection(_thread(12)) is True

    def test_short_answers_suggest_confusion(self, service):
        short = [_pair("Q1", ""), _pair("Q2", "ok")]
        assert service.should_inject_reflection(_thread(5, short)) is True

    def test_detailed_answers_do_not_trigger(self, service):
        detailed = [_pair(f"Q{i}") for i in range(3)]
        assert service.should_inject_reflection(_thread(5, detailed)) is False

    def test_large_coverage_imbalance_triggers(self, service):
        detailed = [_pair(f"Q{i}") for i in range(3)]
        imbalanced = CoverageMap(features=90.0)
        assert service.should_inject_reflection(_thread(6, detailed, imbalanced)) is True

    def test_repeated_calls_agree(self, service):
        """The old implementation rolled dice, so this is a regression guard."""
        thread = _thread(7, [_pair(f"Q{i}") for i in range(3)], CoverageMap(features=80.0))
        results = {service.should_inject_reflection(thread) for _ in range(10)}
        assert len(results) == 1


def _seed_session(storage, session_id="s1"):
    session = SessionData(
        session_id=session_id,
        idea_brief=IdeaBrief(raw_input="An idea", normalized_summary="An idea"),
        threads={
            THREAD_ID: ThreadState(
                id=THREAD_ID,
                session_id=session_id,
                type=ThreadType.KICKOFF,
                title="Kickoff",
                created_at=NOW,
                last_updated=NOW,
            )
        },
        active_thread_id=THREAD_ID,
        created_at=NOW,
        updated_at=NOW,
    )
    storage.save(session_id, session)
    return session


class TestSessionWriteLocking:
    """
    Session mutations are read-modify-write cycles. Serializing them per
    session is what stops concurrent requests from clobbering each other - with
    serializing storage such as FileStorage, an unlocked run loses most writes.
    """

    def test_concurrent_notes_are_all_persisted(self, tmp_path):
        storage = FileStorage(str(tmp_path / "sessions"))
        manager = SessionManager(StubModelClient(), _registry(), storage=storage)
        session = _seed_session(storage)

        writes_per_thread = 10
        errors = []

        def add_notes():
            try:
                for i in range(writes_per_thread):
                    manager.add_plan_note(
                        session_id=session.session_id,
                        thread_id=THREAD_ID,
                        raw=f"note {i}",
                        distilled="distilled",
                        tags=["insight:test"],
                    )
            except Exception as e:  # pragma: no cover - surfaced by the assert
                errors.append(e)

        workers = [threading.Thread(target=add_notes) for _ in range(4)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()

        assert not errors, errors
        stored = storage.get(session.session_id)
        assert len(stored.threads[THREAD_ID].notes) == 4 * writes_per_thread


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
