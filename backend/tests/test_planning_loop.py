"""
Regression tests for the planning loop.

Each of these guards a bug that only shows up *across* requests - a single
response looks fine either way, which is why the older tests missed them:

1. The UI posts answers to ``POST /session/{id}/answer``, but pending questions
   were stored on the session's thread. The endpoint looked in session scope,
   found nothing, and silently dropped every answer (coverage stayed at zero
   forever and the plan reducer never ran).
2. ``thread.coverage`` and the plan state were computed but never written back,
   so every round restarted from zero and questions kept re-targeting the same
   dimension.
3. Global (session-level) coverage was a ``TODO`` that echoed the untouched
   session map instead of aggregating the threads.

Run just this file with::

    python -m pytest backend/tests/test_planning_loop.py -v
"""
import json

import pytest

from app.models.schema import CoverageMap, ThreadState, ThreadType
from app.services.session_manager import aggregate_global_coverage

API = "/api/v1"

# Longer than 20 characters, so each answer earns the maximum coverage
# increment (base 15 + 10 for a specific free-text answer).
DETAILED_ANSWER = "A detailed answer with real context."


def _answers_for(questions, free_text=DETAILED_ANSWER):
    """Build the payload shape the React UI sends for a set of questions."""
    return {
        "answers": [
            {
                "question_id": question["id"],
                "choice_id": question["options"][0]["id"],
                "free_text": free_text,
            }
            for question in questions
        ]
    }


def _create_session(client, idea="A tool for managing building receiverships"):
    resp = client.post(f"{API}/session", json={"idea": idea})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _thread(thread_id, **coverage):
    """A thread state with the given per-dimension coverage scores."""
    return ThreadState(
        id=thread_id,
        session_id="session-1",
        type=ThreadType.KICKOFF,
        title=thread_id,
        coverage=CoverageMap(**coverage),
        created_at="2024-01-01T00:00:00",
        last_updated="2024-01-01T00:00:00",
    )


class TestGlobalCoverageAggregation:
    """Unit coverage of the aggregation applied by the session manager."""

    def test_no_threads_yields_an_empty_map(self):
        aggregated = aggregate_global_coverage({})

        assert aggregated.model_dump().keys() == CoverageMap().model_dump().keys()
        assert sum(aggregated.model_dump().values()) == 0

    def test_dimension_takes_the_best_thread(self):
        """Threads explore different areas, so per dimension the best wins."""
        aggregated = aggregate_global_coverage({
            "a": _thread("a", problem=80.0, risks=10.0),
            "b": _thread("b", problem=40.0, risks=60.0),
        })

        assert aggregated.problem == 80.0
        assert aggregated.risks == 60.0
        assert aggregated.gtm == 0.0

    def test_an_empty_thread_never_lowers_coverage(self):
        """Creating a thread must not undo the planning done in another one."""
        aggregated = aggregate_global_coverage({
            "covered": _thread("covered", features=75.0),
            "fresh": _thread("fresh"),
        })

        assert aggregated.features == 75.0

    def test_threads_are_not_mutated(self):
        threads = {"a": _thread("a", features=50.0)}

        aggregate_global_coverage(threads)

        assert threads["a"].coverage.features == 50.0


