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


HAS_GEMINI = bool(os.getenv("GEMINI_API_KEY"))


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
        "blueprint": None,
        "impact_query": None,
        "impact_summary": None,
        "is_scenario_switch": False,
    }


def _assert_valid_blueprint(bp) -> None:
    assert isinstance(bp, dict), f"blueprint not set: {bp!r}"
    assert bp.get("scene_type") in ("city_grid", "network_graph"), bp
    assert isinstance(bp.get("nodes"), list), bp
    assert isinstance(bp.get("connections"), list), bp


def _assert_valid_zones(zones: list) -> None:
    assert len(zones) == 9, f"expected 9 zones, got {len(zones)}"
    seen = {z["zone_id"] for z in zones}
    assert seen == set(ZONE_IDS), f"zone ids drift: {seen ^ set(ZONE_IDS)}"
    for z in zones:
        assert 0.0 <= z["score"] <= 1.0, z
        assert z["label"] == label_for_score(z["score"]), z  # score wins
        assert len(z["sources"]) <= 3, z


async def test_full_run():
    graph = build_graph()
    config = {"configurable": {"thread_id": "test-thread-1"}}
    result = await graph.ainvoke(_base_state("London flooding"), config)

    assert result["status"] == "complete", result["status"]
    assert result["city"], "city not parsed"
    assert result["scenario"], "scenario not parsed"

    _assert_valid_zones(result["zone_risks"])
    _assert_valid_blueprint(result["blueprint"])
    assert result["research_log"], "research_log empty"
    print(f"PASS: full run — {result['city']} / {result['scenario']}, 9 zones, "
          f"blueprint={result['blueprint']['scene_type']}, status={result['status']}")


async def test_combos():
    """3 scenarios produce 9 valid zones each. With a Gemini key, scores must span >=2 bands
    (the Phase 4 tuning goal); without a key the uniform-LOW fallback skips that assertion."""
    combos = [
        ("London flooding", "London", "flooding"),
        ("NYC power grid failure", "New York", "power grid failure"),
        ("Tokyo transport disruption", "Tokyo", "transport disruption"),
    ]
    for i, (text, exp_city, exp_scenario) in enumerate(combos):
        graph = build_graph()
        config = {"configurable": {"thread_id": f"combo-{i}"}}
        result = await graph.ainvoke(_base_state(text), config)

        assert result["status"] == "complete", result["status"]
        assert result["city"] == exp_city, f"{result['city']} != {exp_city}"
        assert result["scenario"] == exp_scenario, f"{result['scenario']} != {exp_scenario}"
        _assert_valid_zones(result["zone_risks"])
        _assert_valid_blueprint(result["blueprint"])

        if HAS_GEMINI:
            bands = {z["label"] for z in result["zone_risks"]}
            assert len(bands) >= 2, f"{text}: scores too flat, only bands {bands}"
        print(f"PASS: combo — {exp_city} / {exp_scenario}, 9 zones"
              + (f", bands={sorted({z['label'] for z in result['zone_risks']})}" if HAS_GEMINI else " (fallback)"))


async def test_impact():
    """A 'what if' message routes to impact: 9 zones intact, impact_summary set, impact_query cleared."""
    graph = build_graph()
    config = {"configurable": {"thread_id": "impact-1"}}
    base = await graph.ainvoke(_base_state("London flooding"), config)
    assert base["zone_risks"], "no prior zones to assess against"

    follow = dict(base)
    follow["messages"] = [HumanMessage(content="What if London built a flood barrier at zone 4")]
    result = await graph.ainvoke(follow, config)

    assert result["status"] == "complete", result["status"]
    _assert_valid_zones(result["zone_risks"])
    assert result.get("impact_summary"), "impact_summary not set"
    assert not result.get("impact_query"), "impact_query not cleared"
    print(f"PASS: impact — summary set, query cleared, 9 zones intact")


async def test_scenario_switch_flag():
    """is_scenario_switch flips when same city + new scenario arrives on the same thread.
    Run through the graph (shared thread_id) so the checkpointer carries the prior city/scenario."""
    graph = build_graph()
    config = {"configurable": {"thread_id": "switch-1"}}
    first = await graph.ainvoke(_base_state("London flooding"), config)
    assert first["is_scenario_switch"] is False, "first run should not be a switch"

    second = await graph.ainvoke(
        {"messages": [HumanMessage(content="Now show me power grid failure")]}, config
    )
    assert second["city"] == "London", second["city"]
    assert second["scenario"] == "power grid failure", second["scenario"]
    assert second["is_scenario_switch"] is True, "switch flag not set"
    print("PASS: scenario-switch flag set (London flooding → power grid failure)")


async def test_blueprint_present():
    """blueprint_node sets a valid blueprint. Without a Gemini key the fallback yields
    city_grid; with a key a power-grid query should pick network_graph (value asserted
    only when HAS_GEMINI, mirroring the score-variance gate)."""
    graph = build_graph()
    config = {"configurable": {"thread_id": "blueprint-1"}}
    result = await graph.ainvoke(_base_state("UK power grid failure"), config)

    _assert_valid_blueprint(result["blueprint"])
    if HAS_GEMINI:
        assert result["blueprint"]["scene_type"] == "network_graph", result["blueprint"]
    print(f"PASS: blueprint — scene_type={result['blueprint']['scene_type']}"
          + ("" if HAS_GEMINI else " (fallback)"))


async def main():
    await test_full_run()
    await test_combos()
    await test_impact()
    await test_scenario_switch_flag()
    await test_blueprint_present()


if __name__ == "__main__":
    asyncio.run(main())
