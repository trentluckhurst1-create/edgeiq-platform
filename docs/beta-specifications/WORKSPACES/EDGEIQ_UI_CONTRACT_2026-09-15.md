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
Official labels: FAST 1; GOOD 2; GOOD 3; GOOD 4; SOFT 5; SOFT 6; SOFT 7; HEAVY 8; HEAVY 9; HEAVY 10. Actual condition tiles: FAST blue/white; GOOD green/white; SOFT red/white; HEAVY black/white. Colour is supplementary; text remains explicit.

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

### Approved layout
- Uses the global shared shell and canonical EDGEiQ logo.
- `Performance` active in the white sidebar.
- Main hero table: `Runner Performance – Last 5 Runs`.
- Controls may filter the governed run window and track/context where useful.
- Supporting panels may include Performance Insights, Distance Performance, Track Performance and Going Performance when supported by canonical history.

### Main Runner Performance table
Where governed data exists, rows may include:
- Runner number.
- Horse.
- Barrier.
- Last 5 Runs, most recent first.
- Days since last run.
- Distance/range context.
- Track/Going.
- Class.
- EPI.
- R58 or other governed rating only where it remains an approved canonical metric.
- WFA/performance figure where governed.
- Compact finish-position/history trend where useful.
- Margin.
- SP where historical official SP exists.
- EDGEiQ price or other governed current assessment where appropriate and clearly labelled.

No illustrative value from the mockup may be copied into production.

### LAST 5 RUNS FINISH-TILE COLOUR CONTRACT — GLOBAL HARD RULE
For EVERY finish number displayed in the `Last 5 Runs` sequence:
- `1` = GOLD tile.
- `2` = SILVER tile.
- `3` = BRONZE tile.
- `4` and every other finishing number = WHITE tile with BLUE number/text.

This applies to EVERY occurrence of 1st, 2nd and 3rd in every runner's last-five sequence. There are no exceptions based on runner, recency, track, race or table position.

The styling represents finishing position only:
- Gold always means FIRST.
- Silver always means SECOND.
- Bronze always means THIRD.
- No other finishing position receives medal colouring.
- Do not use arbitrary green, grey or blue fills for 1/2/3.
- Non-medal results remain white with blue numbers for a clean, consistent scan pattern.

### Performance Insights
Only evidence-backed insights derived from canonical historical data may be shown. Do not fabricate statements such as consistency, improvement, distance credentials or competitive ability merely to fill the panel.

### Distance / Track / Going Performance
Compact supporting tables may show relevant governed starts/runs, wins, placings and win/place percentages for the current runners. These panels must use correctly matched historical contexts and must not infer missing records.

### Trend / sparkline rule
Any compact performance trend uses actual governed historical observations only. No invented points, smoothing or interpolation.

### Explicitly excluded
- Fabricated last-five results.
- Incorrect medal colours.
- Synthetic performance insights.
- Duplicative low-value statistics merely to fill space.
- Bookmaker/casino presentation.
- Workspace-specific EDGEiQ logo variants.

### Mockup-data rule
ALL runner names, barriers, last-five sequences, days, ratings, margins, SPs, prices, trends, insights and supporting performance statistics in design mockups are ILLUSTRATIVE ONLY. Production consumes canonical field/history/model data.

This Performance specification is now LOCKED. Any future change requires an explicit contract revision.

## 11. FORM GOING RULE — GLOBAL CROSS-WORKSPACE LOCK
Default Form `Going` column shows the runner's record on TODAY'S GOING as plain text, e.g. `8:1-2-4`, not a coloured badge and not today's condition repeated. Historical individual-run tables may show the actual historical going with the global condition colours.

## 12. GOVERNANCE
React is presentation/navigation, not the owner of racing intelligence calculations. Governed builders/services own derived metrics. No invented production data. Illustrative mockup values must never be copied into live data. When implementation conflicts with this contract, implementation must be corrected or the contract explicitly revised. Future approved workspace decisions are written into GitHub.

## LOCK RECORD
Locked in GitHub: 2026-09-15
Affected workspaces: INSIGHTS, OVERVIEW, WEATHER, TRACK, RESULTS, MARKET, SPEED MAP, EPI RATINGS, PERFORMANCE, FORM cross-workspace Going rule, GLOBAL DESIGN SYSTEM, CANONICAL EDGEiQ LOGO.
Next workspace in bottom-up approval sequence: FORM.
