# EDGEIQ UI / WORKSPACE CONTRACT — 2026-09-15

## STATUS: LOCKED

This document records the user-approved EDGEiQ product/UI decisions made during the 15 September 2026 workspace redesign. Where an older workspace specification conflicts with an explicit rule below, THIS CONTRACT TAKES PRECEDENCE until the underlying SPEC is revised.

## 1. GLOBAL PRODUCT DESIGN CONTRACT — LOCKED
EDGEiQ is professional racing intelligence software, not a tipping site, bookmaker interface or gimmicky racing website.

Locked presentation: light/white application shell; white left sidebar; restrained EDGEiQ blue active navigation; crisp modern sans-serif typography; strong navy headings; muted secondary text; white panels with thin cool-grey borders, restrained shadows and small radius; dense scan-friendly tables; consistent shared race-day shell. No decorative clutter, glossy cards, gimmicks, oversized hero treatments or unnecessary explanatory copy. Production values must come from canonical/current-card data, validated historical data or governed EDGEiQ-derived metrics. Never fabricate values. `—`/Unavailable is a last resort.

### CANONICAL EDGEiQ LOGO / BRAND MARK — GLOBAL HARD LOCK
- EVERY tab and workspace MUST use the SAME original/first EDGEiQ logo approved at the beginning of this new light-theme redesign.
- The logo must NOT gradually change, regenerate, morph, restyle, redraw or use a different wordmark from tab to tab.
- The same canonical logo asset/component must be reused globally from the shared shell; individual workspace components must not create their own logo treatment.
- Future mockups must preserve the first approved logo design rather than allowing image-generation drift.
- Implementation must reference one canonical logo source/asset so all screens are visually identical.
- This is a GLOBAL invariant applying to Home, Meetings, Race, Field, Form, Performance, EPI Ratings, Speed Map, Market, Results, Track, Weather, Overview, Insights and Settings.
- A workspace is non-compliant if its EDGEiQ logo differs from the canonical first redesign logo in lettering, proportions, icon geometry, tagline treatment, spacing or colour.

### Track-condition display
Official labels: FAST 1; GOOD 2; GOOD 3; GOOD 4; SOFT 5; SOFT 6; SOFT 7; HEAVY 8; HEAVY 9; HEAVY 10. Actual condition tiles: FAST blue/white; GOOD green/white; SOFT red/white; HEAVY black/white. SYNTHETIC uses a white tile with black text and a restrained border. Colour is supplementary; text remains explicit.

## 2. INSIGHTS — LOCKED
Tabs: Key Insights, Value, Risks, Angles, Summary. Top intelligence cards: Top Value, Key Risk, Angle, Watch Runner. Ranked Key Insights, Value Runners, Risks, Notable Angles, Race Summary and evidence/model-confidence coverage. Every insight must be evidence-backed and traceable.

## 3. OVERVIEW — LOCKED
Subtabs: Overview, Key Runners, Pace & Tempo, Speed Map, Class & Ratings, Trainer/Jockey, Market, Weather & Track, Race Info. Top cards: Race Summary, Top Value, Key Stat, Watch, Risk. Race Shape, Tempo Analysis, Track & Weather, Key Determinants, Class Comparison and Market vs Model. Executive race briefing only; specialist depth belongs in specialist workspaces.

## 4. WEATHER — LOCKED
May display governed current conditions, track conditions, Today/Tomorrow/Day+2 forecast, track/weather history, Weather Impact Analysis, Wind Analysis, Temperature Analysis and Historical Weather. No synthetic forecast, invented weather value or fabricated historical statistic.

## 5. TRACK — LOCKED
Core: Track Profile, clean Track Map, concise evidence-backed Track Characteristics, Current Conditions, Recent Track History, Track Notes. Recent Track History columns are exactly `DATE | RAIL | GOING | RACES`. Explicitly removed: Sectional Analysis, Track Records, Rail Position Performance, Going Performance, Distance Performance and generic low-value historical performance tables.

## 6. RESULTS — LOCKED
Official results use SP ONLY: no Tote column/dividends or exotic dividend panel. Do not host/copy/embed copyrighted replay/media without rights. Raw source sectional times must not be reproduced where rights are unavailable. Permitted sectional inputs may feed EDGEiQ's own governed standard-time comparison expressed in LENGTHS. Locked sign: `-2.5L` slower; `+2.5L` faster; `0.0L` on standard. Stewards information only where permitted and sourced correctly.

