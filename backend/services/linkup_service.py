# STUB — replace with Person C's real service in Phase 4.
# Minimal canned implementation so agent nodes can import + call without breaking
# before Person C lands the real Linkup-backed service (~13:00).
from typing import Optional


class LinkupService:
    """Canned stand-in for the real Linkup web-research client."""

    def __init__(self) -> None:
        # Real service reads LINKUP_API_KEY; the stub needs nothing.
        pass

    async def search(
        self,
        query: str,
        depth: str = "standard",
        output_type: str = "sourcedAnswer",
    ) -> Optional[dict]:
        return {
            "answer": f"[stub] canned research result for query: {query!r}",
            "sources": [
                {"title": "Stub Source", "url": "https://example.com/stub"},
            ],
        }

    async def close(self) -> None:
        pass
