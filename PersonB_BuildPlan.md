# Person B — Build Plan (Agent & Orchestration)

> ## 🔄 SESSION RESTORE — read this first
> **Who:** I am Person B = agent/orchestration engine (LangGraph + Gemini + Linkup + FastAPI + CopilotKit).
> **Read in order before coding:** `SCHEMA.md` → `AGUI_PIPE.md` → this file. Skim `TeamExecutionPlan.md` (Person B section) but it is OUTDATED on transport.
> **Non-negotiables:**
> - Authority order: **SCHEMA.md > AGUI_PIPE.md > TeamExecutionPlan.md**.
> - Stream via `copilotkit_emit_state(config, state)` — shared state. **NOT** frontend `useCopilotAction`/`updateZoneRisk` (that code in TeamExecutionPlan is DEAD — wrong channel).
> - Agent name `citypulse_agent` — identical both backend and frontend.
> - Zone IDs `z_0_0`..`z_2_2`, 0-indexed 3×3. Ignore `zone_1_1` style in HackathonPlan (stale).
> - Staged 3D build = backend loop appends `zone_risks` one at a time + `asyncio.sleep(0.8)` + emit each. Backend is the ONLY clock; frontend adds no stagger.
> - Score bands (SCHEMA §2): LOW 0–0.3 / MEDIUM 0.3–0.6 / HIGH 0.6–0.8 / CRITICAL 0.8–1.0. Label derived from score; score wins on conflict.
> **Env:** Python 3.13, Node 24. Use `backend/.venv`. Install LATEST deps then freeze — do NOT use old pins (`langgraph==0.2.28` etc.) from TeamExecutionPlan; they break on 3.13.
> **Stub strategy:** Person C owns `linkup_service.py` + `redis_service.py` (due 13:00). I write working STUBS so I'm unblocked until then, swap real ones in Phase 4.
> **Progress:** check the `[ ]`/`[x]` boxes below — last unchecked box = where to resume. Repo currently: docs only, no code yet (as of first session).

My execution plan. Authority order: **SCHEMA.md > AGUI_PIPE.md > TeamExecutionPlan.md**.
Agent name `citypulse_agent` both sides. Zone IDs `z_0_0`..`z_2_2` (0-indexed). Stream via
`copilotkit_emit_state(config, state)` — shared state, NOT frontend actions.

---

## Phase 0 — Scaffold + deps (do first)

- [ ] Create dir tree:
  ```
  backend/
    main.py
    requirements.txt
    .env                 # from .env.example backend block (Person C owns real keys)
    agent/
      __init__.py
      state.py
      graph.py
      nodes/
        __init__.py
        parse_node.py
        research_node.py
        scoring_node.py
        emit_node.py
        impact_node.py
    services/
      __init__.py
      linkup_service.py   # stub until Person C delivers; my nodes import it
      redis_service.py    # stub until Person C delivers
    models/
      __init__.py
      city.py
    tests/
      test_pipe.py
  ```
- [ ] `python3 -m venv backend/.venv && source backend/.venv/bin/activate`
- [ ] Install latest (NOT old pins): `pip install langgraph langchain-google-genai fastapi uvicorn copilotkit linkup-sdk "redis[hiredis]" pydantic python-dotenv httpx`
- [ ] Freeze actual resolved versions → `requirements.txt` (`pip freeze | grep -Ei 'langgraph|langchain|fastapi|uvicorn|copilotkit|linkup|redis|pydantic|dotenv|httpx'`)
- [ ] Verify CopilotKit API surface matches plan: `python -c "import copilotkit; from copilotkit.langgraph import copilotkit_emit_state; from copilotkit.integrations.fastapi import add_fastapi_endpoint; from copilotkit import CopilotKitSDK, LangGraphAgent; print('ok')"`
  - If import names differ (SDK version drift), record real names and adapt all files. **Blocking.**

**Gate 0:** all imports resolve. Versions frozen.

---

## Phase 1 — AG-UI pipe (target 12:00, only job until green)

- [ ] `services/redis_service.py` + `services/linkup_service.py` — minimal working stubs so imports
      don't break before Person C lands real ones. Stub `LinkupService.search` returns a canned dict;
      stub `RedisService` get/set are no-ops returning None/True. Mark `# STUB — replace with Person C`.
- [ ] `agent/state.py` — `AgentState` TypedDict byte-exact to SCHEMA §3 Python view.
- [ ] `agent/graph.py` — **PIPE-TEST version only**: single `hello_node` that sets
      `status="researching"`, `research_log=["pipe test: hello from agent"]`, calls
      `copilotkit_emit_state(config, state)`, returns state. `set_entry_point("hello") → END`.
