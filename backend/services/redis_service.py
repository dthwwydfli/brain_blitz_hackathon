# STUB — replace with Person C's real service in Phase 4.
# No-op session store so agent nodes can import + call without breaking
# before Person C lands the real Upstash Redis service (~13:00).
from typing import Optional


class RedisService:
    """No-op stand-in for the real Redis session store."""

    def __init__(self) -> None:
        # Real service reads REDIS_URL / REDIS_TOKEN; the stub needs nothing.
        pass

    async def set_city_state(self, session_id: str, state: dict, ttl: int = 7200) -> None:
        pass

    async def get_city_state(self, session_id: str) -> Optional[dict]:
        return None

    async def set_research(self, session_id: str, scenario: str, results: list, ttl: int = 7200) -> None:
        pass

    async def get_research(self, session_id: str, scenario: str) -> Optional[list]:
        return None

    async def append_message(self, session_id: str, message: dict) -> None:
        pass

    async def get_messages(self, session_id: str) -> list:
        return []

    async def health_check(self) -> bool:
        # Stub is always "up" so /health stays green before real Redis lands.
        return True
