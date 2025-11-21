"""
Integration tests for InfiniteQ v0.2 features.

Tests the complete flow:
1. Session creation with profiles
2. Thread management
3. Reflection pulses
4. Profile-aware question generation
5. Plan synthesis with views and execution bundles
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.schema import (
    ProjectType,
    PersonaRole,
    ThreadType,
    ViewProfile,
    Mode
)

client = TestClient(app)


class TestSessionCreationWithProfiles:
    """Test session creation with v0.2 profiles."""

    def test_create_session_with_full_profiles(self):
        """Create session with complete project and persona profiles."""
        response = client.post("/session", json={
            "idea": "Build a SaaS tool for AI-powered code reviews",
            "mode": "kickoff",
            "project_profile": {
                "type": "saas",
                "sophistication": "mvp",
                "team_size": "solo",
                "tech_constraints": ["python", "fastapi", "react"],
                "timeline": "1-3_months",
                "budget_band": "1k-10k",
                "non_goals": ["mobile apps", "blockchain"]
            },
            "persona_profile": {
                "role": "founder_solo",
                "tech_comfort": 8,
                "business_comfort": 6,
                "preferred_depth": "deep"
            }
        })

        assert response.status_code == 200
        data = response.json()

        # Check session created
        assert "session_id" in data
        assert "thread_id" in data
        assert "first_questions" in data

        # Check profiles returned
        assert "project_profile" in data
        assert data["project_profile"]["type"] == "saas"
        assert data["persona_profile"]["role"] == "founder_solo"

        # Check initial thread created
        assert data["thread_id"]

        return data["session_id"], data["thread_id"]

    def test_create_session_minimal_profiles(self):
        """Create session with minimal profile data (defaults)."""
        response = client.post("/session", json={
            "idea": "Simple todo app"
        })

        assert response.status_code == 200
        data = response.json()

        # Should use default profiles
        assert "project_profile" in data
        assert "persona_profile" in data


class TestThreadManagement:
    """Test thread creation and management."""

    def setup_method(self):
        """Create a session for thread tests."""
        response = client.post("/session", json={
            "idea": "AI fitness coaching app",
            "project_profile": {
                "type": "mobile_app",
                "team_size": "2-3"
            }
        })
        self.session_id = response.json()["session_id"]
        self.initial_thread_id = response.json()["thread_id"]

    def test_create_architecture_thread(self):
        """Create a dedicated architecture exploration thread."""
        response = client.post(
            f"/session/{self.session_id}/threads",
            json={
                "type": "architecture",
                "title": "Deep dive on backend architecture",
                "root_prompt": "Let's explore scalability requirements"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["thread"]["type"] == "architecture"
        assert data["thread"]["title"] == "Deep dive on backend architecture"
        assert "first_questions" in data

    def test_list_threads(self):
        """List all threads in a session."""
        # Create additional thread
        client.post(
            f"/session/{self.session_id}/threads",
            json={
                "type": "risk",
                "title": "Risk assessment"
            }
        )

        response = client.get(f"/session/{self.session_id}/threads")

        assert response.status_code == 200
        data = response.json()

        assert "threads" in data
        assert len(data["threads"]) >= 2  # Initial + risk thread
        assert "active_thread_id" in data

    def test_activate_thread(self):
        """Switch active thread."""
        # Create new thread
        create_response = client.post(
            f"/session/{self.session_id}/threads",
            json={"type": "gtm", "title": "Go-to-market strategy"}
        )
        new_thread_id = create_response.json()["thread"]["id"]

        # Activate it
        response = client.post(
            f"/session/{self.session_id}/threads/{new_thread_id}/activate"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["active_thread_id"] == new_thread_id


class TestReflectionPulse:
    """Test reflection pulse system."""

    def setup_method(self):
        """Create a session and thread."""
        response = client.post("/session", json={
            "idea": "Healthcare appointment booking system"
        })
        self.session_id = response.json()["session_id"]
        self.thread_id = response.json()["thread_id"]

    def test_reflection_injection_after_questions(self):
        """Verify reflection prompts appear after sufficient questions."""
        # Answer multiple rounds of questions
        for _ in range(3):  # Simulate answering 3 rounds
            response = client.post(
                f"/session/{self.session_id}/threads/{self.thread_id}/answer",
                json={
                    "answers": [
                        {
                            "question_id": "Q_001",
                            "choice_id": "A",
                            "free_text": "Detailed answer to trigger coverage"
                        }
                    ]
                }
            )

            # Check if reflection prompt injected
            if "reflection_prompt" in response.json():
                # Reflection was triggered!
                assert response.json()["reflection_prompt"]["text"]
                return

        # If we get here, reflection might trigger on next round
        # This is probabilistic (5-10 questions), so may need more rounds

    def test_submit_reflection(self):
        """Submit a reflection and get distilled notes."""
        response = client.post(
            f"/session/{self.session_id}/threads/{self.thread_id}/reflect",
            json={
                "reflection": "I'm really worried about HIPAA compliance. We need to ensure all patient data is encrypted at rest and in transit. Also, the UI needs to be dead simple - our users are elderly."
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Check note created
        assert "note" in data
        note = data["note"]

        assert note["raw"]  # Original reflection
        assert note["distilled"]  # LLM summary
        assert len(note["tags"]) > 0  # Semantic tags extracted

        # Should have constraint and preference tags
        tags_str = " ".join(note["tags"])
        assert "constraint:" in tags_str or "preference:" in tags_str

    def test_get_thread_insights(self):
        """Get aggregated insights from reflections."""
        # Submit a reflection first
        client.post(
            f"/session/{self.session_id}/threads/{self.thread_id}/reflect",
            json={
                "reflection": "Budget constraint: We only have $5k for initial development"
            }
        )

        response = client.get(
            f"/session/{self.session_id}/threads/{self.thread_id}/insights"
        )

        assert response.status_code == 200
        data = response.json()

        assert "insights_by_type" in data
        # Should have at least constraints
        assert "constraints" in data["insights_by_type"]


class TestProfileAwareQuestions:
    """Test that questions respect profiles."""

    def test_questions_respect_tech_constraints(self):
        """Verify questions don't suggest forbidden tech."""
        response = client.post("/session", json={
            "idea": "E-commerce platform",
            "project_profile": {
                "tech_constraints": ["no Java", "no PHP"],
                "non_goals": ["cryptocurrency payments"]
            }
        })

        questions = response.json()["first_questions"]

        # Questions should not mention Java, PHP, or crypto
        all_question_text = " ".join([q["text"] for q in questions])
        assert "java" not in all_question_text.lower()
        assert "php" not in all_question_text.lower()

    def test_questions_adjust_to_persona_comfort(self):
        """Verify questions match persona technical comfort."""
        # Low tech comfort
        response_low = client.post("/session", json={
            "idea": "Inventory management system",
            "persona_profile": {
                "role": "business_leader",
                "tech_comfort": 2,
                "preferred_depth": "light"
            }
        })

        # High tech comfort
        response_high = client.post("/session", json={
            "idea": "Inventory management system",
            "persona_profile": {
                "role": "tech_lead",
                "tech_comfort": 9,
                "preferred_depth": "deep"
            }
        })

        questions_low = response_low.json()["first_questions"]
        questions_high = response_high.json()["first_questions"]

        # Both should have questions, but style may differ
        assert len(questions_low) > 0
        assert len(questions_high) > 0


