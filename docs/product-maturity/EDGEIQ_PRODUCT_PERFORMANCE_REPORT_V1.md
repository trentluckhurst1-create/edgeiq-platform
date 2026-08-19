# EDGEiQ Product Performance Report V1

Generated: 2026-07-16T17:55:58+00:00

## Bundle Assets

- dist/assets/index-Dt_ODncx.js: 2253358 bytes
- dist/assets/index-bCgbq43x.css: 754058 bytes

## Largest Public Feeds

- public/data/edgeiq_historical_results_warehouse_v2_graphql.csv: 504293405 bytes
- public/data/edgeiq_historical_results_warehouse_v2_graphql_CHECKPOINT_20260623_164849.csv: 504293405 bytes
- public/data/edgeiq_results_master_v1.csv: 481021956 bytes
- public/data/edgeiq_results_terminal_feed_v1.csv: 435242182 bytes
- public/data/edgeiq_standardised_sectionals_v1.csv: 408819581 bytes
- public/data/edgeiq_bet_quality_engine_v1_1.csv: 391793553 bytes
- public/data/edgeiq_epf_v1_1_guardrailed.csv: 323082993 bytes
- public/data/edgeiq_fair_price_v8_brc_fallback_replay_v1.csv: 319946674 bytes
- public/data/edgeiq_form_sectional_profile_feed_v1.csv: 307977606 bytes
- public/data/edgeiq_bet_quality_engine_v1.csv: 302379190 bytes
- public/data/edgeiq_context_warehouse_v2_graphql.csv: 299417169 bytes
- public/data/edgeiq_context_warehouse_v2_graphql_CHECKPOINT_20260623_165745.csv: 299417169 bytes
- public/data/edgeiq_speed_master_v1.csv: 295358552 bytes
- public/data/edgeiq_fair_price_v8_interaction_filter_replay_v1.csv: 294058324 bytes
- public/data/edgeiq_dna_registry_v2.csv: 212429693 bytes
- public/data/edgeiq_epf_v1.csv: 209936117 bytes
- public/data/edgeiq_sectional_intelligence_v1.csv: 202345938 bytes
- public/data/edgeiq_hidden_gem_engine_v1.csv: 182429006 bytes
- public/data/edgeiq_prior_asof_rating_spine_v1.csv: 181788959 bytes
- public/data/edgeiq_execution_v3_replay_v1.csv: 173056278 bytes

## Recommendations

- Code-split larger workspace bundles once route boundaries are stable.
- Consolidate CSV terminal feed parsers into a shared typed CSV loader.
- Keep warehouse-scale files out of React; continue serving compact product feeds only.
