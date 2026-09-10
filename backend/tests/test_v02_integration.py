"""
Integration tests for InfiniteQ v0.2 features.

Runs the real app against a fake LLM client (see conftest.py), so the whole
request path is exercised without network access or a Vultr key.

Covers:
1. Session creation with profiles
2. Thread management
3. Answer submission and coverage
4. Reflection pulses
5. Plan synthesis with views and execution bundles
6. Error handling
"""
import pytest

API = "/api/v1"


def _answer_payload(questions, free_text="A detailed answer with real context."):
    """Build answers matching whatever questions the engine actually returned."""
    return {
        "answers": [
            {
                "question_id": q["id"],
                "choice_id": q["options"][0]["id"],
                "free_text": free_text,
            }
            for q in questions
        ]
    }


class TestSessionCreationWithProfiles:
    """Session creation with v0.2 profiles."""

    def test_create_session_with_full_profiles(self, client):
        resp = client.post(f"{API}/session", json={
            "idea": "Build a SaaS tool for AI-powered code reviews",
            "mode": "kickoff",
            "project_profile": {
                "type": "saas",
                "sophistication": "mvp",
                "team_size": "solo",
                "tech_constraints": ["python", "fastapi", "react"],
                "timeline": "1-3_months",
                "budget_band": "1k-10k",
                "non_goals": ["mobile apps", "blockchain"],
            },
            "persona_profile": {
                "role": "founder_technical",
                "comfort_with_tech": "high",
                "comfort_with_business": "medium",
                "preferred_depth": "deep",
            },
        })

        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert data["session_id"]
        assert data["thread_id"]
        assert len(data["first_questions"]) > 0

        # Profiles echoed back as stored
        assert data["project_profile"]["type"] == "saas"
        assert data["project_profile"]["non_goals"] == ["mobile apps", "blockchain"]
        assert data["persona_profile"]["role"] == "founder_technical"
        assert data["persona_profile"]["preferred_depth"] == "deep"

    def test_create_session_minimal_uses_defaults(self, client):
        resp = client.post(f"{API}/session", json={"idea": "Simple todo app"})

        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Schema defaults apply when profiles are omitted
        assert data["project_profile"]["type"] == "saas"
        assert data["project_profile"]["team_size"] == "solo"
        assert data["persona_profile"]["comfort_with_tech"] == "medium"

    def test_profiles_reach_the_model(self, client, fake_client):
        """Profiles must actually be sent to the question generator, not just stored."""
        client.post(f"{API}/session", json={
            "idea": "E-commerce platform",
            "project_profile": {"tech_constraints": ["no_java"], "non_goals": ["crypto_payments"]},
        })

        qgen = [c for c in fake_client.calls if "panel of expert project designers" in c["system"]]
        assert qgen, "question generation was never called"
        assert "no_java" in qgen[0]["user"]
        assert "crypto_payments" in qgen[0]["user"]

    def test_invalid_profile_enum_rejected(self, client):
        resp = client.post(f"{API}/session", json={
            "idea": "Something",
            "persona_profile": {"comfort_with_tech": "extremely_high"},
        })
        assert resp.status_code == 422


