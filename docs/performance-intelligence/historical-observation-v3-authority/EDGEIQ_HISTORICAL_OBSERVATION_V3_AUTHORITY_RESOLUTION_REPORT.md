# EDGEIQ Historical Observation V3 Authority Resolution

**Status:** `EDGEIQ_HISTORICAL_OBSERVATION_V3_AUTHORITY_RESOLUTION_PHASE1A_6B_V1_FAIL`

**Decision:** `NO_AUTHORITY_PROVEN`

**Selected authority:** None

## Decision rationale

No candidate simultaneously matched the physical population contract, consolidated/GraphQL authority classification, prohibited-source exclusions and minimum identity schema.

## Safety scope

- No warehouse was written.
- Existing V2 was not modified.
- The rejected untracked V3 implementation was not modified.
- Repository file discovery used Git's index rather than recursive filesystem resolution.
- Only highly ranked authority candidates were row-counted.

## Governed population contract

- Physical rows: **879,784**
- Unique raw identities: **879,695**
- Duplicate excess: **89**

## Inspected candidates

| Candidate | Rows | Score | Prohibited | Identity schema |
|---|---:|---:|---|---:|
| `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_ACCEPTANCE_CRITERIA_V1.csv` | 11 | 96 | None | False |
| `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_OUTPUT_CONTRACT_V1.csv` | 17 | 96 | None | False |
| `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_SOURCE_POLICY_V1.csv` | 7 | 96 | None | False |
| `docs/performance-intelligence/historical-observation-v3-audit/EDGEIQ_HISTORICAL_OBSERVATION_V3_GOVERNANCE_MATRIX.csv` | 12 | 96 | None | False |
| `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_fresh_graphql_population_v1.csv` | 7 | 96 | None | False |
| `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_graphql_acquisition_audit_v1.csv` | 5 | 96 | None | False |
| `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_graphql_acquisition_rejections_v1.csv` | 0 | 96 | None | False |
| `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_graphql_acquisition_v1.csv` | 5 | 96 | None | False |
| `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_graphql_api_key_governance_audit_v1.csv` | 4 | 96 | None | False |
| `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_graphql_api_key_governance_v1.csv` | 1 | 96 | None | False |
| `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_graphql_human_migration_review_audit_v1.csv` | 5 | 96 | None | False |
| `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_graphql_integration_e2e_v1.csv` | 10 | 96 | None | False |

## Repository evidence

