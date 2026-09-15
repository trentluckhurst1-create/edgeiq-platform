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

### Form runner sub-tabs — LOCKED ORDER
`Last 5 Runs | Full Form | Race Comments | Trainer/Jockey | Ratings | Map`
`Predictor` is REMOVED.

### LAST 5 RUNS — LOCKED
Key Statistics may show Total Starts, Record/Career, Prize Money, Track, Distance, Track/Distance, Last Start, Win % and Place %. Best Career, Average SP and Tempo Map are removed.
Going Record uses FAST blue, GOOD green, SOFT red, HEAVY black, SYNTHETIC white/black.
Historical table columns exactly:
`Date | Track | Race | Dist | Class | Going | Barrier | Wt | Jockey | Pos | Margin | SP | EPI | ERR | Race Notes`
`EPI` = individual performance figure the horse ran. `ERR` = EDGEiQ Race Rating, the governed overall strength/standard rating of that race.

### FULL FORM — LOCKED
Full Form extends the same professional presentation to every valid historical start available for the selected horse, newest to oldest by default. It uses the same exact semantic columns as Last 5 Runs and does not introduce unrelated analytics. No fabricated history, comments, prices, EPI or ERR.

## 12. RACE / FIELD INFORMATION ARCHITECTURE — LOCKED

### Standalone Field tab is REMOVED
`Field` is no longer a top-level EDGEiQ sidebar workspace. Maintaining separate `Race` and `Field` destinations creates unnecessary overlap and forces the user to decide between two screens that answer closely related questions.

The declared field is now absorbed into the `Race` workspace.

### Product hierarchy
The principal race-day sidebar flow is:
`Home | Meetings | Race | Form | Performance | EPI Ratings | Speed Map | Market | Results | Track | Weather | Overview | Insights`
with `Settings` retained separately at the bottom of the shell.

There must be NO standalone `Field` item in the sidebar after this contract is implemented.

### Race workspace purpose
Race is the authoritative launchpad for the selected race. It answers:
- What race is this?
- What are its conditions?
- Who is running?
- What are the essential current-field facts needed before moving into specialist analysis?

Race must NOT attempt to reproduce the depth of Form, Performance, EPI Ratings, Speed Map or Market. Those remain specialist workspaces.

### Field becomes the default Race view
The selected race opens with its declared field as the principal/default Race view. `Field` may be used as an internal Race sub-tab/view label, but never as a separate sidebar workspace.

The default field/runner board may expose, where canonical data exists:
- Runner number.
- Silk.
- Horse.
- Barrier.
- Trainer.
- Jockey.
- Weight.
- Age/Sex where useful.
- Last 5 Runs using the globally locked finish-tile convention.
- Current relevant record/context such as track, distance or today's going where useful and not duplicative.
- Scratching status.

Rows may expand for concise essential runner context, but Race must not become a second Form guide.

### Race-level information
Race owns race-level metadata such as:
- Race number and official race name.
- Scheduled start time.
- Distance.
- Class/grade.
- Weight conditions.
- Prize money where canonical.
- Track and rail.
- Current official going.
- Field/runner count.
- Scratchings.
- Other canonical race conditions that materially describe the event.

### Internal Race navigation
The exact final internal labels remain subject to the Race mockup, but the approved architecture is a small number of race-level views rather than another large navigation system. Preferred direction:
`Field | Race Details | Key Factors`

`Field` is the default view.

`Race Details` contains the complete canonical conditions/metadata that do not belong in every runner row.

`Key Factors` is permitted only for concise, evidence-backed race-level determinants that do not duplicate Overview/Insights. If it cannot add distinct value, it should be omitted rather than filled with generic commentary.

### Specialist-boundary rule — HARD LOCK
Race is a launchpad, not a duplicate analytics dashboard.
- Individual horse historical depth -> `Form`.
- Historical comparative performance -> `Performance`.
- EPI model/rating analysis -> `EPI Ratings`.
- Opening-position projection -> `Speed Map`.
- Price/market movement -> `Market`.
- Completed race outcomes -> `Results`.

Do not repeat entire specialist tables inside Race.

### Data and interaction rules
- Declared runners and race conditions must come from canonical current-card data.
- Scratchings must be visually unambiguous and governed by the current canonical card state.
- No fabricated runner, barrier, jockey, weight, condition or race metadata.
- Clicking a horse may provide a clear route into its Form workspace while preserving selected meeting/race/runner context.
- Specialist navigation should preserve the currently selected meeting and race.

### Sidebar migration rule
Existing implementation references to the old standalone Field route/tab must be migrated deliberately. Removing the sidebar item must not break runner selection, race selection or deep links. Where legacy Field navigation is retained temporarily for compatibility, it should resolve/redirect to the Race workspace's Field view rather than expose a second competing product screen.

This Race/Field consolidation is now LOCKED. Any future reintroduction of a standalone Field sidebar workspace requires an explicit contract revision.

## 13. FORM GOING RULE — GLOBAL CROSS-WORKSPACE LOCK
Default collapsed/current-field Form `Going` context, where used, shows the runner's record on TODAY'S GOING as plain text such as `8:1-2-4`, not a coloured badge merely repeating today's condition. Historical individual-run tables show actual historical going using the global condition colours.

## 14. GOVERNANCE
React is presentation/navigation, not the owner of racing intelligence calculations. Governed builders/services own derived metrics. No invented production data. Illustrative mockup values must never be copied into live data. When implementation conflicts with this contract, implementation must be corrected or the contract explicitly revised.

## LOCK RECORD
Locked in GitHub: 2026-09-15
Affected workspaces: INSIGHTS, OVERVIEW, WEATHER, TRACK, RESULTS, MARKET, SPEED MAP, EPI RATINGS, PERFORMANCE, FORM-LAST-5-RUNS, FORM-FULL-FORM, RACE/FIELD-CONSOLIDATION, FORM cross-workspace Going rule, GLOBAL DESIGN SYSTEM, CANONICAL EDGEiQ LOGO.
Standalone FIELD sidebar tab: REMOVED.
Next workspace design: RACE (combined Race + Field launchpad).
