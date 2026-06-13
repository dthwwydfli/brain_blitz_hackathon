"""blueprint node — decide scene type + generate the 3D scene structure.

Runs after parse_query, before research. Gemini picks `scene_type`
(`city_grid` for area-wide hazards, `network_graph` for utility networks) and emits
a blueprint the frontend renders. Display metadata only — risk scoring still runs on
the fixed 9 zones (z_0_0..z_2_2); the blueprint does not change the scoring contract.

Shared-state transport: mutate state["blueprint"], then emit the WHOLE state via
copilotkit_emit_state (NOT a partial {"type": ...} dict — that would clobber state).
Reuses agent/llm.py get_llm/parse_json so there is no module-level LLM (import-safe
when GEMINI_API_KEY is absent). Falls back to a city_grid blueprint on any failure.
"""
from copilotkit.langgraph import copilotkit_emit_state

from agent.llm import get_llm, parse_json
from agent.state import AgentState

VALID_SCENE_TYPES = ("city_grid", "network_graph")

BLUEPRINT_PROMPT = (
    "You are a 3D infrastructure visualisation agent. Given a city and a risk "
    "scenario, decide which scene type best represents the infrastructure and "
    "generate a blueprint for it.\n\n"
    "Scene types:\n"
    "- city_grid: area-wide hazards — flooding, air quality, urban heat, "
    "earthquake, any city-level risk.\n"
    "- network_graph: utility/connected networks — power grid, water supply, "
    "internet infrastructure, gas networks.\n\n"
    "Respond with ONLY valid JSON, no preamble, no code fences:\n"
    '{"scene_type": "network_graph", "title": "UK Power Grid — Resilience", '
    '"camera_preset": "isometric", '
    '"nodes": [{"id": "node_1", "label": "Drax Station", "type": "hub", '
    '"risk_score": 0.3, "position": {"x": -4, "y": 0, "z": -2}, "size": 1.2}], '
    '"connections": [{"from": "node_1", "to": "node_2", "risk_score": 0.2}]}\n\n'
    "Rules:\n"
    "- city_grid: nodes are the 9 zones z_0_0..z_2_2, no connections needed.\n"
    "- network_graph: 6-10 nodes max, spread across x(-6..6) z(-4..4), y always 0.\n"
    "- risk_score is your best initial estimate (refined later by scoring).\n"
    "- node labels short (max 3 words).\n"
    "- ONLY output JSON."
)


def _fallback(city: str, scenario: str) -> dict:
    """Safe default — city_grid, no nodes/connections. Never crashes the run."""
    return {
        "scene_type": "city_grid",
        "title": f"{city} — {scenario}".strip(" —"),
        "camera_preset": "isometric",
        "nodes": [],
        "connections": [],
    }


async def blueprint_node(state: AgentState, config) -> AgentState:
    city = state.get("city") or "the city"
    scenario = state.get("scenario") or "infrastructure risk"

    blueprint = None
    try:
        llm = get_llm(temperature=0.1)  # raises if GEMINI_API_KEY absent
        resp = await llm.ainvoke(
            f"{BLUEPRINT_PROMPT}\n\nQuery: {city} — {scenario}\n"
            "Generate the scene blueprint."
        )
        data = parse_json(resp.content)
        if isinstance(data, dict) and data.get("scene_type") in VALID_SCENE_TYPES:
            data.setdefault("title", f"{city} — {scenario}")
            data.setdefault("camera_preset", "isometric")
            data.setdefault("nodes", [])
            data.setdefault("connections", [])
            blueprint = data
    except Exception:
        blueprint = None  # → fallback below

    state["blueprint"] = blueprint if blueprint is not None else _fallback(city, scenario)
    await copilotkit_emit_state(config, state)
    return state
