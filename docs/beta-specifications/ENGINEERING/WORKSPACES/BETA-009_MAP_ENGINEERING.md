# BETA-009 MAP Engineering Specification

Canonical status: implementation-grade target specification. Current implementation, approved target and required migration are deliberately separated.
## 1. Document Control
- Specification ID: BETA-009
- Workspace: MAP
- Version: V1
- Status: Canonical engineering authority
- Last Updated: 2026-07-12
- Audit: scripts/audit_edgeiq_engineering_specification_library_v1.py

## 2. Purpose
Project early positioning from barriers and governed early-speed evidence; it is not a track diagram. The workspace must answer this with governed evidence, not unsupported synthesis. React renders supplied view models only.

## 3. Scope
In scope: layout, data contracts, interaction contracts, missing-data handling, accessibility, testing, audit expectations and migration instructions for this workspace. Out of scope: production implementation during this documentation task.

## 4. Explicit Non-Goals
- React must not calculate racing intelligence, EPI, ERI, ESI, suitability, form momentum, speed projection, map placement or market edge.
- Missing evidence must never be converted to zero, average, neutral, unknown placement, default narrative or fabricated figure.
- No tips, bets, selections, stars, medals, decorative winner colours, exchange-ladder UI, bookmaker order book styling or unsupported AI filler.
- Do not alter raw warehouse files, pricing engines, model outputs or checkpoint copies.

## 5. Locked Product Decisions
Victorian right-to-left. Barriers on the right. Barrier 1 bottom. Highest effective barrier top. No racing-direction arrow. No barrier-group names. Every runner line begins exactly at effective barrier. All lines use EDGEiQ blue.

## 6. Current Repository Trace
CURRENT IMPLEMENTATION TRACE:
- `src/edgeiq-os/race/RaceFileV3.tsx`
- `src/edgeiq-os/race/components/AppNavigation.tsx`
- `src/edgeiq-os/race/components/MeetingsWorkspace.tsx`
- `src/edgeiq-os/race/components/MeetingWorkspace.tsx`
- `src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx`
- `src/edgeiq-os/race/components/MapWorkspace.tsx`
- `src/edgeiq-os/race/components/ResultsWorkspace.tsx`
- `src/edgeiq-os/race/services/threeDayCatalog.ts`

GAPS: the current implementation may be partial or visually/data incomplete. This specification defines the approved target and must not pretend target behaviour already exists.

## 7. Active File Ownership
Active ownership is display/routing in React, feed shaping in services/normalisers and intelligence generation in builders.
- Active path: `src/edgeiq-os/race/RaceFileV3.tsx`
- Active path: `src/edgeiq-os/race/components/AppNavigation.tsx`
- Active path: `src/edgeiq-os/race/components/MeetingsWorkspace.tsx`
- Active path: `src/edgeiq-os/race/components/MeetingWorkspace.tsx`
- Active path: `src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx`
- Active path: `src/edgeiq-os/race/components/MapWorkspace.tsx`
- Active path: `src/edgeiq-os/race/components/ResultsWorkspace.tsx`
- Active path: `src/edgeiq-os/race/services/threeDayCatalog.ts`
- PROPOSED TARGET PATH: `src/edgeiq-os/race/components/MapWorkspace.tsx`
- PROPOSED TARGET PATH: `src/edgeiq-os/race/services/mapFeed.ts`

## 8. Approved Target Architecture
TARGET IMPLEMENTATION CONTRACT: Victorian right-to-left. Barriers on the right. Barrier 1 bottom. Highest effective barrier top. No racing-direction arrow. No barrier-group names. Every runner line begins exactly at effective barrier. All lines use EDGEiQ blue. The component receives a terminal-feed view model. It does not read warehouse files and does not synthesize racing claims.

## 9. Component Hierarchy
Parent hierarchy: EdgeiqOsShell -> AppNavigation -> RaceFileV3 or MeetingWorkspace -> scoped workspace component.

