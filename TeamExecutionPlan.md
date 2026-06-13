# CityPulse — Team Execution Plan
### Hour-by-Hour, Task-by-Task for 3 Seniors
**Hacking window: 11:30 → 18:00 | Feature freeze: 17:30 | Demo: 19:00**

---

## Pre-Hack Checklist (do tonight, before the event)

All three people do this independently before arriving:

```bash
# Clone CopilotKit starter
git clone https://github.com/CopilotKit/open-multi-agent-canvas
cd open-multi-agent-canvas

# Install frontend deps
cd frontend && npm install

# Install backend deps
cd agent && pip install -r requirements.txt
```

- [ ] Sign up for Linkup API key → linkup.so (free tier available)
- [ ] Sign up for Upstash Redis → upstash.com (free tier, get REST URL + token)
- [ ] Confirm Gemini API key works via GCP credits (aistudio.google.com)
- [ ] Everyone has the repo cloned and running locally
- [ ] Agree on a shared `.env` file — Person C owns this, shares via WhatsApp at 11:00
- [ ] Pre-test this Linkup query manually tonight:
  ```
  curl -X POST https://api.linkup.so/v1/search \
    -H "Authorization: Bearer YOUR_KEY" \
    -H "Content-Type: application/json" \
    -d '{"q": "London flooding infrastructure risk 2024", "depth": "standard"}'
  ```
  If it returns good data, you're green. If not, try "Thames flood risk report 2024".

---

## Hard Milestones — Non-Negotiable

| Time | Milestone | Owner |
|------|-----------|-------|
| 11:30 | Hacking starts — everyone on task immediately | All |
| 12:00 | AG-UI SSE pipe tested end-to-end (data flows agent→frontend) | B + A |
| 13:00 | Schema lock — no interface changes after this | All |
| 13:00 | Static 3D city grid rendering in browser | A |
| 13:00 | LangGraph research node returning Linkup data | B |
| 13:00 | Redis read/write confirmed working | C |
| 15:30 | Full integration — agent scores driving 3D zone colours | All |
| 16:30 | Zone click → detail card working end-to-end | A + B |
| 17:00 | "What if" impact query working | B |
| 17:30 | FEATURE FREEZE — no new features, polish only | All |
| 17:45 | Demo run-through — time it, fix anything broken | All |
| 18:00 | Hacking ends | All |

---

---

# PERSON A — Frontend & 3D Scene

**Your domain:** Everything the judges see. The 3D city, the animations, the cards, the sidebar, the layout. You own the wow moment.

**Your north star:** At 15:30, when Person B streams the first zone score over AG-UI, your 3D city must respond. That integration point is the whole product.

---

## 11:30 — 12:00 | Project Bootstrap (30 min)

**Goal:** Running Next.js app in browser with CopilotKit wired.

```bash
cd frontend
npm install @react-three/fiber @react-three/drei three @react-spring/three zustand
npm install @copilotkit/react-core @copilotkit/react-ui
```

Create the root layout with CopilotKit provider:

```tsx
// app/layout.tsx
import { CopilotKit } from "@copilotkit/react-core";

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <CopilotKit runtimeUrl="/api/copilotkit">
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
```

Create the main page split layout — left 65% is 3D canvas, right 35% is agent sidebar:

```tsx
// app/page.tsx
import CityCanvas from "@/components/CityCanvas";
import AgentSidebar from "@/components/AgentSidebar";

export default function Home() {
  return (
    <main className="flex h-screen bg-[#0a0a1a] text-white overflow-hidden">
      <div className="flex-1">
        <CityCanvas />
      </div>
      <div className="w-[380px] border-l border-white/10">
        <AgentSidebar />
      </div>
    </main>
  );
}
```

Set up Zustand store — this is the single source of truth for zone state:

```tsx
// lib/cityStore.ts
import { create } from "zustand";

export type RiskLabel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface ZoneState {
  score: number;
  label: RiskLabel;
  evidence: string[];
  sources: { title: string; url: string }[];
  visible: boolean;
}

interface CityStore {
  city: string;
  scenario: string;
  zones: Record<string, ZoneState>;
  selectedZone: string | null;
  isResearching: boolean;
  setCity: (city: string) => void;
  setScenario: (scenario: string) => void;
  updateZone: (zoneId: string, data: Partial<ZoneState>) => void;
  setSelectedZone: (zoneId: string | null) => void;
  setIsResearching: (v: boolean) => void;
  resetZones: () => void;
}

const ZONE_IDS = [
  "z_0_0","z_0_1","z_0_2",
  "z_1_0","z_1_1","z_1_2",
  "z_2_0","z_2_1","z_2_2",
];

export const useCityStore = create<CityStore>((set) => ({
  city: "",
  scenario: "",
  zones: Object.fromEntries(
    ZONE_IDS.map(id => [id, { score: 0, label: "LOW", evidence: [], sources: [], visible: false }])
  ),
  selectedZone: null,
  isResearching: false,
  setCity: (city) => set({ city }),
  setScenario: (scenario) => set({ scenario }),
  updateZone: (zoneId, data) =>
    set((state) => ({
      zones: { ...state.zones, [zoneId]: { ...state.zones[zoneId], ...data } }
    })),
  setSelectedZone: (selectedZone) => set({ selectedZone }),
  setIsResearching: (isResearching) => set({ isResearching }),
  resetZones: () =>
    set((state) => ({
      zones: Object.fromEntries(
        Object.keys(state.zones).map(id => [id, { score: 0, label: "LOW", evidence: [], sources: [], visible: false }])
      )
    })),
}));
```

**Checkpoint 11:45:** `npm run dev` serves a page. No errors in console.

---

## 12:00 — 13:00 | Static 3D City Grid (60 min)

