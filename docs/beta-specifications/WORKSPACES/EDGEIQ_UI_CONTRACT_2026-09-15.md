# EDGEIQ UI / WORKSPACE CONTRACT — 2026-09-15

## STATUS: LOCKED

This document records the user-approved EDGEiQ product/UI decisions made during the 15 September 2026 workspace redesign. Where an older workspace specification conflicts with an explicit rule below, THIS CONTRACT TAKES PRECEDENCE until the underlying SPEC is revised.

## 1. GLOBAL PRODUCT DESIGN CONTRACT — LOCKED
EDGEiQ is professional racing intelligence software, not a tipping site, bookmaker interface or gimmicky racing website.

Locked presentation: light/white application shell; WHITE left sidebar; restrained EDGEiQ blue active navigation; crisp modern sans-serif typography; strong navy headings; muted secondary text; white panels with thin cool-grey borders, restrained shadows and small radius; dense scan-friendly tables; consistent shared race-day shell. No decorative clutter, glossy cards, gimmicks, oversized hero treatments or unnecessary explanatory copy. Production values must come from canonical/current-card data, validated historical data or governed EDGEiQ-derived metrics. Never fabricate values. `—`/Unavailable is a last resort.

### CANONICAL EDGEiQ LOGO / BRAND MARK — GLOBAL HARD LOCK
EVERY tab and workspace MUST use the SAME original/first EDGEiQ logo approved at the beginning of this new light-theme redesign. The logo must not drift, regenerate, morph, restyle or be redrawn per workspace. One canonical shared-shell asset/component is authoritative across the product.

### Track-condition display
Official labels: FAST 1; GOOD 2; GOOD 3; GOOD 4; SOFT 5; SOFT 6; SOFT 7; HEAVY 8; HEAVY 9; HEAVY 10. Actual condition tiles: FAST blue/white; GOOD green/white; SOFT red/white; HEAVY black/white. SYNTHETIC uses a white tile with black text and restrained border.

### LAST 5 RUNS FINISH-TILE RULE — GLOBAL HARD LOCK
Every Last 5 Runs sequence throughout EDGEiQ uses: `1` GOLD; `2` SILVER; `3` BRONZE; every other finishing number WHITE with BLUE number/text. This applies to every occurrence on every applicable workspace, including Race.

## 2. INSIGHTS — LOCKED
Tabs: Key Insights, Value, Risks, Angles, Summary. Evidence-backed racing intelligence only.

## 3. OVERVIEW — LOCKED
Executive race briefing with Key Runners, Pace & Tempo, Speed Map, Class & Ratings, Trainer/Jockey, Market, Weather & Track and Race Info context.

## 4. WEATHER — LOCKED
Governed current conditions, track conditions, forecasts and relevant weather analysis only. No fabricated weather/history.

## 5. TRACK — LOCKED
Core: Track Profile, Track Map, evidence-backed Track Characteristics, Current Conditions, Recent Track History and Track Notes. Recent Track History columns exactly `DATE | RAIL | GOING | RACES`.

## 6. RESULTS — LOCKED
Official results use SP ONLY; no Tote/dividends. No unlicensed hosted/copied replay/media. Governed EDGEiQ standard comparisons may be expressed in lengths. `-` slower than standard; `+` faster than standard.

## 7. MARKET — LOCKED
Professional pre-race market intelligence. Each runner has an individual actual-observation fluctuation board/sparkline. No invented price movements, exchange ladders, casino styling or Bet Now treatment.

## 8. SPEED MAP — LOCKED
Opening approximately 200m only. Victorian orientation RIGHT TO LEFT. Barriers on right, horses face left, actual barrier lanes and governed Early Speed Score determine mapped early positions. No finish prediction or slow/moderate/fast zones.

## 9. EPI RATINGS — LOCKED
Dedicated governed EDGEiQ Performance Index comparison workspace. No fabricated EPI ratings, ranks, trends or weights.

## 10. PERFORMANCE — LOCKED
Historical runner-performance workspace. Global Last 5 Runs finish-tile rule applies.

## 11. FORM — INCREMENTAL LOCK
Form is a runner-centric professional deep form guide rendered in EDGEiQ's approved light-theme language. It is distinct from Performance.

Form runner sub-tabs: `Last 5 Runs | Full Form | Race Comments | Trainer/Jockey | Ratings | Map`. Predictor is removed. Last 5 Runs and Full Form are locked. Historical semantic columns: `Date | Track | Race | Dist | Class | Going | Barrier | Wt | Jockey | Pos | Margin | SP | EPI | ERR | Race Notes`. EPI is horse-run specific; ERR is the EDGEiQ Race Rating for the race itself.

## 12. RACE / FIELD INFORMATION ARCHITECTURE — LOCKED
Standalone `Field` is removed from the sidebar and absorbed into Race. Principal sidebar flow:
`Home | Meetings | Race | Form | Performance | EPI Ratings | Speed Map | Market | Results | Track | Weather | Overview | Insights`, with Settings at the bottom.

## 13. RACE WORKSPACE — APPROVED AND LOCKED
Race is the authoritative launchpad for the selected race. The approved visual mockup uses the global light-theme shell and MUST retain the WHITE sidebar. A dark/navy sidebar is explicitly non-compliant.

