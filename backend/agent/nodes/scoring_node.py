"""risk_scoring node — Gemini scores 9 zones (JSON-only), label derived from score.

Phase 2: pass-through stub. Body lands in Phase 3.
"""
from agent.state import AgentState


async def risk_scoring_node(state: AgentState, config) -> AgentState:
    # STUB (Phase 2) — Gemini scoring + retry/clamp/label-derive/fallback in Phase 3.
    return state