- [ ] `main.py` — FastAPI, CORS `allow_origins=["*"]`, `CopilotKitSDK(agents=[LangGraphAgent(name="citypulse_agent", ...)])`,
      `add_fastapi_endpoint(app, sdk, "/copilotkit")`, plus `GET /health`.
- [ ] Run `uvicorn main:app --reload --port 8000` from `backend/`.
- [ ] `tests/test_pipe.py` — POST a user message to `/copilotkit`, assert SSE stream contains
      `pipe test: hello from agent`. (Backend-only proof; don't wait on frontend.)
- [ ] Coordinate with Person A: chat message → string shows in sidebar <2s.

**Gate 1 (HARD 12:00):** state flows agent→frontend. If red, debug ONLY this. Use AGUI_PIPE.md failure table.

---

## Phase 2 — Full state + graph skeleton (12:00–13:00)

- [ ] Expand `agent/state.py` to full SCHEMA §3 (keep `research_results` internal, separate from `research_log`).
- [ ] `agent/graph.py` — FULL: nodes `parse_query, research, risk_scoring, emit_zones, impact`.
      Entry `parse_query`. Conditional `should_handle_impact`: `impact_query` set → `impact`, else `research`.
      Edges: `research→risk_scoring→emit_zones→END`, `impact→emit_zones`. `MemorySaver` checkpointer.
- [ ] Stub each node as pass-through returning state (so graph compiles before bodies written).
- [ ] `python -c "from agent.graph import build_graph; build_graph(); print('compiles')"`

**Gate 2 (13:00 schema lock):** graph compiles. Sit with A+C, lock interfaces. No field renames after.

---

## Phase 3 — Node bodies (13:00–15:30)

Order = dependency order. Test each in isolation with a fake state dict before wiring.

1. [ ] **parse_node** (15m) — last message → city + scenario. "what if/barrier/intervention" keywords →
       set `impact_query`. Generate `session_id` (uuid) if absent. `status="researching"`. Emit.
       - Risk: how is city/scenario actually extracted? Keyword heuristic for demo; Gemini fallback if time.
2. [ ] **research_node** (45m) — 5 query templates (city/scenario). Redis cache check first
       (`get_research`). Each query: append human line to `research_log` + emit; `linkup.search`;
       collect raw into `research_results`; `asyncio.sleep(0.3)`. Wrap each call in try/except —
       one bad query must not kill the run. Cache results.
3. [ ] **scoring_node** (45m, hardest) — Gemini `gemini-2.0-flash` temp 0.2. JSON-only system prompt,
       9 zones, score 0–1, evidence 2–3 bullets, sources ≤3. Strip ```` ```json ```` fences. Retry 3×.
       Clamp score. Derive label from score per SCHEMA §2 (score wins). Fallback uniform LOW on total fail.
       `status="scoring"`.
4. [ ] **emit_node** (20m) — SCHEMA §4 canonical staged build:
       reset `zone_risks=[]`; loop scored zones → append one → `emit_state` → `asyncio.sleep(0.8)`.
       Then `status="complete"` → final emit. Persist `city_state` to Redis. **No frontend stagger — this is the only clock.**
5. [ ] **impact_node** (30m) — Linkup search the intervention → Gemini re-scores ONLY affected zones →
       merge back into full `zone_risks` → set `impact_summary`, clear `impact_query` → routes to emit_node.

**Gate 3 (15:30):** "London flooding" → research_log streams → 9 zones emit 800ms apart → A's 3D builds zone-by-zone.

---

## Phase 4 — Tune + harden (15:30–17:30)

- [ ] Tune scoring prompt until scores varied/realistic across zones (not uniform).
- [ ] Test 3+ combos: London flooding, NYC power grid failure, Tokyo transport disruption.
- [ ] Linkup 429 exponential backoff (confirm Person C's service handles; else add in node).
- [ ] Impact test: "What if London built a flood barrier at zone 4" → only affected zones recolour.
- [ ] Scenario switch reuses Redis cache (no re-research same city+scenario).
- [ ] Pair with Person A on any stream/integration bugs.
- [ ] Swap Person C's real `linkup_service`/`redis_service` in; delete my stubs.

---

## Phase 5 — Freeze (17:30)

- [ ] No new features. Demo path only:
      "London flooding" → progress → 3D builds → click zone → card → "what if barrier zone 4" → recolour.
- [ ] Fallback ready: if core loop broken at 17:00, **cut impact_node** — 4-step demo > broken 6-step.

---

## Open questions / risks to resolve while building
- CopilotKit SDK version may rename `copilotkit_emit_state` / endpoint helpers → verify in Phase 0.
- City/scenario extraction method (heuristic vs Gemini) — decide in parse_node, keep cheap.
- Linkup response shape (`answer`/`sources` keys) — confirm against real API in Phase 3, adjust research_node.
- Person C dependency: real services by 13:00. My stubs unblock me until then.
