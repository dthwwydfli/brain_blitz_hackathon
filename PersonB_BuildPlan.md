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
> **Stub strategy:** Person C never delivered `linkup_service.py`/`redis_service.py`. Phase 4 decision (user-confirmed): **I built the real ones myself** (linkup-sdk + redis.asyncio). Both degrade safely when keys absent. Swap C's in only if more robust.
> **⚠ Phase 4 blocker:** `.env` keys all empty/placeholder — live verification blocked until Person C drops real `GEMINI_API_KEY`/`LINKUP_API_KEY`/`REDIS_URL`+`REDIS_TOKEN`. Code complete + structurally green via fallbacks; re-run `tests/test_pipe.py` once keys land.
> **Progress:** Phases 0–4 code done. Only open items: Person A stream pairing (Gate 1/3 live) + live re-verify after keys land. Phase 5 = freeze.

My execution plan. Authority order: **SCHEMA.md > AGUI_PIPE.md > TeamExecutionPlan.md**.
Agent name `citypulse_agent` both sides. Zone IDs `z_0_0`..`z_2_2` (0-indexed). Stream via
`copilotkit_emit_state(config, state)` — shared state, NOT frontend actions.

---

## ✅ RESOLVED API (copilotkit 0.1.94 / langgraph 1.2.5 — verified Phase 0)
> Names DRIFTED from TeamExecutionPlan. Use THESE:
> - `from copilotkit import CopilotKitRemoteEndpoint, LangGraphAGUIAgent` — **NOT** `CopilotKitSDK` / `LangGraphAgent`.
> - `LangGraphAGUIAgent(name="citypulse_agent", graph=build_graph(), description=...)` (keyword-only).
> - `endpoint = CopilotKitRemoteEndpoint(agents=[agent])`
> - `from copilotkit.integrations.fastapi import add_fastapi_endpoint` → `add_fastapi_endpoint(app, endpoint, "/copilotkit")`
> - `from copilotkit.langgraph import copilotkit_emit_state` → `await copilotkit_emit_state(config, state)` (unchanged).
> - Graph must be a compiled `CompiledStateGraph` (pass `build_graph()`).
> Frozen versions in `backend/requirements.txt`.

## Phase 0 — Scaffold + deps ✅ DONE

- [x] Create dir tree:
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
- [x] `python3 -m venv backend/.venv` (use `backend/.venv/bin/python` directly; no activate needed)
- [x] Install latest (NOT old pins). Done — versions higher than plan expected (see RESOLVED API block).
- [x] Freeze resolved versions → `backend/requirements.txt`.
- [x] Verify CopilotKit API surface. Found drift: `LangGraphAgent`→`LangGraphAGUIAgent`, `CopilotKitSDK`→`CopilotKitRemoteEndpoint`. Recorded above.

**Gate 0 ✅:** all imports resolve. Versions frozen. API drift mapped.

---

## Phase 1 — AG-UI pipe (target 12:00, only job until green)

- [x] `services/redis_service.py` + `services/linkup_service.py` — minimal working stubs so imports
      don't break before Person C lands real ones. Stub `LinkupService.search` returns a canned dict;
      stub `RedisService` get/set are no-ops returning None/True. Mark `# STUB — replace with Person C`.
- [x] `agent/state.py` — `AgentState` TypedDict byte-exact to SCHEMA §3 Python view.
- [x] `agent/graph.py` — **PIPE-TEST version only**: single `hello_node` that sets
      `status="researching"`, `research_log=["pipe test: hello from agent"]`, calls
      `copilotkit_emit_state(config, state)`, returns state. `set_entry_point("hello") → END`.
- [x] `main.py` — FastAPI, CORS `allow_origins=["*"]`. NOTE drift: use RESOLVED API
      `LangGraphAGUIAgent(...)` + `CopilotKitRemoteEndpoint(agents=[...])` (NOT `CopilotKitSDK`/`LangGraphAgent`),
      `add_fastapi_endpoint(app, endpoint, "/copilotkit")`, plus `GET /health`.
