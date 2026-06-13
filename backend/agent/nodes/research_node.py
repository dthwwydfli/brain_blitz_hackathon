"""research node — run Linkup query templates, collect raw results, stream research_log.

Redis cache check first. Each query streams a human line to research_log, then searches.
One bad query must not kill the run (try/except per query). Caches results. Phase 3.
"""
import asyncio

from copilotkit.langgraph import copilotkit_emit_state

from agent.state import AgentState
from services.linkup_service import LinkupService
from services.redis_service import RedisService

linkup = LinkupService()
redis = RedisService()


def _query_templates(city: str, scenario: str) -> list[str]:
    """5 research angles for (city, scenario)."""
    return [
        f"{city} infrastructure vulnerability to {scenario}",
        f"historical {scenario} incidents in {city} and affected areas",
        f"{city} official preparedness and resilience plans for {scenario}",
        f"recent news on {scenario} risk in {city}",
        f"which districts or zones of {city} are most exposed to {scenario}",
    ]


async def research_node(state: AgentState, config) -> AgentState:
    city = state.get("city") or "the city"
    scenario = state.get("scenario") or "infrastructure risk"
    session_id = state.get("session_id", "")

    state.setdefault("research_log", [])
    state.setdefault("research_results", [])

    # Cache hit → skip Linkup entirely.
    try:
        cached = await redis.get_research(session_id, scenario)
    except Exception:
        cached = None
    if cached:
        state["research_results"] = cached
        state["research_log"].append(f"Loaded cached research for {city} · {scenario}.")
        await copilotkit_emit_state(config, state)
        return state

    for query in _query_templates(city, scenario):
        state["research_log"].append(f"Researching: {query}")
        await copilotkit_emit_state(config, state)
        try:
            result = await linkup.search(query)
            if result:
                state["research_results"].append(result)
        except Exception as exc:
            state["research_log"].append(f"  ⚠ query failed ({exc}) — skipping.")
            await copilotkit_emit_state(config, state)
        await asyncio.sleep(0.3)

    try:
        await redis.set_research(session_id, scenario, state["research_results"])
    except Exception:
        pass  # cache write best-effort

    return state
