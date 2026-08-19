# EDGEiQ Overview Trace V1

## Scope

Workspace: OVERVIEW

This tranche is display-only. It does not alter pricing, EPI, ERI, EPF, map, market, overview, performance-intelligence, weather, or governed builder logic.

## Required Sections

| Display | Canonical source | Service path | Component path | Availability handling |
| --- | --- | --- | --- | --- |
| Summary intelligence cards | `public/data/edgeiq_overview_terminal_feed_v1.csv` | `src/edgeiq-os/race/services/overviewFeed.ts` | `OverviewWorkspace.tsx` | Shows governed evidence where supplied; otherwise compact status text. |
| What Matters Today | `edgeiq_overview_terminal_feed_v1.csv` | `overviewFeed.ts` | `OverviewWorkspace.tsx` | Uses supplied evidence only; no generated narrative. |
| Speed-map preview | `public/data/edgeiq_map_terminal_feed_v1.csv` | `src/edgeiq-os/race/services/mapFeed.ts` | `OverviewWorkspace.tsx` | Shows runner lanes only when governed position evidence exists; otherwise compact awaiting-evidence state. |
| EPI snapshot | `public/data/edgeiq_epi_workspace_terminal_feed_v1.csv` | `src/edgeiq-os/race/services/epiWorkspaceFeed.ts` | `OverviewWorkspace.tsx` | Shows current EPI only where supplied; unavailable remains unavailable. |
| Runner board | `edgeiq_epi_workspace_terminal_feed_v1.csv` joined visually with `edgeiq_map_terminal_feed_v1.csv` by saddlecloth number | `epiWorkspaceFeed.ts`, `mapFeed.ts` | `OverviewWorkspace.tsx` | Displays concise runner rows and governed status; no ranking or calculation. |
| Race reference | Certified performance intelligence package | `src/edgeiq-os/services/performance-intelligence` | `OverviewWorkspace.tsx` | Displays benchmark level/sample/history/profile counts; product-facing confidence is not displayed. |

## Legitimate Data Gaps Observed

Flemington R5 on the current governed three-day feed has overview rows, but current EPI figures and map position evidence are not supplied. The Overview workspace therefore shows race context and runner rows while keeping EPI and map values unavailable.

## Rejected Product Language

The previous Overview UI exposed `Confidence` and command-centre wording. This tranche removes those labels from the product-facing Overview component.
