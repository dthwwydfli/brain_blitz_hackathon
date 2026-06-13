"""Agent shared state — the AG-UI contract. Byte-exact to SCHEMA.md §3 (Python view).

Frozen at 13:00 schema lock. Field names/types here must match `CityAgentState` on
the frontend. `research_results` is internal (raw Linkup) and NOT sent to the UI;
`research_log` is the human-readable feed the sidebar shows.
"""
from typing import Annotated, Optional, TypedDict
import operator


class ZoneRisk(TypedDict):
    zone_id: str          # "z_0_0" .. "z_2_2"
    score: float          # 0.0 – 1.0
    label: str            # LOW | MEDIUM | HIGH | CRITICAL (derived from score)
    evidence: list[str]   # 2–3 grounded bullets
    sources: list[dict]   # [{"title": str, "url": str}], max 3


class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    city: str
    scenario: str
    session_id: str
    status: str                    # idle | researching | scoring | complete
    research_log: list[str]        # live feed for ResearchProgress sidebar
    research_results: list[dict]   # raw Linkup — internal only, NOT sent to UI
    zone_risks: list[ZoneRisk]     # grows as zones are scored — drives 3D build
    impact_query: Optional[str]    # internal trigger for "what if" queries
    impact_summary: Optional[str]  # set after a "what if" query
    is_scenario_switch: bool
