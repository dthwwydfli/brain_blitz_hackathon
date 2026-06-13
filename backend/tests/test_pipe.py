"""Phase 3 graph test — full run produces 9 consistent zones.

No pytest dep — run directly:
    cd backend && .venv/bin/python tests/test_pipe.py

Uses Person C's stub services (canned Linkup / no-op Redis), so this runs green before
real services land. Gemini scoring needs GEMINI_API_KEY; on total LLM failure the run
falls back to uniform-LOW 9 zones, so the structural asserts below still hold.

Smoke tier (manual): with `uvicorn main:app --port 8000` running, type "London flooding"
in chat → research_log streams → 9 zones materialize ~800ms apart in the 3D map.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()  # GEMINI_API_KEY for live scoring (mirrors main.py)

from langchain_core.messages import HumanMessage

from agent.graph import build_graph
from agent.state import ZONE_IDS, label_for_score


def _base_state(text: str) -> dict:
    return {
        "messages": [HumanMessage(content=text)],
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


async def test_full_run():
    graph = build_graph()
    config = {"configurable": {"thread_id": "test-thread-1"}}
    result = await graph.ainvoke(_base_state("London flooding"), config)

    assert result["status"] == "complete", result["status"]
    assert result["city"], "city not parsed"
    assert result["scenario"], "scenario not parsed"

    zones = result["zone_risks"]
    assert len(zones) == 9, f"expected 9 zones, got {len(zones)}"

    seen_ids = {z["zone_id"] for z in zones}
    assert seen_ids == set(ZONE_IDS), f"zone ids drift: {seen_ids ^ set(ZONE_IDS)}"

    for z in zones:
        assert 0.0 <= z["score"] <= 1.0, z
        assert z["label"] == label_for_score(z["score"]), z  # score wins
        assert len(z["sources"]) <= 3, z

    assert result["research_log"], "research_log empty"
    print(f"PASS: full run — {result['city']} / {result['scenario']}, 9 zones, "
          f"status={result['status']}")


if __name__ == "__main__":
    asyncio.run(test_full_run())
