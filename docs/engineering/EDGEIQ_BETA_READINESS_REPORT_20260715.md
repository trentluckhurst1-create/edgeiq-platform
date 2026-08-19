# EDGEiQ Beta Readiness Report - 2026-07-15

Generated: 2026-07-15T11:05:57Z

## Overall Status

**PARTIAL / STABILISED**

Active catalogue: 16 races / 211 runners.

This v2 report is rebuilt from current-app recovery audits, not stale historical coverage summaries.

## Feature Readiness

| Field | Status | Eligible Rows | Covered Rows | Coverage | Source/Builder | Blocker | Missing Reason |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| EPI | UNAVAILABLE | 211 | 0 | 0.00% | edgeiq_epi_current_rating_v1.csv | stale feed | STALE_FEED_CURRENT_UNIVERSE_MISMATCH |
| Suitability | UNAVAILABLE | 211 | 0 | 0.00% | edgeiq_current_suitability_v1.csv | stale feed | STALE_FEED_CURRENT_UNIVERSE_MISMATCH |
| Form Momentum | UNAVAILABLE | 211 | 0 | 0.00% | edgeiq_current_form_momentum_v1.csv | stale feed | STALE_FEED_CURRENT_UNIVERSE_MISMATCH |
| EDGEiQ Price | UNAVAILABLE | 211 | 0 | 0.00% | edgeiq_current_fair_prices_review_v5_2.csv | stale feed | STALE_FEED_CURRENT_UNIVERSE_MISMATCH |
| Early Speed | UNAVAILABLE | 211 | 0 | 0.00% | edgeiq_current_early_speed_v1.csv | stale feed | STALE_FEED_CURRENT_UNIVERSE_MISMATCH |
| Late Speed | UNAVAILABLE | 211 | 0 | 0.00% | edgeiq_current_late_speed_v1.csv | stale feed | STALE_FEED_CURRENT_UNIVERSE_MISMATCH |
| Market | PARTIAL | 211 | 106 | 50.24% | build_edgeiq_market_terminal_feed_v1.py | missing upstream evidence | No current external market source rows beyond catalog-embedded odds. |
| Market Open/Fluc | UNAVAILABLE | 211 | 0 | 0.00% | edgeiq_tab_market_v1.csv | stale feed | TAB/open/fluctuation source is stale and has no current active-catalogue runner matches. |
| Speed Map | UNAVAILABLE | 211 | 0 | 0.00% | build_edgeiq_map_terminal_feed_v1.py | stale feed | NO_CURRENT_DATE_MAP_SOURCE_ROWS |
| Insights | UNAVAILABLE | 291 | 0 | 0.00% | build_edgeiq_insights_terminal_feed_v1.py | stale feed | NO_CURRENT_DATE_INTELLIGENCE_SOURCE_ROWS |
| Historical EPI Tiles | UNAVAILABLE | 211 | 0 | 0.00% | build_edgeiq_epi_workspace_terminal_feed_v1.py | stale feed | NO_CURRENT_DATE_FORM_ENRICHMENT_ROWS |
| Gear | PARTIAL | 211 | 96 | 45.50% | audit_edgeiq_current_gear_availability_v1.py | partial upstream evidence | Partial current gear terminal detail; remaining rows are blank/no-change or not supplied. |
| ERI | NOT APPLICABLE YET | 16 | 0 | 0.00% | deferred ERI architecture | architecture deferred | WITHHELD_PENDING_GOVERNED_RESULTS_AND_SPEED_DATA |
| Results | UNAVAILABLE | 16 | 0 | 0.00% | build_edgeiq_meeting_results_terminal_feed_v1.py | missing upstream evidence | No governed current result row for active catalogue races. |

## Production Rules Confirmed

- No fabricated racing data was introduced.
- React remains a governed-data display layer.
- No pricing, EPI, suitability, form momentum, speed, sectionals or ERI maths changed.
- Missing values remain blank, pending or unavailable.
- Live-weather v1.2 integration was not overwritten.