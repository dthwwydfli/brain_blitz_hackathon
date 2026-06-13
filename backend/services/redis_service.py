"""Redis session store — real implementation (Phase 4).

Upstash via redis-py async. REDIS_URL is a `rediss://` TLS URL (verified Phase 4), so
`redis.asyncio.from_url` connects directly — no REST/token construction needed.
Keys per SCHEMA §5, TTL 7200s. All reads degrade to None/[] on miss or error so the
demo path never throws. Interface is byte-identical to the old stub — nodes unchanged.
"""
import json
import os
from typing import Optional

import redis.asyncio as aioredis

_TTL = 7200  # 2h, SCHEMA §5


def _key(session_id: str, suffix: str) -> str:
    return f"session:{session_id}:{suffix}"


class RedisService:
    """Real Upstash/Redis-backed session store."""

    def __init__(self) -> None:
        self._url = os.getenv("REDIS_URL") or ""
        self._client: Optional[aioredis.Redis] = None

    def _conn(self) -> Optional[aioredis.Redis]:
        """Lazy singleton client. None if no URL configured (degrade to no-op)."""
        if self._client is None and self._url:
            self._client = aioredis.from_url(self._url, decode_responses=True)
        return self._client

    # ── city state ──────────────────────────────────────────────────────────
    async def set_city_state(self, session_id: str, state: dict, ttl: int = _TTL) -> None:
        c = self._conn()
        if not c:
            return
        try:
            await c.set(_key(session_id, "city_state"), json.dumps(state), ex=ttl)
        except Exception:
            pass

    async def get_city_state(self, session_id: str) -> Optional[dict]:
        c = self._conn()
        if not c:
            return None
        try:
            raw = await c.get(_key(session_id, "city_state"))
            return json.loads(raw) if raw else None
        except Exception:
            return None

    # ── research cache (per scenario) ───────────────────────────────────────
    async def set_research(
        self, session_id: str, scenario: str, results: list, ttl: int = _TTL
    ) -> None:
        c = self._conn()
        if not c:
            return
        try:
            await c.set(_key(session_id, f"research:{scenario}"), json.dumps(results), ex=ttl)
            await c.rpush(_key(session_id, "scenario_history"), scenario)
            await c.expire(_key(session_id, "scenario_history"), ttl)
        except Exception:
            pass

    async def get_research(self, session_id: str, scenario: str) -> Optional[list]:
        c = self._conn()
        if not c:
            return None
        try:
            raw = await c.get(_key(session_id, f"research:{scenario}"))
            return json.loads(raw) if raw else None
        except Exception:
            return None

    # ── message thread ──────────────────────────────────────────────────────
    async def append_message(self, session_id: str, message: dict) -> None:
        c = self._conn()
        if not c:
            return
        try:
            await c.rpush(_key(session_id, "messages"), json.dumps(message))
            await c.expire(_key(session_id, "messages"), _TTL)
        except Exception:
            pass

    async def get_messages(self, session_id: str) -> list:
        c = self._conn()
        if not c:
            return []
        try:
            raw = await c.lrange(_key(session_id, "messages"), 0, -1)
            return [json.loads(m) for m in raw]
        except Exception:
            return []

    async def health_check(self) -> bool:
        c = self._conn()
        if not c:
            return False
        try:
            return bool(await c.ping())
        except Exception:
            return False
