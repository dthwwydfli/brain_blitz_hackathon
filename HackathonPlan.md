# CityPulse — City Infrastructure Risk Agent
### Hackathon Battle Plan | Track 2: Generative UI
**Event:** Google × CopilotKit × A2A Net Hackathon, London
**Track:** Generative UI (AG-UI + A2UI)
**Hacking window:** 11:30 → 18:00 (6.5 hours)
**Feature freeze:** 17:30

---

## The One-Line Pitch

> Type a city and a risk scenario. Watch an intelligent agent research live data, then build a 3D risk map of that city in real time — zone by zone — as it thinks.

---

## The Demo Script (memorise this)

1. Type: **"London — flooding risk"**
2. Agent starts searching via Linkup. Research progress visible in sidebar.
3. 3D city grid materialises **zone by zone** as agent completes each research node. Not all at once — staged, deliberate, dramatic.
4. High-risk zones pulse **red**. Medium zones **amber**. Safe zones **grey**.
5. Click any zone → A2UI generates a detail card: risk level, evidence, Linkup source citations, last updated timestamp.
6. Type follow-up: **"What if we add a flood barrier at zone 4?"** → agent re-evaluates, re-colours affected zones, generates an impact assessment card.
7. Switch scenario: **"Now show me power grid resilience"** → Redis has the city in memory, agent runs a new research pass, overlays new risk data on the same 3D grid.

**Total demo time: 90 seconds. Every second is visual.**

---

## Why This Wins

| Judging Criterion | How CityPulse Scores |
|---|---|
| Originality | No team is building a 3D agent-driven risk visualiser. This is not a chatbot with a pretty sidebar. |
| Economic Value | Emergency planners, insurers, urban developers, councils — all pay £50k+/year for inferior tools. |
| Technical Difficulty | LangGraph orchestration + react-three-fiber + AG-UI streaming + Redis state + Linkup grounding. High bar. |
| Creative use of Gen UI + A2UI | The 3D scene IS the agent's output. Every zone, every colour, every card is generated — not hardcoded. |

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend framework | Next.js 14 (App Router) | Starter repo base, fast |
| 3D rendering | react-three-fiber + @react-three/drei | React-native Three.js, huge ecosystem |
| Agent frontend | CopilotKit + AG-UI | Required. Handles SSE streaming from agent |
| Agent framework | LangGraph (Python) | Required. Orchestrates research nodes |
| LLM | Gemini 2.0 Flash | GCP credits cover it, fast inference |
| Web research | Linkup API | Required. Live risk data grounding |
| Shared memory | Redis (Upstash free tier) | Required. City state + session persistence |
| Generative UI cards | A2UI v0.9 | Required. Zone detail cards, impact panels |
| Backend API | FastAPI | Thin layer between LangGraph and CopilotKit |
| Deployment | Vercel (frontend) + Railway/Render (backend) | Fast, free tier |

---

## Repository Structure

```
citypulse/
├── frontend/                          # Next.js app
│   ├── app/
│   │   ├── page.tsx                   # Main layout — 3D canvas + chat sidebar
│   │   ├── api/
│   │   │   └── copilotkit/
│   │   │       └── route.ts           # AG-UI endpoint
│   ├── components/
│   │   ├── CityCanvas.tsx             # react-three-fiber 3D scene
│   │   ├── CityGrid.tsx               # The 3x3 zone grid of procedural buildings
│   │   ├── RiskZone.tsx               # Individual zone mesh with risk colour
│   │   ├── ZoneDetailCard.tsx         # A2UI generated card per zone
│   │   ├── ImpactAssessmentPanel.tsx  # A2UI generated impact panel
│   │   ├── ResearchProgress.tsx       # Live agent research feed sidebar
│   │   └── ScenarioSwitcher.tsx       # Swap between risk types
│   ├── lib/
│   │   ├── cityState.ts               # City grid state management (Zustand)
│   │   └── copilotkit.ts              # CopilotKit provider config
│   └── package.json
│
├── backend/                           # Python FastAPI + LangGraph
│   ├── main.py                        # FastAPI app entry point
│   ├── agent/
│   │   ├── graph.py                   # LangGraph state machine
│   │   ├── nodes/
│   │   │   ├── research_node.py       # Linkup search calls
│   │   │   ├── risk_scoring_node.py   # Convert research → risk scores per zone
│   │   │   ├── scenario_node.py       # Handle scenario switches
│   │   │   └── impact_node.py        # "What if" query handler
│   │   └── state.py                   # LangGraph state schema
│   ├── services/
│   │   ├── linkup_service.py          # Linkup API wrapper
│   │   └── redis_service.py           # Redis read/write for city state
│   ├── models/
│   │   ├── city.py                    # Pydantic: CityGrid, Zone, RiskScore
│   │   └── events.py                  # Pydantic: AG-UI event payloads
│   └── requirements.txt
│
├── .env.example                       # All required env vars listed
└── README.md                          # Setup instructions
```