## 7. MARKET — LOCKED
Professional pre-race market intelligence, not bookmaker/trading UI. Hero is Market Prices & Fluctuations. Each runner row must expose governed current price information and an INDIVIDUAL inline price-fluctuation board/sparkline. Every runner's board plots actual captured observations only, with useful opening/current/low/high context where available; no smoothing/interpolation/fabrication. Live pre-race price must not be labelled SP. Derived implied probability/EDGE/overround belong to governed builders and use documented conventions. No Back/Lay ladders, exchange order books, bookmaker/casino styling, Bet Now CTAs, invented movements or fabricated commentary.

## 8. SPEED MAP — LOCKED
Early-race positioning workspace for approximately the first 200m only. Victorian presentation runs RIGHT TO LEFT. Barriers/start are on the RIGHT; every horse faces LEFT; each runner starts from its ACTUAL barrier lane; a thin path line runs from barrier to mapped early position. Higher governed Early Speed Score = farther LEFT from barriers. Vertical placement preserves barrier/lane relationship. All horses use the same navy treatment with horse-name tiles; no arbitrary colours. No slow/moderate/fast zones, leader/on-pace/midfield/backmarker zones, finish marker or full-race prediction. Supporting table may show runner, horse, barrier, Early Speed Score and governed early position/rank. Geometry must be canonical-data/model driven.

## 9. EPI RATINGS — LOCKED
EPI Ratings is the dedicated EDGEiQ Performance Index workspace. The principal view is the full-field EPI Ratings table. Where governed values exist rows may expose runner, horse, barrier, prominent EPI Rating, rank, defined delta versus field/race average, actual historical EPI trend, track/distance/going/class components and distinct governed composite assessment. Last-five trends use actual observations only; no interpolation. Component weights must come from canonical EPI configuration and never from mockup values. Insights must be evidence-backed. No fabricated ratings, ranks, trends, weights or generic threshold labels.

## 10. PERFORMANCE — LOCKED
Performance is the approved historical runner-performance workspace. It provides a compact current-field comparison centred on each runner's most recent runs, with deeper contextual performance summaries below.

### LAST 5 RUNS FINISH-TILE COLOUR CONTRACT — GLOBAL HARD RULE
For EVERY finish number displayed in a Last 5 Runs sequence: `1` = GOLD; `2` = SILVER; `3` = BRONZE; every other finishing number = WHITE with BLUE number/text. There are no exceptions.

Performance uses canonical historical/model data only; no fabricated results, insights or trends.

## 11. FORM — INCREMENTAL LOCK
Form is a runner-centric deep form workspace inspired by the information density/usefulness of a professional form guide, but rendered entirely in EDGEiQ's own approved light-theme visual language. It is NOT the Performance workspace.

### Form workspace shell — LOCKED
- Uses the global shared EDGEiQ race-day shell.
- Uses the exact canonical first-design EDGEiQ logo/brand asset. No logo drift or workspace-specific redraw.
- White sidebar with `Form` active.
- Left side contains the compact declared-runner selector/table with runner number/silk, horse, barrier, trainer and weight where governed.
- Selecting a runner opens that horse's detailed Form workspace in the main/right panel.
- Layout spacing must be clean, aligned and deliberately gridded: consistent card gutters, row heights, internal padding and baseline alignment. Avoid irregular empty areas or panels that appear scattered.

### Runner header — LOCKED
The selected-runner header may show canonical runner number, silk, horse name, age/sex/pedigree where available, trainer, jockey and current weight. All values must be canonical; no mockup values may enter production.

### Form runner sub-tabs — LOCKED ORDER
The runner-level navigation is exactly:
`Last 5 Runs | Full Form | Race Comments | Trainer/Jockey | Ratings | Map`

`Predictor` is REMOVED and must not appear anywhere in the Form workspace.

Each sub-tab is designed and approved separately. The currently approved sub-tab is `Last 5 Runs`. `Full Form` is next.

### LAST 5 RUNS — LOCKED
This sub-tab combines the selected horse's concise current profile with its five most recent valid historical starts.

