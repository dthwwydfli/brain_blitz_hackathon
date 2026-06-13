"""parse_query node — extract city + scenario from last message, detect "what if".

Heuristic first (deterministic, demo-safe); Gemini fallback only if heuristic misses.
Sets session_id, status=researching, emits. Phase 3.
"""
import uuid

from copilotkit.langgraph import copilotkit_emit_state

from agent.llm import get_llm, parse_json
from agent.state import AgentState

# Small known-city list — extend as needed. Lowercase contains-match.
KNOWN_CITIES = [
    "london", "new york", "nyc", "tokyo", "paris", "berlin", "mumbai",
    "san francisco", "los angeles", "chicago", "sydney", "singapore",
    "amsterdam", "venice", "miami", "jakarta", "bangkok", "delhi",
]

# scenario keyword → canonical scenario label.
SCENARIO_KEYWORDS = {
    "flood": "flooding",
    "flooding": "flooding",
    "power": "power grid failure",
    "grid": "power grid failure",
    "blackout": "power grid failure",
    "transport": "transport disruption",
    "transit": "transport disruption",
    "traffic": "transport disruption",
    "heat": "extreme heat",
    "heatwave": "extreme heat",
    "earthquake": "earthquake",
    "seismic": "earthquake",
    "wildfire": "wildfire",
    "fire": "wildfire",
    "storm": "storm surge",
    "hurricane": "storm surge",
    "cyber": "cyberattack",
}

IMPACT_TRIGGERS = ("what if", "barrier", "intervention", "what would happen")


def _last_user_text(messages: list) -> str:
    """Last human message content, tolerant of LangChain objects or dicts."""
    for msg in reversed(messages or []):
        role = getattr(msg, "type", None) or (msg.get("role") if isinstance(msg, dict) else None)
        if role in ("human", "user"):
            content = getattr(msg, "content", None)
            if content is None and isinstance(msg, dict):
                content = msg.get("content", "")
            return str(content or "")
    # Fall back to the very last message of any role.
    if messages:
        last = messages[-1]
        return str(getattr(last, "content", None) or (last.get("content", "") if isinstance(last, dict) else ""))
    return ""


def _heuristic(text: str) -> tuple[str, str]:
    low = text.lower()
    city = ""
    for c in KNOWN_CITIES:
        if c in low:
            city = "New York" if c in ("nyc", "new york") else c.title()
            break
    scenario = ""
    for kw, canonical in SCENARIO_KEYWORDS.items():
        if kw in low:
            scenario = canonical
            break
    return city, scenario


async def _gemini_fill(text: str, city: str, scenario: str) -> tuple[str, str]:
    """One JSON-only Gemini call to fill whichever of city/scenario is missing."""
    prompt = (
        "Extract the city and risk scenario from this infrastructure-risk request. "
        'Respond with ONLY JSON: {"city": "<city>", "scenario": "<short scenario>"}. '
        "If a field is unknown, use an empty string.\n\n"
        f"Request: {text}"
    )
    try:
        resp = await get_llm().ainvoke(prompt)
        data = parse_json(resp.content)
        if isinstance(data, dict):
            city = city or str(data.get("city") or "").strip()
            scenario = scenario or str(data.get("scenario") or "").strip()
    except Exception:
        pass  # keep best heuristic guess
    return city, scenario


async def parse_query_node(state: AgentState, config) -> AgentState:
    text = _last_user_text(state.get("messages", []))
    low = text.lower()

    city, scenario = _heuristic(text)
    if not city or not scenario:
        city, scenario = await _gemini_fill(text, city, scenario)

    state["city"] = city or state.get("city", "")
    state["scenario"] = scenario or state.get("scenario", "")

    state["impact_query"] = text if any(t in low for t in IMPACT_TRIGGERS) else None

    if not state.get("session_id"):
        state["session_id"] = str(uuid.uuid4())

    state["status"] = "researching"
    await copilotkit_emit_state(config, state)
    return state