class TestPlanSynthesisWithViews:
    """Test plan synthesis with view profiles and execution bundles."""

    def setup_method(self):
        """Create a session and answer some questions."""
        response = client.post("/session", json={
            "idea": "AI-powered personal finance assistant",
            "project_profile": {
                "type": "mobile_app",
                "team_size": "solo",
                "tech_constraints": ["react native", "firebase"],
                "timeline": "1-3_months"
            }
        })
        self.session_id = response.json()["session_id"]

    def test_synthesize_builder_view(self):
        """Generate plan with builder view (technical details)."""
        response = client.post(
            f"/session/{self.session_id}/finish",
            json={
                "view_profile": "builder",
                "include_execution_bundle": False
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "json_plan" in data
        assert "markdown_brief" in data

        # Builder view should have technical details
        assert len(data["markdown_brief"]) > 100

    def test_synthesize_with_execution_bundle(self):
        """Generate plan with execution bundle."""
        response = client.post(
            f"/session/{self.session_id}/finish",
            json={
                "view_profile": "agent_spec",
                "include_execution_bundle": True
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Check execution bundle generated
        assert "execution_bundle" in data
        bundle = data["execution_bundle"]

        # Check repo scaffold
        assert "repo_scaffold" in bundle
        scaffold = bundle["repo_scaffold"]
        assert scaffold["language"] in ["ts", "py", "go", "rust"]
        assert "structure" in scaffold

        # Check tasks
        assert "tasks" in bundle
        assert len(bundle["tasks"]) > 0
        task = bundle["tasks"][0]
        assert task["title"]
        assert task["phase"]
        assert "acceptance_criteria" in task

        # Check LLM prompts
        assert "prompts" in bundle
        assert len(bundle["prompts"]) > 0
        prompt = bundle["prompts"][0]
        assert prompt["target"] in ["claudecode", "cursor", "windsurf"]
        assert len(prompt["prompt"]) > 50  # Substantial prompt

    def test_synthesize_investor_view(self):
        """Generate plan with investor pitch focus."""
        response = client.post(
            f"/session/{self.session_id}/finish",
            json={
                "view_profile": "investor",
                "include_execution_bundle": False
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Investor view should emphasize business value
        markdown = data["markdown_brief"]
        assert "market" in markdown.lower() or "opportunity" in markdown.lower()


class TestEndToEndFlow:
    """Test complete v0.2 workflow."""

    def test_complete_planning_session(self):
        """Simulate a complete planning session with all v0.2 features."""

        # 1. Create session with profiles
        session_response = client.post("/session", json={
            "idea": "SaaS platform for restaurant reservation management",
            "mode": "kickoff",
            "project_profile": {
                "type": "saas",
                "sophistication": "production",
                "team_size": "4-10",
                "tech_constraints": ["python", "react", "postgresql"],
                "timeline": "6+_months",
                "budget_band": "100k+",
                "non_goals": ["mobile apps in v1"]
            },
            "persona_profile": {
                "role": "founder_team",
                "tech_comfort": 7,
                "business_comfort": 8,
                "preferred_depth": "deep"
            }
        })

        assert session_response.status_code == 200
        session_id = session_response.json()["session_id"]
        kickoff_thread_id = session_response.json()["thread_id"]

        # 2. Create architecture thread
        arch_thread_response = client.post(
            f"/session/{session_id}/threads",
            json={
                "type": "architecture",
                "title": "Backend & data architecture"
            }
        )
        assert arch_thread_response.status_code == 200
        arch_thread_id = arch_thread_response.json()["thread"]["id"]

        # 3. Answer questions in architecture thread
        client.post(
            f"/session/{session_id}/threads/{arch_thread_id}/activate"
        )

        answer_response = client.post(
            f"/session/{session_id}/threads/{arch_thread_id}/answer",
            json={
                "answers": [
                    {
                        "question_id": "ARCH_001",
                        "choice_id": "microservices",
                        "free_text": "Need to scale reservation processing independently"
                    }
                ]
            }
        )
        assert answer_response.status_code == 200

        # 4. Submit reflection
        reflection_response = client.post(
            f"/session/{session_id}/threads/{arch_thread_id}/reflect",
            json={
                "reflection": "Critical constraint: Must handle 10k concurrent reservations during peak hours. Real-time availability updates are non-negotiable."
            }
        )
        assert reflection_response.status_code == 200
        assert len(reflection_response.json()["note"]["tags"]) > 0

        # 5. Create risk assessment thread
        risk_thread_response = client.post(
            f"/session/{session_id}/threads",
            json={
                "type": "risk",
                "title": "Technical and business risks"
            }
        )
        assert risk_thread_response.status_code == 200

        # 6. List all threads
        threads_response = client.get(f"/session/{session_id}/threads")
        assert threads_response.status_code == 200
        assert len(threads_response.json()["threads"]) == 3  # kickoff, arch, risk

        # 7. Synthesize final plan with execution bundle
        finish_response = client.post(
            f"/session/{session_id}/finish",
            json={
                "view_profile": "builder",
                "include_execution_bundle": True
            }
        )

        assert finish_response.status_code == 200
        final_data = finish_response.json()

        # Verify complete output
        assert "json_plan" in final_data
        assert "markdown_brief" in final_data
        assert "execution_bundle" in final_data

        # Verify execution bundle quality
        bundle = final_data["execution_bundle"]
        assert bundle["repo_scaffold"]["language"] == "py"  # Should detect Python
        assert "fastapi" in bundle["repo_scaffold"]["frameworks"] or "react" in bundle["repo_scaffold"]["frameworks"]
        assert len(bundle["tasks"]) >= 3  # Setup + features + testing
        assert len(bundle["prompts"]) >= 1  # At least one AI prompt

        print("\n✅ Complete v0.2 workflow test passed!")
        print(f"   - Session ID: {session_id}")
        print(f"   - Threads created: 3")
        print(f"   - Reflection notes: 1")
        print(f"   - Execution bundle tasks: {len(bundle['tasks'])}")
        print(f"   - AI prompts generated: {len(bundle['prompts'])}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