class TestUIAnswerFlow:
    """The UI's answer endpoint must actually process answers (bug 1)."""

    def test_answers_advance_coverage(self, client):
        created = _create_session(client)
        assert sum(created["coverage"].values()) == 0

        resp = client.post(
            f"{API}/session/{created['session_id']}/answer",
            json=_answers_for(created["first_questions"]),
        )

        assert resp.status_code == 200, resp.text
        coverage = resp.json()["coverage"]
        assert coverage["features"] > 0
        assert coverage["architecture"] > 0

    def test_coverage_is_persisted_not_just_echoed(self, client):
        created = _create_session(client)
        session_id = created["session_id"]

        answered = client.post(
            f"{API}/session/{session_id}/answer",
            json=_answers_for(created["first_questions"]),
        ).json()
        # Guard against the comparison below trivially passing on two maps of zeros.
        assert answered["coverage"]["features"] > 0

        status = client.get(f"{API}/session/{session_id}/status").json()
        assert status["coverage"] == answered["coverage"]

        threads = client.get(f"{API}/session/{session_id}/threads").json()["threads"]
        assert len(threads) == 1
        assert threads[0]["coverage"]["features"] == answered["coverage"]["features"]

    def test_second_round_starts_where_the_first_finished(self, client):
        created = _create_session(client)
        session_id = created["session_id"]

        first = client.post(
            f"{API}/session/{session_id}/answer",
            json=_answers_for(created["first_questions"]),
        ).json()
        second = client.post(
            f"{API}/session/{session_id}/answer",
            json=_answers_for(first["next_questions"]),
        ).json()

        # Round 1 has to have made progress for round 2's numbers to mean anything.
        assert first["coverage"]["features"] > 0
        assert second["coverage"]["features"] > first["coverage"]["features"]
        assert second["coverage"]["architecture"] > first["coverage"]["architecture"]

    def test_plan_state_survives_between_rounds(self, client, fake_client):
        created = _create_session(client)
        session_id = created["session_id"]

        first = client.post(
            f"{API}/session/{session_id}/answer",
            json=_answers_for(created["first_questions"]),
        ).json()
        client.post(
            f"{API}/session/{session_id}/answer",
            json=_answers_for(first["next_questions"]),
        )

        reducer_calls = [
            json.loads(call["user"]) for call in fake_client.calls
            if "maintain a canonical JSON plan" in call["system"]
        ]
        assert len(reducer_calls) == 2

        # Round 1 was handed the stub the session was created with...
        assert reducer_calls[0]["plan_state"]["meta"]["title"] == (
            "A normalized description of the idea"
        )
        # ...and round 2 must be handed the plan round 1 produced.
        assert reducer_calls[1]["plan_state"]["meta"]["title"] == "Test Project"
        # Answers are attributed to the session's active thread.
        assert reducer_calls[0]["thread_id"]


class TestThreadStatePersistence:
    """Thread coverage and phases must survive between rounds (bug 2)."""

    def _session_with_thread(self, client, thread_type="architecture"):
        created = _create_session(client)
        thread = client.post(
            f"{API}/session/{created['session_id']}/threads",
            json={"type": thread_type, "title": "Architecture deep dive"},
        ).json()
        return created["session_id"], thread

    def test_thread_coverage_accumulates_across_rounds(self, client):
        session_id, thread = self._session_with_thread(client)
        thread_id = thread["thread"]["id"]

        first = client.post(
            f"{API}/session/{session_id}/threads/{thread_id}/answer",
            json=_answers_for(thread["first_questions"]),
        ).json()
        second = client.post(
            f"{API}/session/{session_id}/threads/{thread_id}/answer",
            json=_answers_for(first["next_questions"]),
        ).json()

        assert first["thread_coverage"]["features"] > 0
        # Identical answers in both rounds, so round 2 must land exactly one
        # increment above round 1 rather than repeating the same score.
        assert second["thread_coverage"]["features"] == pytest.approx(
            2 * first["thread_coverage"]["features"]
        )

    def test_phase_coverage_persists_across_rounds(self, client):
        session_id, thread = self._session_with_thread(client)
        thread_id = thread["thread"]["id"]

        first = client.post(
            f"{API}/session/{session_id}/threads/{thread_id}/answer",
            json=_answers_for(thread["first_questions"]),
        ).json()
        second = client.post(
            f"{API}/session/{session_id}/threads/{thread_id}/answer",
            json=_answers_for(first["next_questions"]),
        ).json()

        assert first["phase_coverage"]["v1"]["features"] > 0
        assert second["phase_coverage"]["v1"]["features"] > (
            first["phase_coverage"]["v1"]["features"]
        )

    def test_thread_coverage_reaches_status_and_thread_list(self, client):
        session_id, thread = self._session_with_thread(client)
        thread_id = thread["thread"]["id"]

        answered = client.post(
            f"{API}/session/{session_id}/threads/{thread_id}/answer",
            json=_answers_for(thread["first_questions"]),
        ).json()

        status = client.get(f"{API}/session/{session_id}/status").json()
        assert status["coverage"]["features"] == answered["thread_coverage"]["features"]

        threads = client.get(f"{API}/session/{session_id}/threads").json()["threads"]
        stored = next(t for t in threads if t["id"] == thread_id)
        assert stored["coverage"]["features"] == answered["thread_coverage"]["features"]


class TestGlobalCoverageAcrossThreads:
    """Session coverage is aggregated from every thread (bug 3)."""

    def test_global_coverage_combines_threads(self, client):
        created = _create_session(client)
        session_id = created["session_id"]

        # The kickoff thread answers the features question only.
        features_questions = [
            q for q in created["first_questions"] if q["coverage_key"] == "features"
        ]
        assert features_questions
        kickoff = client.post(
            f"{API}/session/{session_id}/answer",
            json=_answers_for(features_questions),
        ).json()
        assert kickoff["coverage"]["features"] > 0
        assert kickoff["coverage"]["architecture"] == 0

        # A second thread covers a different dimension.
        thread = client.post(
            f"{API}/session/{session_id}/threads",
            json={"type": "architecture", "title": "Architecture deep dive"},
        ).json()
        architecture_questions = [
            q for q in thread["first_questions"] if q["coverage_key"] == "architecture"
        ]
        assert architecture_questions
        second = client.post(
            f"{API}/session/{session_id}/threads/{thread['thread']['id']}/answer",
            json=_answers_for(architecture_questions),
        ).json()

        global_coverage = second["global_coverage"]
        # The second thread's answer must not discard the kickoff thread's work.
        assert global_coverage["features"] == kickoff["coverage"]["features"]
        assert global_coverage["architecture"] == (
            second["thread_coverage"]["architecture"]
        )
        assert global_coverage["risks"] == 0

        persisted = client.get(f"{API}/session/{session_id}/status").json()["coverage"]
        assert persisted == global_coverage

    def test_global_coverage_is_not_lost_by_an_empty_thread(self, client):
        created = _create_session(client)
        session_id = created["session_id"]

        answered = client.post(
            f"{API}/session/{session_id}/answer",
            json=_answers_for(created["first_questions"]),
        ).json()
        assert answered["coverage"]["features"] > 0

        client.post(
            f"{API}/session/{session_id}/threads",
            json={"type": "risk", "title": "Risk assessment"},
        )

        persisted = client.get(f"{API}/session/{session_id}/status").json()["coverage"]
        assert persisted == answered["coverage"]


class TestFileStoragePersistence:
    """
    The production default is file-backed storage, where the session is serialized
    on every request. The state added by the planning-loop fixes (plan state,
    thread coverage, phase coverage, notes) has to survive that JSON round trip.
    """

    def test_the_loop_works_end_to_end_on_file_storage(self, make_client, tmp_path):
        from app.services.session_storage import FileStorage

        client = make_client(FileStorage(str(tmp_path / "sessions")))

        created = _create_session(client)
        session_id = created["session_id"]

        first = client.post(
            f"{API}/session/{session_id}/answer",
            json=_answers_for(created["first_questions"]),
        ).json()
        assert first["coverage"]["features"] > 0

        second = client.post(
            f"{API}/session/{session_id}/answer",
            json=_answers_for(first["next_questions"]),
        ).json()
        assert second["coverage"]["features"] > first["coverage"]["features"]

        # Everything is still there after re-reading the session from disk.
        status = client.get(f"{API}/session/{session_id}/status").json()
        assert status["coverage"] == second["coverage"]

        thread = client.get(f"{API}/session/{session_id}/threads").json()["threads"][0]
        assert thread["coverage"]["features"] == second["coverage"]["features"]
        assert thread["questions_asked"] > 0

        finished = client.post(f"{API}/session/{session_id}/finish", json={})
        assert finished.status_code == 200, finished.text
        assert finished.json()["markdown_brief"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
