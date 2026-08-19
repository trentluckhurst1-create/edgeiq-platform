# FINAL LIVE DATA POPULATION AUDIT V1

Marker: `EDGEIQ_FINAL_LIVE_DATA_POPULATION_AUDIT_PASS`

## Canonical Universe

- Pipeline status: `READY`
- Melbourne date: `2026-07-20`
- Window dates: `2026-07-20; 2026-07-21; 2026-07-22`
- Meetings: `4`
- Races: `26`
- Catalog runners: `374`
- HOME today meetings: `2`
- HOME today races: `10`
- HOME today declared: `170`

## Checks

| Check | Expected | Actual | Status | Notes |
|---|---|---:|---|---|
| pipeline_status_ready | READY | READY | PASS |  |
| current_window_dates | 2026-07-20..2026-07-22 | 2026-07-20;2026-07-21;2026-07-22 | PASS |  |
| catalog_meeting_count | >=4 | 4 | PASS |  |
| catalog_race_count | 26 | 26 | PASS |  |
| catalog_runner_count | 374 | 374 | PASS |  |
| home_today_meetings | >=2 | 2 | PASS |  |
| home_today_races | 10 | 10 | PASS | Coleraine trial meeting has 0 races; Pakenham has 10 races |
| home_today_declared | 170 | 170 | PASS |  |
| no_public_data_browser_paths | 0 | 0 | PASS |  |
| no_raw_failed_fetch_visible | controlled unavailable state | controlled | PASS |  |
| no_demo_mock_runtime_catalog_records | 0 | 0 | PASS |  |
| runtime_feed_http_200 | 32 | 32 | PASS |  |
| runtime_feed_parse_success | 32 | 32 | PASS |  |
| live_feed_catalogue_alignment | all live aligned or no-date | 12 | PASS |  |
| probability_integrity_proxy | market and epi feeds >= catalog runners | market=374; epi=374 | PASS | No pricing/probability math altered; presence/count integrity only |
| workspace_source_availability | 19 | 19 | PASS | HOME; MEETINGS; RACE; FIELD; FORM GUIDE; PERFORMANCE; MAP; EPI; MARKET; OVERVIEW; SCRATCHINGS; GEAR CHANGES; TRACK; WEATHER; RESULTS; INSIGHTS; LAB; COMPARE; REVIEW |

## Workspace Source Map

| Workspace | Primary governed source | Browser population expectation |
|---|---|---|
| HOME | edgeiq_three_day_product_catalog_v1.json + edgeiq_daily_pipeline_status_v1.json | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| MEETINGS | edgeiq_three_day_product_catalog_v1.json | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| RACE | edgeiq_three_day_product_catalog_v1.json + edgeiq_overview_terminal_feed_v1.csv | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| FIELD | edgeiq_three_day_product_catalog_v1.json | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| FORM GUIDE | edgeiq_form_guide_enriched_v2.json | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| PERFORMANCE | public/performance-intelligence/edgeiq_performance_intelligence_product_feeds_v1.json | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| MAP | edgeiq_map_terminal_feed_v1.csv | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| EPI | edgeiq_epi_workspace_terminal_feed_v1.csv | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| MARKET | edgeiq_market_terminal_feed_v1.csv | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| OVERVIEW | edgeiq_overview_terminal_feed_v1.csv | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| SCRATCHINGS | edgeiq_three_day_product_catalog_v1.json runner scratch flags | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| GEAR CHANGES | edgeiq_gear_terminal_feed_v1.csv | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| TRACK | edgeiq_on_track_weather_governed_v1_2.json + track profile feeds | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| WEATHER | edgeiq_on_track_weather_governed_v1_2.json | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| RESULTS | edgeiq_meeting_results_terminal_feed_v1.csv | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| INSIGHTS | edgeiq_insights_terminal_feed_v1.csv | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| LAB | active governed research datasets | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| COMPARE | current catalogue runner context | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
| REVIEW | meeting results feed when completed | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |
