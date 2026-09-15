# EDGEiQ UI IMPLEMENTATION AUDIT — 2026-09-15

## VERDICT: IMPLEMENTATION NOT YET CONTRACT-COMPLIANT

Audit target: current `main` implementation versus the user-approved 15 Sep 2026 UI/workspace contracts.

This is an implementation audit, not a redesign. Approved contracts remain authoritative.

## P0 — EDGEiQ LOGO / IP — RELEASE BLOCKER

FAIL.

Current `AppNavigation.tsx` constructs the brand from an `E` mark plus live text (`EDGE` + `iQ`) instead of consuming one immutable canonical logo asset. `src/assets` contains only `react.svg`; `public/assets` contains track folders and no canonical EDGEiQ logo asset was found in the inspected asset roots.

Required fix:
1. Establish ONE canonical EDGEiQ logo/wordmark asset from the first approved light-theme design.
2. Create one shared `EdgeiqBrand` component (or equivalent) that renders only that asset.
3. All workspaces receive the brand through the shared shell/navigation; no workspace may create its own logo text or image.
4. Remove alternate EDGEiQ text-lockups/marks where they visually compete with the canonical brand.
5. Add an automated UI/DOM guard: one canonical brand source; no per-workspace logo implementation.
6. Logo mismatch is a RELEASE-BLOCKING defect.

## P0 — NAVIGATION / INFORMATION ARCHITECTURE

FAIL.

Current `AppNavigation.tsx` still exposes `Field` as a standalone item, labels Home as `Dashboard`, and includes Review, Research Lab and Compare. It does not expose Track or Weather. Current `RaceFileV3.tsx` still imports/routes a standalone `FieldWorkspace` and retains `field`, `review`, `lab` and `compare` as global sections.

Required locked navigation:
`Home | Meetings | Race | Form | Performance | EPI Ratings | Speed Map | Market | Results | Track | Weather | Overview | Insights`
Settings at bottom. Field is internal to Race only.

## WORKSPACE-BY-WORKSPACE AUDIT

### Home — FAIL / REBUILD TO LOCK
Current `EdgeiqOsHome.tsx` is the older Dashboard command-centre layout and even states that Dashboard and Meetings are the only active workspaces. It does not implement the newly locked Home composition. Replace with the approved Home contract while retaining canonical data-only behaviour.

### Meetings — FAIL / REBUILD TO LOCK
Current implementation is the older meeting list + selected Meeting Overview side panel. It generates club-code identity marks rather than the approved jurisdiction PRA grouping/authority assets. It also contains controls/panels not matching the newly approved jurisdiction-grouped Meetings layout. Rebuild to the locked Today/Tomorrow/Day+2 jurisdiction sections and correct PRA identity treatment. No single page-level weather hero.

### Race — FAIL / PARTIAL BASE ONLY
Current Race has basic race facts and a simple runner board. It lacks the approved internal `Field | Race Details | Key Determinants` architecture and the approved dense Field-default semantics including Last 5, Going context, ERR, EPI, EDGEiQ Price, Market and Edge where governed. Standalone Field routing must be removed.

### Field — REMOVE
Current `FieldWorkspace.tsx` still exists and is routed as a top-level workspace. Contract requires Field to be absorbed into Race. Retain/reuse code only as internal Race implementation if useful; no sidebar/global route.

### Form — FAIL / PARTIAL BASE ONLY
Current Form is a simple expandable field table. It does not implement the locked runner-centric Form navigation `Last 5 Runs | Full Form | Race Comments | Trainer/Jockey | Ratings | Map`, nor the exact historical columns with EPI and ERR semantics. Current finish styling combines 2 and 3 into one `is-place` class; locked rule requires distinct SILVER for every 2 and BRONZE for every 3. Rebuild against Form contract.

### Performance — FAIL / RECONCILE
Current Performance contains substantial historical/rating logic, but presentation and Last-5 finish-tile treatment must be reconciled to the approved Performance mockup/contract. Ensure 1 gold, 2 silver, 3 bronze, all others white/blue everywhere.

### EPI Ratings — FAIL / PARTIAL BASE ONLY
Current implementation provides rank and a single EPI column plus basic runner facts. Approved workspace requires the richer governed EPI comparison surface/trends/components where available. Keep canonical EPI retrieval but rebuild presentation; do not invent missing components.

