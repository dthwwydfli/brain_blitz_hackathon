"""emit_zones node — staged build: append one zone, emit, sleep 0.8s. Backend is the only clock.

SCHEMA §4 canonical pattern: reset zone_risks, re-append one-by-one in ZONE_IDS order
with an 800ms gap + emit each, then status=complete + final emit. Persist city_state. Phase 3.
"""
import asyncio
from datetime import datetime, timezone

from copilotkit.langgraph import copilotkit_emit_state

from agent.state import AgentState, ZONE_IDS
from services.redis_service import RedisService

redis = RedisService()


def _ordered(zones: list) -> list:
    """Sort scored zones into canonical ZONE_IDS order."""
    by_id = {z.get("zone_id"): z for z in zones if isinstance(z, dict)}
    return [by_id[z] for z in ZONE_IDS if z in by_id]


async def emit_zones_node(state: AgentState, config) -> AgentState:
    scored = _ordered(state.get("zone_risks", []))

    # network_graph scenes have more nodes → tighter stagger so the build stays snappy.
    scene_type = (state.get("blueprint") or {}).get("scene_type", "city_grid")
    delay = 0.8 if scene_type == "city_grid" else 0.5

    # Staged build — the 3D map materializes zone-by-zone off this loop.
    state["zone_risks"] = []
    state["status"] = "scoring"
    for zone in scored:
        state["zone_risks"].append(zone)
        await copilotkit_emit_state(config, state)
        await asyncio.sleep(delay)  # THE drama delay — frontend adds no stagger

    state["status"] = "complete"
    await copilotkit_emit_state(config, state)

    # Persist final city_state (SCHEMA §5).
    city_state = {
        "city": state.get("city", ""),
        "scenario": state.get("scenario", ""),
        "blueprint": state.get("blueprint"),
        "zones": {z["zone_id"]: z for z in state["zone_risks"]},
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await redis.set_city_state(state.get("session_id", ""), city_state)
    except Exception:
        pass  # persistence best-effort; demo path unaffected

    return state
