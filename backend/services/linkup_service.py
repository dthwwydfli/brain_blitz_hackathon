"""Linkup web-research client — real implementation (Phase 4).

Wraps linkup-sdk's native async `async_search` with `output_type="sourcedAnswer"`.
Returns the frozen node contract: {"answer": str, "sources": [{"title", "url"}]}.
Bounded exponential backoff on 429 / transient errors. Canned fallback if key absent
so the demo path never hard-fails. Interface is byte-identical to the old stub —
nodes need no changes.
"""
import asyncio
import os
from typing import Optional

from linkup import LinkupClient, LinkupTooManyRequestsError

_BACKOFF = (0.5, 1.0, 2.0)  # seconds between retries; len = max attempts


def _canned(query: str) -> dict:
    return {
        "answer": f"[fallback] no Linkup key set — canned result for query: {query!r}",
        "sources": [{"title": "Fallback Source", "url": "https://example.com/fallback"}],
    }


class LinkupService:
    """Real Linkup-backed web-research client."""

    def __init__(self) -> None:
        self._key = os.getenv("LINKUP_API_KEY") or ""
        # Lazy client — only built when a key exists.
        self._client: Optional[LinkupClient] = (
            LinkupClient(api_key=self._key) if self._key else None
        )

    async def search(
        self,
        query: str,
        depth: str = "standard",
        output_type: str = "sourcedAnswer",
    ) -> Optional[dict]:
        if self._client is None:
            return _canned(query)

        last_exc: Optional[Exception] = None
        for attempt, wait in enumerate(_BACKOFF):
            try:
                resp = await self._client.async_search(
                    query=query, depth=depth, output_type=output_type
                )
                return self._to_dict(resp)
            except LinkupTooManyRequestsError as exc:
                # 429 — back off and retry.
                last_exc = exc
                if attempt < len(_BACKOFF) - 1:
                    await asyncio.sleep(wait)
            except Exception as exc:
                # Other transient errors: one more shot, then give up.
                last_exc = exc
                if attempt < len(_BACKOFF) - 1:
                    await asyncio.sleep(wait)
        # Exhausted retries — let the node's per-query try/except log + skip.
        raise last_exc if last_exc else RuntimeError("Linkup search failed")

    @staticmethod
    def _to_dict(resp) -> dict:
        """Map a LinkupSourcedAnswer (or dict) → {answer, sources:[{title,url}]}."""
        answer = getattr(resp, "answer", None)
        raw_sources = getattr(resp, "sources", None)
        if answer is None and isinstance(resp, dict):
            answer = resp.get("answer")
            raw_sources = resp.get("sources")

        sources = []
        for s in raw_sources or []:
            title = getattr(s, "name", None) or (s.get("name") if isinstance(s, dict) else None)
            url = getattr(s, "url", None) or (s.get("url") if isinstance(s, dict) else None)
            if url:
                sources.append({"title": str(title or url), "url": str(url)})

        return {"answer": str(answer or ""), "sources": sources[:3]}

    async def close(self) -> None:
        pass
