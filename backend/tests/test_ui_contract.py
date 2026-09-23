"""
The API contract the React UI depends on.

The UI and the backend drifted apart once already: the idea form sent
``mode: "software"`` while the schema only accepts kickoff/deep_dive/sanity_check,
so creating a session returned 422 and the app could not be used at all.

These tests pin the payloads the UI actually sends, and compare the frontend's
enum definitions against the backend schema.
"""
import re
from pathlib import Path

import pytest

from app.models.schema import (
    CoverageKey,
    Mode,
    PersonaRole,
    Phase,
    ProjectType,
    ThreadType,
    ViewProfile,
)

API = "/api/v1"

TYPES_FILE = Path(__file__).resolve().parents[2] / "frontend" / "src" / "types" / "index.ts"

# The values the idea form offers (frontend/src/components/IdeaInput.tsx).
UI_MODES = ["kickoff", "deep_dive", "sanity_check"]

# What the profile form produces (frontend/src/components/v02/ProfileForms.tsx).
UI_PROJECT_PROFILE = {
    "type": "saas",
    "sophistication": "mvp",
    "team_size": "solo",
    "tech_constraints": ["python", "react"],
    "timeline": "1-4_weeks",
    "budget_band": "1k-10k",
    "non_goals": ["mobile apps"],
}

UI_PERSONA_PROFILE = {
    "role": "founder_technical",
    "comfort_with_tech": "high",
    "comfort_with_business": "medium",
    "preferred_depth": "balanced",
}


def _frontend_enum(name: str) -> set[str]:
    """Extract the string values of an enum from the frontend types file."""
    match = re.search(rf"export enum {name} \{{(.*?)\n\}}", TYPES_FILE.read_text(), re.S)
    assert match, f"enum {name} not found in {TYPES_FILE}"
    return set(re.findall(r'=\s*"([^"]+)"', match.group(1)))


@pytest.mark.parametrize("name,backend_enum", [
    ("CoverageKey", CoverageKey),
    ("Mode", Mode),
    ("Phase", Phase),
    ("PersonaRole", PersonaRole),
    ("ProjectType", ProjectType),
    ("ThreadType", ThreadType),
    ("ViewProfile", ViewProfile),
])
def test_frontend_enums_match_the_backend(name, backend_enum):
    """A frontend enum that drifts from the schema means 422s in the browser."""
    if not TYPES_FILE.exists():
        pytest.skip("frontend sources not present")

    frontend_values = _frontend_enum(name)
    backend_values = {member.value for member in backend_enum}

    assert frontend_values == backend_values, (
        f"{name} drifted: only in UI {frontend_values - backend_values}, "
        f"only in backend {backend_values - frontend_values}"
    )


class TestUIPayloads:
    """Payload shapes taken from the components that send them."""

    def test_every_mode_the_ui_offers_is_accepted(self, client):
        for mode in UI_MODES:
            resp = client.post(f"{API}/session", json={"idea": "A tool", "mode": mode})
            assert resp.status_code == 200, f"{mode} rejected: {resp.text}"

    def test_the_old_broken_mode_is_rejected(self, client):
        """Regression guard for the drift that broke session creation."""
        resp = client.post(f"{API}/session", json={"idea": "A tool", "mode": "software"})
        assert resp.status_code == 422

    def test_profile_form_payload_is_accepted_and_echoed(self, client):
        resp = client.post(f"{API}/session", json={
            "idea": "A tool for tracking water intake",
            "mode": "kickoff",
            "project_profile": UI_PROJECT_PROFILE,
            "persona_profile": UI_PERSONA_PROFILE,
        })

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["project_profile"]["non_goals"] == ["mobile apps"]
        assert body["persona_profile"]["comfort_with_tech"] == "high"
        assert body["persona_profile"]["preferred_depth"] == "balanced"

    def test_reflection_payload_uses_text(self, client):
        created = client.post(f"{API}/session", json={"idea": "A tool"}).json()

        resp = client.post(
            f"{API}/session/{created['session_id']}/threads/{created['thread_id']}/reflect",
            json={"text": "Budget is capped at $5k for v1."},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["note"]["tags"]

        # The old (documented) shape is what used to be sent, and it is invalid.
        old_shape = client.post(
            f"{API}/session/{created['session_id']}/threads/{created['thread_id']}/reflect",
            json={"reflection": "Budget is capped at $5k for v1."},
        )
        assert old_shape.status_code == 422

    def test_finish_payload_returns_the_bundle(self, client):
        created = client.post(f"{API}/session", json={"idea": "A tool"}).json()

        resp = client.post(
            f"{API}/session/{created['session_id']}/finish",
            json={"view_profile": "agent_spec", "include_execution_bundle": True},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["markdown_brief"]
        assert body["execution_bundle"]["repo_scaffold"]["language"]
        assert body["execution_bundle"]["tasks"]
        assert body["execution_bundle"]["prompts"]

    def test_thread_list_exposes_what_the_sidebar_renders(self, client):
        """The sidebar reads pending questions, coverage and notes off the list."""
        created = client.post(f"{API}/session", json={"idea": "A tool"}).json()

        listing = client.get(f"{API}/session/{created['session_id']}/threads").json()

        assert listing["active_thread_id"] == created["thread_id"]
        thread = listing["threads"][0]
        for key in (
            "id", "type", "title", "coverage", "phase_coverage",
            "questions_asked", "notes", "pending_questions", "active",
        ):
            assert key in thread, f"the UI reads thread.{key}"
        assert thread["pending_questions"], "the UI renders these as question cards"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