class TestThreadManagement:
    """Thread creation and management."""

    def test_create_architecture_thread(self, client, session):
        session_id, _ = session
        resp = client.post(f"{API}/session/{session_id}/threads", json={
            "type": "architecture",
            "title": "Deep dive on backend architecture",
            "root_prompt": "Let's explore scalability requirements",
        })

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["thread"]["type"] == "architecture"
        assert data["thread"]["title"] == "Deep dive on backend architecture"
        assert len(data["first_questions"]) > 0

    def test_list_threads(self, client, session):
        session_id, initial_thread_id = session
        client.post(f"{API}/session/{session_id}/threads",
                    json={"type": "risk", "title": "Risk assessment"})

        resp = client.get(f"{API}/session/{session_id}/threads")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert len(data["threads"]) == 2  # kickoff + risk
        assert data["active_thread_id"] == initial_thread_id

    def test_activate_thread(self, client, session):
        session_id, _ = session
        created = client.post(f"{API}/session/{session_id}/threads",
                              json={"type": "gtm", "title": "Go-to-market strategy"})
        new_thread_id = created.json()["thread"]["id"]

        resp = client.post(f"{API}/session/{session_id}/threads/{new_thread_id}/activate")
        assert resp.status_code == 200, resp.text
        assert resp.json()["thread_id"] == new_thread_id

        # The switch is persisted, not just returned
        listing = client.get(f"{API}/session/{session_id}/threads").json()
        assert listing["active_thread_id"] == new_thread_id

    def test_update_thread_title(self, client, session):
        session_id, thread_id = session
        resp = client.patch(f"{API}/session/{session_id}/threads/{thread_id}",
                            json={"title": "Renamed thread"})
        assert resp.status_code == 200, resp.text

        listing = client.get(f"{API}/session/{session_id}/threads").json()
        titles = [t["title"] for t in listing["threads"]]
        assert "Renamed thread" in titles


class TestAnswerSubmission:
    """Answering questions advances plan state and coverage."""

    def test_thread_answers_advance_coverage(self, client, session):
        session_id, _ = session
        created = client.post(f"{API}/session/{session_id}/threads", json={
            "type": "architecture", "title": "Arch",
        }).json()
        arch_id = created["thread"]["id"]

        resp = client.post(f"{API}/session/{session_id}/threads/{arch_id}/answer",
                           json=_answer_payload(created["first_questions"]))
        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert "next_questions" in data
        assert "thread_coverage" in data
        assert "phase_coverage" in data

        # Answering should move at least one coverage dimension off zero
        assert sum(data["thread_coverage"].values()) > 0

    def test_answer_unknown_session_404(self, client):
        resp = client.post(f"{API}/session/does-not-exist/threads/nope/answer",
                           json={"answers": []})
        assert resp.status_code == 404


class TestReflectionPulse:
    """Reflection pulse capture and distillation."""

    def test_submit_reflection(self, client, session):
        session_id, thread_id = session
        resp = client.post(f"{API}/session/{session_id}/threads/{thread_id}/reflect", json={
            "text": (
                "I'm worried about HIPAA compliance. Patient data must be encrypted "
                "at rest and in transit. The UI also needs to be dead simple."
            ),
        })

        assert resp.status_code == 200, resp.text
        note = resp.json()["note"]

        assert note["raw"]
        assert note["distilled"]
        assert len(note["tags"]) > 0
        assert any(t.startswith(("constraint:", "risk:", "decision:")) for t in note["tags"])

    def test_reflection_requires_text(self, client, session):
        session_id, thread_id = session
        resp = client.post(f"{API}/session/{session_id}/threads/{thread_id}/reflect",
                           json={"text": ""})
        assert resp.status_code == 422

    def test_get_thread_insights(self, client, session):
        session_id, thread_id = session
        client.post(f"{API}/session/{session_id}/threads/{thread_id}/reflect",
                    json={"text": "Budget constraint: only $5k for initial development."})

        resp = client.get(f"{API}/session/{session_id}/threads/{thread_id}/insights")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert data["note_count"] == 1
        assert len(data["notes"]) == 1
        # Tags are grouped into a human-readable summary
        assert "Constraints" in data["insights"]