**Goal:** A beautiful static 3D city on screen before schema lock. No agent data yet — just geometry.

```tsx
// components/CityCanvas.tsx
"use client";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment } from "@react-three/drei";
import CityGrid from "./CityGrid";

export default function CityCanvas() {
  return (
    <Canvas
      camera={{ position: [12, 14, 12], fov: 45 }}
      shadows
      className="w-full h-full"
    >
      <color attach="background" args={["#0a0a1a"]} />
      <ambientLight intensity={0.3} />
      <directionalLight position={[10, 20, 10]} intensity={1} castShadow />
      <fog attach="fog" args={["#0a0a1a", 30, 60]} />
      <CityGrid />
      {/* Lock camera — no free roam in demo */}
      <OrbitControls
        enablePan={false}
        enableZoom={false}
        enableRotate={false}
      />
    </Canvas>
  );
}
```

```tsx
// components/CityGrid.tsx
"use client";
import { useMemo } from "react";
import RiskZone from "./RiskZone";

// 3x3 grid, each zone at a world position
const ZONE_LAYOUT = [
  { id: "z_0_0", position: [-6, 0, -6] as [number,number,number] },
  { id: "z_0_1", position: [0,  0, -6] as [number,number,number] },
  { id: "z_0_2", position: [6,  0, -6] as [number,number,number] },
  { id: "z_1_0", position: [-6, 0,  0] as [number,number,number] },
  { id: "z_1_1", position: [0,  0,  0] as [number,number,number] },
  { id: "z_1_2", position: [6,  0,  0] as [number,number,number] },
  { id: "z_2_0", position: [-6, 0,  6] as [number,number,number] },
  { id: "z_2_1", position: [0,  0,  6] as [number,number,number] },
  { id: "z_2_2", position: [6,  0,  6] as [number,number,number] },
];

export default function CityGrid() {
  return (
    <group>
      {/* Ground plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, 0]} receiveShadow>
        <planeGeometry args={[22, 22]} />
        <meshStandardMaterial color="#111122" />
      </mesh>
      {/* Grid lines — thin road network */}
      <gridHelper args={[22, 6, "#1a1a3a", "#1a1a3a"]} />
      {ZONE_LAYOUT.map((zone) => (
        <RiskZone key={zone.id} id={zone.id} position={zone.position} />
      ))}
    </group>
  );
}
```

```tsx
// components/RiskZone.tsx
"use client";
import { useRef, useMemo } from "react";
import { useSpring, animated } from "@react-spring/three";
import { useCityStore } from "@/lib/cityStore";

// Seeded random for consistent building layout per zone
function seededRandom(seed: number) {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

function getRiskColour(score: number): string {
  if (score >= 0.8) return "#dc2626"; // critical red
  if (score >= 0.6) return "#f87171"; // high red
  if (score >= 0.3) return "#fb923c"; // amber
  return "#4ade80";                    // safe green
}

interface RiskZoneProps {
  id: string;
  position: [number, number, number];
}

export default function RiskZone({ id, position }: RiskZoneProps) {
  const zone = useCityStore((s) => s.zones[id]);
  const setSelectedZone = useCityStore((s) => s.setSelectedZone);

  // Generate 6–9 buildings per zone from seeded random
  const buildings = useMemo(() => {
    const seed = id.charCodeAt(2) * 100 + id.charCodeAt(4);
    const count = 6 + Math.floor(seededRandom(seed) * 4);
    return Array.from({ length: count }, (_, i) => ({
      x: (seededRandom(seed + i * 7) - 0.5) * 3.5,
      z: (seededRandom(seed + i * 13) - 0.5) * 3.5,
      height: 0.4 + seededRandom(seed + i * 3) * 1.8,
      width: 0.3 + seededRandom(seed + i * 5) * 0.5,
    }));
  }, [id]);

  // Materialisation animation — triggered when zone becomes visible
  const { scaleY, opacity } = useSpring({
    scaleY: zone.visible ? 1 : 0,
    opacity: zone.visible ? 1 : 0,
    config: { tension: 120, friction: 14 },
  });

  const colour = getRiskColour(zone.score);

  return (
    <group position={position}>
      {buildings.map((b, i) => (
        <animated.mesh
          key={i}
          position={[b.x, b.height / 2, b.z]}
          scale-y={scaleY}
          castShadow
          onClick={() => zone.visible && setSelectedZone(id)}
          onPointerOver={(e) => { e.stopPropagation(); document.body.style.cursor = "pointer"; }}
          onPointerOut={() => { document.body.style.cursor = "auto"; }}
        >
          <boxGeometry args={[b.width, b.height, b.width]} />
          <meshStandardMaterial
            color={colour}
            emissive={colour}
            emissiveIntensity={zone.score >= 0.8 ? 0.3 : 0.05}
            transparent
          />
        </animated.mesh>
      ))}
      {/* Zone base plate */}
      <mesh position={[0, -0.02, 0]} rotation={[-Math.PI/2, 0, 0]}>
        <planeGeometry args={[4.5, 4.5]} />
        <meshStandardMaterial
          color={colour}
          transparent
          opacity={zone.visible ? 0.08 : 0}
        />
      </mesh>
    </group>
  );
}
```

**Checkpoint 13:00:** Static city renders. 9 zones visible (all green for now). Buildings are distinct shapes. Camera is locked. Click on a zone logs the zone ID to console.

---

## 13:00 — 13:15 | Schema Lock

Stop. Read the schema section in HACKATHON_PLAN.md with Person B and C. Agree on zone score event format. Do not start the next phase until all three of you have agreed.

---

## 13:15 — 15:30 | Wire Agent Data to 3D Scene (135 min)

**Goal:** When the agent emits zone scores via AG-UI, the 3D city responds.

