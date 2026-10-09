# EDGEiQ — LAB245B warehouse runner LVS identity-lineage inspection (2026-10-09)

**Verdict: IMPORTED_UNPROVEN / STOP.**

Approved sole script: `scripts/research/build_lab245b_warehouse_runner_lvs.py`, branch `research/profitability-program-20261004`, blob `8794c2892e38921027792560d1747749c039e1aa`.

The script's `WAREHOUSE` points to `docs/performance-intelligence/warehouse/edgeiq_performance_fact_warehouse_v1.csv`, NOT `edgeiq_historical_results_warehouse_v2_graphql.csv`. Its `use` list includes `canonical_race_id` and `canonical_horse_id`; `pd.read_csv(WAREHOUSE,usecols=use,low_memory=False)` imports both. The script does not construct canonical IDs or compare them to historical results `race_id` and `runner_id`. `rc_identity` groups by `canonical_race_id` to test race-attribute consistency, which is not cross-warehouse identity equivalence or a one-to-one, zero-collision crosswalk.

Required `canonical_race_id == race_id`: UNPROVEN.
Required `canonical_horse_id == runner_id`: UNPROVEN.
Required one-to-one mapping and zero collisions: UNPROVEN.

Only authorised script source read. No other scripts, data files, CSVs, warehouse, crosswalk, coverage, fit, score or sealed years accessed. Historical 50,209 provisional flat races remain uncertified for modelling. Evaluation-year exposure remains UNPROVEN. Stage011 unchanged.

Any next lineage inspection requires a separate explicit Grok approval.