"""LangGraph graph — PIPE-TEST version only (Phase 1).

Single hello_node that proves agent shared-state flows agent→frontend over AG-UI.
Phase 2 replaces this with the full parse→research→scoring→emit→impact graph.
Keep it pipe-test-only until Gate 1 (12:00) is green.
"""
from langgraph.graph import StateGraph, END
from copilotkit.langgraph import copilotkit_emit_state

from agent.state import AgentState


async def hello_node(state: AgentState, config) -> AgentState:
    state["status"] = "researching"
    state["research_log"] = ["pipe test: hello from agent"]
    await copilotkit_emit_state(config, state)
    return state


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("hello", hello_node)
    graph.set_entry_point("hello")
    graph.add_edge("hello", END)
    return graph.compile()
