# CityPulse — AG-UI Pipe (the one thing that must work)

**Decision:** Use the CopilotKit **CoAgent shared-state** pattern, not frontend actions. This is what the `open-multi-agent-canvas` starter uses. Everyone codes to this — no second approach.

If this pipe is not flowing by **12:00**, stop all other work and debug only this. Nothing else matters if state doesn't reach the 3D scene.

---

## The mistake we are avoiding

The original TeamPlan mixed two incompatible channels:

- Backend: `copilotkit_emit_state(config, {...})`  → pushes **agent state**
- Frontend: `useCopilotAction({ name: "updateZoneRisk", handler })` → receives **agent-invoked tool calls**

These are different transports. State emitted with `emit_state` does **not** trigger `useCopilotAction` handlers. As written, the city would never update. **Pick one channel: shared state.**

---

## How it actually flows

```
LangGraph node mutates state.zone_risks
        │
        ▼
copilotkit_emit_state(config, state)        # backend pushes whole state object
        │  (SSE over AG-UI)
        ▼
useCoAgent<CityAgentState>({ name: "citypulse_agent" })   # frontend subscribes
        │
        ▼
Zustand mirror  →  CityCanvas re-renders zones from state.zone_risks
```

One direction for the demo: **agent → frontend**. The chat input (city + scenario) goes the normal CopilotKit way (user message → agent run).

---

## Backend side

Agent name must match on both sides: **`citypulse_agent`**.

```python
# main.py
sdk = CopilotKitSDK(
    agents=[
        LangGraphAgent(
            name="citypulse_agent",          # <-- frontend must use this exact name
            description="Infrastructure risk intelligence agent",
            graph=build_graph(),
        )
    ]
)
add_fastapi_endpoint(app, sdk, "/copilotkit")
```

Emit the **whole state object** after each meaningful change:

```python
from copilotkit.langgraph import copilotkit_emit_state

await copilotkit_emit_state(config, state)
```

Call it: once when research starts (`status="researching"`), on each `research_log` append, after each `zone_risks` append (with the 800ms gap — see SCHEMA §4), and once at `status="complete"`.

State keys emitted must match `CityAgentState` in `SCHEMA.md` §3 exactly.

---

## Frontend side

```tsx
// lib/useCityAgent.ts
import { useCoAgent } from "@copilotkit/react-core";
import { useEffect } from "react";
import { useCityStore } from "./cityStore";

export interface CityAgentState {
  city: string;
  scenario: string;
  session_id: string;
  status: "idle" | "researching" | "scoring" | "complete";
  research_log: string[];
  zone_risks: {
    zone_id: string;
    score: number;
    label: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
    evidence: string[];
    sources: { title: string; url: string }[];
  }[];
  impact_summary: string | null;
}

export function useCityAgent() {
  const { state } = useCoAgent<CityAgentState>({
    name: "citypulse_agent",          // <-- must match backend
    initialState: {
      city: "", scenario: "", session_id: "",
      status: "idle", research_log: [], zone_risks: [], impact_summary: null,
    },
  });

  // Mirror agent state into Zustand so the 3D scene + cards read one source
  const syncFromAgent = useCityStore((s) => s.syncFromAgent);
  useEffect(() => {
    if (state) syncFromAgent(state);
  }, [state, syncFromAgent]);

  return state;
}
```

Zustand store gains one method instead of the old per-zone actions:

```ts
// lib/cityStore.ts  — replaces updateZone/startResearch/researchComplete actions
syncFromAgent: (s: CityAgentState) => set({
  city: s.city,
  scenario: s.scenario,
  isResearching: s.status === "researching" || s.status === "scoring",
  zones: Object.fromEntries(
    s.zone_risks.map((z) => [z.zone_id, {
      score: z.score, label: z.label,
      evidence: z.evidence, sources: z.sources,
      visible: true,                 // present in array = visible
    }])
  ),
}),
```

A zone not yet in `zone_risks` keeps its default `{ visible: false }` and stays hidden — that is the staged build, for free.

---

## The 12:00 pipe test (do this first, both A + B)

Minimal graph that proves state flows:

```python
# graph.py — PIPE TEST ONLY
async def hello_node(state, config):
    state["status"] = "researching"
    state["research_log"] = ["pipe test: hello from agent"]
    await copilotkit_emit_state(config, state)
    return state
```

Frontend: render `state.research_log` somewhere visible.

**Pass condition:** type anything in chat → `"pipe test: hello from agent"` shows in the sidebar within ~2s. When that works, the product is de-risked. Build everything else on top.

---

## Quick failure checklist

| Symptom | Likely cause |
|---|---|
| Frontend state stays `idle` | agent `name` mismatch (`citypulse_agent` both sides) |
| State updates once then stops | not calling `emit_state` after each mutation |
| Zones all appear at once | missing `await asyncio.sleep(0.8)` between appends |
| CORS error in console | `allow_origins=["*"]` missing in FastAPI middleware |
| 404 on `/copilotkit` | `NEXT_PUBLIC_API_URL` wrong or backend not on :8000 |
| Nothing streams | runtime route not pointing remoteAction at backend `/copilotkit` |