---

## The LangGraph Agent — Detailed

The agent is a directed graph with 5 nodes. Each node completion triggers a frontend update via AG-UI SSE stream.

### State Schema

```python
class CityAgentState(TypedDict):
    city: str                          # "London"
    scenario: str                      # "flooding"
    research_results: list[dict]       # Raw Linkup results
    zone_risk_scores: dict[str, float] # zone_id → risk score 0.0–1.0
    zone_evidence: dict[str, list]     # zone_id → list of evidence items
    impact_query: Optional[str]        # "What if flood barrier at zone 4"
    session_id: str                    # Redis key prefix
    messages: list                     # AG-UI message history
```

### Node 1: Query Builder
**Input:** city + scenario from user
**Does:** Constructs 4–6 targeted Linkup search queries
**Emits to frontend:** "Starting research for {city} — {scenario}"

```python
queries = [
    f"{city} {scenario} risk assessment 2024",
    f"{city} {scenario} infrastructure vulnerability report",
    f"{city} {scenario} historical incidents",
    f"{city} emergency planning {scenario}",
]
```

### Node 2: Research Node (runs queries in parallel)
**Input:** Query list
**Does:** Calls Linkup API for each query, collects results
**Emits to frontend:** Each result as it arrives — feeds the research progress sidebar live
**Redis write:** Raw results cached with session_id key

```python
# Linkup call pattern
response = linkup_client.search(
    query=query,
    depth="standard",       # "deep" available but slower
    output_type="sourcedAnswer"
)
```

### Node 3: Risk Scoring Node
**Input:** Research results
**Does:** Uses Gemini to analyse results and produce a risk score (0.0–1.0) for each of 9 city zones (3x3 grid). Also extracts 2–3 evidence bullets per zone.
**Emits to frontend:** Zone scores as structured JSON → triggers 3D city to colour zones one by one

```python
# Output format (strict JSON, validated by Pydantic)
# Zone IDs are z_{row}_{col}, 0-indexed — see SCHEMA.md (canonical)
{
  "zones": {
    "z_0_0": { "score": 0.85, "label": "HIGH", "evidence": [...] },
    "z_0_1": { "score": 0.4,  "label": "MEDIUM", "evidence": [...] },
    ...
  },
  "summary": "London faces significant flooding risk in eastern zones..."
}
```

**Redis write:** Zone scores saved to `session:{id}:city_state`

### Node 4: Impact Assessment Node (conditional)
**Triggered only when:** User asks a "what if" question
**Input:** Current zone scores + user's impact query
**Does:** Runs a focused Linkup search for the intervention, then re-scores affected zones only
**Emits to frontend:** Updated zone scores for affected zones + impact card JSON

### Node 5: Scenario Switch Node (conditional)
**Triggered only when:** User switches risk scenario
**Input:** New scenario + session_id
**Does:** Reads existing city from Redis (no re-render needed), runs new research pass for new scenario, produces new zone scores
**Redis read/write:** Loads existing city state, writes new scenario layer

---

## The 3D City — Detailed

### What It Looks Like
A stylised isometric-style 3D grid. Think SimCity 2000 aesthetic — clean, readable, clearly abstract. Not photorealistic. Not Google Maps. The abstraction is intentional and actually looks better.

