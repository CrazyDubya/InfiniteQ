"""
Tests for execution bundle generation.

The synthesizer prefers the LLM-driven IntelligentBundleGenerator and only
falls back to its built-in templates when generation fails, so finishing a
session never breaks on a bad model response.

The tell for "which path produced this bundle?" is the fake model's scaffold,
which contains a ``celery`` framework the template fallbacks never emit.
"""
import pytest

API = "/api/v1"

# Substrings unique to the three prompts IntelligentBundleGenerator sends.
BUNDLE_GENERATION_PROMPTS = (
    "expert software architect",
    "technical project manager",
    "writing prompts for AI coding assistants",
)


def _session_id(client):
    resp = client.post(f"{API}/session", json={"idea": "Reservation platform for restaurants"})
    assert resp.status_code == 200, resp.text
    return resp.json()["session_id"]


def _finish(client, session_id, view_profile="agent_spec"):
    resp = client.post(
        f"{API}/session/{session_id}/finish",
        json={"view_profile": view_profile, "include_execution_bundle": True},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestIntelligentBundle:
    """Bundles are generated from the plan, not from static templates."""

    def test_bundle_comes_from_the_model(self, client):
        bundle = _finish(client, _session_id(client))["execution_bundle"]

        assert "celery" in bundle["repo_scaffold"]["frameworks"]
        assert bundle["tasks"][0]["title"] == "Scaffold the monorepo"
        assert bundle["prompts"][0]["title"] == "Bootstrap the monorepo"
        assert bundle["prompts"][0]["target"] == "claudecode"

    def test_scaffold_tasks_and_prompts_are_all_generated(self, client, fake_client):
        _finish(client, _session_id(client))

        generated = [
            call for call in fake_client.calls
            if any(prompt in call["user"] for prompt in BUNDLE_GENERATION_PROMPTS)
        ]
        assert len(generated) == len(BUNDLE_GENERATION_PROMPTS)

    def test_bundle_degrades_gracefully_to_the_fallbacks(self, client, fake_client, monkeypatch):
        """A dead model must still produce a usable bundle, not a 500."""
        original = fake_client.chat_completion_json

        def failing(model, messages, **kwargs):
            blob = " ".join(m.get("content", "") for m in messages)
            if any(prompt in blob for prompt in BUNDLE_GENERATION_PROMPTS):
                raise RuntimeError("model unavailable")
            return original(model, messages, **kwargs)

        monkeypatch.setattr(fake_client, "chat_completion_json", failing)

        bundle = _finish(client, _session_id(client))["execution_bundle"]

        assert "celery" not in bundle["repo_scaffold"]["frameworks"]
        assert bundle["tasks"][0]["title"] != "Scaffold the monorepo"
        assert bundle["repo_scaffold"]["structure"]
        assert len(bundle["tasks"]) > 0
        assert len(bundle["prompts"]) > 0

    def test_synthesizer_templates_are_the_last_resort(self, client, monkeypatch):
        """
        If the generator itself blows up, the synthesizer's own templates cover it.
        """
        from app.services.intelligent_bundle_generator import IntelligentBundleGenerator

        def explode(self, plan_state, project_profile, target_tool="claudecode"):
            raise RuntimeError("generator exploded")

        monkeypatch.setattr(IntelligentBundleGenerator, "generate_bundle", explode)

        bundle = _finish(client, _session_id(client))["execution_bundle"]

        # Wording only the synthesizer's template prompt uses.
        assert "with the following requirements" in bundle["prompts"][0]["prompt"]
        assert bundle["repo_scaffold"]["structure"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