> ⚠️ **SUPERSEDED TRANSPORT.** The `useCopilotAction` / `updateZoneRisk` / `setTimeout`-stagger code below does **not** work — it listens on the wrong CopilotKit channel (see `AGUI_PIPE.md` "The mistake we are avoiding"). Use the **CoAgent shared-state** pattern instead: `useCoAgent<CityAgentState>({ name: "citypulse_agent" })` → `syncFromAgent` into Zustand. Full replacement code in `AGUI_PIPE.md`. The `ResearchProgress` and `ZoneDetailCard` components below are still correct — keep them. Only the `AgentSidebar` action wiring is replaced.

Set up the CopilotKit action that listens for zone score updates from the agent:

```tsx
// components/AgentSidebar.tsx
"use client";
import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { useCityStore } from "@/lib/cityStore";
import ZoneDetailCard from "./ZoneDetailCard";
import ResearchProgress from "./ResearchProgress";

export default function AgentSidebar() {
  const { city, scenario, zones, selectedZone, updateZone, setIsResearching, resetZones } = useCityStore();

  // Make city state readable to the agent
  useCopilotReadable({
    description: "Current city and risk scenario being analysed",
    value: { city, scenario, zonesScored: Object.values(zones).filter(z => z.visible).length },
  });

  // Agent calls this to update a zone's risk score
  // This is the critical integration point — fires when agent completes a zone
  useCopilotAction({
    name: "updateZoneRisk",
    description: "Update a zone's risk score and evidence from agent research",
    parameters: [
      { name: "zone_id", type: "string", description: "Zone identifier e.g. z_0_0" },
      { name: "score", type: "number", description: "Risk score 0.0 to 1.0" },
      { name: "label", type: "string", description: "LOW | MEDIUM | HIGH | CRITICAL" },
      { name: "evidence", type: "object", description: "Array of evidence strings" },
      { name: "sources", type: "object", description: "Array of {title, url} source objects" },
    ],
    handler: ({ zone_id, score, label, evidence, sources }) => {
      // Stagger zone materialisation by 800ms per zone for visual drama
      const zoneIndex = Object.keys(zones).indexOf(zone_id);
      setTimeout(() => {
        updateZone(zone_id, {
          score,
          label: label as any,
          evidence: evidence as string[],
          sources: sources as any[],
          visible: true,
        });
      }, zoneIndex * 200); // slight stagger even within the 800ms window
    },
  });

  // Agent calls this to signal research has started
  useCopilotAction({
    name: "startResearch",
    description: "Signal that agent research has begun — reset city state",
    parameters: [
      { name: "city", type: "string" },
      { name: "scenario", type: "string" },
    ],
    handler: ({ city, scenario }) => {
      resetZones();
      setIsResearching(true);
      useCityStore.getState().setCity(city);
      useCityStore.getState().setScenario(scenario);
    },
  });

  // Agent calls this when all research is complete
  useCopilotAction({
    name: "researchComplete",
    description: "Signal that all zone research is complete",
    parameters: [],
    handler: () => {
      setIsResearching(false);
    },
  });

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-white/10">
        <h1 className="text-lg font-bold text-white">CityPulse</h1>
        <p className="text-xs text-white/40">Infrastructure Risk Intelligence</p>
      </div>
      <ResearchProgress />
      {selectedZone && zones[selectedZone]?.visible && (
        <ZoneDetailCard zoneId={selectedZone} zone={zones[selectedZone]} />
      )}
      <div className="flex-1">
        <CopilotChat
          instructions="You are CityPulse, an infrastructure risk intelligence agent. When given a city and risk scenario, research it thoroughly and call updateZoneRisk for each of the 9 zones."
          className="h-full"
        />
      </div>
    </div>
  );
}
```

```tsx
// components/ResearchProgress.tsx
"use client";
import { useCityStore } from "@/lib/cityStore";

export default function ResearchProgress() {
  const { isResearching, city, scenario, zones } = useCityStore();
  const scored = Object.values(zones).filter(z => z.visible).length;

  if (!city) return null;

  return (
    <div className="p-4 border-b border-white/10 text-sm">
      <div className="flex items-center gap-2 mb-2">
        {isResearching && (
          <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
        )}
        <span className="text-white/60">
          {isResearching ? `Researching ${city} — ${scenario}` : `${city} — ${scenario}`}
        </span>
      </div>
      <div className="w-full bg-white/10 rounded-full h-1">
        <div
          className="bg-blue-400 h-1 rounded-full transition-all duration-500"
          style={{ width: `${(scored / 9) * 100}%` }}
        />
      </div>
      <p className="text-white/30 text-xs mt-1">{scored}/9 zones analysed</p>
    </div>
  );
}
```

```tsx
// components/ZoneDetailCard.tsx
"use client";
import { ZoneState } from "@/lib/cityStore";

interface Props {
  zoneId: string;
  zone: ZoneState;
}

const LABEL_COLOURS = {
  LOW: "text-green-400 bg-green-400/10",
  MEDIUM: "text-orange-400 bg-orange-400/10",
  HIGH: "text-red-400 bg-red-400/10",
  CRITICAL: "text-red-300 bg-red-300/10 animate-pulse",
};

export default function ZoneDetailCard({ zoneId, zone }: Props) {
  return (
    <div className="m-4 p-4 rounded-lg border border-white/10 bg-white/5">
      <div className="flex justify-between items-start mb-3">
        <div>
          <p className="text-xs text-white/40 uppercase tracking-wider">Zone {zoneId.replace("z_","").replace("_","-")}</p>
          <p className="text-white font-semibold mt-0.5">Risk Assessment</p>
        </div>
        <span className={`text-xs font-bold px-2 py-1 rounded ${LABEL_COLOURS[zone.label]}`}>
          {zone.label}
        </span>
      </div>
      <div className="mb-3">
        <div className="flex justify-between text-xs text-white/40 mb-1">
          <span>Risk Score</span>
          <span>{(zone.score * 100).toFixed(0)}%</span>
        </div>
        <div className="w-full bg-white/10 rounded-full h-2">
          <div
            className="h-2 rounded-full transition-all duration-700"
            style={{
              width: `${zone.score * 100}%`,
              backgroundColor: zone.score >= 0.8 ? "#dc2626" : zone.score >= 0.6 ? "#f87171" : zone.score >= 0.3 ? "#fb923c" : "#4ade80"
            }}
          />
        </div>
      </div>
      <div className="space-y-1 mb-3">
        {zone.evidence.map((e, i) => (
          <div key={i} className="flex gap-2 text-xs text-white/60">
            <span className="text-white/30 mt-0.5">•</span>
            <span>{e}</span>
          </div>
        ))}
      </div>
      {zone.sources.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-2 border-t border-white/10">
          {zone.sources.map((s, i) => (
            <a key={i} href={s.url} target="_blank" className="text-xs text-blue-400 hover:underline">
              {s.title}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
```