### Grid Specification
- 3×3 zone grid (9 zones total — manageable, readable, enough variation)
- Each zone contains a cluster of procedurally generated box buildings
- Building heights randomised within a range for visual interest
- Fixed camera angle: slightly elevated, slight angle — never free-roam (too hard to demo)
- Background: dark (#0a0a1a) — makes risk colours pop dramatically

### Risk Colour Scheme
```
score 0.0–0.3  → #4ade80  (green)   Safe
score 0.3–0.6  → #fb923c  (amber)   Moderate risk
score 0.6–0.8  → #f87171  (red)     High risk
score 0.8–1.0  → #dc2626  (deep red) Critical — add pulsing animation
```

### The Materialisation Animation (the wow moment)
Zones do NOT all appear at once. Each zone materialises when the agent completes scoring it — buildings rise from the ground plane with a smooth scale-Y animation over 600ms. This visually represents the agent building its understanding. It needs to feel like the city is being assembled by intelligence, not loaded.

```tsx
// RiskZone.tsx — key animation logic
const { scale } = useSpring({
  scale: isVisible ? 1 : 0,
  config: { tension: 120, friction: 14 }
})

// Triggered by agent emitting zone score via AG-UI
useEffect(() => {
  if (zoneScore !== null) setIsVisible(true)
}, [zoneScore])
```

### Zone Click → Card Generation
Clicking a zone fires a `useCopilotAction` hook that asks the agent to generate a detail card for that zone. The card appears as an A2UI component in the sidebar:

```
ZONE 4 — EAST LONDON
Risk Level: HIGH (0.83)
Scenario: Flooding

Evidence:
• Thames Barrier capacity warnings reported (Reuters, Jan 2024)
• Canary Wharf underground infrastructure at risk below 2.1m surge
• Environment Agency: Zone 4 in highest tidal flood category

Sources: [Reuters] [Environment Agency] [BBC News]
Last researched: 2 minutes ago
```

---

## Redis — What Gets Stored

```
session:{id}:city_state        → Full zone grid with scores, JSON
session:{id}:research_raw      → Raw Linkup results (for evidence cards)
session:{id}:scenario_history  → List of scenarios run this session
session:{id}:messages          → AG-UI message thread
```

TTL: 2 hours per session. Enough for a demo, light on resources.

**Why Redis matters for the demo:** Switch scenario mid-session and the city loads instantly from Redis — no re-render. This proves shared persistent memory is working. Call it out explicitly in the demo: "The city is in memory — watch how fast the new risk layer loads."

---

## Team Split — 3 People

### Person A: Frontend & 3D (Hacker A role)
**Owns:** CityCanvas.tsx, CityGrid.tsx, RiskZone.tsx, all animation logic

Morning tasks (11:30–13:00):
- Set up Next.js project from CopilotKit starter repo
- Get react-three-fiber rendering a static 3D grid
- Wire CopilotKit provider

Post-schema-lock tasks (13:00–15:30):
- Implement zone colour logic driven by risk score JSON
- Build materialisation animation
- Build zone click handler

Integration tasks (15:30–17:30):
- Wire live agent scores to 3D scene
- Build ZoneDetailCard with A2UI
- Polish camera, lighting, background

### Person B: Agent & Orchestration (Hacker B role)
**Owns:** LangGraph graph, all agent nodes, FastAPI endpoints

Morning tasks (11:30–13:00):
- Set up FastAPI + LangGraph skeleton
- Define CityAgentState schema
- Wire CopilotKit AG-UI endpoint

Post-schema-lock tasks (13:00–15:30):
- Build research_node with Linkup integration
- Build risk_scoring_node with Gemini
- Build impact_node for "what if" queries
- Test full agent loop end-to-end

Integration tasks (15:30–17:30):
- Debug SSE streaming to frontend
- Tune Gemini prompts for consistent JSON output
- Handle edge cases (Linkup rate limits, empty results)

### Person C: Infrastructure & Data (Hacker C role)
**Owns:** Redis service, Linkup service, deployment, Pydantic models

Morning tasks (11:30–13:00):
- Set up Redis (Upstash free tier — 5 minute job)
- Build Linkup service wrapper with error handling
- Define all Pydantic models (Zone, CityGrid, RiskScore, EventPayload)

Post-schema-lock tasks (13:00–15:30):
- Wire Redis read/write into agent nodes
- Build scenario switch logic
- Set up deployment pipeline (Vercel + Railway)

Integration tasks (15:30–17:30):
- End-to-end testing with real Linkup queries
- Fix any Redis session bugs
- Prepare demo environment (clean session, preloaded city)

---

## The Schema Lock (13:00 hard deadline)

Everyone stops at 13:00 and agrees on these exact contracts. Nothing after this point changes these interfaces.

> **CANONICAL SCHEMA LIVES IN `SCHEMA.md`.** The snippets below are illustrative. Where they disagree with `SCHEMA.md`, `SCHEMA.md` wins. AG-UI transport is the CoAgent shared-state pattern — see `AGUI_PIPE.md` (not `useCopilotAction`).

### Zone risk (item inside shared-state `zone_risks[]`)
```json
{
  "zone_id": "z_1_2",
  "score": 0.73,
  "label": "HIGH",
  "evidence": [
    "Thames Barrier warnings issued Q4 2023",
    "EA flood zone category 3 designation"
  ],
  "sources": [{ "title": "Reuters", "url": "https://reuters.com" }]
}
```

### City State (Redis)
```json
{
  "city": "London",
  "scenario": "flooding",
  "zones": {
    "z_0_0": { "zone_id": "z_0_0", "score": 0.85, "label": "HIGH", "evidence": [] },
    "z_0_1": { "zone_id": "z_0_1", "score": 0.4,  "label": "MEDIUM", "evidence": [] }
  },
  "last_updated": "2026-06-13T11:45:00Z"
}
```

### Zone Detail Card Props (A2UI component)
```typescript
interface ZoneDetailCardProps {
  zone_id: string
  label: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
  score: number
  scenario: string
  evidence: string[]
  sources: { title: string; url: string }[]
  last_updated: string
}
```

---

## Environment Variables

```bash
# Backend (.env)
GEMINI_API_KEY=
LINKUP_API_KEY=
REDIS_URL=                    # Upstash Redis REST URL
REDIS_TOKEN=                  # Upstash Redis REST token
COPILOTKIT_API_KEY=           # If using CopilotKit cloud

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=          # Backend FastAPI URL
```

---

## Risks & Mitigations

| Risk | Probability | Mitigation |
|---|---|---|
| Linkup returns thin data for chosen city/scenario | Medium | Pre-test 3 queries before hacking starts. Have "London flooding" and "Birmingham power grid" as known-good queries. |
| Gemini produces inconsistent JSON for zone scores | High | Use strict JSON mode + Pydantic validation. If invalid JSON, retry once then fall back to even distribution. |
| AG-UI SSE streaming breaks between agent and 3D scene | Medium | Test this pipeline first, at 11:30. Nothing else matters if this doesn't work. |
| react-three-fiber performance on demo laptop | Low | Use instanced meshes for buildings. Cap at 200 building objects total. Test on demo machine. |
| 3D scene looks bad | Medium | Dark background, clean colours, no textures. Simple is better. Do not add complexity to make it look "realistic." |
| Redis connection fails during demo | Low | Have a local Redis fallback. Upstash free tier is reliable but have a plan. |
| Running out of time | High | Feature freeze is 17:30. If behind at 15:30, cut the impact node. Core loop: query → research → 3D render → zone cards. That alone wins. |

---

## Minimum Viable Demo (if behind at 15:30)

Cut everything except:
1. User types city + scenario
2. Agent researches via Linkup
3. 3D city materialises with risk zones coloured
4. Click zone → detail card appears

That four-step loop, working cleanly and reliably, beats a buggy version of the full spec every time.

---

## Presentation Script (19:00 demo)

**Opening line (10 seconds):**
"Emergency planners, insurers, and urban developers spend thousands on risk intelligence tools that are slow, expensive, and impossible to interact with. CityPulse changes that."

**Live demo (60–90 seconds):**
Run the exact demo script from the top of this document. Say nothing while the 3D city builds — let the visuals speak.

**Closer (20 seconds):**
"Every zone you see was researched from live web data 30 seconds ago. Every card was generated by the agent. The UI didn't exist before the query. That's generative UI — not a dashboard, not a chatbot. An agent that builds its own interface."

---

## Submission Checklist

- [ ] Demo video recorded (screen capture, 2–3 minutes, show the full loop)
- [ ] GitHub repo public with README and setup instructions
- [ ] Social media post drafted (tag @CopilotKit @GoogleCloud @a2anet)
- [ ] CopilotKit + AG-UI confirmed in codebase
- [ ] A2UI components confirmed in codebase
- [ ] Linkup confirmed integrated and cited
- [ ] Redis confirmed integrated and demonstrably in use

---

## Quick Start for Team

```bash
# Clone the CopilotKit starter
git clone https://github.com/CopilotKit/open-multi-agent-canvas
cd open-multi-agent-canvas

# Frontend
cd frontend && npm install
npm install @react-three/fiber @react-three/drei three @react-spring/three zustand

# Backend
cd backend
pip install langgraph langchain-google-genai fastapi uvicorn linkup-sdk redis pydantic

# Start
# Terminal 1: cd backend && uvicorn main:app --reload
# Terminal 2: cd frontend && npm run dev
```

---

*Last updated: Day of hackathon. Feature freeze 17:30. Demo 19:00. Win.*