# CityPulse — City Infrastructure Risk Agent

> Type a city and a risk scenario. An agent researches live web data, then builds a 3D risk map of that city in real time — zone by zone — as it thinks.

**Track 2: Generative UI** — Google × CopilotKit × A2A Net Hackathon, London.

The 3D scene *is* the agent's output. Every zone, colour, and detail card is generated from live research — not hardcoded. Not a dashboard, not a chatbot.

---

## How it works

```
User: "London — flooding risk"
   │
   ▼
LangGraph agent (FastAPI)
   ├─ parse query        → city + scenario
   ├─ research (Linkup)  → live web data, 5 queries
   ├─ risk scoring (Gemini 2.0 Flash) → 9 zone scores 0.0–1.0
   └─ emit zones         → one every 800ms  ───┐
                                                │ AG-UI shared state (SSE)
   ▼                                            ▼
Redis (Upstash)                          Next.js + react-three-fiber
session state + cache                    3D city materialises zone by zone
                                         click zone → A2UI detail card
```

Switch scenario mid-session → loads instantly from Redis (shared persistent memory). Ask "what if we add a flood barrier at zone 4" → agent re-scores affected zones.

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 (App Router), react-three-fiber, @react-three/drei, Zustand |
| Agent UI bridge | CopilotKit + AG-UI (CoAgent shared state) |
| Agent | LangGraph (Python), Gemini 2.0 Flash |
| Generative cards | A2UI v0.9 (see `A2UI.md`) |
| Research | Linkup API |
| Memory | Upstash Redis |
| Backend | FastAPI |
| Deploy | Vercel (frontend) + Railway (backend) |

---

## Docs in this repo

| File | What |
|---|---|
| `SCHEMA.md` | **Canonical** data contracts — zone IDs, score bands, shared-state shape. Frozen at schema lock. |
| `AGUI_PIPE.md` | How agent state reaches the 3D scene (CoAgent pattern). The must-work pipe. |
| `A2UI.md` | A2UI integration decision — agent-generated detail cards. |
| `HackathonPlan.md` | Strategy, pitch, demo script, risks. |
| `TeamExecutionPlan.md` | Hour-by-hour build plan for 3 people. |

> Where any doc disagrees with `SCHEMA.md`, `SCHEMA.md` wins.

---

## Setup

### Prerequisites
- Node 18+, Python 3.11+
- API keys: Gemini, Linkup, Upstash Redis (see `.env.example`)

### 1. Clone
```bash
git clone https://github.com/CopilotKit/open-multi-agent-canvas
cd open-multi-agent-canvas
```

### 2. Env
```bash
cp .env.example backend/.env          # fill in keys
cp .env.example frontend/.env.local   # set NEXT_PUBLIC_API_URL
```

### 3. Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

### 5. (Optional) Seed demo data
Makes the demo independent of live Linkup latency:
```bash
cd backend && python scripts/seed_demo.py
```

---

## Verify the pipe (do this first)

The whole product depends on agent state reaching the frontend. Test it before anything else — see `AGUI_PIPE.md` "The 12:00 pipe test". Type anything in chat; the agent's `research_log` should appear in the sidebar within ~2s.

---

## Demo path

1. Type `London — flooding risk`
2. Research progress streams in the sidebar
3. 3D city builds zone by zone — red = high risk, amber = moderate, green = safe
4. Click a zone → A2UI detail card (score, evidence, sources)
5. `What if we add a flood barrier at zone 4` → affected zones re-colour
6. Switch scenario → loads from Redis instantly

---

## Status

Hackathon build. Feature freeze 17:30. See `TeamExecutionPlan.md` for current task ownership.
