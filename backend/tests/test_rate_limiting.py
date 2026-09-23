"""
Rate limiting tests.

The shared `client` fixture disables the limiter so the rest of the suite is
order-independent. These tests turn it back on to check it actually works.

This also guards a real regression: slowapi resolves the Starlette request by
looking for a parameter literally named `request`. When the rate-limited
handlers named the Pydantic body `request` and the Starlette request `req`,
every one of them raised at runtime.
"""
import pytest

from app.api.routes import limiter

API = "/api/v1"


@pytest.fixture
def limited_client(client):
    """The shared client with rate limiting switched back on."""
    limiter.enabled = True
    limiter.reset()
    yield client
    limiter.enabled = False


def test_rate_limited_endpoint_does_not_crash(limited_client):
    """
    A rate-limited endpoint must serve normally, not raise.

    Regression guard: this returned 500 with
    "parameter `request` must be an instance of starlette.requests.Request"
    when the handler parameters were named the other way round.
    """
    resp = limited_client.post(f"{API}/session", json={"idea": "A small tool"})
    assert resp.status_code == 200, resp.text


def test_session_creation_is_rate_limited(limited_client):
    """The 10/minute session limit should eventually return 429, not 500."""
    statuses = [
        limited_client.post(f"{API}/session", json={"idea": f"Idea {i}"}).status_code
        for i in range(12)
    ]

    assert 200 in statuses, "no request succeeded; limit is too tight"
    assert 429 in statuses, f"limit never triggered: {statuses}"
    # A tripped limit must be a clean 429, never a server error.
    assert 500 not in statuses, f"limiter raised instead of rejecting: {statuses}"


def test_llm_heavy_route_is_rate_limited(limited_client):
    """
    Thread creation calls several models, so it is a target for abuse and must
    be metered rather than left open.
    """
    session_id = limited_client.post(
        f"{API}/session", json={"idea": "A small tool"}
    ).json()["session_id"]

    statuses = [
        limited_client.post(
            f"{API}/session/{session_id}/threads",
            json={"type": "risk", "title": f"Thread {i}"},
        ).status_code
        for i in range(35)
    ]

    assert 200 in statuses, f"no request succeeded: {statuses[:5]}"
    assert 429 in statuses, f"the LLM limit never triggered: {statuses}"
    assert 500 not in statuses, f"limiter raised instead of rejecting: {statuses}"


def test_limiter_finds_starlette_request_on_every_limited_route(client):
    """
    Every @limiter.limit handler must take a Starlette Request named `request`.

    Checked by signature so a future rename fails here rather than in production.
    """
    from fastapi import Request
    import inspect

    from app.api import routes

    # Every route is metered: LLM-calling routes, session lifecycle, and cheap
    # reads. A new route that forgets its decorator is caught below.
    limited = [
        routes.create_session,
        routes.submit_answers,
        routes.finish_session,
        routes.create_thread,
        routes.list_threads,
        routes.update_thread,
        routes.activate_thread,
        routes.submit_thread_answers,
        routes.submit_reflection,
        routes.get_thread_insights,
        routes.get_session_status,
    ]

    for fn in limited:
        params = inspect.signature(fn).parameters
        assert "request" in params, f"{fn.__name__} has no `request` parameter"
        assert params["request"].annotation is Request, (
            f"{fn.__name__}'s `request` is {params['request'].annotation}, "
            "but slowapi requires a starlette Request"
        )


def test_every_api_route_is_metered(client):
    """No handler may be left without a limit."""
    from app.api.rate_limit import limiter
    from app.api.routes import router

    # slowapi records decorated handlers under "<module>.<function name>".
    def slowapi_key(route):
        endpoint = route.endpoint
        return f"{endpoint.__module__}.{endpoint.__name__}"

    unmetered = [
        route.endpoint.__name__ for route in router.routes
        if slowapi_key(route) not in limiter._route_limits
    ]

    assert not unmetered, f"routes without a rate limit: {unmetered}"
