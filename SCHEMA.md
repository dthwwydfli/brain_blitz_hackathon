# CityPulse — Schema Lock (single source of truth)

**This file wins.** If `HackathonPlan.md` or `TeamExecutionPlan.md` disagree with anything here, this file is correct. Locked at 13:00 — no interface changes after that.

---

## 1. Zone IDs — CANONICAL

Always `z_{row}_{col}`, **0-indexed**, 3×3 grid, 9 zones.

```
z_0_0  z_0_1  z_0_2     (north:  NW  N  NE)
z_1_0  z_1_1  z_1_2     (middle:  W  C   E)
z_2_0  z_2_1  z_2_2     (south:  SW  S  SE)
```

> NOTE: `HackathonPlan.md` JSON examples use `zone_1_1` style. Those are **stale** — ignore them. Use `z_0_0` everywhere. Backend `ZONE_IDS` and frontend `ZONE_IDS` must be byte-identical to this list.

No 20×20 grid. It is 3×3 / 9 zones. Each zone holds 6–9 procedural buildings (visual only, not addressable).

---

## 2. Risk Label ↔ Score bands (single definition)

| Label    | Score range | Colour     | Hex       |
|----------|-------------|------------|-----------|
| LOW      | 0.0 – 0.3   | green      | `#4ade80` |
| MEDIUM   | 0.3 – 0.6   | amber      | `#fb923c` |
| HIGH     | 0.6 – 0.8   | red        | `#f87171` |
| CRITICAL | 0.8 – 1.0   | deep red   | `#dc2626` (pulsing) |

Boundary rule: band is `score >= floor`. So `0.3 → MEDIUM`, `0.6 → HIGH`, `0.8 → CRITICAL`.
**Label is derived from score** — agent must keep them consistent; frontend trusts `score` for colour, `label` for text. If they ever conflict, **score wins** for colour.

---

## 3. Agent shared state — the AG-UI contract

The agent owns a single state object. Frontend subscribes to it (see `AGUI_PIPE.md`). The agent mutates this object and emits it; the frontend re-renders from it. **No frontend tool calls drive zone updates.**

### State shape (TypeScript view — frontend)

```typescript
type RiskLabel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

interface Source {
  title: string;
  url: string;
}

interface ZoneRisk {
  zone_id: string;        // "z_0_0" .. "z_2_2"
  score: number;          // 0.0 – 1.0
  label: RiskLabel;
  evidence: string[];     // 2–3 grounded bullets
  sources: Source[];      // 0–3 items
}

interface CityAgentState {
  city: string;                 // "London"
  scenario: string;             // "flooding"
  session_id: string;           // Redis key prefix
  status: "idle" | "researching" | "scoring" | "complete";
  research_log: string[];       // live feed for ResearchProgress sidebar
  zone_risks: ZoneRisk[];       // grows as zones are scored — drives 3D build
  impact_summary: string | null;// set after a "what if" query
}
```

### State shape (Python view — backend, `agent/state.py`)

```python
class ZoneRisk(TypedDict):
    zone_id: str          # "z_0_0"
    score: float          # 0.0 – 1.0
    label: str            # LOW | MEDIUM | HIGH | CRITICAL
    evidence: list[str]   # 2–3 bullets
    sources: list[dict]   # [{"title": str, "url": str}], max 3

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    city: str
    scenario: str
    session_id: str
    status: str                    # idle|researching|scoring|complete
    research_log: list[str]
    research_results: list[dict]   # raw Linkup, internal only — NOT sent to UI
    zone_risks: list[ZoneRisk]
    impact_query: Optional[str]    # internal trigger
    impact_summary: Optional[str]
    is_scenario_switch: bool
```

`research_results` is internal (raw Linkup). `research_log` is the human-readable feed the UI shows. Keep them separate.

---

## 4. The staged build mechanism

The "zones appear one by one" drama is driven by the **backend** appending to `zone_risks` one item at a time with an 800ms gap, emitting state after each append. Frontend renders whatever is in `zone_risks` — a zone is "visible" iff it exists in the array.

```python
# emit_node.py — canonical pattern
state["zone_risks"] = []
state["status"] = "scoring"
for zone in scored_zones:               # 9 zones
    state["zone_risks"].append(zone)
    await copilotkit_emit_state(config, state)
    await asyncio.sleep(0.8)            # THE drama delay
state["status"] = "complete"
await copilotkit_emit_state(config, state)
```

Frontend does **not** add its own stagger. Backend timing is the single clock. (Old TeamPlan code had a `setTimeout` stagger in `updateZoneRisk` — drop it.)

---

## 5. Redis keys

```
session:{id}:city_state        → CityStateModel JSON
session:{id}:research:{scenario} → raw Linkup results (internal)
session:{id}:scenario_history  → list of scenarios run
session:{id}:messages          → AG-UI message thread
```

TTL 7200s (2h). Demo seed uses TTL 86400 and fixed session `demo_session_citypulse`.

`city_state` JSON:
```json
{
  "city": "London",
  "scenario": "flooding",
  "zones": { "z_0_0": { "zone_id": "z_0_0", "score": 0.85, "label": "HIGH", "evidence": ["..."], "sources": [] } },
  "last_updated": "2026-06-13T11:45:00Z"
}
```

---

## 6. Zone Detail Card props (click → card)

Card reads straight from `zone_risks[selectedZone]` in shared state. No separate fetch.

```typescript
interface ZoneDetailCardProps {
  zone_id: string;
  label: RiskLabel;
  score: number;
  scenario: string;
  evidence: string[];
  sources: Source[];
}
```

---

## 7. What is frozen at 13:00

- Zone ID format (`z_r_c`, 0-indexed) — §1
- Score bands and colours — §2
- `CityAgentState` field names and types — §3
- Staged build = backend-timed — §4
- Redis key format — §5

Anything not in this list can change after 13:00. Anything in it cannot.