- [x] Run `uvicorn main:app --reload --port 8000` from `backend/` — boots clean, `/health` → `{"status":"ok"}`.
- [x] `tests/test_pipe.py` — no pytest dep; run `.venv/bin/python tests/test_pipe.py`. Invokes graph,
      asserts `research_log == ["pipe test: hello from agent"]` + `status=="researching"`. PASS.
      (Manual SSE smoke via curl documented in docstring; full handshake validated with Person A.)
- [ ] Coordinate with Person A: chat message → string shows in sidebar <2s. **← resume here (Gate 1, 12:00)**

**Gate 1 (HARD 12:00):** state flows agent→frontend. If red, debug ONLY this. Use AGUI_PIPE.md failure table.

---

## Phase 2 — Full state + graph skeleton (12:00–13:00)

- [x] Expand `agent/state.py` to full SCHEMA §3 (keep `research_results` internal, separate from `research_log`).
      (Already full from Phase 1 — verified, no change.)
- [x] `agent/graph.py` — FULL: nodes `parse_query, research, risk_scoring, emit_zones, impact`.
      Entry `parse_query`. Conditional `should_handle_impact`: `impact_query` set → `impact`, else `research`.
      Edges: `research→risk_scoring→emit_zones→END`, `impact→emit_zones`. `MemorySaver` checkpointer.
- [x] Stub each node as pass-through returning state (so graph compiles before bodies written).
      Files: `parse_node`/`research_node`/`scoring_node`/`emit_node`/`impact_node` in `agent/nodes/`.
- [x] `python -c "from agent.graph import build_graph; build_graph(); print('compiles')"` → `compiles`.
      NOTE: `tests/test_pipe.py` now expected-red (asserts dropped `hello_node`; also needs `thread_id`
      in config now MemorySaver is wired). Rewrite in Phase 3 against real node output.

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

> **⚠ KEY BLOCKER (Person C):** `backend/.env` keys are all EMPTY/placeholder
> (`GEMINI_API_KEY`/`LINKUP_API_KEY`/`REDIS_TOKEN` empty; `REDIS_URL=rediss://your-upstash-url`).
> Code is complete + structurally verified via graceful-degradation fallbacks (uniform-LOW
> scoring, canned Linkup, no-op Redis). **Live verification (score variance, real research,
> cache reuse) is BLOCKED until Person C drops real keys.** Re-run `tests/test_pipe.py` once
> keys land — the `HAS_GEMINI` gate auto-enables the ≥2-band variance assertion.

- [x] **Built real services myself** (Person C never delivered): `services/linkup_service.py` uses
      `linkup-sdk` `async_search` (sourcedAnswer → `{answer, sources:[{title,url}]}`);
      `services/redis_service.py` uses `redis.asyncio.from_url` on the `rediss://` URL, SCHEMA §5 keys,
      TTL 7200. Both degrade safely (canned / no-op) when keys absent. Interfaces byte-identical to old
      stubs — zero node changes. Swap Person C's in later only if more robust.
- [x] Tune scoring prompt — `_build_prompt` now demands score spread (≥1 HIGH/CRITICAL + ≥1 LOW),
      ties scores to grid geography, cites research. (Variance unverifiable until Gemini key lands.)
- [x] Test 3+ combos — `tests/test_pipe.py` runs London flooding / NYC power grid / Tokyo transport;
      asserts 9 valid zones each. ≥2-band variance asserted only when `GEMINI_API_KEY` set.
- [x] Linkup 429 exponential backoff — in `linkup_service.search` (0.5→1→2s on
      `LinkupTooManyRequestsError`/transient), node try/except is outer net.
- [x] Impact test — `test_impact`: "what if flood barrier at zone 4" → 9 zones intact,
      `impact_summary` set, `impact_query` cleared.
- [x] Scenario switch — `parse_node` now sets `is_scenario_switch` (same city, new scenario);
      `research_node` cache reuse path ready (`test_scenario_switch_flag` green). Cache HIT needs real Redis.
- [ ] Pair with Person A on any stream/integration bugs. (N/A this session — solo.)
- [x] ~~Swap Person C's real services in~~ → superseded: built real services myself (above).

**All 6 structural tests green via fallback. `/health` boots OK (`redis:disconnected` w/ placeholder).**

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
