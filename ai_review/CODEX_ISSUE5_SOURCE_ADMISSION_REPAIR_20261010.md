# CODEX Issue #5 Source Admission Repair

Status: **BLOCKED**

Scope: Source-admission repair after commit `6c279d6a`. This audit used existing plans, scripts, metadata, inventories, summaries, manifests, filenames, sizes, and lineage documents only. It did not fit or score models, did not access market/SP/BSP/price archives, did not read mixed-year source data rows, and did not claim the invalid Issue #5 results are valid.

## Decision

The original A-H bake-off is **not ready to run**.

Two required source families are still not available as independently certified 2021-2024-only artifacts:

1. Stage011 strict-prior clean placing history, currently rebuilt from LAB026 `edgeiq_certified_flat_walk_forward_epi_026.csv`.
2. Stage016 current-race context, currently sourced from LAB031/LAB032 context authorities.

Because at least one required source is missing, source search stops here and the compliant next step is an upstream export proposal, not another model comparison.

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

Therefore the existing LAB026 authority is certified for chronology and no-market usage, but it is **not** certified as sealed-year-free for this Issue #5 research runner. No separate 2021-2024-only LAB026 clean placing partition was found.

Stage011 cannot be reconstructed entirely from already admissible sources because the clean placing history source is mixed-year and no admitted partition exists.

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

Because LAB031/LAB032 are built on the LAB026 calculated universe and no 2021-2024-only context partition was found, Stage016 cannot be reconstructed entirely from already admissible sources.

## Exact Blockers Preventing A-H Execution

- Candidate A requires Stage011 reconstruction for common scored-artifact parity. That reconstruction requires clean placing features from LAB026.
- Candidates C and D also require the same Stage011 35-feature matrix for logistic and random forest comparisons.
- Candidates B, E, F, and G additionally require Stage016 LAB031/LAB032 context features.
- The existing LAB026, LAB031, and LAB032 authorities are mixed-year sources under the Issue #5 sealed-year rule.
- The approved plan forbids reading mixed-year rows and filtering out 2025-2026 afterward.
- No independent 2021-2024-only LAB026 clean placing partition was found.
- No independent 2021-2024-only LAB031/LAB032 context partition was found.

## Upstream Export Proposal

### Source Must Be Partitioned

An authorised upstream process should partition these sources:

1. LAB026 clean placing authority:
   - Input: `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_026\edgeiq_certified_flat_walk_forward_epi_026.csv`
   - Required output: a 2021-2024-only artifact containing at minimum `canonical_horse_id`, `race_date`, and `finish_position`.

2. LAB031 Stage016 context authority:
   - Input: `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_031\certified_current_race_context_031.csv`
   - Required output: a 2021-2024-only artifact containing the exact LAB031 identity/date fields plus the nine Stage016 context fields.

Optionally, if the research owner decides LAB032 should supersede LAB031 for corrected context geometry, that is a separate governance choice. The current Issue #5 A-H plan should not silently substitute LAB032 for LAB031.

### How The Export Should Be Produced

The export must be run outside the Issue #5 research runner by a separately authorised process that is allowed to read the mixed-year authorities. It should write new artifacts containing only rows with:

- `race_date >= 2021-01-01`
- `race_date <= 2024-12-31`

The Issue #5 research runner must receive only the partitioned outputs and their manifests. It must not open or inspect the original mixed-year LAB026/LAB031/LAB032 rows.

### Required Verification Artifacts

Each exported partition must be accompanied by a manifest containing:

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

The Issue #5 runner should fail closed unless:

- the output SHA256 matches the manifest;
- date bounds are within 2021-2024;
- required columns are present;
- forbidden columns are absent;
- the Stage011 primary universe has 100% race/runner coverage after joins.

### Governance Approval Required

Required approval text:

```text
I approve a one-time upstream source-partition export for Issue #5 from LAB026 and LAB031 mixed-year authorities into sealed-year-free 2021-2024-only artifacts, with the export process allowed to read the mixed-year inputs, the Issue #5 research runner forbidden from reading those mixed-year inputs, no market/SP/BSP/odds access, no model fitting/scoring during export, and manifest verification by row counts, date bounds, checksums, column lists, and lineage.
```

## Shortest Compliant Path

1. Obtain the upstream export approval above.
2. Produce the LAB026 and LAB031 2021-2024 partitions plus manifests outside the Issue #5 research runner.
3. Amend `run_codex_issue5_bounded_bakeoff_20261010.py` to accept only manifest-admitted partition paths and to fail closed on any unpartitioned LAB026/LAB031/LAB032 input.
4. Re-run source admission only.
5. If source admission passes, request separate approval to execute the original A-H bake-off. Do not redesign A-H.

Final state: **BLOCKED**, not ready to run.