| COMPONENT | FILE | PROPS | STATE | EVENTS | DATA OWNER | TESTS |
| --- | --- | --- | --- | --- | --- | --- |
| RaceFileV3 | `src/edgeiq-os/race/RaceFileV3.tsx` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| AppNavigation | `src/edgeiq-os/race/components/AppNavigation.tsx` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| MeetingsWorkspace | `src/edgeiq-os/race/components/MeetingsWorkspace.tsx` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| MeetingWorkspace | `src/edgeiq-os/race/components/MeetingWorkspace.tsx` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| RaceFormGuideWorkspace | `src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| MapWorkspace | PROPOSED TARGET PATH `src/edgeiq-os/race/components/MapWorkspace.tsx` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| ResultsWorkspace | `src/edgeiq-os/race/components/ResultsWorkspace.tsx` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| threeDayCatalog | `src/edgeiq-os/race/services/threeDayCatalog.ts` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| MapWorkspace | PROPOSED TARGET PATH `src/edgeiq-os/race/components/MapWorkspace.tsx` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| mapFeed | PROPOSED TARGET PATH `src/edgeiq-os/race/services/mapFeed.ts` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |

## 10. React Component Contracts
Parent hierarchy: EdgeiqOsShell -> AppNavigation -> RaceFileV3 or MeetingWorkspace -> scoped workspace component.

| COMPONENT | FILE | PROPS | STATE | EVENTS | DATA OWNER | TESTS |
| --- | --- | --- | --- | --- | --- | --- |
| RaceFileV3 | `src/edgeiq-os/race/RaceFileV3.tsx` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| AppNavigation | `src/edgeiq-os/race/components/AppNavigation.tsx` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| MeetingsWorkspace | `src/edgeiq-os/race/components/MeetingsWorkspace.tsx` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| MeetingWorkspace | `src/edgeiq-os/race/components/MeetingWorkspace.tsx` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| RaceFormGuideWorkspace | `src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| MapWorkspace | PROPOSED TARGET PATH `src/edgeiq-os/race/components/MapWorkspace.tsx` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| ResultsWorkspace | `src/edgeiq-os/race/components/ResultsWorkspace.tsx` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| threeDayCatalog | `src/edgeiq-os/race/services/threeDayCatalog.ts` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| MapWorkspace | PROPOSED TARGET PATH `src/edgeiq-os/race/components/MapWorkspace.tsx` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |
| mapFeed | PROPOSED TARGET PATH `src/edgeiq-os/race/services/mapFeed.ts` | Typed view-model props only; preserve current mounted props during migration. | Selection/hover/focus/filter/expansion only. | Typed callbacks for navigation and row selection. | Builder/service; React display-only. | Unit, integration and visual audit. |

## 11. TypeScript Interfaces
```ts
export type EngineeringStatus = 'current' | 'target' | 'migration-required' | 'loading' | 'empty' | 'unavailable' | 'stale' | 'error';

export type BETA009Row = {
    no: string | number | null;
    horse: string | number | null;
    barrier: string | number | null;
    effective_barrier: string | number | null;
    run_style: string | number | null;
    early_speed: string | number | null;
    projected_position: string | number | null;
    source: string | null;
    sourceTimestamp: string | null;
    sourceConfidence: 'official' | 'governed' | 'derived' | 'unavailable' | null;
};

export type BETA009ViewModel = {
  workspaceId: 'BETA-009';
  meetingKey: string | null;
  raceKey: string | null;
  generatedAt: string | null;
  status: EngineeringStatus;
  rows: BETA009Row[];
};
```

## 12. Canonical Data Contracts
Locked column/field order:

`NO|HORSE|BARRIER|EFFECTIVE BARRIER|RUN STYLE|EARLY SPEED|PROJECTED POSITION`