- `docs/operations-readiness/betting/edgeiq_daily_betting_readiness_v1.csv:16` — performance_fact_rows,879784
- `docs/operations-readiness/betting/edgeiq_daily_betting_readiness_v1.json:19` — "performance_fact_rows": 879784,
- `docs/operations-readiness/betting/edgeiq_daily_betting_readiness_v1.md:19` — - performance_fact_rows: 879784
- `docs/operations-readiness/daily-refresh/edgeiq_daily_product_refresh_v1_run_log.txt:124` — warehouse {'rows': 879784, 'corrected_seconds_rows': 712856, 'invalid_time_rows': 166928, 'implausible_seconds_before_rows': 0}
- `docs/operations-readiness/operations/EDGEIQ_DAILY_OPERATIONS_RUNBOOK_V1.md:46` — Only run the governed performance-intelligence historical builders when source governance changes. Normal daily startup must not require the 879,784-row rebuild.
- `docs/performance-intelligence/canonical-identities/edgeiq_canonical_identity_resolution_audit_v1.json:6` — "raw_identity_rows": 879784,
- `docs/performance-intelligence/canonical-identities/edgeiq_canonical_identity_resolution_audit_v1.json:57` — "raw_mappings": 879784,
- `docs/performance-intelligence/canonical-identities/edgeiq_canonical_identity_resolution_audit_v1.json:58` — "canonical_identities": 879784,
- `docs/performance-intelligence/canonical-identities/edgeiq_canonical_identity_resolution_audit_v1.json:59` — "resolved_rows": 879784,
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_ACCEPTANCE_CRITERIA_V1.csv:2` — AUTHORITY_SOURCE_EXCLUSIVE,PASS,Only consolidated GraphQL creates historical observation rows.
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_ACCEPTANCE_CRITERIA_V1.csv:3` — PHYSICAL_ROW_PRESERVATION,PASS,879784
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_ACCEPTANCE_CRITERIA_V1.csv:4` — UNIQUE_RAW_IDENTITY_COUNT,PASS,879695
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_AUDIT_V1.json:5` — "detail": "actual=879784; expected=879784",
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_AUDIT_V1.json:10` — "detail": "actual=879695; expected=879695",
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_AUDIT_V1.md:7` — - **PASS** â€” `source_row_count`: actual=879784; expected=879784
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_AUDIT_V1.md:8` — - **PASS** â€” `unique_raw_key_count`: actual=879695; expected=879695
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_V1.json:5` — "expected_value": "Only consolidated GraphQL creates historical observation rows.",
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_V1.json:10` — "expected_value": "879784",
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_V1.json:15` — "expected_value": "879695",
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_V1.json:63` — "detail": "actual=879784; expected=879784",
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_V1.json:68` — "detail": "actual=879695; expected=879695",
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_V1.json:108` — "rows": 879784,
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_V1.json:110` — "unique_raw_keys": 879695
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_V1.json:190` — "source_or_method": "Physical row number in consolidated GraphQL warehouse."
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_V1.json:233` — "governed_reason": "Population is already represented in the consolidated GraphQL warehouse.",
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_V1.md:11` — - Physical rows: 879784
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_V1.md:12` — - Unique `race_id + runner_id` keys: 879695
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_V1.md:41` — - `AUTHORITY_SOURCE_EXCLUSIVE`: Only consolidated GraphQL creates historical observation rows.
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_V1.md:42` — - `PHYSICAL_ROW_PRESERVATION`: 879784
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION_V1.md:43` — - `UNIQUE_RAW_IDENTITY_COUNT`: 879695
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_OUTPUT_CONTRACT_V1.csv:15` — source_row_number,REQUIRED,Physical row number in consolidated GraphQL warehouse.
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_SOURCE_POLICY_V1.csv:3` — MONTHLY_GRAPHQL_RESULT_FILES,EXCLUDE_DUPLICATE_SOURCE,False,False,,edgeiq_graphql_<month>_<year>_results_v1.csv,Population is already represented in the consolidated GraphQL warehouse.
- `docs/performance-intelligence/historical-observation-v3-audit/EDGEIQ_HISTORICAL_OBSERVATION_V3_BUILDER_PHASE1A_6A_REPORT.json:105` — "physical_rows": 879784,
- `docs/performance-intelligence/historical-observation-v3-audit/EDGEIQ_HISTORICAL_OBSERVATION_V3_BUILDER_PHASE1A_6A_REPORT.json:106` — "unique_raw_identities": 879695
- `docs/performance-intelligence/historical-observation-v3-audit/EDGEIQ_HISTORICAL_OBSERVATION_V3_BUILDER_PHASE1A_6A_REPORT.json:120` — "requirement": "Source admission must use the approved consolidated GraphQL authority only.",
- `docs/performance-intelligence/historical-observation-v3-audit/EDGEIQ_HISTORICAL_OBSERVATION_V3_BUILDER_PHASE1A_6A_REPORT.json:162` — "requirement": "Physical population must equal 879,784 rows.",
- `docs/performance-intelligence/historical-observation-v3-audit/EDGEIQ_HISTORICAL_OBSERVATION_V3_BUILDER_PHASE1A_6A_REPORT.json:169` — "requirement": "Unique raw observation identities must equal 879,695.",
- `docs/performance-intelligence/historical-observation-v3-audit/EDGEIQ_HISTORICAL_OBSERVATION_V3_BUILDER_PHASE1A_6A_REPORT.json:176` — "requirement": "The governed duplicate excess must remain 89.",
- `docs/performance-intelligence/historical-observation-v3-audit/EDGEIQ_HISTORICAL_OBSERVATION_V3_BUILDER_PHASE1A_6A_REPORT.json:199` — "recommendation_reason": "The existing builder's source-admission architecture is broad and does not enforce the locked consolidated GraphQL authority. Because source authority defines the warehouse population, this is a foundational divergence rather than a cosmetic defect.",
- `docs/performance-intelligence/historical-observation-v3-audit/EDGEIQ_HISTORICAL_OBSERVATION_V3_BUILDER_PHASE1A_6A_REPORT.md:20` — The existing builder's source-admission architecture is broad and does not enforce the locked consolidated GraphQL authority. Because source authority defines the warehouse population, this is a foundational divergence rather than a cosmetic defect.

## Deliverables

- `docs/performance-intelligence/historical-observation-v3-authority/EDGEIQ_HISTORICAL_OBSERVATION_V3_AUTHORITY_RESOLUTION_REPORT.json`
- `docs/performance-intelligence/historical-observation-v3-authority/EDGEIQ_HISTORICAL_OBSERVATION_V3_AUTHORITY_RESOLUTION_REPORT.md`
- `docs/performance-intelligence/historical-observation-v3-authority/EDGEIQ_HISTORICAL_OBSERVATION_V3_AUTHORITY_CANDIDATES.csv`
- `docs/performance-intelligence/historical-observation-v3-authority/edgeiq_historical_observation_v3_authority_contract.json`
