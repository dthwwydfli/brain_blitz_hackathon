"""emit_zones node — staged build: append one zone, emit, sleep 0.8s. Backend is the only clock.

Phase 2: pass-through stub. Body lands in Phase 3 (SCHEMA §4 canonical pattern).
"""
from agent.state import AgentState


async def emit_zones_node(state: AgentState, config) -> AgentState:
    # STUB (Phase 2) — staged emit loop + Redis persist in Phase 3.
    return state
