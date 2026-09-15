# EDGEIQ UI / WORKSPACE CONTRACT — 2026-09-15

## STATUS: LOCKED

This document records the user-approved EDGEiQ product/UI decisions made during the 15 September 2026 workspace redesign. It is an implementation authority for the affected workspaces and supplements the existing SPEC files. Where an older workspace specification conflicts with an explicit rule below, THIS CONTRACT TAKES PRECEDENCE until the underlying SPEC is revised.

## 1. GLOBAL PRODUCT DESIGN CONTRACT

EDGEiQ is professional racing intelligence software, not a tipping site, bookmaker interface or gimmicky racing website.

Locked presentation:
- Light/white application shell.
- White left sidebar.
- EDGEiQ logo at top; active navigation uses restrained EDGEiQ blue.
- Crisp modern sans-serif typography; strong navy headings; muted secondary text.
- White cards/panels with thin cool-grey borders, restrained shadows and small radius.
- Dense, aligned, scan-friendly tables.
- EDGEiQ blue is the primary accent. Green/red/orange are used only where semantically meaningful.
- All race-day tabs use the same shared shell, spacing, header hierarchy, meeting header, race selector and footer treatment.
- No decorative clutter, glossy cards, gimmicks, oversized hero treatments or unnecessary explanatory copy.
- Production values must come from canonical/current-card data, validated historical data or governed EDGEiQ-derived metrics. Never fabricate values to fill a UI.
- `—`/Unavailable is a last resort when governed evidence genuinely does not exist.

### Track-condition display
Official labels are uppercase:
FAST 1; GOOD 2; GOOD 3; GOOD 4; SOFT 5; SOFT 6; SOFT 7; HEAVY 8; HEAVY 9; HEAVY 10.

Where an actual condition badge/tile is appropriate:
- FAST = blue / white text
- GOOD = green / white text
- SOFT = red / white text
- HEAVY = black / white text

Colour is supplementary; text remains explicit.

## 2. INSIGHTS — LOCKED

The approved Insights workspace uses the common shell and contains:
- Tabs: Key Insights, Value, Risks, Angles, Summary.
- Top intelligence cards: Top Value, Key Risk, Angle, Watch Runner.
- Ranked Key Insights panel.
- Value Runners table.
- Risks to Consider table.
- Notable Angles.
- Race Summary.
- Model/evidence confidence and data-quality coverage panel.

Every displayed insight must be evidence-backed and traceable. No fabricated prices, confidence values, risks, angles or commentary. No gimmicky presentation.

## 3. OVERVIEW — LOCKED

Approved Overview structure:
- Subtabs: Overview, Key Runners, Pace & Tempo, Speed Map, Class & Ratings, Trainer/Jockey, Market, Weather & Track, Race Info.
- Top cards: Race Summary, Top Value, Key Stat, Watch, Risk.
- Race Shape panel showing expected positional groups.
- Tempo Analysis.
- Track & Weather summary with compact track profile.
- Key Determinants.
- Class Comparison.
- Market vs Model comparison.

The workspace is an executive race briefing; deeper detail belongs in specialist workspaces. All intelligence is builder/evidence driven.

## 4. WEATHER — LOCKED

Approved Weather workspace may display, where governed data exists:
- Current Conditions: temperature, condition, feels-like, humidity, rainfall 24h, pressure, wind, cloud cover, last update.
- Track Conditions: track rating, rail, irrigation, rainfall 7d, penetrometer, going stick where available.
- Governed forecast information for Today/Tomorrow/Day+2 with useful time slots, chance of rain, wind and humidity where a licensed/approved source supplies it.
- Track/weather history where governed historical weather data exists.
- Weather Impact Analysis.
- Wind Analysis.
- Temperature Analysis.
- Historical Weather.

No synthetic forecast, invented weather value or fabricated historical statistic. If unavailable, show a professional unavailable state. Actual track-condition badges follow the global colour contract.

## 5. TRACK — LOCKED

The Track workspace must contain only useful, actionable track context. It is deliberately stripped of low-value statistical clutter.

