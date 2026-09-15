# EDGEIQ UI / WORKSPACE CONTRACT — 2026-09-15

## STATUS: LOCKED

This document records the user-approved EDGEiQ product/UI decisions made during the 15 September 2026 workspace redesign. Where an older workspace specification conflicts with an explicit rule below, THIS CONTRACT TAKES PRECEDENCE until the underlying SPEC is revised.

## 1. GLOBAL PRODUCT DESIGN CONTRACT — LOCKED
EDGEiQ is professional racing intelligence software, not a tipping site, bookmaker interface or gimmicky racing website.

Locked presentation: light/white application shell; WHITE left sidebar; restrained EDGEiQ blue active navigation; crisp modern sans-serif typography; strong navy headings; muted secondary text; white panels with thin cool-grey borders, restrained shadows and small radius; dense scan-friendly tables; consistent shared shell. No decorative clutter, glossy cards, gimmicks, oversized hero treatments or unnecessary explanatory copy. Production values must come from canonical/current-card data, validated historical data or governed EDGEiQ-derived metrics. Never fabricate values. `—`/Unavailable is a last resort.

### CANONICAL EDGEiQ LOGO / BRAND MARK — GLOBAL HARD LOCK
EVERY tab and workspace MUST use the SAME original/first EDGEiQ logo approved at the beginning of this new light-theme redesign. The logo must not drift, regenerate, morph, restyle or be redrawn per workspace. One canonical shared-shell asset/component is authoritative across the product.

### Track-condition display
Official labels: FAST 1; GOOD 2; GOOD 3; GOOD 4; SOFT 5; SOFT 6; SOFT 7; HEAVY 8; HEAVY 9; HEAVY 10. Actual condition tiles: FAST blue/white; GOOD green/white; SOFT red/white; HEAVY black/white. SYNTHETIC uses a white tile with black text and restrained border.

### LAST 5 RUNS FINISH-TILE RULE — GLOBAL HARD LOCK
Every Last 5 Runs sequence throughout EDGEiQ uses: `1` GOLD; `2` SILVER; `3` BRONZE; every other finishing number WHITE with BLUE number/text.

## 2. INSIGHTS — LOCKED
Evidence-backed racing intelligence only.

## 3. OVERVIEW — LOCKED
Executive race briefing with specialist race context.

## 4. WEATHER — LOCKED
Governed current conditions, track conditions, forecasts and relevant weather analysis only. No fabricated weather/history.

## 5. TRACK — LOCKED
Track Profile, Track Map, evidence-backed Track Characteristics, Current Conditions, Recent Track History and Track Notes. Recent Track History columns exactly `DATE | RAIL | GOING | RACES`.

## 6. RESULTS — LOCKED
Official results use SP ONLY; no Tote/dividends. No unlicensed hosted/copied replay/media. Governed EDGEiQ standard comparisons may be expressed in lengths. `-` slower than standard; `+` faster than standard.

## 7. MARKET — LOCKED
Professional pre-race market intelligence. Each runner has an individual actual-observation fluctuation board/sparkline. No invented movements, exchange ladders, casino styling or Bet Now treatment.

## 8. SPEED MAP — LOCKED
Opening approximately 200m only. Victorian orientation RIGHT TO LEFT. Barriers on right, horses face left, actual barrier lanes and governed Early Speed Score determine mapped early positions.

## 9. EPI RATINGS — LOCKED
Dedicated governed EDGEiQ Performance Index comparison workspace.

## 10. PERFORMANCE — LOCKED
Historical runner-performance workspace. Global Last 5 Runs finish-tile rule applies.

## 11. FORM — INCREMENTAL LOCK
Runner-centric professional deep form guide. Runner sub-tabs: `Last 5 Runs | Full Form | Race Comments | Trainer/Jockey | Ratings | Map`. Predictor removed. EPI is horse-run specific; ERR is EDGEiQ Race Rating for the race itself.

## 12. RACE / FIELD INFORMATION ARCHITECTURE — LOCKED
Standalone Field is removed from the sidebar and absorbed into Race. Principal sidebar flow: `Home | Meetings | Race | Form | Performance | EPI Ratings | Speed Map | Market | Results | Track | Weather | Overview | Insights`, with Settings at bottom.

## 13. RACE WORKSPACE — APPROVED AND LOCKED
Race is the authoritative launchpad for the selected race. White sidebar. Internal navigation `Field | Race Details | Key Determinants`, Field default. Dense current-field runner board with governed current-card/model data. No specialist-workspace duplication. Global Last 5 finish-tile rule applies. Mockup values are illustrative only.

## 14. MEETINGS WORKSPACE — APPROVED AND LOCKED
Meetings is the multi-jurisdiction race-day directory and meeting-selection workspace. It must make it immediately clear what meetings are available across EDGEiQ's supported jurisdictions without pretending that one meeting's local conditions describe all meetings.

