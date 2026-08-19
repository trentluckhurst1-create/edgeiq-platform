# EDGEiQ Race Workspace Baseline - 2026-07-15

Generated: 2026-07-15T13:12:23

## Scope

This baseline records the current Race Workspace implementation before the gated beta lock work continues. It is an inspection artifact only; no race-workspace UI source is changed by this task.

## Active Navigation

- Global sections: MEETINGS, RESULTS, LAB, SETTINGS.
- Race-level tabs: FORM GUIDE, MAP, MARKET, OVERVIEW, INSIGHTS, EPI, REVIEW.
- Runner-level tabs: PROFILE, COMPARE, RESULTS, DNA, MARKET, MAP.
- Race state is selected in `RaceFileV3.tsx` and passed into `RaceWorkspace.tsx` as `raceBook`, `field`, `meetingRaces`, and `selectedRaceKey`.

## Active Components

| Component | File | Lines | Role |
| --- | --- | ---: | --- |
| RaceFileV3 | `src/edgeiq-os/race/RaceFileV3.tsx` | 647 | Global orchestrator; builds active race file from meeting/race state and mounts race or runner workspaces. |
| WorkspaceShell | `src/edgeiq-os/race/components/WorkspaceShell.tsx` | 43 | Shared shell, app nav, page header and footer. |
| RaceWorkspace | `src/edgeiq-os/race/components/RaceWorkspace.tsx` | 200 | Race-level tab container: FORM GUIDE, MAP, MARKET, OVERVIEW, INSIGHTS, EPI, REVIEW. |
| RaceFormGuideWorkspace | `src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx` | 584 | Full race form guide table, metric guide, runner profile stack and recent form rows. |
| MapWorkspace | `src/edgeiq-os/race/components/MapWorkspace.tsx` | 320 | Race and runner map view using map terminal feed plus race-context fallback. |
| MarketWorkspace | `src/edgeiq-os/race/components/MarketWorkspace.tsx` | 212 | Race market board using market terminal feed plus Pending Market fallback. |
| OverviewWorkspace | `src/edgeiq-os/race/components/OverviewWorkspace.tsx` | 208 | Race overview cards and evidence table using overview terminal feed. |
| InsightsWorkspace | `src/edgeiq-os/race/components/InsightsWorkspace.tsx` | 208 | Nexus-style insights workspace currently labelled INSIGHTS. |
| EpiWorkspaceWorkspace | `src/edgeiq-os/race/components/EpiWorkspaceWorkspace.tsx` | 291 | Performance/EPI matrix using current race EPI terminal feed. |
| ResultsWorkspace | `src/edgeiq-os/race/components/ResultsWorkspace.tsx` | 151 | Runner-level historical results workspace; race-level REVIEW is currently a pending shell. |
| RunnerProfileWorkspace | `src/edgeiq-os/race/components/RunnerProfileWorkspace.tsx` | 130 | Runner-level workspace container for profile/compare/results/dna/market/map. |

## Active Services And Feeds

| Area | Service | Feed / Purpose |
| --- | --- | --- |
| Three-day catalogue | `src/edgeiq-os/race/services/threeDayCatalog.ts` | `/data/edgeiq_three_day_product_catalog_v1.json` |
| Form guide enrichment | `src/edgeiq-os/race/services/formGuideEnrichedFeed.ts` | `/data/edgeiq_form_guide_enriched_v2.json` |
| Form guide normaliser | `src/edgeiq-os/race/services/formGuideNormaliser.ts` | `Normalises raceBook + field + enriched JSON into display rows` |
| MAP | `src/edgeiq-os/race/services/mapFeed.ts` | `/data/edgeiq_map_terminal_feed_v1.csv` |
| MARKET | `src/edgeiq-os/race/services/marketFeed.ts` | `/data/edgeiq_market_terminal_feed_v1.csv` |
| OVERVIEW | `src/edgeiq-os/race/services/overviewFeed.ts` | `/data/edgeiq_overview_terminal_feed_v1.csv` |
| INSIGHTS | `src/edgeiq-os/race/services/insightsFeed.ts` | `/data/edgeiq_insights_terminal_feed_v1.csv` |
| EPI | `src/edgeiq-os/race/services/epiWorkspaceFeed.ts` | `/data/edgeiq_epi_workspace_terminal_feed_v1.csv` |
| Fallback race book | `src/edgeiq-os/services/RaceFileService.ts` | `Builds in-memory fallback race book from race-file-v2 services` |

## Current Data Surface

| File | Size bytes | Exists |
| --- | ---: | --- |
| `public/data/edgeiq_three_day_product_catalog_v1.json` | 4495851 | yes |
| `public/data/edgeiq_form_guide_enriched_v2.json` | 21713616 | yes |
| `public/data/edgeiq_map_terminal_feed_v1.csv` | 31974 | yes |
| `public/data/edgeiq_market_terminal_feed_v1.csv` | 54627 | yes |
| `public/data/edgeiq_overview_terminal_feed_v1.csv` | 30057 | yes |
| `public/data/edgeiq_insights_terminal_feed_v1.csv` | 107296 | yes |
| `public/data/edgeiq_epi_workspace_terminal_feed_v1.csv` | 125891 | yes |

## Inspection Findings

- FORM GUIDE is the most complete race workspace surface. It uses `edgeiq_form_guide_enriched_v2.json`, displays summary metrics, all-runner profiles, recent form, profile records, jockey/class/preparation sections, and ESI split columns.
- MAP, MARKET, OVERVIEW, INSIGHTS and EPI all use small terminal feed loaders with frontend guards that reject parsed CSV feeds above 10,000 rows.
- Race-level REVIEW is currently a pre-race pending shell; the richer `ResultsWorkspace.tsx` is mounted only inside the runner-level RESULTS tab.
- Current visible race-level MAP/MARKET/OVERVIEW/EPI/INSIGHTS surfaces still expose operational/developer language such as workspace ids, feed rows, loaded rows, matched rows, feed status, source names, and model information.
- Current race-level MAP table columns are `NO / HORSE / BARRIER / EFFECTIVE BARRIER / RUN STYLE / EARLY SPEED / PROJECTED POSITION`, not the locked customer-facing MAP table.
- Current race-level MARKET table columns include HIGH, LOW, MOVE and STATUS, not the locked customer-facing MARKET table.
- `RaceWorkspace.tsx` tab labels currently include INSIGHTS and EPI rather than the brief's NEXUS / PERFORMANCE naming.
- No Meeting workspace source files were modified for this baseline task. The existing weather v1.2 integration must remain authoritative in later visual polish.

## Baseline Gate

Task 1 requires the audit marker `EDGEIQ_RACE_WORKSPACE_BASELINE_V1_AUDIT_PASS` and a passing `npm run build` before feature or visual changes continue.

