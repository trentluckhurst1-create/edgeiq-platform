# EDGEIQ UI / WORKSPACE CONTRACT — 2026-09-15

## STATUS: LOCKED

This document records the user-approved EDGEiQ product/UI decisions made during the 15 September 2026 workspace redesign. It is an implementation authority for the affected workspaces and supplements the existing SPEC files. Where an older workspace specification conflicts with an explicit rule below, THIS CONTRACT TAKES PRECEDENCE until the underlying SPEC is revised.

## 1. GLOBAL PRODUCT DESIGN CONTRACT
EDGEiQ is professional racing intelligence software, not a tipping site, bookmaker interface or gimmicky racing website.
Locked presentation: light/white application shell; white left sidebar; restrained EDGEiQ blue active navigation; crisp modern sans-serif typography; strong navy headings; muted secondary text; white panels with thin cool-grey borders, restrained shadows and small radius; dense scan-friendly tables; consistent shared race-day shell. No decorative clutter, glossy cards, gimmicks, oversized hero treatments or unnecessary explanatory copy. Production values must come from canonical/current-card data, validated historical data or governed EDGEiQ-derived metrics. Never fabricate values. `—`/Unavailable is a last resort.

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

EPI Ratings is the dedicated EDGEiQ Performance Index workspace. It is a dense comparative ratings screen designed to rank the current field and expose the governed components behind each runner's EPI assessment without bookmaker-style presentation or unnecessary explanatory clutter.

### Approved shell and navigation
- Uses the common EDGEiQ meeting/race shell and race selector.
- `EPI Ratings` is active in the white sidebar.
- Approved EPI sub-navigation may include: `EPI Ratings | Key Determinants | Form & EPI Trend | Class & Conditions | Runner Comparison`.
- The principal view is the full-field EPI Ratings table.

### EPI Ratings table — approved information architecture
Where governed values exist, each runner row may expose:
- Runner number.
- Horse.
- Barrier.
- EPI Rating as a prominent numeric value with a restrained comparative bar.
- EPI Rank.
- Delta versus the relevant governed field/race average (`Δ vs Avg`) where the comparison basis is explicitly defined.
- Last-five EPI trend as a compact sparkline where valid historical EPI observations exist.
- Track suitability/component score.
- Distance suitability/component score.
- Going suitability/component score.
- Class component/assessment.
- Overall/current composite assessment where this is a distinct governed output rather than a duplicate invented value.

The table must be sortable/scan-friendly in implementation and keep the EPI Rating/rank visually dominant over supporting components.

### Trend display
- Last-five trend uses actual governed historical EPI observations only.
- Never manufacture missing historical points or interpolate a smooth trend.
- If fewer valid observations exist, show only those observations or an appropriate insufficient-history state.
- Trend direction/shape is analytical evidence, not decorative animation.

### Component and determinant presentation
Supporting panels may include `EPI Insights` and `EPI Component Weights`/determinants where these values genuinely exist in the governed EPI methodology.
- Component weights shown in the product MUST come from the canonical EPI model/configuration.
- Never copy the illustrative percentages from a design mockup into production.
- Never invent a component merely to complete a visual.
- If EPI architecture changes, the UI must consume the governed current architecture rather than preserving stale hard-coded weights.

### EPI Insights
Concise evidence-backed insights may identify meaningful field-leading ratings, component strengths/weaknesses, trend changes or suitability differences. No fabricated horse commentary, improvement claims or confidence language.

### Methodology / About EPI
A restrained methodology panel may explain what EPI represents at product level, but it must not expose false formulas or claim inputs/weights that are not present in the governed EPI model. Detailed implementation/model logic remains owned by the governed builder/model documentation, not React copy.

### Semantic colour
- EDGEiQ blue is the default rating/bar colour.
- Green/red may be used sparingly for genuinely positive/negative deltas such as above/below a defined field average.
- Do not turn the table into a heatmap or traffic-light tipping interface.

### Explicitly excluded
- Fabricated EPI ratings or ranks.
- Hard-coded component weights derived from the mockup.
- Synthetic last-five trends.
- Generic labels such as `strong`, `weak`, `improving` unless supported by governed thresholds/evidence.
- Betting calls-to-action or bookmaker styling.
- Duplicative metrics that do not add analytical value.

### Mockup-data rule
ALL runner names, ratings, ranks, deltas, trend paths, component scores, weights and insight text in the approved visual mockup are ILLUSTRATIVE ONLY. Production must use canonical field data and governed EDGEiQ EPI outputs.

This EPI Ratings specification is now LOCKED. Any future change requires an explicit contract revision.

## 10. FORM GOING RULE — GLOBAL CROSS-WORKSPACE LOCK
Default Form `Going` column shows the runner's record on TODAY'S GOING as plain text, e.g. `8:1-2-4`, not a coloured badge and not today's condition repeated. Historical individual-run tables may show the actual historical going with the global condition colours.

## 11. GOVERNANCE
React is presentation/navigation, not the owner of racing intelligence calculations. Governed builders/services own derived metrics. No invented production data. Illustrative mockup values must never be copied into live data. When implementation conflicts with this contract, implementation must be corrected or the contract explicitly revised. Future approved workspace decisions are written into GitHub.

## LOCK RECORD
Locked in GitHub: 2026-09-15
Affected workspaces: INSIGHTS, OVERVIEW, WEATHER, TRACK, RESULTS, MARKET, SPEED MAP, EPI RATINGS, FORM cross-workspace Going rule, GLOBAL DESIGN SYSTEM.
Next workspace in bottom-up approval sequence: PERFORMANCE.