Wire up the AG-UI API route:

```typescript
// app/api/copilotkit/route.ts
import { CopilotRuntime, LangChainAdapter } from "@copilotkit/runtime";
import { NextRequest } from "next/server";

export const POST = async (req: NextRequest) => {
  const runtime = new CopilotRuntime({
    remoteActions: [
      {
        url: `${process.env.NEXT_PUBLIC_API_URL}/copilotkit`,
      },
    ],
  });
  return runtime.response(req);
};
```

**Checkpoint 15:30:** Manually call `updateZoneRisk` from browser console → zone materialises in 3D scene with correct colour. All 9 zones can be triggered. Zone click opens detail card.

---

## 15:30 — 16:30 | Polish & Integration Testing (60 min)

At this point Person B should be streaming real agent data. Your job now is making it look excellent.

**Pulsing animation for CRITICAL zones:**

```tsx
// Add to RiskZone.tsx — useFrame for pulsing emissive on critical zones
import { useFrame } from "@react-three/fiber";
import { useRef } from "react";

// Inside the component:
const matRef = useRef<THREE.MeshStandardMaterial>(null);
useFrame(({ clock }) => {
  if (matRef.current && zone.label === "CRITICAL") {
    matRef.current.emissiveIntensity = 0.2 + Math.sin(clock.elapsedTime * 3) * 0.2;
  }
});
// Add ref={matRef} to meshStandardMaterial
```

**Scenario switcher component:**

```tsx
// components/ScenarioSwitcher.tsx
const SCENARIOS = ["flooding", "power grid failure", "transport disruption", "air quality"];

export default function ScenarioSwitcher() {
  const scenario = useCityStore(s => s.scenario);
  return (
    <div className="flex gap-2 p-4 border-b border-white/10 overflow-x-auto">
      {SCENARIOS.map(s => (
        <button
          key={s}
          className={`text-xs px-3 py-1.5 rounded-full whitespace-nowrap transition-colors ${
            scenario === s
              ? "bg-blue-500 text-white"
              : "bg-white/5 text-white/50 hover:bg-white/10"
          }`}
        >
          {s}
        </button>
      ))}
    </div>
  );
}
```

**Checkpoint 16:30:** Full loop works. Query → research progress visible → zones materialise one by one → click zone → card appears. Demo is runnable.

---

## 16:30 — 17:30 | Final Polish (60 min)

- Add a city name label floating above the 3D scene using `<Html>` from drei
- Add subtle particle/fog effect to give atmosphere
- Make the progress bar in sidebar animate smoothly
- Test on demo machine — not just your laptop
- Record a backup screen capture in case live demo has issues
- **DO NOT add new features. Polish only.**

---
---

# PERSON B — Agent & Orchestration

**Your domain:** The intelligence layer. LangGraph, Gemini, Linkup, the agent loop, FastAPI endpoints. You are the engine.

**Your north star:** At 12:00, data must flow through AG-UI from your backend to Person A's frontend. Everything else is secondary to that pipe working.

---

## 11:30 — 12:00 | AG-UI Pipe First (30 min)

**This is your only job for the first 30 minutes. Nothing else.**

```bash
mkdir -p backend/agent backend/services backend/models
cd backend
pip install langgraph langchain-google-genai fastapi uvicorn copilotkit linkup-sdk redis pydantic python-dotenv
```

```python
# backend/main.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitSDK, LangGraphAgent
from agent.graph import build_graph

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

sdk = CopilotKitSDK(
    agents=[
        LangGraphAgent(
            name="citypulse_agent",
            description="Infrastructure risk intelligence agent",
            graph=build_graph(),
        )
    ]
)

add_fastapi_endpoint(app, sdk, "/copilotkit")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

Minimal graph that just proves the pipe works:

```python
# backend/agent/graph.py — MINIMAL VERSION for pipe test
from langgraph.graph import StateGraph, END
from copilotkit.langgraph import copilotkit_emit_message
from typing import TypedDict, Annotated
import operator

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    city: str
    scenario: str

async def hello_node(state: AgentState, config):
    # Emit a test action to prove the pipe works
    await copilotkit_emit_message(config, "Testing pipe — if you see this in the frontend, we're good.")
    return state

def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("hello", hello_node)
    graph.set_entry_point("hello")
    graph.add_edge("hello", END)
    return graph.compile()
```

```bash
uvicorn main:app --reload --port 8000
```

Go to Person A and confirm a message appears in their CopilotChat from the agent. **This must be done by 12:00.** If not working, debug this exclusively — do not move on.

---

## 12:00 — 13:00 | Full State Schema & LangGraph Architecture (60 min)

```python
# backend/agent/state.py
from typing import TypedDict, Annotated, Optional
import operator

