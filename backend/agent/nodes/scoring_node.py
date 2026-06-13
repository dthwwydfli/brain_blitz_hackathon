"""risk_scoring node — Gemini scores 9 zones (JSON-only), label derived from score.

Strip ```json fences, retry ×3, clamp score, derive label per SCHEMA §2 (score wins),
uniform-LOW fallback on total failure. Phase 3. `score_zones` is reused by impact_node.
"""
from copilotkit.langgraph import copilotkit_emit_state

from agent.llm import get_llm, parse_json
from agent.state import AgentState, ZONE_IDS, ZoneRisk, label_for_score

_GRID_LEGEND = (
    "Zones form a 3×3 grid over the city:\n"
    "z_0_0 NW  z_0_1 N  z_0_2 NE\n"
    "z_1_0 W   z_1_1 C  z_1_2 E\n"
    "z_2_0 SW  z_2_1 S  z_2_2 SE"
)


def _research_digest(state: AgentState, limit: int = 4000) -> str:
    parts = []
    for r in state.get("research_results", []):
        if isinstance(r, dict):
            ans = r.get("answer")
            if ans:
                parts.append(str(ans))
    return ("\n\n".join(parts))[:limit] or "No external research available."


def _normalize_zone(raw: dict, zone_id: str) -> ZoneRisk:
    try:
        score = float(raw.get("score", 0.1))
    except (TypeError, ValueError):
        score = 0.1
    score = max(0.0, min(1.0, score))

    evidence = [str(e) for e in (raw.get("evidence") or []) if str(e).strip()][:3]
    if not evidence:
        evidence = ["No specific evidence returned."]

    sources = []
    for s in (raw.get("sources") or [])[:3]:
        if isinstance(s, dict) and s.get("url"):
            sources.append({"title": str(s.get("title") or s["url"]), "url": str(s["url"])})

    return ZoneRisk(
        zone_id=zone_id,
        score=score,
        label=label_for_score(score),
        evidence=evidence,
        sources=sources,
    )


def _fallback_zones() -> list[ZoneRisk]:
    """Uniform LOW across all 9 zones — never crash the run."""
    return [
        ZoneRisk(
            zone_id=z,
            score=0.1,
            label=label_for_score(0.1),
            evidence=["Scoring unavailable — defaulted to low risk."],
            sources=[],
        )
        for z in ZONE_IDS
    ]


def _build_prompt(city: str, scenario: str, digest: str, zone_ids: list[str]) -> str:
    return (
        f"You are an infrastructure risk analyst. Score the {scenario} risk for {city}.\n\n"
        f"{_GRID_LEGEND}\n"
        "Reason from the real geography of each compass sector (rivers/coast, elevation, "
        "density, critical infrastructure) — do NOT give every zone the same score.\n\n"
        f"Research notes:\n{digest}\n\n"
        f"Score EXACTLY these zones: {zone_ids}.\n"
        "Respond with ONLY a JSON array, no prose, no code fences. Each element:\n"
        '{"zone_id": "z_r_c", "score": 0.0-1.0, '
        '"evidence": ["2-3 short grounded bullets, citing the research notes where possible"], '
        '"sources": [{"title": "...", "url": "..."}] (max 3, may be empty)}\n\n'
        "Scoring rules:\n"
        "- Spread scores across the grid: unless the research clearly says otherwise, include at "
        "least one HIGH-or-CRITICAL zone (>=0.6) and at least one LOW zone (<0.3).\n"
        "- Bands: LOW 0.0-0.3, MEDIUM 0.3-0.6, HIGH 0.6-0.8, CRITICAL 0.8-1.0.\n"
        "- Tie each score to that sector's specific exposure for THIS scenario; identical scores "
        "across zones is almost always wrong."
    )


async def score_zones(
    city: str, scenario: str, digest: str, zone_ids: list[str]
) -> list[ZoneRisk] | None:
    """Gemini-score the given zones. Retry ×3. Returns None on total failure."""
    prompt = _build_prompt(city, scenario, digest, zone_ids)
    try:
        llm = get_llm(temperature=0.2)  # raises if GEMINI_API_KEY absent
    except Exception:
        return None  # → caller uses uniform-LOW fallback

    for _ in range(3):
        try:
            resp = await llm.ainvoke(prompt)
            data = parse_json(resp.content)
        except Exception:
            data = None
        if not isinstance(data, list):
            continue

        by_id = {}
        for raw in data:
            if isinstance(raw, dict) and raw.get("zone_id") in zone_ids:
                by_id[raw["zone_id"]] = raw
        if by_id:
            # Fill any zone the model omitted with a low-risk default.
            return [
                _normalize_zone(by_id.get(z, {"score": 0.1}), z) for z in zone_ids
            ]
    return None


async def risk_scoring_node(state: AgentState, config) -> AgentState:
    state["status"] = "scoring"
    await copilotkit_emit_state(config, state)

    city = state.get("city") or "the city"
    scenario = state.get("scenario") or "infrastructure risk"
    digest = _research_digest(state)

    scored = await score_zones(city, scenario, digest, ZONE_IDS)
    state["zone_risks"] = scored if scored is not None else _fallback_zones()
    return state
