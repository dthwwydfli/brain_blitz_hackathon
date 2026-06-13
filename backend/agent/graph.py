"""LangGraph graph — FULL skeleton (Phase 2).

Topology locked at Gate 2 (13:00 schema lock). Node bodies are pass-through stubs
until Phase 3. Flow:

    parse_query ──┬─(impact_query set)─→ impact ─────────────────→ emit_zones ──→ END
                  └─(else)──→ blueprint → research → risk_scoring → emit_zones → END

blueprint decides scene_type (city_grid | network_graph) + scene structure before
research. Display metadata only — scoring stays on the fixed 9 zones (z_0_0..z_2_2).

Stream via copilotkit_emit_state(config, state) inside node bodies (Phase 3) — shared state,
NOT frontend useCopilotAction. Agent name `citypulse_agent` (see main.py).
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import AgentState
from agent.nodes.parse_node import parse_query_node
from agent.nodes.blueprint_node import blueprint_node
from agent.nodes.research_node import research_node
from agent.nodes.scoring_node import risk_scoring_node
from agent.nodes.emit_node import emit_zones_node
from agent.nodes.impact_node import impact_assessment_node


def should_handle_impact(state: AgentState) -> str:
    """Route a 'what if' query to impact re-scoring; otherwise blueprint→research."""
    if state.get("impact_query"):
        return "impact"
    return "blueprint"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("parse_query", parse_query_node)
    graph.add_node("blueprint", blueprint_node)
    graph.add_node("research", research_node)
    graph.add_node("risk_scoring", risk_scoring_node)
    graph.add_node("emit_zones", emit_zones_node)
    graph.add_node("impact", impact_assessment_node)

    graph.set_entry_point("parse_query")
    graph.add_conditional_edges("parse_query", should_handle_impact, {
        "blueprint": "blueprint",
        "impact": "impact",
    })
    graph.add_edge("blueprint", "research")
    graph.add_edge("research", "risk_scoring")
    graph.add_edge("risk_scoring", "emit_zones")
    graph.add_edge("impact", "emit_zones")
    graph.add_edge("emit_zones", END)

    return graph.compile(checkpointer=MemorySaver())
