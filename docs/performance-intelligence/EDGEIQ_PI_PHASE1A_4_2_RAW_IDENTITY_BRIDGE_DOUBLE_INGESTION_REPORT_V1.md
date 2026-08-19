# EDGEIQ Performance Intelligence

## Phase 1A.4.2 Raw Identity Bridge and Double-Ingestion Audit V1

- Program ID: `EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE1A_4_2_RAW_IDENTITY_BRIDGE_DOUBLE_INGESTION_AUDIT_V1`
- Generated UTC: `2026-07-27T03:41:24+00:00`
- Overall status: **FAIL**

## Dataset Profiles

| Target | Rows | Unique Raw Keys | Duplicate Rows | Duplicate Groups |
|---|---:|---:|---:|---:|
| `GRAPHQL_RAW` | 879784 | 879695 | 89 | 89 |
| `OBSERVATION_RAW` | 1772640 | 881580 | 879980 | 879802 |
| `PERFORMANCE_WAREHOUSE_SOURCE_RECORD_KEY` | 879784 | 879695 | 89 | 89 |

## Raw Identity Overlap

| Left | Right | Intersection | Left Only | Right Only | Jaccard |
|---|---|---:|---:|---:|---:|
| `GRAPHQL_RAW` | `OBSERVATION_RAW` | 879695 | 0 | 1885 | 0.9978617936 |
| `GRAPHQL_RAW` | `PERFORMANCE_WAREHOUSE_SOURCE_RECORD_KEY` | 879695 | 0 | 0 | 1.0 |
| `OBSERVATION_RAW` | `PERFORMANCE_WAREHOUSE_SOURCE_RECORD_KEY` | 879695 | 1885 | 0 | 0.9978617936 |

## Observation Source Paths