| FIELD | BUILDER | OUTPUT | SERVICE | VIEW MODEL | COMPONENT | NULL RULE | AUDIT |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NO | Canonical builder listed in this spec. | Governed `public/data` terminal feed. | Workspace service/normaliser. | `no`. | Table/panel cell for NO. | Do not coerce to zero, average, neutral or invented text. | Contract audit verifies presence, null count and format. |
| HORSE | Canonical builder listed in this spec. | Governed `public/data` terminal feed. | Workspace service/normaliser. | `horse`. | Table/panel cell for HORSE. | Do not coerce to zero, average, neutral or invented text. | Contract audit verifies presence, null count and format. |
| BARRIER | Canonical builder listed in this spec. | Governed `public/data` terminal feed. | Workspace service/normaliser. | `barrier`. | Table/panel cell for BARRIER. | Do not coerce to zero, average, neutral or invented text. | Contract audit verifies presence, null count and format. |
| EFFECTIVE BARRIER | Canonical builder listed in this spec. | Governed `public/data` terminal feed. | Workspace service/normaliser. | `effective_barrier`. | Table/panel cell for EFFECTIVE BARRIER. | Do not coerce to zero, average, neutral or invented text. | Contract audit verifies presence, null count and format. |
| RUN STYLE | Canonical builder listed in this spec. | Governed `public/data` terminal feed. | Workspace service/normaliser. | `run_style`. | Table/panel cell for RUN STYLE. | Do not coerce to zero, average, neutral or invented text. | Contract audit verifies presence, null count and format. |
| EARLY SPEED | Canonical builder listed in this spec. | Governed `public/data` terminal feed. | Workspace service/normaliser. | `early_speed`. | Table/panel cell for EARLY SPEED. | Do not coerce to zero, average, neutral or invented text. | Contract audit verifies presence, null count and format. |
| PROJECTED POSITION | Canonical builder listed in this spec. | Governed `public/data` terminal feed. | Workspace service/normaliser. | `projected_position`. | Table/panel cell for PROJECTED POSITION. | Do not coerce to zero, average, neutral or invented text. | Contract audit verifies presence, null count and format. |

```json
{
  "workspace_id": "BETA-009",
  "meeting_key": "example-meeting-key",
  "race_key": "example-race-key",
  "generated_at": null,
  "rows": [
    {
      "no": null,
      "horse": null,
      "barrier": null,
      "effective_barrier": null,
      "run_style": null,
      "early_speed": null,
      "projected_position": null
    }
  ]
}
```

## 13. Builder and Service Ownership
Builders own intelligence and generated outputs. Services own loading/normalisation. Components own display.
- `scripts/build_edgeiq_three_day_product_catalog_v1.py`
- `scripts/build_edgeiq_current_early_speed_v1.py`
- `scripts/build_edgeiq_current_late_speed_v1.py`
- `scripts/build_edgeiq_current_suitability_v1.py`
- `scripts/build_edgeiq_current_form_momentum_v1.py`
- `scripts/build_edgeiq_current_map_v1.py`
- `scripts/build_edgeiq_map_workspace_v3.py`
- `scripts/build_edgeiq_metropolitan_weather_v1.py`
- `scripts/build_edgeiq_weather_beta_v1.py`
- `scripts/run_edgeiq_form_guide_current_intelligence_pipeline_v1.ps1`

