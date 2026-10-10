# CODEX Issue #5 Source Admission Repair

Status: **READY FOR BAKE-OFF AUTHORISATION**

Scope: Source-admission repair after commit `6c279d6a`, followed by the authorised one-time upstream source-partition export. No model fitting or scoring was performed. No market/SP/BSP/price archive work was performed. The previous Issue #5 fit results remain invalid and quarantined.

## Decision

The original A-H bake-off is now **ready for separate execution authorisation**, using only the newly partitioned and manifest-admitted source artifacts.

The previous blocker was that two required source families were not available as independently certified 2021-2024-only artifacts:

1. Stage011 strict-prior clean placing history, currently rebuilt from LAB026 `edgeiq_certified_flat_walk_forward_epi_026.csv`.
2. Stage016 current-race context, currently sourced from LAB031/LAB032 context authorities.

That blocker has been repaired by the authorised export. The bake-off runner has also been updated to fail closed unless these partition manifests match the supplied data files.

## Evidence Reviewed

Reviewed metadata and lineage:

- `ai_review/CODEX_WINNING_MODEL_PLAN_20261010.md`
- `ai_review/CODEX_ISSUE5_EXECUTION_GOVERNANCE_AUDIT_20261010.md`
- `scripts/research/run_v2_stage011_clean_placing.py`
- `scripts/research/run_v2_stage011_reproduction_artifact.py`
- `scripts/research/run_v2_stage016_context_family.py`
- `scripts/research/run_codex_issue5_bounded_bakeoff_20261010.py`
- `outputs/research/model_v2/stage011_reproduction/STAGE011_REPRODUCTION_REPORT.json`
- `outputs/research/model_v2/stage001/V2_STAGE001_DATA_ESTATE_INVENTORY.csv`
- `outputs/research/profitability_program/v2/V2_001_DATA_ESTATE_INVENTORY.csv`
- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_026\MODEL_LAB_026_SUMMARY.json`
- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_026\certified_epi_coverage_by_year_026.csv`
- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_031\MODEL_LAB_031_SUMMARY.json`
- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_032\MODEL_LAB_032_SUMMARY.json`

File-inventory search found no pre-existing artifact named or documented as a sealed/free 2021-2024 partition for LAB026 clean placing history or LAB031/LAB032 Stage016 context. The only 2021-2024 files found in the broader inventory were `PL001_ENRICHED_LOCAL_UNIVERSE_2021_2024.csv` and `PL002_ENRICHED_LOCAL_UNIVERSE_2021_2024.csv`; existing inventory metadata shows market/SP-derived columns in those files, and they are not approved Stage016 lineage.

The authorised export then created the required source partitions under:

- `outputs/research/codex_issue5_source_admission/CODEX_ISSUE5_LAB026_CLEAN_PLACING_2021_2024.csv`
- `outputs/research/codex_issue5_source_admission/CODEX_ISSUE5_LAB026_CLEAN_PLACING_2021_2024.manifest.json`
- `outputs/research/codex_issue5_source_admission/CODEX_ISSUE5_LAB031_CONTEXT_2021_2024.csv`
- `outputs/research/codex_issue5_source_admission/CODEX_ISSUE5_LAB031_CONTEXT_2021_2024.manifest.json`
- `outputs/research/codex_issue5_source_admission/CODEX_ISSUE5_SOURCE_PARTITION_AUDIT_20261010.json`

## Source Family Findings

### Stage011 Strict-Prior Clean Placing History

Current Stage011 scripts rebuild the final five clean placing features from:

- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_026\edgeiq_certified_flat_walk_forward_epi_026.csv`

The required columns are:

- `canonical_horse_id`
- `race_date`
- `finish_position`

Existing LAB026 summary records:

- `status`: `PASS_CERTIFIED_FLAT_WALK_FORWARD_EPI`
- `runner_rows`: `863755`
- `calculated_runner_epi`: `631102`
- governance: `market=NO`, `future_history=PROHIBITED`, `same_day_history=PROHIBITED`

However, existing year coverage metadata includes 2025 and 2026:

- 2025: `runner_rows=48765`, `calculated=31465`
- 2026: `runner_rows=24144`, `calculated=13222`

Therefore the existing LAB026 authority is certified for chronology and no-market usage, but it is **not** certified as sealed-year-free for this Issue #5 research runner. No pre-existing separate 2021-2024-only LAB026 clean placing partition was found.

The authorised export created a sealed-year-free partition:

- rows: `149242`
- unique races: `11794`
- unique horses: `19947`
- date bounds: `2021-01-01` to `2024-12-31`
- year counts: `2021=33908`, `2022=8948`, `2023=52312`, `2024=54074`
- output SHA256: `efa216c87854c001560e672452a7f2a180f8477dc0ec96fc24f0e409d8fb251e`
- forbidden-column scan: `PASS`

Stage011 clean placing reconstruction can now use the partitioned artifact without opening the mixed-year LAB026 authority in the Issue #5 runner.

### Stage016 LAB031/LAB032 Context

Stage016 adds the predeclared current-race context family from LAB031:

- `current_weight_kg`
- `weight_change_kg`
- `distance_change_metres`
- `abs_distance_change_metres`
- `prior_same_class_starts`
- `prior_exact_distance_starts_031`
- `context_authority_missing`
- `weight_change_missing`
- `distance_change_missing`

Existing context authorities:

- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_031\certified_current_race_context_031.csv`
- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_032\certified_current_race_context_032.csv`

Existing LAB031 summary records:

- `status`: `PASS_CERTIFIED_CURRENT_RACE_CONTEXT`
- `output_rows`: `631102`
- `unique_races`: `49853`
- `temporal_violations`: `0`
- governance: `source=CANONICAL_PERFORMANCE_WAREHOUSE`, `target_universe=MODEL_LAB_026_CALCULATED_ONLY`, `market=NO`, `future_history=PROHIBITED`, `current_result_as_feature=NO`

Existing LAB032 summary records:

- `status`: `REVIEW_BARRIER_GEOMETRY`
- `rows`: `631102`
- governance: `field_size_source=FULL_CANONICAL_WAREHOUSE_RACE_MEMBERSHIP`, `model_fitting=NO`, `production_changed=NO`

Because LAB031/LAB032 are built on the LAB026 calculated universe, no pre-existing 2021-2024-only context partition was admissible.

The authorised export created a sealed-year-free LAB031 partition:

- rows: `109946`
- unique races: `8569`
- unique horses: `19040`
- date bounds: `2021-01-01` to `2024-12-31`
- year counts: `2021=29329`, `2022=8438`, `2023=37050`, `2024=35129`
- output SHA256: `3af6bd924b510267ae1b45a252b2aa6d9ea9b65d67084eac9e515cbdaf383c09`
- forbidden-column scan: `PASS`

Stage016 can now use the partitioned LAB031 artifact without opening the mixed-year LAB031 authority in the Issue #5 runner.

## Exact Blockers Preventing A-H Execution

- Previous blocker: Candidate A/C/D reconstruction required clean placing features from mixed-year LAB026.
- Previous blocker: Candidates B/E/F/G additionally required Stage016 LAB031 context from a mixed-year authority.
- Repair: both source families now have 2021-2024-only partitions with manifests, date bounds, row counts, checksums, and forbidden-column scans.
- Enforcement: `scripts/research/run_codex_issue5_bounded_bakeoff_20261010.py` now requires `--perf026-manifest` and `--lab031-context-manifest`; it validates purpose, output path, SHA256, date bounds, year-count keys, required columns, and forbidden-column scan before row-level access.

## Upstream Export Completion

### Source Must Be Partitioned

The authorised upstream process partitioned these sources:

1. LAB026 clean placing authority:
   - Input: `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_026\edgeiq_certified_flat_walk_forward_epi_026.csv`
   - Output: `outputs/research/codex_issue5_source_admission/CODEX_ISSUE5_LAB026_CLEAN_PLACING_2021_2024.csv`

2. LAB031 Stage016 context authority:
   - Input: `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_031\certified_current_race_context_031.csv`
   - Output: `outputs/research/codex_issue5_source_admission/CODEX_ISSUE5_LAB031_CONTEXT_2021_2024.csv`

LAB032 was not substituted for LAB031. The current Issue #5 A-H plan remains unchanged.

### How The Export Should Be Produced

The export was run by:

- `scripts/research/run_codex_issue5_source_partition_export_20261010.py`

The Issue #5 research runner must now receive only the partitioned outputs and their manifests. It must not open or inspect the original mixed-year LAB026/LAB031/LAB032 rows.

### Required Verification Artifacts

Each exported partition is accompanied by a manifest containing:

- Source path.
- Source SHA256.
- Output path.
- Output SHA256.
- Output byte size.
- Output row count.
- Output unique race count where `canonical_race_id` exists.
- Output unique horse count.
- Minimum `race_date`.
- Maximum `race_date`.
- Year counts for 2021, 2022, 2023, and 2024 only.
- Explicit assertion that no row has `race_date` after `2024-12-31`.
- Exact column list.
- Forbidden-column scan result for market/SP/BSP/odds/price/bet/stake/return columns.
- Lineage statement linking the partition to the LAB026/LAB031 source summary and governance.

The Issue #5 runner now fails closed unless:

- the output SHA256 matches the manifest;
- date bounds are within 2021-2024;
- required columns are present;
- forbidden columns are absent;
- the Stage011 primary universe has 100% race/runner coverage after joins.

### Governance Status

The one-time upstream source-partition export has been performed. Separate approval is still required before model fitting/scoring.

No model run has been authorised or performed in this repair step.

## Shortest Compliant Path

1. Request separate approval to execute the original A-H bake-off using only the admitted partitions and manifests.
2. Run the bake-off command with:
   - `--perf026 outputs\research\codex_issue5_source_admission\CODEX_ISSUE5_LAB026_CLEAN_PLACING_2021_2024.csv`
   - `--perf026-manifest outputs\research\codex_issue5_source_admission\CODEX_ISSUE5_LAB026_CLEAN_PLACING_2021_2024.manifest.json`
   - `--lab031-context outputs\research\codex_issue5_source_admission\CODEX_ISSUE5_LAB031_CONTEXT_2021_2024.csv`
   - `--lab031-context-manifest outputs\research\codex_issue5_source_admission\CODEX_ISSUE5_LAB031_CONTEXT_2021_2024.manifest.json`
3. Do not redesign A-H.

Final state: **READY FOR BAKE-OFF AUTHORISATION**, not yet run.