class ZoneRisk(TypedDict):
    zone_id: str
    score: float          # 0.0 – 1.0
    label: str            # LOW | MEDIUM | HIGH | CRITICAL
    evidence: list[str]   # 2–4 bullet strings
    sources: list[dict]   # [{title, url}]

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    city: str
    scenario: str
    session_id: str
    research_results: list[dict]       # raw Linkup output
    zone_risks: list[ZoneRisk]         # scored zones
    impact_query: Optional[str]        # "what if" question
    is_scenario_switch: bool           # true if switching existing city
```

Full LangGraph graph:

```python
# backend/agent/graph.py — FULL VERSION
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agent.state import AgentState
from agent.nodes.parse_node import parse_query_node
from agent.nodes.research_node import research_node
from agent.nodes.scoring_node import risk_scoring_node
from agent.nodes.emit_node import emit_zones_node
from agent.nodes.impact_node import impact_assessment_node

def should_handle_impact(state: AgentState) -> str:
    if state.get("impact_query"):
        return "impact"
    return "research"

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("parse_query", parse_query_node)
    graph.add_node("research", research_node)
    graph.add_node("risk_scoring", risk_scoring_node)
    graph.add_node("emit_zones", emit_zones_node)
    graph.add_node("impact", impact_assessment_node)

    graph.set_entry_point("parse_query")

    graph.add_conditional_edges("parse_query", should_handle_impact, {
        "research": "research",
        "impact": "impact",
    })

    graph.add_edge("research", "risk_scoring")
    graph.add_edge("risk_scoring", "emit_zones")
    graph.add_edge("emit_zones", END)
    graph.add_edge("impact", "emit_zones")

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
```

---

## 13:00 — 15:30 | Build All Agent Nodes (150 min)

**Parse Node (15 min):**

```python
# backend/agent/nodes/parse_node.py
from agent.state import AgentState
from copilotkit.langgraph import copilotkit_emit_state
import uuid

async def parse_query_node(state: AgentState, config) -> AgentState:
    """
    Extract city and scenario from the latest user message.
    Detect if this is a 'what if' impact query.
    """
    messages = state.get("messages", [])
    last_message = messages[-1]["content"] if messages else ""

    # Simple keyword detection — Gemini will do the heavy lifting
    is_impact = any(kw in last_message.lower() for kw in ["what if", "what would", "if we add", "if we remove", "barrier", "intervention"])

    session_id = state.get("session_id") or str(uuid.uuid4())

    # Emit start signal to frontend
    await copilotkit_emit_state(config, {
        "type": "research_started",
        "message": f"Starting analysis..."
    })

    return {
        **state,
        "session_id": session_id,
        "impact_query": last_message if is_impact else None,
        "is_scenario_switch": False,
    }
```

**Research Node (45 min):**

```python
# backend/agent/nodes/research_node.py
from agent.state import AgentState
from services.linkup_service import LinkupService
from services.redis_service import RedisService
from copilotkit.langgraph import copilotkit_emit_state
import asyncio

linkup = LinkupService()
redis = RedisService()

QUERY_TEMPLATES = [
    "{city} {scenario} risk assessment infrastructure 2024",
    "{city} {scenario} vulnerability report emergency planning",
    "{city} {scenario} historical incidents damage",
    "{city} infrastructure {scenario} zone analysis",
    "{city} {scenario} government report recommendations",
]

async def research_node(state: AgentState, config) -> AgentState:
    city = state["city"]
    scenario = state["scenario"]

    # Check Redis cache first — don't re-research same city+scenario
    cached = await redis.get_research(state["session_id"], scenario)
    if cached:
        return {**state, "research_results": cached}

    queries = [
        t.format(city=city, scenario=scenario)
        for t in QUERY_TEMPLATES
    ]

    results = []

    # Run queries with slight stagger to avoid rate limits
    for i, query in enumerate(queries):
        await copilotkit_emit_state(config, {
            "type": "research_progress",
            "message": f"Searching: {query}",
            "progress": i / len(queries)
        })
        try:
            result = await linkup.search(query)
            if result:
                results.append({
                    "query": query,
                    "content": result.get("answer", ""),
                    "sources": result.get("sources", [])[:3],  # cap at 3 sources
                })
        except Exception as e:
            print(f"Linkup error for query '{query}': {e}")
            # Continue — don't fail the whole agent on one bad query
        await asyncio.sleep(0.3)  # rate limit buffer

    # Cache results in Redis
    await redis.set_research(state["session_id"], scenario, results)

    return {**state, "research_results": results}
```

**Risk Scoring Node (45 min — most critical):**

```python
# backend/agent/nodes/scoring_node.py
from agent.state import AgentState, ZoneRisk
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import json
import re

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.2,
)

ZONE_IDS = [
    "z_0_0", "z_0_1", "z_0_2",
    "z_1_0", "z_1_1", "z_1_2",
    "z_2_0", "z_2_1", "z_2_2",
]

SYSTEM_PROMPT = """You are an infrastructure risk analyst. Given research about a city and risk scenario, 
assign risk scores to 9 geographical zones of the city (arranged in a 3x3 grid, 
z_0_0=northwest, z_0_1=north, z_0_2=northeast, z_1_0=west, z_1_1=centre, z_1_2=east, 
z_2_0=southwest, z_2_1=south, z_2_2=southeast).

You MUST respond with ONLY valid JSON. No preamble, no explanation, no markdown fences.

Response format:
{
  "zones": {
    "z_0_0": {
      "score": 0.75,
      "label": "HIGH",
      "evidence": ["Evidence point 1", "Evidence point 2", "Evidence point 3"],
      "sources": [{"title": "Source Name", "url": "https://example.com"}]
    }
  },
  "summary": "One sentence summary of overall risk"
}

Rules:
- score is 0.0 to 1.0
- label: LOW (0-0.3), MEDIUM (0.3-0.6), HIGH (0.6-0.8), CRITICAL (0.8-1.0)
- evidence: exactly 2-3 specific, grounded bullet points per zone. No vague statements.
- sources: include real sources from the research where possible
- Vary scores across zones — real risk is never uniform
- ONLY output JSON. Nothing else."""

