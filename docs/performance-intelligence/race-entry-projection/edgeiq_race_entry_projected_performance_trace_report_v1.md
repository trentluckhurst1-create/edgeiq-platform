# Race Entry Projected Performance Builder Trace V1

Active builder: `scripts\build_edgeiq_race_entry_projected_performance_fact_v1.py`

Entry function: `main`

Output: `public/data/edgeiq_race_entry_projected_performance_fact_v1.csv`

Output rows: `0`

Input paths discovered:

- `ADJUSTED_PATH` -> `public/data/edgeiq_race_entry_context_adjusted_performance_fact_v1.csv` exists=YES rows=0
- `AGGREGATE_PATH` -> `public/data/edgeiq_race_entry_suitability_aggregate_fact_v1.csv` exists=YES rows=0
- `OUTPUT_PATH` -> `public/data/edgeiq_race_entry_projected_performance_fact_v1.csv` exists=YES rows=0
- `schema_contract` -> `contracts\performance-intelligence\edgeiq_race_entry_projected_performance_fact_v1_contract.json` exists=YES rows=
- `audit_script` -> `scripts\audit_edgeiq_race_entry_projected_performance_fact_v1.py` exists=YES rows=

Required decisions/statuses:

- `EXPECTED_ADJUSTED_DECISION` = `PERFORMANCE_ADJUSTED`
- `EXPECTED_ADJUSTED_STATUS` = `GOVERNED_CONTEXT_ADJUSTED_PERFORMANCE`
- `EXPECTED_AGGREGATE_DECISION` = `SUITABILITY_AGGREGATED`
- `EXPECTED_AGGREGATE_STATUS` = `GOVERNED_SUITABILITY_AGGREGATE`
- `PUBLICATION_DECISION` = `PROJECTED_PERFORMANCE_PUBLISHED`
- `RECONCILIATION_DECISION` = `PROJECTED_PERFORMANCE_RECONCILED`
- `PROJECTED_STATUS` = `GOVERNED_PROJECTED_PERFORMANCE`

Active consumers:

- `scripts\apply_edgeiq_australian_synthetic_performance_v2.py`
- `scripts\audit_edgeiq_epi_performance_dependency_v1.py`
- `scripts\audit_edgeiq_performance_intelligence_final_live_v2.py`
- `scripts\audit_edgeiq_race_entry_eri_context_fact_v1.py`
- `scripts\audit_edgeiq_race_entry_projected_performance_builder_trace_v1.py`
- `scripts\audit_edgeiq_race_entry_projected_performance_fact_v1.py`
- `scripts\audit_edgeiq_race_eri_fact_v1.py`
- `scripts\build_edgeiq_race_entry_epi_component_fact_v1.py`
- `scripts\build_edgeiq_race_entry_eri_context_fact_v1.py`
- `scripts\build_edgeiq_race_eri_fact_v1.py`

Trace conclusion: projected-performance output is one row per suitability aggregate. Current aggregate rows are zero, so the projected builder is not the first row-loss stage.