## 14. Data Lineage
| FIELD | BUILDER | OUTPUT | SERVICE | VIEW MODEL | COMPONENT | NULL RULE | AUDIT |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NO | Canonical builder listed in this spec. | Governed `public/data` terminal feed. | Workspace service/normaliser. | `no`. | Table/panel cell for NO. | Do not coerce to zero, average, neutral or invented text. | Contract audit verifies presence, null count and format. |
| HORSE | Canonical builder listed in this spec. | Governed `public/data` terminal feed. | Workspace service/normaliser. | `horse`. | Table/panel cell for HORSE. | Do not coerce to zero, average, neutral or invented text. | Contract audit verifies presence, null count and format. |
| BARRIER | Canonical builder listed in this spec. | Governed `public/data` terminal feed. | Workspace service/normaliser. | `barrier`. | Table/panel cell for BARRIER. | Do not coerce to zero, average, neutral or invented text. | Contract audit verifies presence, null count and format. |
| EFFECTIVE BARRIER | Canonical builder listed in this spec. | Governed `public/data` terminal feed. | Workspace service/normaliser. | `effective_barrier`. | Table/panel cell for EFFECTIVE BARRIER. | Do not coerce to zero, average, neutral or invented text. | Contract audit verifies presence, null count and format. |
| RUN STYLE | Canonical builder listed in this spec. | Governed `public/data` terminal feed. | Workspace service/normaliser. | `run_style`. | Table/panel cell for RUN STYLE. | Do not coerce to zero, average, neutral or invented text. | Contract audit verifies presence, null count and format. |
| EARLY SPEED | Canonical builder listed in this spec. | Governed `public/data` terminal feed. | Workspace service/normaliser. | `early_speed`. | Table/panel cell for EARLY SPEED. | Do not coerce to zero, average, neutral or invented text. | Contract audit verifies presence, null count and format. |
| PROJECTED POSITION | Canonical builder listed in this spec. | Governed `public/data` terminal feed. | Workspace service/normaliser. | `projected_position`. | Table/panel cell for PROJECTED POSITION. | Do not coerce to zero, average, neutral or invented text. | Contract audit verifies presence, null count and format. |

## 15. State Ownership
Allowed React state: selected day, meeting, race, runner, tab, sort/filter/search controls, hover/focus row, expansion and scroll. Disallowed React state: calculated ratings, intelligence narratives, speed/map projections, market edge or confidence values.

## 16. Routing and Navigation
Route context uses meeting key, race key, tab key and optional runner key. Navigation must preserve selected context and not trigger browser-side data rebuilding.

## 17. Desktop Layout Geometry
Use active EDGEiQ OS shell geometry. Full-width analytical surfaces. 8px base rhythm. 12-16px section gaps. 34-40px table rows. 44-64px header bands. Identity columns retain enough width to avoid awkward wrapping at 1440px desktop.

## 18. Responsive Behaviour
Narrow screens use controlled horizontal scrolling. Do not transform desktop analytical tables into oversized cards. Sticky identity columns require keyboard and screen-reader verification.

## 19. Design Tokens
Use MASTER-001: canvas #F4F6F9, primary surface #FFFFFF, secondary #FAFBFC, primary blue #1F5FD6, text #1A1A1A, border #E5E8EE. No gradients, glow, dark terminal panels, stars or medals.

## 20. Typography
Page title 26-28px/600; workspace title 20-22px/600; section title 14-16px/600; table header 11-12px/600; table body 13-14px/400-500; supporting text 12-13px. One canonical application font family inherited from active CSS.

## 21. Spacing
Use 8px base rhythm. Table cell padding 8-12px. Header strips 10-14px vertical padding. Dense scan-first layout is preferred over tall empty panels.

## 22. Borders and Surfaces
Panels are #FFFFFF or #FAFBFC with #E5E8EE borders. Tables use subtle horizontal separators and no visible vertical dividers unless a structural split is explicitly approved.

