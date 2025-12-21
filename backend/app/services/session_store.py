"""
Session Store: Persistent storage for sessions using Redis or file-based fallback.
Fixes the critical "infinite questioning" gap - sessions are now persistent.
"""
import json
import logging
import os
from typing import Optional, List
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from pathlib import Path

from app.models.schema import SessionData

logger = logging.getLogger(__name__)


class SessionStoreBase(ABC):
    """Abstract base class for session storage."""

    @abstractmethod
    def save(self, session: SessionData) -> bool:
        """Save a session."""
        pass

    @abstractmethod
    def load(self, session_id: str) -> Optional[SessionData]:
        """Load a session by ID."""
        pass

    @abstractmethod
    def delete(self, session_id: str) -> bool:
        """Delete a session."""
        pass

    @abstractmethod
    def list_sessions(self, limit: int = 100) -> List[str]:
        """List recent session IDs."""
        pass

    @abstractmethod
    def cleanup_expired(self, max_age_hours: int = 168) -> int:
        """Remove sessions older than max_age_hours. Returns count deleted."""
        pass


class RedisSessionStore(SessionStoreBase):
    """Redis-backed session storage for production use."""

    def __init__(self, redis_url: str = None):
        """
        Initialize Redis connection.

        Args:
            redis_url: Redis connection URL. Defaults to REDIS_URL env var.
        """
        try:
            import redis
            self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            self.client.ping()
            self.prefix = "infiniteq:session:"
            self.ttl_seconds = 7 * 24 * 60 * 60  # 7 days default
            logger.info(f"Redis session store connected: {self.redis_url}")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    def _key(self, session_id: str) -> str:
        return f"{self.prefix}{session_id}"

    def save(self, session: SessionData) -> bool:
        """Save session to Redis with TTL."""
        try:
            key = self._key(session.session_id)
            data = session.model_dump_json()
            self.client.setex(key, self.ttl_seconds, data)
            logger.debug(f"Saved session {session.session_id} to Redis")
            return True
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    def load(self, session_id: str) -> Optional[SessionData]:
        """Load session from Redis."""
        try:
            key = self._key(session_id)
            data = self.client.get(key)
            if data:
                return SessionData.model_validate_json(data)
            return None
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def delete(self, session_id: str) -> bool:
        """Delete session from Redis."""
        try:
            key = self._key(session_id)
            result = self.client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False

    def list_sessions(self, limit: int = 100) -> List[str]:
        """List session IDs matching prefix."""
        try:
            pattern = f"{self.prefix}*"
            keys = list(self.client.scan_iter(pattern, count=limit))
            return [k.replace(self.prefix, "") for k in keys[:limit]]
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    def cleanup_expired(self, max_age_hours: int = 168) -> int:
        """Redis TTL handles expiration automatically. This is a no-op."""
        return 0


class FileSessionStore(SessionStoreBase):
    """File-based session storage as fallback when Redis unavailable."""

    def __init__(self, storage_dir: str = None):
        """
        Initialize file storage.

        Args:
            storage_dir: Directory for session files. Defaults to ./data/sessions
        """
        self.storage_dir = Path(storage_dir or os.getenv("SESSION_STORAGE_DIR", "./data/sessions"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"File session store initialized: {self.storage_dir}")

    def _path(self, session_id: str) -> Path:
        return self.storage_dir / f"{session_id}.json"

    def save(self, session: SessionData) -> bool:
        """Save session to file."""
        try:
            path = self._path(session.session_id)
            with open(path, 'w') as f:
                f.write(session.model_dump_json(indent=2))
            logger.debug(f"Saved session {session.session_id} to file")
            return True
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    def load(self, session_id: str) -> Optional[SessionData]:
        """Load session from file."""
        try:
            path = self._path(session_id)
            if path.exists():
                with open(path, 'r') as f:
                    data = f.read()
                return SessionData.model_validate_json(data)
            return None
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def delete(self, session_id: str) -> bool:
        """Delete session file."""
        try:
            path = self._path(session_id)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False

    def list_sessions(self, limit: int = 100) -> List[str]:
        """List session files."""
        try:
            files = list(self.storage_dir.glob("*.json"))
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            return [f.stem for f in files[:limit]]
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    def cleanup_expired(self, max_age_hours: int = 168) -> int:
        """Remove session files older than max_age_hours."""
        try:
            cutoff = datetime.now() - timedelta(hours=max_age_hours)
            deleted = 0
            for path in self.storage_dir.glob("*.json"):
                if datetime.fromtimestamp(path.stat().st_mtime) < cutoff:
                    path.unlink()
                    deleted += 1
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} expired sessions")
            return deleted
        except Exception as e:
            logger.error(f"Failed to cleanup sessions: {e}")
            return 0


class HybridSessionStore(SessionStoreBase):
    """
    Hybrid store that uses in-memory cache with persistent backend.
    Provides fast reads with durability.
    """

    def __init__(self, backend: SessionStoreBase = None, cache_size: int = 100):
        """
        Initialize hybrid store.

        Args:
            backend: Persistent backend store. Defaults to FileSessionStore.
            cache_size: Max sessions to keep in memory.
        """
        self.backend = backend or FileSessionStore()
        self.cache: dict = {}
        self.cache_order: list = []  # LRU tracking
        self.cache_size = cache_size

    def _update_lru(self, session_id: str):
        """Update LRU order."""
        if session_id in self.cache_order:
            self.cache_order.remove(session_id)
        self.cache_order.append(session_id)

        # Evict if over size
        while len(self.cache_order) > self.cache_size:
            evict_id = self.cache_order.pop(0)
            self.cache.pop(evict_id, None)

    def save(self, session: SessionData) -> bool:
        """Save to both cache and backend."""
        # Save to backend first (durability)
        success = self.backend.save(session)

        # Update cache
        self.cache[session.session_id] = session
        self._update_lru(session.session_id)

        return success

    def load(self, session_id: str) -> Optional[SessionData]:
        """Load from cache or backend."""
        # Check cache first
        if session_id in self.cache:
            self._update_lru(session_id)
            return self.cache[session_id]

        # Load from backend
        session = self.backend.load(session_id)
        if session:
            self.cache[session.session_id] = session
            self._update_lru(session_id)

        return session

    def delete(self, session_id: str) -> bool:
        """Delete from both cache and backend."""
        self.cache.pop(session_id, None)
        if session_id in self.cache_order:
            self.cache_order.remove(session_id)
        return self.backend.delete(session_id)

    def list_sessions(self, limit: int = 100) -> List[str]:
        """List from backend."""
        return self.backend.list_sessions(limit)

    def cleanup_expired(self, max_age_hours: int = 168) -> int:
        """Cleanup backend."""
        return self.backend.cleanup_expired(max_age_hours)


def create_session_store() -> SessionStoreBase:
    """
    Factory function to create the appropriate session store.

    Tries Redis first, falls back to file storage.
    """
    redis_url = os.getenv("REDIS_URL")

    if redis_url:
        try:
            backend = RedisSessionStore(redis_url)
            logger.info("Using Redis session store")
            return HybridSessionStore(backend)
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}), falling back to file storage")

    logger.info("Using file-based session store")
    return HybridSessionStore(FileSessionStore())
