"""
Shared test fixtures for InfiniteQ.

The only external I/O in the backend is VultrClient, so tests swap in a fake
one. Everything else - session manager, routes, reducer, synthesizer - runs for
real, which keeps the suite deterministic and offline while still exercising
the actual code paths.
"""
import os
import pytest

# Sessions must not be written to disk during tests.
os.environ.setdefault("STORAGE_TYPE", "memory")
os.environ.setdefault("VULTR_INFERENCE_API_KEY", "test-key")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.api.routes import init_routes, limiter  # noqa: E402
from app.services.model_registry import ModelRegistry  # noqa: E402
from app.services.session_manager import SessionManager  # noqa: E402
from app.services.question_engine import QuestionEngine  # noqa: E402
from app.services.plan_reducer import PlanReducer  # noqa: E402
from app.services.plan_synthesizer import PlanSynthesizer  # noqa: E402
from app.services.reflection_service import ReflectionService  # noqa: E402
from app.services.session_storage import InMemoryStorage  # noqa: E402


# Ids chosen so ModelRegistry populates every role. Note it checks synthesis
# before strategy, so a "kimi-k2-*" id lands in synthesis, not strategy.
FAKE_MODELS = [
    {"id": "deepseek-r1-distill-qwen-32b"},   # reasoning
    {"id": "qwen2.5-coder-32b-instruct"},     # code_tech
    {"id": "llama-3.3-70b-instruct-fp8"},     # synthesis
    {"id": "kimi-latest"},                    # strategy
]


def _questions(prefix="Q"):
    """Two schema-valid questions covering different dimensions."""
    return {
        "questions": [
            {
                "id": f"{prefix}_001",
                "coverage_key": "features",
                "phase": "v1",
                "priority": 0.9,
                "text": "Which feature cluster matters most for v1?",
                "options": [
                    {"id": "A", "text": "Core workflows only", "effect": "narrow_scope"},
                    {"id": "B", "text": "Core plus analytics", "effect": "add_analytics"},
                    {"id": "OTHER", "text": "Other (please specify)", "effect": "custom"},
                ],
            },
            {
                "id": f"{prefix}_002",
                "coverage_key": "architecture",
                "phase": "prototype",
                "priority": 0.8,
                "text": "How should the backend be structured?",
                "options": [
                    {"id": "A", "text": "Single service", "effect": "monolith"},
                    {"id": "B", "text": "Split services", "effect": "microservices"},
                    {"id": "OTHER", "text": "Other (please specify)", "effect": "custom"},
                ],
            },
        ]
    }


def _plan_state():
    """A populated plan the synthesizer can work from."""
    return {
        "meta": {"title": "Test Project", "type": "software", "priority": "", "owner": ""},
        "problem": {"summary": "A test problem worth solving", "pain_points": ["slow", "manual"]},
        "users": [{"role": "operator", "needs": ["speed"], "environment": "desktop"}],
        "constraints": {"time": "4 weeks", "budget": "$5k", "compliance": [], "technical": []},
        "features": [
            {"id": "F1", "title": "User authentication", "must_have": True, "notes": "OAuth"},
            {"id": "F2", "title": "Reporting", "must_have": False, "notes": ""},
        ],
        "architecture": {
            "frontend": "React", "backend": "FastAPI (Python)", "data": "Postgres",
            "integrations": [], "infrastructure": "",
        },
        "milestones": [{"name": "MVP", "duration_weeks": 4, "goals": ["ship core"]}],
        "risks": [{"risk": "scope creep", "mitigation": "freeze v1 scope"}],
        "open_questions": [],
    }


class FakeVultrClient:
    """
    Stand-in for VultrClient that returns canned, schema-valid responses.

    Dispatches on the system prompt so each service gets the shape it expects.
    Records calls so tests can assert on what was sent to the model.
    """

    def __init__(self):
        self.calls = []

    def list_models(self):
        return list(FAKE_MODELS)

    def chat_completion(self, model, messages, **kwargs):
        return "canned completion"

    def chat_completion_json(self, model, messages, **kwargs):
        system = next(
            (m["content"] for m in messages if m.get("role") == "system"), ""
        )
        user = next(
            (m["content"] for m in messages if m.get("role") == "user"), ""
        )
        self.calls.append({"model": model, "system": system, "user": user})

        if "normalizing a user's initial project idea" in system:
            return {
                "normalized_summary": "A normalized description of the idea",
                "inferred_type": "software",
                "key_entities": ["user", "system"],
                "initial_scope": "Focused MVP",
            }

        if "extracts actionable insights" in system:
            return {
                "distilled": "Budget is limited, so prefer free tiers.",
                "tags": ["constraint:budget", "decision:free_tier", "risk:scope_creep"],
            }

        if "selecting the best next questions" in system:
            return _questions("AGG")

        if "panel of expert project designers" in system:
            return _questions("GEN")

        if "maintain a canonical JSON plan" in system:
            return _plan_state()

        if "build-ready project brief" in system:
            return {
                "json_plan": _plan_state(),
                "markdown_brief": (
                    "# Test Project\n\n## Problem & Context\nA test problem.\n\n"
                    "## Market Opportunity\nA large market opportunity.\n\n"
                    "## Recommended Architecture\nFastAPI backend, React frontend.\n"
                ),
            }

        # Unknown prompt: fail loudly rather than silently returning junk.
        raise AssertionError(f"FakeVultrClient got an unrecognized system prompt: {system[:120]!r}")


@pytest.fixture
def fake_client():
    """The fake LLM client, so tests can inspect what was sent."""
    return FakeVultrClient()


@pytest.fixture
def client(fake_client):
    """
    TestClient with all services wired to the fake LLM client.

    app.main's lifespan would build real services and call the live API, so the
    routes are initialized directly here and the lifespan is bypassed.
    """
    # Rate limits are per-IP and every test shares one client address, so a
    # full run would trip the 10/minute session limit. Disabled here to keep
    # tests order-independent; see test_rate_limiting.py for its own coverage.
    limiter.enabled = False

    registry = ModelRegistry(fake_client)
    registry.discover_models()

    session_manager = SessionManager(fake_client, registry, storage=InMemoryStorage())
    init_routes(
        session_manager=session_manager,
        question_engine=QuestionEngine(fake_client, registry),
        plan_reducer=PlanReducer(fake_client, registry),
        plan_synthesizer=PlanSynthesizer(fake_client, registry),
        reflection_service=ReflectionService(fake_client, registry),
    )

    # TestClient(...) as a plain object skips lifespan startup.
    return TestClient(app)


@pytest.fixture
def session(client):
    """A created session; yields (session_id, thread_id)."""
    resp = client.post("/api/v1/session", json={
        "idea": "A SaaS tool for managing building receiverships",
        "mode": "kickoff",
        "project_profile": {
            "type": "saas",
            "sophistication": "mvp",
            "team_size": "solo",
            "tech_constraints": ["python", "react"],
            "timeline": "1-3_months",
            "budget_band": "1k-10k",
            "non_goals": ["mobile apps"],
        },
        "persona_profile": {
            "role": "founder_technical",
            "comfort_with_tech": "high",
            "comfort_with_business": "medium",
            "preferred_depth": "deep",
        },
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    return body["session_id"], body["thread_id"]