| System | Class | Path | Rows | Unique Keys | Within-Path Duplicates |
|---|---|---|---:|---:|---:|
| EDGEIQ | EDGEIQ_SOURCE | `public/data/edgeiq_horse_performance_observation_fact_v1.csv` | 18 | 18 | 0 |
| EDGEIQ | EDGEIQ_SOURCE | `public/data/edgeiq_ladbrokes_market_feed_v1.csv` | 14 | 0 | 14 |
| EDGEIQ | EDGEIQ_SOURCE | `public/data/edgeiq_live_nexus_contextual_feed_v2.csv` | 41 | 0 | 41 |
| EDGEIQ | EDGEIQ_SOURCE | `public/data/edgeiq_live_runner_board_governed_v1_checkpoint_before_current_intel_rebuild_20260711_163748.csv` | 37 | 37 | 0 |
| EDGEIQ | EDGEIQ_SOURCE | `public/data/edgeiq_live_sectional_intelligence_v1.csv` | 44 | 0 | 44 |
| EDGEIQ | EDGEIQ_SOURCE | `public/data/edgeiq_live_terminal_feed_v1.csv` | 131 | 131 | 0 |
| EDGEIQ | EDGEIQ_SOURCE | `public/data/edgeiq_pace_advantage_ui_feed_v1.csv` | 32 | 0 | 32 |
| EDGEIQ | EDGEIQ_SOURCE | `public/data/edgeiq_race_entry_fact_v1_rejected_v1.csv` | 67 | 0 | 67 |
| EDGEIQ | EDGEIQ_SOURCE | `public/data/edgeiq_vic_live_terminal_feed_v1.csv` | 70 | 70 | 0 |
| EDGEIQ | EDGEIQ_SOURCE | `public/data/upcoming_runner_ra_links.csv` | 473 | 473 | 0 |
| RACINGCOM | CONSOLIDATED_GRAPHQL_WAREHOUSE | `public/data/edgeiq_historical_results_warehouse_v2_graphql.csv` | 879784 | 879695 | 89 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2001_results_v1.csv` | 3083 | 3083 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2002_results_v1.csv` | 2735 | 2735 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2003_results_v1.csv` | 3312 | 3312 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2004_results_v1.csv` | 2846 | 2846 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2005_results_v1.csv` | 3392 | 3392 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2006_results_v1.csv` | 4097 | 4097 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2007_results_v1.csv` | 3976 | 3976 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2008_results_v1.csv` | 3750 | 3750 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2009_results_v1.csv` | 2039 | 2039 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2010_results_v1.csv` | 3244 | 3244 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2012_results_v1.csv` | 3496 | 3496 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2013_results_v1.csv` | 3177 | 3177 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2014_results_v1.csv` | 2834 | 2834 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2015_results_v1.csv` | 2117 | 2117 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2018_results_v1.csv` | 3185 | 3185 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2019_results_v1.csv` | 3117 | 3117 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2020_results_v1.csv` | 3259 | 3259 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2021_results_v1.csv` | 3458 | 3458 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2022_results_v1.csv` | 2620 | 2620 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2023_results_v1.csv` | 4498 | 4498 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2024_results_v1.csv` | 4405 | 4405 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2025_results_v1.csv` | 3543 | 3543 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_april_2026_results_v1.csv` | 4688 | 4688 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2000_results_v1.csv` | 2816 | 2816 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2001_results_v1.csv` | 1512 | 1512 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2002_results_v1.csv` | 3241 | 3241 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2003_results_v1.csv` | 3159 | 3159 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2004_results_v1.csv` | 3345 | 3345 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2005_results_v1.csv` | 3760 | 3760 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2006_results_v1.csv` | 3452 | 3452 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2007_results_v1.csv` | 2755 | 2755 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2008_results_v1.csv` | 3932 | 3932 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2009_results_v1.csv` | 2895 | 2895 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2010_results_v1.csv` | 3461 | 3461 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2012_results_v1.csv` | 2663 | 2663 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2013_results_v1.csv` | 3187 | 3187 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2014_results_v1.csv` | 3449 | 3449 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2015_results_v1.csv` | 2436 | 2436 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2018_results_v1.csv` | 2701 | 2701 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2019_results_v1.csv` | 2534 | 2534 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2020_results_v1.csv` | 3401 | 3401 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2021_results_v1.csv` | 3028 | 3028 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2023_results_v1.csv` | 3960 | 3960 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2024_results_v1.csv` | 4933 | 4933 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_august_2025_results_v1.csv` | 4620 | 4620 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2000_results_v1.csv` | 2992 | 2992 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2001_results_v1.csv` | 2832 | 2832 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2002_results_v1.csv` | 3011 | 3011 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2003_results_v1.csv` | 1912 | 1912 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2004_results_v1.csv` | 3223 | 3223 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2005_results_v1.csv` | 3376 | 3376 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2006_results_v1.csv` | 3353 | 3353 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2007_results_v1.csv` | 3571 | 3571 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2008_results_v1.csv` | 1605 | 1605 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2009_results_v1.csv` | 3607 | 3607 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2012_results_v1.csv` | 2054 | 2054 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2013_results_v1.csv` | 3409 | 3409 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2014_results_v1.csv` | 2424 | 2424 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2015_results_v1.csv` | 2419 | 2419 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2018_results_v1.csv` | 3056 | 3056 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2019_results_v1.csv` | 2953 | 2953 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2020_results_v1.csv` | 2813 | 2813 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2021_results_v1.csv` | 2178 | 2178 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2023_results_v1.csv` | 4249 | 4249 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2024_results_v1.csv` | 5083 | 5083 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_december_2025_results_v1.csv` | 4832 | 4832 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2001_results_v1.csv` | 2907 | 2907 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2002_results_v1.csv` | 2507 | 2507 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2003_results_v1.csv` | 3092 | 3092 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2004_results_v1.csv` | 2585 | 2585 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2005_results_v1.csv` | 3465 | 3465 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2006_results_v1.csv` | 3236 | 3236 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2007_results_v1.csv` | 2619 | 2619 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2008_results_v1.csv` | 3526 | 3526 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2009_results_v1.csv` | 2214 | 2214 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2010_results_v1.csv` | 3304 | 3304 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2012_results_v1.csv` | 3200 | 3200 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2013_results_v1.csv` | 2632 | 2632 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2014_results_v1.csv` | 2428 | 2428 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2015_results_v1.csv` | 1908 | 1908 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2016_results_v1.csv` | 2145 | 2145 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2018_results_v1.csv` | 2824 | 2824 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2019_results_v1.csv` | 1279 | 1279 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2020_results_v1.csv` | 2165 | 2165 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2021_results_v1.csv` | 2441 | 2441 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2022_results_v1.csv` | 1927 | 1927 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2023_results_v1.csv` | 4332 | 4332 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2024_results_v1.csv` | 4143 | 4143 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2025_results_v1.csv` | 2822 | 2822 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_february_2026_results_v1.csv` | 4293 | 4293 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2001_results_v1.csv` | 3018 | 3018 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2002_results_v1.csv` | 2975 | 2975 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2003_results_v1.csv` | 3316 | 3316 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2004_results_v1.csv` | 2412 | 2412 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2005_results_v1.csv` | 3603 | 3603 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2006_results_v1.csv` | 3391 | 3391 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2007_results_v1.csv` | 3596 | 3596 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2008_results_v1.csv` | 3758 | 3758 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2009_results_v1.csv` | 2155 | 2155 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2010_results_v1.csv` | 3522 | 3522 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2012_results_v1.csv` | 3314 | 3314 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2013_results_v1.csv` | 2984 | 2984 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2014_results_v1.csv` | 2991 | 2991 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2015_results_v1.csv` | 2568 | 2568 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2016_results_v1.csv` | 2697 | 2697 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2018_results_v1.csv` | 2883 | 2883 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2019_results_v1.csv` | 1663 | 1663 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2020_results_v1.csv` | 2678 | 2678 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2021_results_v1.csv` | 2957 | 2957 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2022_results_v1.csv` | 1658 | 1658 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2023_results_v1.csv` | 4322 | 4322 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2024_results_v1.csv` | 4465 | 4465 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_january_2026_results_v1.csv` | 4655 | 4655 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2001_results_v1.csv` | 2136 | 2136 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2002_results_v1.csv` | 3169 | 3169 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2003_results_v1.csv` | 3187 | 3187 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2004_results_v1.csv` | 3391 | 3391 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2005_results_v1.csv` | 3749 | 3749 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2006_results_v1.csv` | 3219 | 3219 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2007_results_v1.csv` | 3399 | 3399 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2008_results_v1.csv` | 3685 | 3685 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2009_results_v1.csv` | 2564 | 2564 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2010_results_v1.csv` | 3741 | 3741 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2012_results_v1.csv` | 3545 | 3545 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2013_results_v1.csv` | 3692 | 3692 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2014_results_v1.csv` | 3171 | 3171 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2015_results_v1.csv` | 2323 | 2323 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2018_results_v1.csv` | 3216 | 3216 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2019_results_v1.csv` | 3007 | 3007 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2020_results_v1.csv` | 2983 | 2983 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2021_results_v1.csv` | 3044 | 3044 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2023_results_v1.csv` | 4777 | 4777 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2024_results_v1.csv` | 4910 | 4910 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_july_2025_results_v1.csv` | 4872 | 4872 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2001_results_v1.csv` | 3316 | 3316 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2002_results_v1.csv` | 3330 | 3330 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2003_results_v1.csv` | 3348 | 3348 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2004_results_v1.csv` | 2696 | 2696 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2005_results_v1.csv` | 3780 | 3780 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2006_results_v1.csv` | 3752 | 3752 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2007_results_v1.csv` | 4169 | 4169 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2008_results_v1.csv` | 4265 | 4265 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2009_results_v1.csv` | 1363 | 1363 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2010_results_v1.csv` | 3699 | 3699 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2012_results_v1.csv` | 3604 | 3604 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2013_results_v1.csv` | 3872 | 3872 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2014_results_v1.csv` | 3272 | 3272 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2015_results_v1.csv` | 2559 | 2559 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2018_results_v1.csv` | 3642 | 3642 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2019_results_v1.csv` | 3553 | 3553 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2020_results_v1.csv` | 3343 | 3343 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2021_results_v1.csv` | 3757 | 3757 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2023_results_v1.csv` | 4571 | 4571 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2024_results_v1.csv` | 5336 | 5336 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2025_results_v1.csv` | 5272 | 5272 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_june_2026_results_v1.csv` | 4223 | 4223 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2001_results_v1.csv` | 2902 | 2902 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2002_results_v1.csv` | 3066 | 3066 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2003_results_v1.csv` | 3021 | 3021 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2004_results_v1.csv` | 2192 | 2192 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2005_results_v1.csv` | 3399 | 3399 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2006_results_v1.csv` | 3195 | 3195 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2007_results_v1.csv` | 3469 | 3469 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2008_results_v1.csv` | 3853 | 3853 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2009_results_v1.csv` | 2897 | 2897 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2010_results_v1.csv` | 2930 | 2930 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2012_results_v1.csv` | 3432 | 3432 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2013_results_v1.csv` | 3331 | 3331 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2014_results_v1.csv` | 2787 | 2787 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2015_results_v1.csv` | 924 | 924 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2018_results_v1.csv` | 2821 | 2821 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2019_results_v1.csv` | 2817 | 2817 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2020_results_v1.csv` | 3088 | 3088 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2021_results_v1.csv` | 2526 | 2526 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2022_results_v1.csv` | 846 | 846 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2023_results_v1.csv` | 4731 | 4731 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2024_results_v1.csv` | 4743 | 4743 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2025_results_v1.csv` | 3436 | 3436 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_march_2026_results_v1.csv` | 4768 | 4768 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2001_results_v1.csv` | 3445 | 3445 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2002_results_v1.csv` | 3225 | 3225 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2003_results_v1.csv` | 4192 | 4192 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2004_results_v1.csv` | 2095 | 2095 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2005_results_v1.csv` | 3851 | 3851 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2006_results_v1.csv` | 3912 | 3912 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2007_results_v1.csv` | 4329 | 4329 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2008_results_v1.csv` | 4144 | 4144 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2009_results_v1.csv` | 3132 | 3132 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2010_results_v1.csv` | 3736 | 3736 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2012_results_v1.csv` | 3869 | 3869 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2013_results_v1.csv` | 3402 | 3402 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2014_results_v1.csv` | 3178 | 3178 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2015_results_v1.csv` | 2740 | 2740 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2018_results_v1.csv` | 3270 | 3270 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2019_results_v1.csv` | 3884 | 3884 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2020_results_v1.csv` | 4245 | 4245 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2021_results_v1.csv` | 4038 | 4038 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_may_2022_results_v1.csv` | 2068 | 2068 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2001_results_v1.csv` | 3283 | 3283 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2002_results_v1.csv` | 3967 | 3967 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2003_results_v1.csv` | 1979 | 1979 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2004_results_v1.csv` | 4018 | 4018 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2005_results_v1.csv` | 3811 | 3811 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2006_results_v1.csv` | 1925 | 1925 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2007_results_v1.csv` | 3910 | 3910 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2008_results_v1.csv` | 3099 | 3099 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2009_results_v1.csv` | 3499 | 3499 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2012_results_v1.csv` | 2894 | 2894 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2013_results_v1.csv` | 4048 | 4048 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2014_results_v1.csv` | 3609 | 3609 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2015_results_v1.csv` | 1950 | 1950 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2018_results_v1.csv` | 3679 | 3679 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2019_results_v1.csv` | 3416 | 3416 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2020_results_v1.csv` | 3602 | 3602 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2021_results_v1.csv` | 2628 | 2628 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2023_results_v1.csv` | 4634 | 4634 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_november_2024_results_v1.csv` | 5424 | 5424 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_october_2001_results_v1.csv` | 2969 | 2969 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_october_2002_results_v1.csv` | 3339 | 3339 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_october_2003_results_v1.csv` | 3101 | 3101 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_october_2004_results_v1.csv` | 3723 | 3723 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_october_2005_results_v1.csv` | 3832 | 3832 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_october_2006_results_v1.csv` | 2462 | 2462 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_october_2007_results_v1.csv` | 3710 | 3710 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_october_2008_results_v1.csv` | 2863 | 2863 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_october_2009_results_v1.csv` | 669 | 669 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_october_2012_results_v1.csv` | 3765 | 3765 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_october_2013_results_v1.csv` | 3963 | 3963 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_october_2014_results_v1.csv` | 3484 | 3484 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_october_2015_results_v1.csv` | 1534 | 1534 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_october_2018_results_v1.csv` | 3708 | 3708 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_october_2019_results_v1.csv` | 3039 | 3039 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_october_2020_results_v1.csv` | 3947 | 3947 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_october_2021_results_v1.csv` | 1952 | 1952 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2001_results_v1.csv` | 2971 | 2971 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2002_results_v1.csv` | 3500 | 3500 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2003_results_v1.csv` | 3376 | 3376 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2004_results_v1.csv` | 174 | 174 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2005_results_v1.csv` | 3358 | 3358 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2006_results_v1.csv` | 3576 | 3576 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2007_results_v1.csv` | 4718 | 4718 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2008_results_v1.csv` | 3656 | 3656 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2009_results_v1.csv` | 3036 | 3036 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2010_results_v1.csv` | 84 | 84 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2012_results_v1.csv` | 3562 | 3562 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2013_results_v1.csv` | 3581 | 3581 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2014_results_v1.csv` | 2962 | 2962 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2015_results_v1.csv` | 2846 | 2846 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2018_results_v1.csv` | 3456 | 3456 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2019_results_v1.csv` | 3223 | 3223 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2020_results_v1.csv` | 3167 | 3167 | 0 |
| RACINGCOM | MONTHLY_GRAPHQL_RESULT_FILE | `public/data/edgeiq_graphql_september_2021_results_v1.csv` | 2486 | 2486 | 0 |
| RACINGCOM | OTHER_GRAPHQL_RESULT_SOURCE | `public/data/edgeiq_graphql_results_warehouse_week1_2025_v1.csv` | 813 | 813 | 0 |
| RACINGCOM | OTHER_SOURCE | `outputs/sectionals/checkpoints/racingcom_speed_5_race_baseline_20260722_051140/edgeiq_racingcom_canonical_runner_speed_fact_v2.csv` | 39 | 39 | 0 |
| RACINGCOM | OTHER_SOURCE | `public/data/edgeiq_graphql_january_2025_master_v1.csv` | 2617 | 2617 | 0 |
| RACINGCOM | OTHER_SOURCE | `public/data/edgeiq_graphql_master_v2.csv` | 62931 | 62842 | 89 |
| RACINGCOM | OTHER_SOURCE | `public/data/edgeiq_racingcom_canonical_runner_speed_fact_v2_1.csv` | 353 | 353 | 0 |
| RACINGCOM | OTHER_SOURCE | `public/data/edgeiq_racingcom_graphql_speed_normalised_v1.csv` | 58 | 58 | 0 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_layout_b_derived_metrics_v1.csv` | 189 | 0 | 189 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_0000_normalised.csv` | 34 | 0 | 34 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_0040_normalised.csv` | 13 | 0 | 13 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_0250_normalised.csv` | 29 | 0 | 29 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_0500_normalised.csv` | 31 | 0 | 31 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_0750_normalised.csv` | 27 | 0 | 27 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_1000_normalised.csv` | 35 | 0 | 35 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_10250_normalised.csv` | 667 | 0 | 667 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_11250_normalised.csv` | 865 | 0 | 865 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_12250_normalised.csv` | 775 | 0 | 775 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_1250_normalised.csv` | 70 | 0 | 70 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_13250_normalised.csv` | 662 | 0 | 662 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_14250_normalised.csv` | 655 | 0 | 655 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_15250_normalised.csv` | 941 | 0 | 941 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_16250_normalised.csv` | 1077 | 0 | 1077 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_17250_normalised.csv` | 817 | 0 | 817 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_1750_normalised.csv` | 81 | 0 | 81 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_2250_normalised.csv` | 108 | 0 | 108 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_2750_normalised.csv` | 128 | 0 | 128 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_3250_normalised.csv` | 127 | 0 | 127 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_3750_normalised.csv` | 141 | 0 | 141 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_4250_normalised.csv` | 104 | 0 | 104 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_4750_normalised.csv` | 139 | 0 | 139 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_5250_normalised.csv` | 378 | 0 | 378 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_6250_normalised.csv` | 405 | 0 | 405 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_7250_normalised.csv` | 467 | 0 | 467 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_8250_normalised.csv` | 480 | 0 | 480 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_rendered_speed_data_batches/batch_9250_normalised.csv` | 483 | 0 | 483 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_sectional_history_master_v1.csv` | 7 | 0 | 7 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_sectional_warehouse_v1.csv` | 1 | 0 | 1 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_sectional_warehouse_v2.csv` | 942 | 0 | 942 |
| RACINGCOM | OTHER_SOURCE | `public/data/racingcom_sectionals_normalised_v1.csv` | 4 | 0 | 4 |

## Audit

- **PASS** — `required_file_availability`: all six governed target files available
- **PARTIAL** — `raw_identity_extraction`: graphql_missing=0; observation_missing=11080; performance_missing=0; performance_parse_failures=0
- **FAIL** — `observation_double_ingestion_check`: raw identities present in both monthly files and consolidated warehouse=814236
- **PASS** — `graphql_observation_raw_identity_overlap`: intersection=879695; graphql_only=0; observation_only=1885
- **PASS** — `graphql_performance_bridge`: intersection=879695; graphql_only=0; performance_only=0
- **PASS** — `snapshot_source_row_lineage`: valid_rows=879784; invalid_rows=0; sha_matches=879784; sha_mismatches=0
- **PASS** — `epi_parent_population`: epi_rows=533387; unique_ids=533387; missing_ids=0; not_in_parent=0

## Governance

- Existing production datasets were read only.
- No duplicate records were deleted.
- No builder was changed.
- No warehouse was promoted to canonical status.
- A FAIL indicates discovered evidence requiring correction, not script failure.
