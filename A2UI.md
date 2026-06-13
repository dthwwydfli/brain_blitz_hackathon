# CityPulse — A2UI Integration (closing the requirement gap)

## The gap

Submission checklist requires **"A2UI components confirmed in codebase."** Track 2 is judged on *creative use of Gen UI + A2UI*. The current `ZoneDetailCard` and `ImpactAssessmentPanel` in the plan are plain hand-written React — they satisfy nothing. This must be real.

## Decision

Make **agent-generated, schema-driven UI** the A2UI surface. The agent does not return prose — it returns a **UI spec** (JSON) that the frontend renders through an A2UI renderer. Two components become A2UI-driven:

1. **ZoneDetailCard** — generated when a zone is clicked.
2. **ImpactAssessmentPanel** — generated after a "what if" query.

Everything structural (3D scene, sidebar shell, chat) stays normal React. Only the *content cards the agent produces* go through A2UI. That is the honest, defensible line for judges: "the UI inside these panels did not exist before the query — the agent emitted its spec."

## Minimal contract (frozen with SCHEMA)

Agent emits, per card, an A2UI component spec:

```json
{
  "a2ui_version": "0.9",
  "component": "Card",
  "props": { "title": "Zone E — East London", "accent": "#f87171" },
  "children": [
    { "component": "Badge", "props": { "text": "HIGH", "tone": "danger" } },
    { "component": "Metric", "props": { "label": "Risk Score", "value": 0.83, "format": "percent" } },
    { "component": "BulletList", "props": { "items": ["Thames Barrier capacity warnings (Reuters, 2024)", "Canary Wharf substructure < 2.1m surge"] } },
    { "component": "SourceLinks", "props": { "sources": [{ "title": "Environment Agency", "url": "https://gov.uk/..." }] } }
  ]
}
```

Frontend keeps a small renderer mapping `component` → React element. Whitelist of ~6 primitives: `Card`, `Badge`, `Metric`, `BulletList`, `SourceLinks`, `Text`. Unknown component → skip (never crash the scene).

```tsx
// components/A2UIRenderer.tsx — the whole A2UI surface, ~40 lines
const REGISTRY: Record<string, React.FC<any>> = {
  Card, Badge, Metric, BulletList, SourceLinks, Text,
};

export function A2UIRenderer({ node }: { node: A2UINode }) {
  const Comp = REGISTRY[node.component];
  if (!Comp) return null;                       // graceful skip
  return (
    <Comp {...node.props}>
      {node.children?.map((c, i) => <A2UIRenderer key={i} node={c} />)}
    </Comp>
  );
}
```

Agent side: add a node that takes a `ZoneRisk` (or impact result) and asks Gemini to emit the A2UI spec JSON — same strict-JSON + retry pattern as the scoring node. Or, faster and more reliable for the demo: **build the spec deterministically in Python from the already-scored `ZoneRisk`** (no second LLM call). Recommended — one less failure point, and it's still genuine A2UI rendering.

## Where it slots in the timeline

- **Person A** (after 15:30 polish): build `A2UIRenderer` + the 6 primitives. Swap `ZoneDetailCard` body to render the spec.
- **Person B / C**: add `build_zone_card_spec(zone: ZoneRisk) -> dict` helper, attach it to each zone in shared state as `zone.card_spec`, or generate on zone-click via a `useCopilotAction("generateZoneCard")`.

## Fallback (if behind at 17:00)

Deterministic spec built in Python (no LLM), rendered by the 6-primitive registry. Still real A2UI, still satisfies the checklist, zero added demo risk. Do **not** cut A2UI entirely — it is a scored criterion, not optional.