class TestPlanSynthesisWithViews:
    """Plan synthesis with view profiles and execution bundles."""

    def test_synthesize_builder_view(self, client, session):
        session_id, _ = session
        resp = client.post(f"{API}/session/{session_id}/finish", json={
            "view_profile": "builder",
            "include_execution_bundle": False,
        })

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["json_plan"]
        assert len(data["markdown_brief"]) > 100
        assert data.get("execution_bundle") is None

    def test_synthesize_with_execution_bundle(self, client, session):
        session_id, _ = session
        resp = client.post(f"{API}/session/{session_id}/finish", json={
            "view_profile": "agent_spec",
            "include_execution_bundle": True,
        })

        assert resp.status_code == 200, resp.text
        bundle = resp.json()["execution_bundle"]
        assert bundle is not None

        scaffold = bundle["repo_scaffold"]
        assert scaffold["language"] in ["ts", "py", "go", "rust", "java"]
        assert scaffold["structure"]

        assert len(bundle["tasks"]) > 0
        task = bundle["tasks"][0]
        assert task["title"]
        assert task["phase"] in ["prototype", "v1", "scale_up", "v2_plus"]
        assert task["acceptance_criteria"]

        assert len(bundle["prompts"]) > 0
        assert bundle["prompts"][0]["target"] in ["cursor", "claudecode", "windsurf", "generic"]
        assert len(bundle["prompts"][0]["prompt"]) > 50

    def test_view_profile_reaches_synthesizer(self, client, session, fake_client):
        session_id, _ = session
        client.post(f"{API}/session/{session_id}/finish",
                    json={"view_profile": "investor", "include_execution_bundle": False})

        synth = [c for c in fake_client.calls if "build-ready project brief" in c["system"]]
        assert synth, "synthesis was never called"
        assert "investor" in synth[-1]["user"]

    def test_finish_unknown_session_404(self, client):
        resp = client.post(f"{API}/session/does-not-exist/finish", json={})
        assert resp.status_code == 404


class TestEndToEndFlow:
    """A complete v0.2 planning session."""

    def test_complete_planning_session(self, client):
        # 1. Create a session with profiles
        created = client.post(f"{API}/session", json={
            "idea": "SaaS platform for restaurant reservation management",
            "mode": "kickoff",
            "project_profile": {
                "type": "saas",
                "sophistication": "production",
                "team_size": "4-10",
                "tech_constraints": ["python", "react", "postgresql"],
                "timeline": "6+_months",
                "budget_band": "100k+",
                "non_goals": ["mobile apps in v1"],
            },
            "persona_profile": {
                "role": "tech_lead",
                "comfort_with_tech": "high",
                "comfort_with_business": "high",
                "preferred_depth": "deep",
            },
        })
        assert created.status_code == 200, created.text
        session_id = created.json()["session_id"]

        # 2. Open an architecture thread and answer its questions
        arch = client.post(f"{API}/session/{session_id}/threads", json={
            "type": "architecture", "title": "Backend & data architecture",
        }).json()
        arch_id = arch["thread"]["id"]

        client.post(f"{API}/session/{session_id}/threads/{arch_id}/activate")
        answered = client.post(
            f"{API}/session/{session_id}/threads/{arch_id}/answer",
            json=_answer_payload(arch["first_questions"],
                                 "Need to scale reservation processing independently."),
        )
        assert answered.status_code == 200, answered.text

        # 3. Capture a reflection
        reflected = client.post(f"{API}/session/{session_id}/threads/{arch_id}/reflect", json={
            "text": "Must handle 10k concurrent reservations at peak. "
                    "Real-time availability is non-negotiable.",
        })
        assert reflected.status_code == 200, reflected.text
        assert reflected.json()["note"]["tags"]

        # 4. Add a risk thread
        assert client.post(f"{API}/session/{session_id}/threads", json={
            "type": "risk", "title": "Technical and business risks",
        }).status_code == 200

        # 5. All three threads present
        threads = client.get(f"{API}/session/{session_id}/threads").json()["threads"]
        assert len(threads) == 3

        # 6. Status reflects the work
        status = client.get(f"{API}/session/{session_id}/status")
        assert status.status_code == 200, status.text

        # 7. Synthesize with an execution bundle
        final = client.post(f"{API}/session/{session_id}/finish", json={
            "view_profile": "builder",
            "include_execution_bundle": True,
        })
        assert final.status_code == 200, final.text
        data = final.json()

        assert data["json_plan"]
        assert data["markdown_brief"]
        bundle = data["execution_bundle"]
        assert bundle["repo_scaffold"]["language"] == "py"  # FastAPI backend in the plan
        assert len(bundle["tasks"]) >= 2
        assert len(bundle["prompts"]) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
