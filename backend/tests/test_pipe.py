"""Phase 1 pipe test — backend-only proof the hello_node emits expected state.

Unit tier (this file): invoke the compiled graph, assert research_log + status.
Proves node logic without HTTP / frontend. No pytest dep — run directly:
    cd backend && .venv/bin/python tests/test_pipe.py

Smoke tier (manual): with `uvicorn main:app --port 8000` running, eyeball the SSE:
    curl -N -X POST localhost:8000/copilotkit \
      -H "Content-Type: application/json" \
      -d '{"messages":[{"role":"user","content":"hi"}],"threadId":"t1","runId":"r1"}'
You should see "pipe test: hello from agent" in the streamed state.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.graph import build_graph

EMPTY_STATE = {
    "messages": [],
    "city": "",
    "scenario": "",
    "session_id": "",
    "status": "idle",
    "research_log": [],
    "research_results": [],
    "zone_risks": [],
    "impact_query": None,
    "impact_summary": None,
    "is_scenario_switch": False,
}


async def test_hello_node_emits_pipe_message():
    graph = build_graph()
    result = await graph.ainvoke(EMPTY_STATE)
    assert result["research_log"] == ["pipe test: hello from agent"], result["research_log"]
    assert result["status"] == "researching", result["status"]


if __name__ == "__main__":
    asyncio.run(test_hello_node_emits_pipe_message())
    print("PASS: pipe test — hello_node emits 'pipe test: hello from agent'")
