"""impact node — "what if" query: re-score affected zones only, merge, set impact_summary.

Linkup-search the intervention → Gemini re-scores ONLY affected zones → merge back into
the full zone_risks (unaffected unchanged) → set impact_summary, clear impact_query. Phase 3.
Routes on to emit_node, which re-streams the merged set.
"""
from copilotkit.langgraph import copilotkit_emit_state

from agent.llm import get_llm, parse_json
from agent.nodes.scoring_node import _normalize_zone, score_zones
from agent.state import AgentState, ZONE_IDS
from services.linkup_service import LinkupService

linkup = LinkupService()


def _zones_by_id(state: AgentState) -> dict:
    return {z["zone_id"]: z for z in state.get("zone_risks", []) if isinstance(z, dict)}


async def impact_assessment_node(state: AgentState, config) -> AgentState:
    query = state.get("impact_query") or ""
    city = state.get("city") or "the city"
    scenario = state.get("scenario") or "infrastructure risk"

    state.setdefault("research_log", [])
    state["status"] = "researching"
    state["research_log"].append(f"Assessing intervention: {query}")
    await copilotkit_emit_state(config, state)

    # Research the intervention.
    digest = ""
    try:
        result = await linkup.search(query)
        if result and result.get("answer"):
            digest = str(result["answer"])
    except Exception:
        pass

    existing = _zones_by_id(state)

    # No prior scores to merge into → degrade to a full fresh scoring pass.
    if not existing:
        scored = await score_zones(city, scenario, digest, ZONE_IDS)
        if scored:
            state["zone_risks"] = scored
        state["impact_summary"] = f"Assessed: {query}"
        state["impact_query"] = None
        return state

    state["status"] = "scoring"
    await copilotkit_emit_state(config, state)

    updated, summary = await _rescore_affected(query, city, scenario, digest, existing)

    # Merge updated zones back; unaffected zones untouched.
    existing.update({z["zone_id"]: z for z in updated})
    state["zone_risks"] = [existing[z] for z in ZONE_IDS if z in existing]
    state["impact_summary"] = summary or f"Assessed intervention: {query}"
    state["impact_query"] = None
    return state


async def _rescore_affected(
    query: str, city: str, scenario: str, digest: str, existing: dict
) -> tuple[list, str]:
    """Ask Gemini which zones the intervention changes + their new scores. Retry ×3."""
    current = {z: existing[z]["score"] for z in existing}
    prompt = (
        f"Current {scenario} risk scores by zone for {city}: {current}.\n"
        f"Proposed intervention: {query}\n"
        f"Research notes: {digest or 'none'}\n\n"
        "Return ONLY JSON, no fences:\n"
        '{"summary": "1-2 sentence plain-English effect", '
        '"zones": [{"zone_id": "z_r_c", "score": 0.0-1.0, '
        '"evidence": ["why this zone changed"], "sources": []}]}\n'
        "Include in 'zones' ONLY the zones whose risk the intervention actually changes."
    )
    try:
        llm = get_llm(temperature=0.2)  # raises if GEMINI_API_KEY absent
    except Exception:
        return [], ""  # no LLM → leave existing scores unchanged
    for _ in range(3):
        try:
            resp = await llm.ainvoke(prompt)
            data = parse_json(resp.content)
        except Exception:
            data = None
        if isinstance(data, dict) and isinstance(data.get("zones"), list):
            updated = [
                _normalize_zone(z, z["zone_id"])
                for z in data["zones"]
                if isinstance(z, dict) and z.get("zone_id") in existing
            ]
            return updated, str(data.get("summary") or "")
    return [], ""