### Shared meeting/race header
Race preserves the approved shared shell with:
- Canonical EDGEiQ logo.
- Search/navigation header.
- Selected meeting and date.
- Live/status context where genuine.
- Meeting heading and compact weather/track/rail context where governed.
- Horizontal R1–Rn selector with selected race highlighted in EDGEiQ blue.
- Race header containing official race number/name, distance, class/grade, weight conditions, rail, prize money, runner count, official going/weather and scheduled start time where canonical.

### Internal Race navigation
Approved direction:
`Field | Race Details | Key Determinants`

`Field` is the DEFAULT internal Race view. It is not restored to the sidebar.

### Field runner board — APPROVED
The principal Race view is a dense professional current-field table. Approved semantic direction, where canonical/governed values exist:
`# | Silks | Horse | Barrier | Trainer | Jockey | Weight | Age | Sex | Last 5 Runs | Going | ERR | EPI | EDGEiQ Price | Market | Edge`
plus a restrained row action/chevron for deeper runner navigation.

Implementation may adjust widths/responsive grouping without changing the information semantics.

### Last 5 Runs presentation — HARD RULE
Within the Race field table, EVERY occurrence of:
- `1` is GOLD.
- `2` is SILVER.
- `3` is BRONZE.
- all other finishing numbers are WHITE with BLUE text.
No exceptions. This is the same global rule used elsewhere in EDGEiQ.

### Going in Race field table
The Race view should show useful current-going context for the runner rather than fabricate data. If the column represents the actual current official track condition, it must be labelled/structured so that meaning is clear. If it represents the runner's record on today's going, use the governed record representation rather than merely repeating today's condition. Final implementation must avoid semantic ambiguity.

### ERR / EPI
- `EPI` remains the governed horse-specific performance/model figure.
- `ERR` remains EDGEiQ Race Rating and must retain its defined race-strength semantics.
- Do not generate these figures in React or populate illustrative mockup numbers.

### EDGEiQ Price / Market / Edge
These columns may appear where genuine current model and market data exist. Market values must be timestamped/sourced through the governed market pipeline. Edge must use the documented EDGEiQ convention; no mockup percentage may enter production.

### Supporting Race panels
The approved Race mockup uses restrained supporting panels below the field table:
- `Race Summary` — factual concise canonical race description only.
- `Market vs EDGEiQ Price` — only where governed current market/model data exists; no fabricated favourite/value callouts.
- `Quick Links` — useful navigation into specialist workspaces such as Form, Speed Map, Market and Track.

These panels must remain secondary to the field table and must not turn Race into a duplicate Overview/Insights dashboard.

### Race Details
Owns complete canonical race conditions/metadata that do not need to be repeated in every runner row.

### Key Determinants
Permitted only for concise evidence-backed race-level determinants. It must not duplicate Overview/Insights or be filled with generic generated commentary. If no governed determinants exist, show a truthful unavailable/empty state or omit the content.

### Specialist-boundary rule — HARD LOCK
- Individual historical horse depth -> Form.
- Historical comparative performance -> Performance.
- EPI model/rating analysis -> EPI Ratings.
- Opening-position projection -> Speed Map.
- Price/fluctuation depth -> Market.
- Completed outcomes -> Results.
Race does not duplicate those specialist workspaces.

### Race data integrity
All horse names, silks, barriers, connections, weights, ages/sex, last-five runs, going context, ERR, EPI, EDGEiQ prices, market prices, edges, summaries and determinants shown in design mockups are ILLUSTRATIVE ONLY. Production uses canonical/governed sources. No mockup value may be copied into live data.

### Race visual lock
- Sidebar = WHITE.
- Canonical first-design EDGEiQ logo only.
- Active Race navigation uses restrained blue highlight.
- White/light canvas and panels.
- Dense blue/navy typography and thin cool-grey borders.
- No dark sidebar.
- No bookmaker/casino treatment.
- No unnecessary explanatory copy.

This combined Race/Field workspace is now APPROVED AND LOCKED. Any structural redesign requires explicit contract revision.

## 14. FORM GOING RULE — GLOBAL CROSS-WORKSPACE LOCK
Default collapsed/current-field Form Going context, where used, shows the runner's record on TODAY'S GOING as plain text such as `8:1-2-4`, not a coloured badge merely repeating today's condition. Historical individual-run tables show actual historical going using the global condition colours.

## 15. GOVERNANCE
React is presentation/navigation, not the owner of racing intelligence calculations. Governed builders/services own derived metrics. No invented production data. Illustrative mockup values must never be copied into live data. When implementation conflicts with this contract, implementation must be corrected or the contract explicitly revised.

## LOCK RECORD
Locked in GitHub: 2026-09-15
Affected workspaces: INSIGHTS, OVERVIEW, WEATHER, TRACK, RESULTS, MARKET, SPEED MAP, EPI RATINGS, PERFORMANCE, FORM-LAST-5-RUNS, FORM-FULL-FORM, RACE/FIELD-CONSOLIDATION, RACE-WORKSPACE, FORM cross-workspace Going rule, GLOBAL DESIGN SYSTEM, CANONICAL EDGEiQ LOGO.
Standalone FIELD sidebar tab: REMOVED.
RACE workspace: APPROVED AND LOCKED.
Next workspace design: MEETINGS.
