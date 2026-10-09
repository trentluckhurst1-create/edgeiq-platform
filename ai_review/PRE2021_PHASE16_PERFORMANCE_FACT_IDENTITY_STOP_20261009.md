# EDGEiQ — Phase 1.6 performance-fact producer identity inspection (2026-10-09)

**Verdict: IMPORTED_UNPROVEN / STOP.**

Approved sole script: `scripts/performance-intelligence/phase1_6/build_edgeiq_performance_fact_warehouse_phase1_6.py` on `research/profitability-program-20261004`, blob `937a72ee442519e27f7c5a4bf2026811aea1cace`.

The script's `SOURCE` is `public/data/edgeiq_historical_results_warehouse_v2_graphql.csv`. Its output directly copies `race_id: row.get('race_id')` and `runner_id: row.get('runner_id')`, and computes a separate `performance_fact_id` hash of the two. It does NOT create or assign `canonical_race_id` or `canonical_horse_id`. Its timestamped Phase 1.6 output is not shown to be the `docs/performance-intelligence/warehouse/edgeiq_performance_fact_warehouse_v1.csv` read by LAB245B. Therefore neither canonical equivalence nor one-to-one zero-collision mapping is demonstrated.

No other script, CSV, manifest, warehouse or source contents opened. No crosswalk, coverage, fitting, scoring, or 2025–2026 access. The 50,209 pre-2021 provisional flat races remain uncertified; evaluation-year exposure UNPROVEN. Coverage execution STOP. No further inspection without new Grok approval.