## 23. Table Specifications
| ORDER | COLUMN | FIELD KEY | SOURCE FIELD | TYPE | NULLABLE RULE | DISPLAY FORMAT | MIN WIDTH | ALIGNMENT | SORTING | FILTERING | HOVER | CLICK | KEYBOARD | SCRATCHING | RESPONSIVE |
| ---: | --- | --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | NO | `no` | Governed feed field mapped by service. | string/number/status | Null remains blank, unavailable or pending. | Racing display format; never raw JSON. | 76 | centre | Builder-supported only. | Builder-supported only. | Source/timestamp/null reason. | Open route only if implemented. | Focus follows visual order. | Reduced opacity and SCRATCHED label where applicable. | Horizontal scroll; do not cardify desktop table. |
| 2 | HORSE | `horse` | Governed feed field mapped by service. | string/number/status | Null remains blank, unavailable or pending. | Racing display format; never raw JSON. | 160 | left | Builder-supported only. | Builder-supported only. | Source/timestamp/null reason. | Open route only if implemented. | Focus follows visual order. | Reduced opacity and SCRATCHED label where applicable. | Horizontal scroll; do not cardify desktop table. |
| 3 | BARRIER | `barrier` | Governed feed field mapped by service. | string/number/status | Null remains blank, unavailable or pending. | Racing display format; never raw JSON. | 76 | centre | Builder-supported only. | Builder-supported only. | Source/timestamp/null reason. | Open route only if implemented. | Focus follows visual order. | Reduced opacity and SCRATCHED label where applicable. | Horizontal scroll; do not cardify desktop table. |
| 4 | EFFECTIVE BARRIER | `effective_barrier` | Governed feed field mapped by service. | string/number/status | Null remains blank, unavailable or pending. | Racing display format; never raw JSON. | 76 | centre | Builder-supported only. | Builder-supported only. | Source/timestamp/null reason. | Open route only if implemented. | Focus follows visual order. | Reduced opacity and SCRATCHED label where applicable. | Horizontal scroll; do not cardify desktop table. |
| 5 | RUN STYLE | `run_style` | Governed feed field mapped by service. | string/number/status | Null remains blank, unavailable or pending. | Racing display format; never raw JSON. | 76 | centre | Builder-supported only. | Builder-supported only. | Source/timestamp/null reason. | Open route only if implemented. | Focus follows visual order. | Reduced opacity and SCRATCHED label where applicable. | Horizontal scroll; do not cardify desktop table. |
| 6 | EARLY SPEED | `early_speed` | Governed feed field mapped by service. | string/number/status | Null remains blank, unavailable or pending. | Racing display format; never raw JSON. | 76 | centre | Builder-supported only. | Builder-supported only. | Source/timestamp/null reason. | Open route only if implemented. | Focus follows visual order. | Reduced opacity and SCRATCHED label where applicable. | Horizontal scroll; do not cardify desktop table. |
| 7 | PROJECTED POSITION | `projected_position` | Governed feed field mapped by service. | string/number/status | Null remains blank, unavailable or pending. | Racing display format; never raw JSON. | 76 | centre | Builder-supported only. | Builder-supported only. | Source/timestamp/null reason. | Open route only if implemented. | Focus follows visual order. | Reduced opacity and SCRATCHED label where applicable. | Horizontal scroll; do not cardify desktop table. |

## 24. Component-by-Component Rendering Rules
Render formatted value when present. Render blank, pending or unavailable when null according to contract. Render stale state from feed metadata. Never infer from neighbouring fields.

## 25. Interaction Behaviour
Rows and controls activate only implemented routes. Disabled controls expose unavailable reason. Hover-only critical information is prohibited.

## 26. Hover Behaviour
Hover may show source, timestamp, null reason and audit metadata. Touch and keyboard users require focus/click equivalents.

## 27. Keyboard Behaviour
Tab order follows visual order. Enter activates. Escape closes overlays. Arrow-key table navigation requires roving-tabindex tests before adoption.

## 28. Selection Behaviour
Selected rows use pale blue tint and thin blue outline. Selection never mutates source rows. Parent workspace owns selected context.

## 29. Sorting
Default order follows official/product order. Sorting is permitted only when stable null ordering and tests exist. React must not recompute ranks.

## 30. Filtering
Filters operate on already loaded terminal feeds. Required scratched/unavailable rows remain visible where product rules demand it.

## 31. Searching
Search may use horse, meeting, jockey, trainer or official label fields. It must not trigger warehouse-scale CSV loading.

