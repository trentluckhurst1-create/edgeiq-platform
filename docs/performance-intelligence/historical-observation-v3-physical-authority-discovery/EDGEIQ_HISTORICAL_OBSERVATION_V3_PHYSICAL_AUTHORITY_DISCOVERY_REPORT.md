# EDGEIQ Historical Observation V3 Physical Authority Discovery

**Status:** `EDGEIQ_HISTORICAL_OBSERVATION_V3_PHYSICAL_AUTHORITY_DISCOVERY_PHASE1A_6B_0_V1_FAIL`

**Decision:** `AMBIGUOUS_PHYSICAL_AUTHORITY`

**Selected physical authority:** None

## Decision rationale

Multiple physical datasets satisfy the row and identity requirements. Source lineage must distinguish the upstream consolidated GraphQL authority from downstream derived warehouses.

## Governed contract

- Physical rows: **879,784**
- Unique raw identities: **879,695**
- Duplicate excess: **89**

## Safety

- No warehouse was written.
- Existing V2 was not modified.
- The rejected untracked V3 implementation was not modified.
- Repository discovery was limited to Git-indexed and visible untracked paths.

## Inspected physical candidates

| Physical dataset | Rows | Fields | Direct refs | Producer refs | Identity |
|---|---:|---:|---:|---:|---:|
| `public/data/edgeiq_racingcom_performance_warehouse_v2.csv` | 138 | 35 | 0 | 19 | True |
| `docs/performance-intelligence/warehouse/performance-facts-corrected/eiq_performance_facts_v0_2_a0c3715ab506d19f9301d8a4/canonical_performance_facts_v0_2.csv` | 879,784 | 52 | 0 | 11 | True |
| `public/data/edgeiq_historical_run_observation_fact_v2.csv` | 1,772,640 | 37 | 0 | 8 | False |
| `public/data/edgeiq_vic_three_day_meeting_universe.csv` | 108 | 63 | 0 | 10 | True |
| `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_graphql_acquisition_v1.csv` | 5 | 16 | 0 | 8 | False |
| `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_graphql_parser_output_v2.csv` | 898 | 33 | 0 | 7 | True |
| `docs/performance-intelligence/warehouse/performance-facts/eiq_performance_facts_snapshot_23704301541550b883a8a05d3419c3a1/canonical_performance_facts.csv` | 879,784 | 51 | 0 | 6 | False |
| `docs/performance-intelligence/warehouse/edgeiq_performance_fact_warehouse_v1.csv` | 879,784 | 32 | 0 | 6 | False |
| `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_graphql_race_evidence_v1.csv` | 7 | 25 | 0 | 6 | False |
| `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_graphql_source_admission_v1.csv` | 5 | 23 | 0 | 6 | False |
| `docs/performance-intelligence/warehouse-v2/historical-observation-failure-classification-v1/edgeiq_failure_reason_detail_v1.csv` | 1,305,045 | 17 | 0 | 4 | False |
| `docs/performance-intelligence/racingcom-source-discovery/edgeiq_racingcom_network_request_ledger_v1.csv` | 1,910 | 13 | 0 | 7 | False |
| `docs/performance-intelligence/epi/edgeiq_epi_performance_fact_v1.csv` | 533,387 | 26 | 0 | 6 | False |
| `docs/performance-intelligence/warehouse/raw/eiq_warehouse_snapshot_b24578e0eb795ab6bd076452bfff3f5e/canonical_performance_evidence.csv` | 879,784 | 21 | 0 | 5 | True |
| `public/data/edgeiq_canonical_horse_alias_v2.csv` | 942,307 | 11 | 0 | 6 | False |
| `public/data/edgeiq_performance_intelligence_base_fact_v1.csv` | 168 | 26 | 0 | 6 | False |
| `docs/performance-intelligence/warehouse/performance-facts-corrected/eiq_performance_facts_v0_2_a0c3715ab506d19f9301d8a4/performance_fact_quality_states_v0_2.csv` | 879,784 | 11 | 0 | 4 | False |
| `docs/performance-intelligence/warehouse/raw/eiq_warehouse_snapshot_b24578e0eb795ab6bd076452bfff3f5e/asset_catalog.csv` | 2 | 10 | 0 | 5 | False |
| `docs/performance-intelligence/warehouse/raw/eiq_warehouse_snapshot_b24578e0eb795ab6bd076452bfff3f5e/materialisation_checks.csv` | 8 | 3 | 0 | 5 | False |
| `public/data/edgeiq_canonical_horse_master_v2.csv` | 893,408 | 18 | 0 | 5 | False |
| `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_graphql_response_validation_v1.csv` | 5 | 18 | 0 | 4 | False |
| `docs/performance-intelligence/warehouse-v2/historical-run-observation/edgeiq_historical_run_observation_v2_identity_failures.csv` | 1,305,045 | 8 | 0 | 2 | False |
| `docs/performance-intelligence/racingcom-source-discovery/edgeiq_racingcom_network_response_ledger_v1.csv` | 1,935 | 18 | 0 | 5 | False |
| `public/data/edgeiq_vic_three_day_race_list_v1.csv` | Not proven | 0 | 0 | 5 | False |
| `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_race_discovery_contract_v2.csv` | 59 | 32 | 0 | 5 | False |
| `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_graphql_request_contract_v1.csv` | 5 | 26 | 0 | 3 | False |
| `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_graphql_migration_dry_run_v1.csv` | 13 | 4 | 0 | 3 | False |
| `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_graphql_rollback_dry_run_v1.csv` | 3 | 4 | 0 | 3 | False |
| `docs/performance-intelligence/warehouse-v2/historical-observation-warehouse-v3/edgeiq_historical_observation_v3_unresolved_identity.csv` | 2,281,674 | 18 | 0 | 1 | True |
| `docs/performance-intelligence/warehouse-v2/historical-observation-warehouse-v3/edgeiq_historical_observation_v3_identity_ledger.csv` | 2,431,489 | 17 | 0 | 1 | True |

## Result

Phase 1A.6B warehouse construction is **not yet authorised**.

## Deliverables

- `docs/performance-intelligence/historical-observation-v3-physical-authority-discovery/EDGEIQ_HISTORICAL_OBSERVATION_V3_PHYSICAL_AUTHORITY_DISCOVERY_REPORT.json`
- `docs/performance-intelligence/historical-observation-v3-physical-authority-discovery/EDGEIQ_HISTORICAL_OBSERVATION_V3_PHYSICAL_AUTHORITY_DISCOVERY_REPORT.md`
- `docs/performance-intelligence/historical-observation-v3-physical-authority-discovery/EDGEIQ_HISTORICAL_OBSERVATION_V3_PHYSICAL_AUTHORITY_CANDIDATES.csv`
- `docs/performance-intelligence/historical-observation-v3-physical-authority-discovery/EDGEIQ_HISTORICAL_OBSERVATION_V3_PHYSICAL_AUTHORITY_REFERENCE_MATRIX.csv`
- `docs/performance-intelligence/historical-observation-v3-physical-authority-discovery/EDGEIQ_HISTORICAL_OBSERVATION_V3_PHYSICAL_AUTHORITY_PRODUCER_MATRIX.csv`
- `docs/performance-intelligence/historical-observation-v3-physical-authority-discovery/edgeiq_historical_observation_v3_physical_authority_contract.json`