#### Key Statistics
May show, where governed:
- Total Starts.
- Record / Career.
- Prize Money.
- Track record.
- Distance record.
- Track/Distance record.
- Last Start result/margin.
- Win %.
- Place %.

Explicitly REMOVED from this panel:
- Best Career.
- Average SP.
- Tempo Map.

Run Style (Last 5) may be retained only where it is a governed evidence-based output and adds useful context; it is not a substitute for the dedicated Map workspace.

#### Going Record
The selected horse's historical record by going may be shown using the locked going colours:
- FAST = blue tile / white text.
- GOOD = green tile / white text.
- SOFT = red tile / white text.
- HEAVY = black tile / white text.
- SYNTHETIC = white tile / black text with restrained border.

Going records must come from matched canonical historical starts.

#### Historical Last 5 Runs table — exact semantic columns
The table is:
`Date | Track | Race | Dist | Class | Going | Barrier | Wt | Jockey | Pos | Margin | SP | EPI | ERR | Race Notes`

Column semantics must not be mangled or substituted in implementation.

- `EPI` = the individual performance figure the HORSE ran in that specific historical race.
- `ERR` = `EDGEiQ Race Rating`, the governed overall standard/strength rating assigned to THAT RACE.
- ERR represents the assessed strength/standard of the race using the eventual governed EDGEiQ methodology, considering validated factors such as race time/standard, field quality/strength, race shape/pace, conditions and other approved evidence.
- ERR is race-level, therefore the same historical race has the same ERR for all runners from that race.
- EPI is runner-level and varies by horse/performance.
- The exact EPI/ERR formulae are owned by governed builders/model methodology, never invented in React.
- Historical SP is official SP only where genuinely available.
- Race Notes are sourced or independently governed EDGEiQ notes only; no fabricated prose.

#### Historical going display
The historical `Going` cell shows the ACTUAL condition for that run and uses the locked FAST/GOOD/SOFT/HEAVY/SYNTHETIC treatment above.

#### Supporting panels
The approved Last 5 Runs view may include:
- `Form Analysis` — concise evidence-backed analysis only.
- `Track / Going Record` — compact starts/wins/places/win% summary from matched historical data.
- `Ratings Explained` — restrained definitions of EPI and ERR.

Ratings explanation:
- **EPI (EDGEiQ Performance Index):** individual performance figure achieved by the horse in that run.
- **ERR (EDGEiQ Race Rating):** overall EDGEiQ assessment of the strength/standard of the race itself; same race-level value for all runners from that race.

### Form design exclusions — LOCKED
- No Predictor tab.
- No Tempo Map in Last 5 Runs.
- No Best Career row.
- No Average SP row.
- No duplicate Performance-workspace layout masquerading as Form.
- No fabricated race comments, EPI, ERR, records, run style, SP or statistics.
- No workspace-specific EDGEiQ logo variant.

### Mockup-data rule
ALL horse names, silks, records, statistics, dates, race details, SPs, EPI/ERR values, going records, analysis and notes visible in Form design mockups are ILLUSTRATIVE ONLY. Production consumes canonical field/history/model data.

The `Last 5 Runs` Form sub-tab is now LOCKED. The overall Form workspace remains incrementally open until its remaining approved sub-tabs are designed and locked.

## 12. FORM GOING RULE — GLOBAL CROSS-WORKSPACE LOCK
Default collapsed/current-field Form `Going` context, where used, shows the runner's record on TODAY'S GOING as plain text such as `8:1-2-4`, not a coloured badge merely repeating today's condition. Historical individual-run tables show the actual historical going with the global condition colours.

## 13. GOVERNANCE
React is presentation/navigation, not the owner of racing intelligence calculations. Governed builders/services own derived metrics. No invented production data. Illustrative mockup values must never be copied into live data. When implementation conflicts with this contract, implementation must be corrected or the contract explicitly revised. Future approved workspace decisions are written into GitHub.

## LOCK RECORD
Locked in GitHub: 2026-09-15
Affected workspaces: INSIGHTS, OVERVIEW, WEATHER, TRACK, RESULTS, MARKET, SPEED MAP, EPI RATINGS, PERFORMANCE, FORM-LAST-5-RUNS, FORM cross-workspace Going rule, GLOBAL DESIGN SYSTEM, CANONICAL EDGEiQ LOGO.
Next Form sub-tab: FULL FORM.