### Meetings visual shell
- Uses the exact canonical EDGEiQ logo and WHITE sidebar.
- `Meetings` is the active sidebar item with restrained EDGEiQ-blue state.
- Light/white canvas, compact professional typography, thin cool-grey borders and dense tables.
- No dark sidebar, bookmaker/casino treatment or oversized decorative content.

### NO page-level weather/track block — HARD LOCK
The Meetings page MUST NOT display a single weather/temperature/wind/track-condition hero block at the top of the page. Meetings can span different tracks, states, time zones and countries, so a single local weather block is semantically misleading.

Weather and track condition belong at the INDIVIDUAL MEETING ROW level where sourced for that meeting, or inside the selected meeting/race specialist views.

### Three-day meeting window
The primary date selector remains:
`Today | Tomorrow | Day +2`
with the resolved calendar date shown clearly. The current day is highlighted in EDGEiQ blue.

### Filters/search
Meetings may provide compact filters such as:
- Meeting.
- State / Region.
- Rail.
- Track / Track Condition where useful.
- Search meetings.
- Jurisdiction quick filter: `All | VIC | WA | HK`.

Filters must operate on canonical meeting data and should not create empty decorative controls with no function.

### Jurisdiction grouping — LOCKED
Meetings are grouped by supported jurisdiction, currently:
- Victoria.
- Western Australia.
- Hong Kong.

Each jurisdiction section header MUST display the appropriate PRA/racing-authority logo/brand mark for THAT jurisdiction, not a generic map blob/icon and not the EDGEiQ logo.

Approved authority identity direction:
- Victoria -> Racing Victoria PRA/authority identity.
- Western Australia -> Racing WA PRA/authority identity.
- Hong Kong -> Hong Kong Jockey Club authority identity.

Implementation must use authorised/correctly sourced brand assets and preserve their proportions. Do not redraw, hallucinate or approximate authority logos from mockups. If an authority logo cannot legally/technically be used, use a restrained text fallback until an approved asset is available rather than inventing a logo.

### Jurisdiction section summary
Each jurisdiction header may show concise canonical totals such as number of meetings and number of races for the selected date.

### Meeting table — approved semantic direction
Each meeting row may show, where canonical/current data exists:
`Meeting | Abbr | Track | Rail | Track Condition | Weather | First Race | Races | Scratchings | View`

- `Meeting` is the meeting/venue identity.
- `Abbr` uses canonical abbreviation only where available.
- `Track` must not merely duplicate Meeting unless the underlying data distinguishes meeting identity from course/track; redundant columns should be removed during implementation if semantically identical.
- `Rail` uses the published rail position.
- `Track Condition` uses the locked global condition labels/colours.
- `Weather` is specific to THAT meeting/location and only shown where sourced.
- `First Race` is the scheduled first-race time in the relevant meeting context.
- `Races` is the canonical race count.
- `Scratchings` is the current canonical scratching count.
- `View` provides restrained navigation such as `View Races ->` into that meeting.

### Meeting navigation
Selecting a meeting / View Races must preserve the selected date and route into the meeting/race context without requiring the user to reselect jurisdiction/date unnecessarily.

### Meetings data-integrity rule
All meeting names, abbreviations, rail positions, track conditions, weather, first-race times, race counts and scratchings in visual mockups are ILLUSTRATIVE ONLY unless they match canonical production data. Never copy mockup values into production.

### Scope
Meetings is a directory/selection screen. It must not become a race-analysis dashboard. Deep runner/race analysis remains in Race, Form, Performance, EPI Ratings, Speed Map, Market and other specialist workspaces.

This Meetings workspace is now APPROVED AND LOCKED. Any structural redesign requires explicit contract revision.

## 15. FORM GOING RULE — GLOBAL CROSS-WORKSPACE LOCK
Default collapsed/current-field Form Going context, where used, shows the runner's record on TODAY'S GOING as plain text such as `8:1-2-4`, not a coloured badge merely repeating today's condition. Historical individual-run tables show actual historical going using the global condition colours.

## 16. GOVERNANCE
React is presentation/navigation, not the owner of racing intelligence calculations. Governed builders/services own derived metrics. No invented production data. Illustrative mockup values must never be copied into live data. When implementation conflicts with this contract, implementation must be corrected or the contract explicitly revised.

## LOCK RECORD
Locked in GitHub: 2026-09-15
Affected workspaces: INSIGHTS, OVERVIEW, WEATHER, TRACK, RESULTS, MARKET, SPEED MAP, EPI RATINGS, PERFORMANCE, FORM-LAST-5-RUNS, FORM-FULL-FORM, RACE/FIELD-CONSOLIDATION, RACE-WORKSPACE, MEETINGS, FORM cross-workspace Going rule, GLOBAL DESIGN SYSTEM, CANONICAL EDGEiQ LOGO.
Standalone FIELD sidebar tab: REMOVED.
RACE workspace: APPROVED AND LOCKED.
MEETINGS workspace: APPROVED AND LOCKED.
Next and final workspace design: HOME.
