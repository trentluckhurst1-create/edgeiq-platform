# EDGEIQ Historical Observation V3 Authority Lineage Audit

**Status:** `EDGEIQ_HISTORICAL_OBSERVATION_V3_AUTHORITY_LINEAGE_PHASE1A_6B_1_V1_FAIL`

**Decision:** `LINEAGE_NOT_YET_PROVEN`

**Selected physical authority:** None

## Decision rationale

The two population-matching datasets could not be distinguished with sufficient physical lineage evidence. No authority has been locked.

## Candidate classification

- Raw evidence candidate: `docs/performance-intelligence/warehouse/raw/eiq_warehouse_snapshot_b24578e0eb795ab6bd076452bfff3f5e/canonical_performance_evidence.csv`
- Corrected fact candidate: `docs/performance-intelligence/warehouse/performance-facts-corrected/eiq_performance_facts_v0_2_a0c3715ab506d19f9301d8a4/canonical_performance_facts_v0_2.csv`

## Population

- Raw evidence rows: **879,784**
- Corrected fact rows: **879,784**
- Governed expected rows: **879,784**

## Governance checks

| Check | Result | Detail |
|---|---:|---|
| `RAW_PATH_CLASSIFICATION` | **PASS** | docs/performance-intelligence/warehouse/raw/eiq_warehouse_snapshot_b24578e0eb795ab6bd076452bfff3f5e/canonical_performance_evidence.csv |
| `CORRECTED_PATH_CLASSIFICATION` | **PASS** | docs/performance-intelligence/warehouse/performance-facts-corrected/eiq_performance_facts_v0_2_a0c3715ab506d19f9301d8a4/canonical_performance_facts_v0_2.csv |
| `RAW_POPULATION_MATCH` | **PASS** | actual=879784; expected=879784 |
| `CORRECTED_POPULATION_MATCH` | **PASS** | actual=879784; expected=879784 |
| `RAW_IDENTITY_PRESENT` | **FAIL** | race_id |
| `RAW_LINEAGE_PRESENT` | **PASS** | source_row_number |
| `CORRECTED_DERIVATION_PRESENT` | **PASS** | benchmark_eligible, performance_fact_id, quality_state |
| `RAW_ASSET_CATALOG_REFERENCE` | **PASS** | docs/performance-intelligence/warehouse/raw/eiq_warehouse_snapshot_b24578e0eb795ab6bd076452bfff3f5e/asset_catalog.csv |
| `RAW_MATERIALISATION_REFERENCE` | **PASS** | docs/performance-intelligence/warehouse/raw/eiq_warehouse_snapshot_b24578e0eb795ab6bd076452bfff3f5e/materialisation_checks.csv |
| `PIPELINE_LINEAGE_SCRIPT` | **PASS** | scripts/audit_edgeiq_historical_observation_v3_authority_lineage_phase1a_6b_1_v1.py |
| `FILES_ARE_NOT_BYTE_IDENTICAL` | **PASS** | raw_sha256=5754e424b57031b3a6e50b4ecd8675af21b10a7a624b85d3810795562e0d1df2; corrected_sha256=51c5c04ce04bdd28dbcec5beb3c4766bdff4d0e5e6da555d22e2046280c6ec1b |

## Safety

- No warehouse was written.
- Existing V2 was not modified.
- The rejected untracked V3 implementation was not modified.

## Deliverables

- `docs/performance-intelligence/historical-observation-v3-authority-lineage/EDGEIQ_HISTORICAL_OBSERVATION_V3_AUTHORITY_LINEAGE_REPORT.json`
- `docs/performance-intelligence/historical-observation-v3-authority-lineage/EDGEIQ_HISTORICAL_OBSERVATION_V3_AUTHORITY_LINEAGE_REPORT.md`
- `docs/performance-intelligence/historical-observation-v3-authority-lineage/EDGEIQ_HISTORICAL_OBSERVATION_V3_AUTHORITY_LINEAGE_SCRIPT_MATRIX.csv`
- `docs/performance-intelligence/historical-observation-v3-authority-lineage/EDGEIQ_HISTORICAL_OBSERVATION_V3_AUTHORITY_LINEAGE_SCHEMA_MATRIX.csv`
- `docs/performance-intelligence/historical-observation-v3-authority-lineage/edgeiq_historical_observation_v3_authority_lineage_contract.json`