Approved core panels:
- Track Profile: track name, location, direction/type, circumference, home straight, surface, current track rating, current rail, irrigation, penetrometer/going-stick where available, last update.
- Clean Track Map: course shape, direction, winning post/home straight and useful distance/start markers where accurate.
- Track Characteristics: concise evidence-backed permanent/operational characteristics only.
- Current Conditions.
- Recent Track History.
- Track Notes: concise, evidence-backed operational notes only.

### Recent Track History — locked columns
`DATE | RAIL | GOING | RACES`

There is NO duplicate Track column.

### Explicitly removed from Track
- Sectional Analysis
- Track Records
- Rail Position Performance
- Going Performance
- Distance Performance
- Other generic historical performance tables that do not provide valuable current-race intelligence

These removed components must not be reintroduced merely because data exists.

## 6. RESULTS — LOCKED

Results is a professional post-race evidence workspace, not a media/replay page.

### Official results table
Use official finishing order and relevant runner information. Market price display is:
- SP ONLY.
- NO Tote column.
- NO Tote dividends.
- NO Win/Place/Quinella/Exacta/Trifecta/First 4 dividend panel.

### Media rights rule
Do not host, copy or embed race replay video, replay thumbnails, last-600/400/200 video, photo-finish images or other copyrighted race media unless EDGEiQ has explicit appropriate rights/authorisation.

An ordinary outbound link to an authorised provider may be considered only where permitted. No scraping/rehosting of video.

### Sectional / standard-time intelligence
EDGEiQ must NOT reproduce source raw sectional times in the product where reproduction rights are unavailable.

Permitted source speed/sectional information may feed a governed EDGEiQ calculation where lawful/contractually permitted. The displayed product is EDGEiQ's OWN derived standard-time comparison expressed in LENGTHS, not copied raw seconds.

Standards should be appropriately normalised for relevant context such as track, distance, going and class rather than using a crude universal benchmark.

### Locked sign convention
- `-2.5L` means 2.5 lengths SLOWER than EDGEiQ standard.
- `+2.5L` means 2.5 lengths FASTER than EDGEiQ standard.
- `0.0L` means on standard.

This sign convention supersedes any older SPEC wording that states the opposite.

The UI must label the metric clearly as an EDGEiQ standard comparison so it cannot be confused with an official raw time.

Stewards information may be shown where its use is permitted and sourced correctly. EDGEiQ analytical notes must be independently derived and evidence-backed.

## 7. MARKET — CURRENT LOCKED DIRECTION

Market remains under active design, but the following decisions are already locked:
- Professional analytical market workspace; not a bookmaker/trading interface.
- Compare current market price with canonical EDGEiQ Price and governed edge/value classification.
- No Back/Lay ladder, exchange order book or trading UI.
- Each runner MUST have its OWN inline price-fluctuation board/sparkline directly in that runner's row rather than relying only on one large generic fluctuation chart.
- Runner fluctuation display should show the actual captured price path and useful low/high context.
- No smoothing or invented interpolation. Only captured governed price observations.
- The table remains dense and scan-friendly.
- Supporting Market Summary / Market Movers / Market Notes may be used when evidence-backed and useful.

The detailed Market contract remains open for further user refinement; these locked rules must survive later revisions.

## 8. FORM GOING RULE — GLOBAL CROSS-WORKSPACE LOCK

For the default runner Form table, the `Going` column does NOT show a coloured condition badge and does NOT merely repeat today's track condition.

It shows the runner's record on TODAY'S GOING as plain text, e.g. `8:1-2-4` = starts:wins-seconds-thirds.

Historical individual-run tables may show the actual going for that historical run using the uppercase condition label and global condition colours.

## 9. GOVERNANCE

- React is presentation/navigation, not the owner of racing intelligence calculations.
- Governed builders/services own derived metrics.
- No invented production data.
- Any illustrative values used in design mockups are NOT production data and must never be copied into the live product.
- When implementation conflicts with this document, implementation must be corrected or this contract explicitly revised.
- Future user-approved workspace decisions should be appended/revised in GitHub, not merely retained in chat.

## LOCK RECORD

Locked in GitHub: 2026-09-15

Affected workspaces: INSIGHTS, OVERVIEW, WEATHER, TRACK, RESULTS, MARKET (partial/current direction), FORM cross-workspace Going rule, GLOBAL DESIGN SYSTEM.