async def risk_scoring_node(state: AgentState, config) -> AgentState:
    research_text = "\n\n".join([
        f"Query: {r['query']}\nFindings: {r['content']}\nSources: {[s.get('url','') for s in r['sources']]}"
        for r in state["research_results"]
    ])

    prompt = f"""City: {state['city']}
Risk Scenario: {state['scenario']}

Research Findings:
{research_text}

Now assign risk scores to all 9 zones."""

    # Retry up to 3 times for valid JSON
    for attempt in range(3):
        try:
            response = await llm.ainvoke([
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ])

            raw = response.content.strip()

            # Strip any accidental markdown fences
            raw = re.sub(r"```json|```", "", raw).strip()

            data = json.loads(raw)
            zones_data = data["zones"]

            zone_risks: list[ZoneRisk] = []
            for zone_id in ZONE_IDS:
                z = zones_data.get(zone_id, {})
                score = float(z.get("score", 0.2))
                zone_risks.append(ZoneRisk(
                    zone_id=zone_id,
                    score=min(max(score, 0.0), 1.0),  # clamp
                    label=z.get("label", "LOW"),
                    evidence=z.get("evidence", ["Insufficient data for this zone"])[:3],
                    sources=z.get("sources", [])[:3],
                ))

            return {**state, "zone_risks": zone_risks}

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Scoring attempt {attempt+1} failed: {e}")
            if attempt == 2:
                # Fallback — return uniform low risk rather than crash
                return {**state, "zone_risks": [
                    ZoneRisk(zone_id=z, score=0.2, label="LOW",
                             evidence=["Research data insufficient for precise scoring"],
                             sources=[])
                    for z in ZONE_IDS
                ]}
```

**Emit Zones Node (20 min):**

```python
# backend/agent/nodes/emit_node.py
from agent.state import AgentState
from copilotkit.langgraph import copilotkit_emit_state
from services.redis_service import RedisService
import asyncio

redis = RedisService()

async def emit_zones_node(state: AgentState, config) -> AgentState:
    """
    Emit each zone score individually with a delay.
    The delay creates the staged materialisation effect in the 3D scene.
    """
    # Signal research start to reset frontend
    await copilotkit_emit_state(config, {
        "type": "start_research",
        "city": state["city"],
        "scenario": state["scenario"],
    })

    # Emit each zone with 800ms gap — this drives the staged 3D build
    for zone in state["zone_risks"]:
        await copilotkit_emit_state(config, {
            "type": "zone_score_update",
            **zone
        })
        await asyncio.sleep(0.8)  # THE KEY DELAY — creates the materialisation drama

    # Signal completion
    await copilotkit_emit_state(config, {
        "type": "research_complete",
    })

    # Persist final city state to Redis
    await redis.set_city_state(state["session_id"], {
        "city": state["city"],
        "scenario": state["scenario"],
        "zones": {z["zone_id"]: z for z in state["zone_risks"]},
    })

    return state
```

**Impact Assessment Node (30 min):**

```python
# backend/agent/nodes/impact_node.py
from agent.state import AgentState, ZoneRisk
from services.linkup_service import LinkupService
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import json, re

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2)
linkup = LinkupService()

async def impact_assessment_node(state: AgentState, config) -> AgentState:
    """Handle 'what if' queries — re-score affected zones only."""
    query = state["impact_query"]
    current_zones = {z["zone_id"]: z for z in state.get("zone_risks", [])}

    # Search for the specific intervention
    intervention_research = await linkup.search(
        f"{state['city']} {query} infrastructure impact effectiveness"
    )

    prompt = f"""Current city: {state['city']}
Current scenario: {state['scenario']}
Intervention proposed: {query}
Research on intervention: {intervention_research.get('answer', 'No data found')}

Current zone risk scores:
{json.dumps({k: v['score'] for k,v in current_zones.items()}, indent=2)}

Which zones would this intervention affect and how would their scores change?
Respond with ONLY JSON in this exact format:
{{
  "affected_zones": {{
    "z_1_1": {{
      "score": 0.4,
      "label": "MEDIUM",
      "evidence": ["Intervention reduces risk because...", "Historical precedent shows..."],
      "sources": [{{"title": "Source", "url": "https://example.com"}}]
    }}
  }},
  "impact_summary": "One sentence explaining the overall effect"
}}"""

    try:
        response = await llm.ainvoke([
            SystemMessage(content="You are an infrastructure risk analyst. Respond ONLY with valid JSON."),
            HumanMessage(content=prompt)
        ])
        raw = re.sub(r"```json|```", "", response.content).strip()
        data = json.loads(raw)

        # Merge affected zones back into full zone list
        affected = data.get("affected_zones", {})
        updated_zones = []
        for zone in state.get("zone_risks", []):
            if zone["zone_id"] in affected:
                updated_zones.append(ZoneRisk(
                    zone_id=zone["zone_id"],
                    **{k: v for k, v in affected[zone["zone_id"]].items()}
                ))
            else:
                updated_zones.append(zone)

        return {**state, "zone_risks": updated_zones, "impact_query": None}

    except Exception as e:
        print(f"Impact node error: {e}")
        return {**state, "impact_query": None}
