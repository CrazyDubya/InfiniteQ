"""
Shared rate limiter for the API.

Single source of truth: main.py registers this instance on the app (for the
429 handler) and the route modules decorate their handlers with it, so the
limits are enforced by the same limiter everywhere.

Limit policy (all overridable by env var):

- ``RATE_LIMIT_LLM``      routes that call inference models. These are the
                          expensive ones, so they get a tight budget.
- ``RATE_LIMIT_SESSION``  session lifecycle (create/finish).
- ``RATE_LIMIT_READ``     cheap reads and metadata updates.

Handlers decorated with ``@limiter.limit(...)`` must take a Starlette Request
literally named ``request`` - slowapi resolves it out of the call kwargs and
raises at runtime if that name holds anything else (e.g. a Pydantic body).
See backend/tests/test_rate_limiting.py.
"""
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

RATE_LIMIT_LLM = os.environ.get("RATE_LIMIT_LLM", "30/minute")
RATE_LIMIT_SESSION = os.environ.get("RATE_LIMIT_SESSION", "10/minute")
RATE_LIMIT_READ = os.environ.get("RATE_LIMIT_READ", "120/minute")

limiter = Limiter(key_func=get_remote_address)