## 32. Expansion and Collapse
Expansion reveals supported details only. Collapsed state retains accessible context. One-open-at-a-time rules must be explicit when used.

## 33. Loading States
Loading skeletons match table geometry and never show fabricated racing values.

## 34. Empty States
Empty means governed feed returned no rows for selected context. Message must name context and feed/audit owner.

## 35. Unavailable States
Unavailable means trusted source cannot provide evidence. Render unavailable, blank or pending trusted feed. Do not convert to zero.

## 36. Stale Data States
Stale means feed timestamp exceeds threshold or selected meeting/race date no longer matches active window. Display stale metadata and avoid current claims.

## 37. Error States
Errors include parse failure, missing keys, route context failure and feed version mismatch. Copy is concise; dev console diagnostics are bounded.

## 38. Scratching Behaviour
Scratchings remain visible where required. Scratched rows use reduced opacity and clear SCRATCHED labels. Scratched runners cannot affect active ranks/averages unless a governed feed supplies scratched-state values.

## 39. Accessibility
Use semantic tables or tested ARIA grids. Icon-only controls need labels. Colour-coded values require text or sign. Focus states must be visible.

## 40. Performance Budget
React loads terminal feeds only. Any frontend parser seeing more than 10,000 rows must warn and reject state setting. Target render under 250ms after data availability.

## 41. Builder Tests
Builder tests verify row counts, required keys, null semantics, timestamp/version fields, locked column order and no fabricated defaults.

## 42. TypeScript Unit Tests
Unit tests verify parsing, null display, stale state, default order, scratching presentation and disabled interaction behaviour.

## 43. Integration Tests
Integration tests open the workspace, select context, verify rows/columns, verify no warehouse feed fetch and preserve tab state.

## 44. Data Contract Audits
Audits check exact columns, required fields, source metadata, null counts, stale timestamps, benchmark sign convention and builder/React boundary.

## 45. Visual Regression Requirements
Capture 1440px desktop and narrow horizontal-scroll screenshots. Verify alignment, selected/null/scratched/stale states and absence of prohibited UI.

## 46. Screenshot Acceptance Matrix
| VIEW | WIDTH | REQUIRED ASSERTION |
| --- | ---: | --- |
| Populated | 1440 | Header, table and key panels visible with locked columns. |
| Missing data | 1440 | Null/unavailable copy visible without fabricated values. |
| Narrow | 1024 | Horizontal scroll preserves table semantics. |

## 47. Migration Plan
1. Verify backend feed contract. 2. Add/repair service normaliser. 3. Add component shell. 4. Wire typed view model. 5. Verify null/stale/scratching states. 6. Capture screenshots. 7. Run audits and npm build.

## 48. Files Expected to Change During Implementation
- `src/edgeiq-os/race/components/MapWorkspace.tsx`
- `src/edgeiq-os/race/services/mapFeed.ts`
- Associated service/audit files only when scoped by implementation task.

## 49. Files That Must Not Change
- Raw warehouse files except named generated terminal/audit outputs.
- Pricing/model engines unless explicitly scoped.
- Checkpoint copies and archived specifications.

## 50. Codex Implementation Sequence
Read MASTER-001 and this spec, inspect active files, checkpoint, implement smallest scoped change, run builder/audit, run npm build, capture screenshots and report gaps.

## 51. Acceptance Criteria
- Locked columns render in exact order.
- Null/unavailable/stale/error states behave as specified.
- React remains display-only.
- Prohibited elements are absent.
- Build and audit pass.

## 52. Completion Report Contract
Report files changed, feeds/audits run, screenshots, build result, remaining data limitations and confirmation that no prohibited UI/language/calculation boundary was introduced.

## 53. Engineering Governance
This spec is canonical. Deviations require spec and audit updates before implementation proceeds.

## 54. Revision History
| VERSION | DATE | CHANGE |
| --- | --- | --- |
| V1 | 2026-07-12 | Full recovery from outline into implementation-grade specification. |
