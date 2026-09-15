# EDGEIQ UI / WORKSPACE CONTRACT — 2026-09-15

## STATUS: LOCKED

This document records the user-approved EDGEiQ product/UI decisions made during the 15 September 2026 workspace redesign. Where an older workspace specification conflicts with an explicit rule below, THIS CONTRACT TAKES PRECEDENCE until the underlying SPEC is revised.

## 1. GLOBAL PRODUCT DESIGN CONTRACT — LOCKED
EDGEiQ is professional racing intelligence software, not a tipping site, bookmaker interface or gimmicky racing website.

Locked presentation: light/white application shell; white left sidebar; restrained EDGEiQ blue active navigation; crisp modern sans-serif typography; strong navy headings; muted secondary text; white panels with thin cool-grey borders, restrained shadows and small radius; dense scan-friendly tables; consistent shared race-day shell. No decorative clutter, glossy cards, gimmicks, oversized hero treatments or unnecessary explanatory copy. Production values must come from canonical/current-card data, validated historical data or governed EDGEiQ-derived metrics. Never fabricate values. `—`/Unavailable is a last resort.

### CANONICAL EDGEiQ LOGO / BRAND MARK — GLOBAL HARD LOCK
EVERY tab and workspace MUST use the SAME original/first EDGEiQ logo approved at the beginning of this new light-theme redesign. The logo must not drift, regenerate, morph, restyle or be redrawn per workspace. One canonical shared-shell asset/component is authoritative across the product.

### Track-condition display
Official labels: FAST 1; GOOD 2; GOOD 3; GOOD 4; SOFT 5; SOFT 6; SOFT 7; HEAVY 8; HEAVY 9; HEAVY 10. Actual condition tiles: FAST blue/white; GOOD green/white; SOFT red/white; HEAVY black/white. SYNTHETIC uses a white tile with black text and restrained border.

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
Historical runner-performance workspace. Last-five finish tiles globally: `1` GOLD; `2` SILVER; `3` BRONZE; every other finish WHITE with BLUE number/text.

## 11. FORM — INCREMENTAL LOCK
Form is a runner-centric professional deep form guide rendered in EDGEiQ's approved light-theme language. It is distinct from Performance.

### Form workspace shell — LOCKED
- Global shared race-day shell and exact canonical EDGEiQ logo.
- White sidebar with `Form` active.
- Compact declared-runner selector/table at left.
- Selected runner opens detailed form workspace at right.
- Clean deliberate grid, consistent gutters, row heights and padding.

### Runner header — LOCKED
May show canonical runner number, silk, horse name, age/sex/pedigree where available, trainer, jockey and current weight.

### Form runner sub-tabs — LOCKED ORDER
`Last 5 Runs | Full Form | Race Comments | Trainer/Jockey | Ratings | Map`

`Predictor` is REMOVED.

### LAST 5 RUNS — LOCKED
Key Statistics may show Total Starts, Record/Career, Prize Money, Track, Distance, Track/Distance, Last Start, Win % and Place %. Best Career, Average SP and Tempo Map are removed.

Going Record uses FAST blue, GOOD green, SOFT red, HEAVY black, SYNTHETIC white/black.

Historical table semantic columns exactly:
`Date | Track | Race | Dist | Class | Going | Barrier | Wt | Jockey | Pos | Margin | SP | EPI | ERR | Race Notes`

`EPI` = individual performance figure the horse ran in that historical race.
`ERR` = EDGEiQ Race Rating, the governed overall strength/standard rating of the race itself. ERR is race-level and therefore identical for all runners from the same race; EPI is runner-level.

Supporting panels may include evidence-backed Form Analysis, Track/Going Record and Ratings Explained.

### FULL FORM — LOCKED
The Full Form sub-tab extends the approved Last 5 Runs presentation to the selected horse's complete available canonical race history. It is intentionally the same visual language and core information architecture as Last 5 Runs rather than a separate gimmicky design.

#### Full Form purpose
- Show every valid historical start available for the selected runner, newest to oldest by default.
- Preserve the same runner header, key-statistics context, going-record treatment and runner-level navigation so switching between Last 5 Runs and Full Form feels continuous.
- Full Form differs from Last 5 Runs primarily by historical depth, not by introducing unrelated analytics.

#### Full Form history table — exact semantic columns
`Date | Track | Race | Dist | Class | Going | Barrier | Wt | Jockey | Pos | Margin | SP | EPI | ERR | Race Notes`

These semantics are identical to Last 5 Runs:
- `EPI` = horse-specific individual performance figure for that run.
- `ERR` = EDGEiQ Race Rating for the race itself.
- Historical Going uses the locked actual-condition colour system.
- Historical SP is official SP only where available.
- Race Notes must be sourced or governed EDGEiQ analysis; never fabricated.

#### Full Form behaviour
- The table must support a long career history without making the workspace visually chaotic; compact rows, sticky/clear headings and practical scrolling/pagination/expansion are permitted implementation choices.
- The complete history must remain scan-friendly and chronological.
- Missing history is not manufactured to create a full-looking table.
- The screen may retain the approved evidence-backed supporting panels from Last 5 Runs where useful, but they must not crowd out the full-history table.

#### Explicit Full Form exclusions
- No additional duplicate rating column beyond governed EPI and ERR merely to fill space.
- No Predictor.
- No fabricated historical starts, comments, prices, EPI or ERR.
- No unrelated Performance dashboard widgets.
- No workspace-specific logo treatment.

The `Full Form` sub-tab is now LOCKED.

### Form design exclusions — GLOBAL WITHIN FORM
No Predictor tab. No Tempo Map in Last 5 Runs. No Best Career row. No Average SP row. No fabricated comments/ratings/statistics. No duplicate Performance workspace masquerading as Form.

### Mockup-data rule
ALL horse names, silks, records, statistics, dates, race details, SPs, EPI/ERR values, going records, analysis and notes visible in Form design mockups are ILLUSTRATIVE ONLY. Production consumes canonical field/history/model data.

## 12. FORM GOING RULE — GLOBAL CROSS-WORKSPACE LOCK
Default collapsed/current-field Form `Going` context, where used, shows the runner's record on TODAY'S GOING as plain text such as `8:1-2-4`, not a coloured badge merely repeating today's condition. Historical individual-run tables show actual historical going using the global condition colours.

## 13. GOVERNANCE
React is presentation/navigation, not the owner of racing intelligence calculations. Governed builders/services own derived metrics. No invented production data. Illustrative mockup values must never be copied into live data. When implementation conflicts with this contract, implementation must be corrected or the contract explicitly revised.

## LOCK RECORD
Locked in GitHub: 2026-09-15
Affected workspaces: INSIGHTS, OVERVIEW, WEATHER, TRACK, RESULTS, MARKET, SPEED MAP, EPI RATINGS, PERFORMANCE, FORM-LAST-5-RUNS, FORM-FULL-FORM, FORM cross-workspace Going rule, GLOBAL DESIGN SYSTEM, CANONICAL EDGEiQ LOGO.
Next workspace review: FIELD / RACE information-architecture consolidation.
