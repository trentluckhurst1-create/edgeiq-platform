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

## 7. MARKET — LOCKED

Market is the approved professional pre-race market-intelligence workspace. It is analytical software, not a bookmaker, exchange or trading interface.

### Approved layout
- Common EDGEiQ meeting/race shell and race selector.
- Market sub-navigation may include: Market, Price Fluctuations, Implied Probability, Market vs EDGE, Runner Comparison.
- Hero component is the full-width `Market Prices & Fluctuations` runner table.
- Supporting panels below may include Market Summary, Price Distribution and concise Market Notes when supported by governed evidence.
- Dense, aligned, scan-friendly presentation consistent with the global design system.

### Runner table — locked information architecture
Each runner row must expose, where governed data exists:
1. Runner number / saddlecloth.
2. Horse.
3. Official SP where applicable as a historical/post-race reference; SP must NOT be mislabelled as the live/current pre-race market.
4. Current Win price.
5. Current Place price where a governed source supplies it.
6. An INDIVIDUAL inline Price Fluctuation board/sparkline for that runner.
7. Captured-period Low.
8. Captured-period High.
9. Implied Win probability.
10. Implied Place probability where a valid place price exists.
11. Governed EDGE metric.
12. Value/overlay classification.

### Per-runner fluctuation board — mandatory
The fluctuation board is not one generic chart for the race. EVERY runner has its own compact board directly in its row.

It must:
- Plot the runner's actual captured price observations chronologically.
- Show enough visual resolution to identify firming, drifting and stable movement.
- Display or expose useful opening/current/low/high context when captured.
- Use the same time window across runners when comparing the race.
- Use captured governed observations only.
- Never smooth, interpolate or fabricate missing observations.
- Never imply continuous price coverage where only sparse snapshots exist.
- Preserve historical captured observations as immutable market history.
- Show a professional unavailable/insufficient-history state if no valid fluctuation history exists.

A larger Price Fluctuations view may exist as a secondary analytical tab, but it does NOT replace the mandatory per-runner boards.

### Market price semantics
- The live/pre-race column must be labelled `Current Price`, `Market`, or another accurate source-specific label — NOT `SP`.
- `SP` means official Starting Price and is only displayed when it genuinely exists.
- Source/feed and last-updated timestamp must be explicit where practical.
- Do not claim a `consolidated Australian market` unless the canonical builder genuinely consolidates multiple authorised sources.
- No fabricated live prices, price histories or bookmaker data.

### Derived metrics
Derived values belong to governed builders/services, not ad-hoc React calculations.

Where supplied by the canonical builder:
- Raw market implied win probability = `1 / decimal current win price`.
- EDGEiQ implied probability = `1 / canonical EDGEiQ decimal price`.
- Any displayed EDGE/value percentage must use one documented convention consistently across EDGEiQ; probability edge and price overlay must not be silently mixed.
- Market overround may be displayed only when a complete enough governed market exists and is calculated from the applicable runner prices.
- Low/high values refer only to the captured governed observation window, never an invented 24-hour range.

### Market summary / notes
Useful evidence-backed summary items may include:
- Current market favourite.
- Market overround.
- Largest captured firmer.
- Largest captured drifter.
- Largest governed EDGEiQ overlay/value divergence.
- Last update/feed health.

Low-value summary statistics must not be included merely to fill cards. Market Notes must be factual, concise and generated from governed evidence; no generic or invented commentary.

### Explicitly excluded
- Back/Lay ladders.
- Exchange order books.
- Matched-volume/trading-terminal UI.
- Bookmaker logos or casino styling.
- `Bet Now` or wagering calls-to-action.
- Invented price movements.
- Smoothed/interpolated fluctuation histories.
- Fabricated market commentary.
- Tote/dividend presentation imported from Results.

### Mockup-data rule
All prices, runners, percentages, fluctuation paths, market notes and summary figures appearing in design mockups are ILLUSTRATIVE ONLY and must never be copied into production unless independently present in governed canonical data.

This Market specification is now LOCKED. Any future change requires an explicit contract revision.

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

Affected workspaces: INSIGHTS, OVERVIEW, WEATHER, TRACK, RESULTS, MARKET, FORM cross-workspace Going rule, GLOBAL DESIGN SYSTEM.

Next workspace in bottom-up approval sequence: SPEED MAP.
