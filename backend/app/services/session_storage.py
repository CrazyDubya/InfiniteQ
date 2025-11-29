"""
Session Storage: abstraction for session persistence backends.
Supports in-memory and Redis storage.
"""
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from datetime import datetime

import redis

from app.models.schema import SessionData

logger = logging.getLogger(__name__)


class SessionStorage(ABC):
    """Abstract base class for session storage backends."""

    @abstractmethod
    def save(self, session_id: str, session: SessionData) -> None:
        """Save a session."""
        pass

    @abstractmethod
    def get(self, session_id: str) -> Optional[SessionData]:
        """Get a session by ID."""
        pass

    @abstractmethod
    def delete(self, session_id: str) -> bool:
        """Delete a session. Returns True if deleted."""
        pass

    @abstractmethod
    def list_ids(self) -> List[str]:
        """List all session IDs."""
        pass

    @abstractmethod
    def exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        pass


class InMemoryStorage(SessionStorage):
    """In-memory session storage (default, non-persistent)."""

    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}
        logger.info("Initialized in-memory session storage")

    def save(self, session_id: str, session: SessionData) -> None:
        self.sessions[session_id] = session

    def get(self, session_id: str) -> Optional[SessionData]:
        return self.sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def list_ids(self) -> List[str]:
        return list(self.sessions.keys())

    def exists(self, session_id: str) -> bool:
        return session_id in self.sessions


class RedisStorage(SessionStorage):
    """Redis-backed session storage for persistence across restarts."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        key_prefix: str = "infiniteq:session:",
        ttl_seconds: int = 86400 * 7  # 7 days default
    ):
        """
        Initialize Redis storage.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
            key_prefix: Prefix for all session keys
            ttl_seconds: Time-to-live for sessions (default 7 days)
        """
        self.redis_url = redis_url or os.environ.get(
            "REDIS_URL", "redis://localhost:6379/0"
        )
        self.key_prefix = key_prefix
        self.ttl_seconds = ttl_seconds

        try:
            self.client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.client.ping()
            logger.info(f"Connected to Redis at {self._safe_url()}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _safe_url(self) -> str:
        """Return URL with password masked for logging."""
        if "@" in self.redis_url:
            parts = self.redis_url.split("@")
            return f"***@{parts[-1]}"
        return self.redis_url

    def _key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"{self.key_prefix}{session_id}"

    def save(self, session_id: str, session: SessionData) -> None:
        """Save session to Redis with TTL."""
        key = self._key(session_id)
        try:
            # Serialize session to JSON
            data = session.model_dump_json()
            self.client.setex(key, self.ttl_seconds, data)
            logger.debug(f"Saved session {session_id} to Redis")
        except Exception as e:
            logger.error(f"Failed to save session to Redis: {e}")
            raise

    def get(self, session_id: str) -> Optional[SessionData]:
        """Get session from Redis."""
        key = self._key(session_id)
        try:
            data = self.client.get(key)
            if data:
                return SessionData.model_validate_json(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get session from Redis: {e}")
            return None

    def delete(self, session_id: str) -> bool:
        """Delete session from Redis."""
        key = self._key(session_id)
        try:
            result = self.client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete session from Redis: {e}")
            return False

    def list_ids(self) -> List[str]:
        """List all session IDs."""
        try:
            keys = self.client.keys(f"{self.key_prefix}*")
            prefix_len = len(self.key_prefix)
            return [key[prefix_len:] for key in keys]
        except Exception as e:
            logger.error(f"Failed to list sessions from Redis: {e}")
            return []

    def exists(self, session_id: str) -> bool:
        """Check if session exists in Redis."""
        key = self._key(session_id)
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check session existence in Redis: {e}")
            return False

    def refresh_ttl(self, session_id: str) -> bool:
        """Refresh TTL for an active session."""
        key = self._key(session_id)
        try:
            return self.client.expire(key, self.ttl_seconds)
        except Exception as e:
            logger.error(f"Failed to refresh TTL: {e}")
            return False


def create_storage(storage_type: Optional[str] = None) -> SessionStorage:
    """
    Factory function to create the appropriate storage backend.

    Args:
        storage_type: "redis" or "memory" (default from STORAGE_TYPE env var)

    Returns:
        SessionStorage instance
    """
    storage_type = storage_type or os.environ.get("STORAGE_TYPE", "memory")

    if storage_type.lower() == "redis":
        redis_url = os.environ.get("REDIS_URL")
        ttl = int(os.environ.get("SESSION_TTL_SECONDS", 86400 * 7))
        return RedisStorage(redis_url=redis_url, ttl_seconds=ttl)
    else:
        return InMemoryStorage()