### Speed Map — FAIL — MAJOR CONTRACT CONFLICT
Current `SpeedMapWorkspace.tsx` explicitly classifies runners into `Leader | On Pace | Midfield | Back | Unmapped` lanes. This directly conflicts with the locked design. Required map is opening ~200m only, Victoria right-to-left, barriers on RIGHT, horses face LEFT, each runner begins in actual barrier lane, path line from barrier to governed early position, higher Early Speed Score farther LEFT, and NO leader/on-pace/midfield/backmarker zones.

### Market — FAIL / PARTIAL BASE ONLY
Current Market is a static table of Market/Fair/Edge. It does not provide the locked per-runner individual fluctuation board/sparkline. Implement actual captured price observations only, with no interpolation/fabrication, plus governed current/model price context.

### Results — FAIL — CONTRACT CONFLICT
The currently routed Results implementation in `RemainingWorkspaces.tsx` includes a `TIME` column and reads `spTab`. Locked Results requires SP only, no Tote/dividend products, and no raw sectional/final-time presentation under the agreed rule. Results must be rebuilt around official results plus EDGEiQ sectional-vs-standard lengths where governed. No unlicensed replay/media.

### Track — MISSING FROM CURRENT GLOBAL ROUTE
Track is required by the locked navigation but is absent from current `GlobalSection`/AppNavigation/RaceFileV3 routing. No matching current `TrackWorkspace.tsx` was found at the expected active component path. Implement the locked Track workspace: Track Profile, Track Map, evidence-backed Track Characteristics, Current Conditions, Recent Track History (`DATE | RAIL | GOING | RACES`) and Track Notes.

### Weather — MISSING FROM CURRENT GLOBAL ROUTE
Weather is required by the locked navigation but is absent from current global navigation/routing. No matching current `WeatherWorkspace.tsx` was found at the expected active component path. Implement the locked Weather workspace using governed weather/current/forecast/history data only.

### Overview — FAIL / PARTIAL BASE ONLY
Current Overview is essentially race facts plus a Field Snapshot table. It does not implement the approved executive briefing structure/subtabs and race-shape/tempo/key-determinant/class/market-model context. Rebuild without duplicating specialist tabs.

### Insights — FAIL / PARTIAL / ROUTING DUPLICATION RISK
There are multiple Insights implementations in the component tree. `RaceFileV3` currently imports Insights from `RemainingWorkspaces.tsx`, while a richer `InsightsWorkspace.tsx` also exists. Consolidate to ONE active implementation and align it to the locked evidence-backed Insights design. No generic/generated filler.

### Settings — RETAIN, SHELL RECONCILIATION REQUIRED
Settings is retained at bottom. Current runtime coverage diagnostics can remain useful, but it must use the exact same canonical shared shell/logo and visual system.

## CROSS-WORKSPACE HARD RULES TO ENFORCE

1. WHITE sidebar on every workspace.
2. ONE canonical EDGEiQ logo asset/component everywhere — exact same IP mark.
3. Global Last 5: 1 GOLD, 2 SILVER, 3 BRONZE, all others WHITE/BLUE.
4. Going colours: FAST blue, GOOD green, SOFT red, HEAVY black, SYNTHETIC white/black.
5. No fabricated production values or copied mockup values.
6. React presentation must not invent governed model metrics.
7. Shared meeting/race selection context must persist across specialist tabs.
8. No standalone Field sidebar route.
9. No duplicate active workspace implementations for the same user-facing tab.
10. Contract-compliance audit must pass before a tab is considered production-locked.

## IMPLEMENTATION ORDER

P0: canonical logo/shared shell + navigation cleanup.
P1: Home and Meetings.
P2: Race consolidation/remove standalone Field.
P3: Form, Performance, EPI Ratings, Speed Map, Market.
P4: Results, Track, Weather, Overview, Insights.
P5: final visual/data-integrity regression audit across every route and responsive state.

## RELEASE GATE

Do NOT call the redesign implemented merely because contracts/mockups are locked. Production sign-off requires the live code to match the contracts. The first gate is the canonical EDGEiQ logo: if any tab shows a different mark, proportions, lettering, colours or tagline treatment, the release FAILS.
