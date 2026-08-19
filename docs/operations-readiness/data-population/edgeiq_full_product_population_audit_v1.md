# EDGEIQ Full Product Population Audit V1

Overall Status: PARTIAL
Daily Betting Readiness: NO

Current Meetings: 2
Current Races: 17
Declared Runners: 246
Active Runners: 213
Scratched Runners: 33

## Coverage
- Recent Form Eligible / Populated: 186 / 186
- Epi Eligible / Populated: 186 / 167
- Eri Eligible / Populated: 186 / 167
- Early Speed Eligible / Populated: 213 / 107
- Late Speed Eligible / Populated: 213 / 109
- Suitability Eligible / Populated: 213 / 169
- Form Momentum Eligible / Populated: 213 / 172
- Fair Price Eligible / Populated: 213 / 166
- Market Available / Populated: 241 / 241
- Edge Eligible / Populated: 166 / 166
- Map Eligible / Populated: 213 / 107
- Profile Eligible / Populated: 213 / 187

Unexplained Blanks: 0

## Failure Reasons
- STALE_PUBLIC_FEED: 137
- SCRATCHED: 119
- FIRST_STARTER: 112
- NO_RUN_STYLE_EVIDENCE: 106
- BUILD_ORDER_FAILURE: 75
- ELIGIBILITY_FAILURE: 66
- INSUFFICIENT_HISTORICAL_RUNS: 61
- SOURCE_NOT_BUILT: 57
- GENUINELY_UNAVAILABLE: 54
- NO_HISTORICAL_EARLY_SPEED: 52
- NO_ASOF_EVIDENCE: 52
- INSUFFICIENT_RUNS: 42
- INSUFFICIENT_BENCHMARKED_RUNS: 20
- OTHER: 20
- INSUFFICIENT_FACTOR_FAMILIES: 16
- MARKET_UNAVAILABLE: 10
- NO_COMPARABLE_DISTANCE: 4
- SOURCE_EMPTY: 2

## Root Cause
Stale race_fields/current form/EPI/fair-price publication. Current race fields and as-of form/speed/map joins were repaired; EPI/ERI/fair-price are governed-limited by prior performance evidence rather than blank upstream publication.