```

**Checkpoint 15:30:** Full agent loop runs. Type "London flooding" → agent researches → emits 9 zone scores with 800ms gaps → Person A's 3D scene responds.

---

## 15:30 — 17:30 | Tune & Harden (120 min)

- Tune the Gemini system prompt until zone scores feel realistic and varied
- Test with at least 3 different city+scenario combinations
- Add error handling for Linkup rate limit (429) — exponential backoff
- Test the "what if" impact node with: "What if London built a flood barrier at zone 4"
- Make sure scenario switching reuses Redis cache correctly
- Work with Person A on any integration bugs in the AG-UI stream

---
---

# PERSON C — Infrastructure, Data & Deployment

**Your domain:** Everything that makes the other two people's work actually run. Redis, Linkup service, Pydantic models, deployment, environment management, and integration testing.

**Your north star:** At 13:00, both the Redis service and Linkup service must be working and importable by Person B. You unblock the team.

---

## 11:30 — 12:00 | Services Bootstrap (30 min)

**Linkup Service:**

```python
# backend/services/linkup_service.py
import httpx
import os
from typing import Optional

class LinkupService:
    def __init__(self):
        self.api_key = os.getenv("LINKUP_API_KEY")
        self.base_url = "https://api.linkup.so/v1"
        self.client = httpx.AsyncClient(timeout=15.0)

    async def search(
        self,
        query: str,
        depth: str = "standard",
        output_type: str = "sourcedAnswer"
    ) -> Optional[dict]:
        if not self.api_key:
            raise ValueError("LINKUP_API_KEY not set")

        try:
            response = await self.client.post(
                f"{self.base_url}/search",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "q": query,
                    "depth": depth,
                    "outputType": output_type,
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                print(f"Linkup rate limit hit — backing off")
                import asyncio
                await asyncio.sleep(2)
                return await self.search(query, depth, output_type)
            print(f"Linkup HTTP error: {e}")
            return None
        except Exception as e:
            print(f"Linkup error: {e}")
            return None

    async def close(self):
        await self.client.aclose()
```

**Redis Service:**

```python
# backend/services/redis_service.py
import os
import json
from typing import Optional
import redis.asyncio as redis

class RedisService:
    def __init__(self):
        self.url = os.getenv("REDIS_URL")
        self.token = os.getenv("REDIS_TOKEN")

        # Upstash uses REST URL + token
        # If using standard Redis URL, just use redis.from_url()
        if self.token:
            # Upstash Redis REST (recommended for hackathon)
            self.client = redis.from_url(
                self.url,
                password=self.token,
                decode_responses=True,
            )
        else:
            self.client = redis.from_url(
                self.url or "redis://localhost:6379",
                decode_responses=True,
            )

    async def set_city_state(self, session_id: str, state: dict, ttl: int = 7200):
        key = f"session:{session_id}:city_state"
        await self.client.setex(key, ttl, json.dumps(state))

    async def get_city_state(self, session_id: str) -> Optional[dict]:
        key = f"session:{session_id}:city_state"
        data = await self.client.get(key)
        return json.loads(data) if data else None

    async def set_research(self, session_id: str, scenario: str, results: list, ttl: int = 7200):
        key = f"session:{session_id}:research:{scenario}"
        await self.client.setex(key, ttl, json.dumps(results))

    async def get_research(self, session_id: str, scenario: str) -> Optional[list]:
        key = f"session:{session_id}:research:{scenario}"
        data = await self.client.get(key)
        return json.loads(data) if data else None

    async def append_message(self, session_id: str, message: dict):
        key = f"session:{session_id}:messages"
        await self.client.rpush(key, json.dumps(message))
        await self.client.expire(key, 7200)

    async def get_messages(self, session_id: str) -> list:
        key = f"session:{session_id}:messages"
        items = await self.client.lrange(key, 0, -1)
        return [json.loads(i) for i in items]

    async def health_check(self) -> bool:
        try:
            await self.client.ping()
            return True
        except Exception:
            return False
```

Run a quick health check test:

```python
# Quick test — run this directly: python -c "import asyncio; from services.redis_service import RedisService; asyncio.run(RedisService().health_check())"
```

**Checkpoint 12:00:** Both services import without errors. Redis health check returns True. Linkup returns data for "London flooding infrastructure risk".

---

## 12:00 — 13:00 | Pydantic Models & Environment (60 min)

```python
# backend/models/city.py
from pydantic import BaseModel, Field, validator
from typing import Optional
from enum import Enum

class RiskLabel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class Source(BaseModel):
    title: str
    url: str

class ZoneRiskModel(BaseModel):
    zone_id: str
    score: float = Field(ge=0.0, le=1.0)
    label: RiskLabel
    evidence: list[str] = Field(max_items=4)
    sources: list[Source] = Field(max_items=3, default=[])

    @validator("label", pre=True, always=True)
    def derive_label_from_score(cls, v, values):
        if "score" in values:
            s = values["score"]
            if s >= 0.8: return RiskLabel.CRITICAL
            if s >= 0.6: return RiskLabel.HIGH
            if s >= 0.3: return RiskLabel.MEDIUM
        return v or RiskLabel.LOW

class CityStateModel(BaseModel):
    city: str
    scenario: str
    zones: dict[str, ZoneRiskModel]
    last_updated: str

class ZoneScoreEvent(BaseModel):
    type: str = "zone_score_update"
    zone_id: str
    score: float
    label: str
    evidence: list[str]
    sources: list[dict]
```

```bash
# backend/.env
GEMINI_API_KEY=your_key_here
LINKUP_API_KEY=your_key_here
REDIS_URL=rediss://your-upstash-url
REDIS_TOKEN=your_upstash_token

# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Add a health endpoint to FastAPI for deployment verification:

```python
# Add to main.py
@app.get("/health")
async def health():
    redis_ok = await RedisService().health_check()
    return {
        "status": "ok",
        "redis": "connected" if redis_ok else "disconnected",
        "version": "1.0.0"
    }
```

---

## 13:00 — 15:30 | Deployment & Integration Testing (150 min)

**Deploy backend to Railway (30 min):**

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login
railway init
railway up

# Set env vars
railway variables set GEMINI_API_KEY=xxx
railway variables set LINKUP_API_KEY=xxx
railway variables set REDIS_URL=xxx
railway variables set REDIS_TOKEN=xxx
```

Add `Procfile`:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

Add `requirements.txt` — pin versions to avoid surprises:
```
langgraph==0.2.28
langchain-google-genai==2.0.7
fastapi==0.115.0
uvicorn==0.32.0
copilotkit==0.1.34
linkup-sdk==0.2.0
redis==5.2.0
pydantic==2.9.0
python-dotenv==1.0.1
httpx==0.27.0
```

**Deploy frontend to Vercel (15 min):**

```bash
npm install -g vercel
vercel --prod
# Set NEXT_PUBLIC_API_URL to Railway URL in Vercel dashboard
```

**Integration testing script — run this at 15:00 (90 min):**

Test 1 — Redis round-trip:
```python
# python tests/test_redis.py
import asyncio
from services.redis_service import RedisService

async def test():
    r = RedisService()
    await r.set_city_state("test_session", {"city": "London", "scenario": "flooding", "zones": {}})
    result = await r.get_city_state("test_session")
    assert result["city"] == "London", "FAIL: Redis set/get broken"
    print("PASS: Redis round-trip works")

asyncio.run(test())
```

Test 2 — Linkup real query:
```python
# python tests/test_linkup.py
import asyncio
from services.linkup_service import LinkupService

async def test():
    l = LinkupService()
    result = await l.search("London flooding infrastructure risk 2024")
    assert result is not None, "FAIL: Linkup returned None"
    assert "answer" in result, "FAIL: No answer in Linkup response"
    print(f"PASS: Linkup returned {len(result['answer'])} chars")
    print(f"Sources: {[s.get('url') for s in result.get('sources', [])]}")

asyncio.run(test())
```

Test 3 — Full agent end-to-end:
```bash
curl -X POST http://localhost:8000/copilotkit \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "London flooding risk"}], "threadId": "test-123", "runId": "run-1"}'
```
Watch the SSE stream in your terminal. You should see zone_score_update events arriving 800ms apart.

**Checkpoint 15:30:** All three tests pass. Deployed URLs working. Share Railway URL with Person A so they can update their `.env.local`.

---

## 15:30 — 17:30 | Hardening & Demo Prep (120 min)

**Build a demo seed script** — pre-loads Redis with known-good data so demo works even if Linkup is slow:

```python
# scripts/seed_demo.py
"""
Run this before the demo: python scripts/seed_demo.py
Seeds Redis with pre-researched data for London flooding
so the demo doesn't depend on live Linkup latency.
"""
import asyncio, json
from services.redis_service import RedisService

DEMO_SESSION = "demo_session_citypulse"

DEMO_RESEARCH = [
    {
        "query": "London flooding infrastructure risk 2024",
        "content": "London faces significant flooding risk particularly in eastern zones. The Thames Barrier has been raised 200 times since 1982, with increasing frequency. The Environment Agency classifies zones 3 and 4 as highest risk. Underground infrastructure including the Jubilee Line is particularly vulnerable to sustained flooding events above 2.1m surge.",
        "sources": [
            {"title": "Environment Agency", "url": "https://www.gov.uk/government/organisations/environment-agency"},
            {"title": "Thames Barrier Operations", "url": "https://www.gov.uk/guidance/the-thames-barrier"}
        ]
    },
    # Add 2-3 more with real data you've pre-tested
]

async def seed():
    r = RedisService()
    await r.set_research(DEMO_SESSION, "flooding", DEMO_RESEARCH, ttl=86400)
    print(f"Seeded demo session: {DEMO_SESSION}")
    print("Set DEMO_SESSION_ID={DEMO_SESSION} in your frontend .env.local")

asyncio.run(seed())
```

**Monitor during demo:**

```bash
# Keep this terminal open during demo
redis-cli -u $REDIS_URL monitor | grep "session:demo"
```

**Load test — simulate rapid queries:**

```bash
# Make sure the backend doesn't fall over
for i in {1..5}; do
  curl -X POST http://localhost:8000/copilotkit \
    -H "Content-Type: application/json" \
    -d '{"messages": [{"role": "user", "content": "London flooding"}], "threadId": "test-'$i'"}' &
done
```

---

## 17:00 — 17:30 | Demo Environment Lock

- Set `NODE_ENV=production` on Vercel
- Clear all test Redis sessions: `redis-cli FLUSHDB` (only test DB, not demo seed)
- Run the demo seed script
- Confirm deployed URLs work from a phone (not just your machine)
- Write down all env vars in a shared note in case someone needs to restart a service
- Prepare a local fallback: have `localhost:3000` running on one machine in case Vercel is slow

---

## Shared: 17:30 — 18:00 | Demo Run-Through

All three people in front of one screen. Run the demo script from HACKATHON_PLAN.md exactly as written. Time it. It should be 90 seconds maximum.

If anything breaks, Person C fixes infra, Person B fixes agent, Person A fixes UI. Do not switch roles. Do not add features. Fix only what's broken for the demo path.

**The demo path is sacred:**
1. Type "London — flooding risk"
2. Watch research progress
3. Watch 3D city build zone by zone
4. Click a zone, see the card
5. Type "What if we add a flood barrier at zone 4"
6. Watch affected zones re-colour

That's it. Everything else is bonus.

---

*If you're reading this at 17:00 and the core loop isn't working — cut the impact query. Four steps, not six. A working four-step demo beats a broken six-step demo every time.*