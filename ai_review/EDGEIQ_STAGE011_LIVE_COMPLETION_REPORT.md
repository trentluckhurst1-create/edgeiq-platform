# EDGEiQ Stage011 Live Completion Report

Status: RESEARCH-ONLY SOURCE-ADMITTED FEATURE RECOVERY, NO SCORING PERFORMED

## Scope

Built and validated the Stage011 live feature recovery path for the Caulfield 2026-10-14 dry run. The script reconstructs the exact 35 Stage011 feature columns from admitted live/current, Racing.com form, LAB245B timing, and D45/PERF026 personnel sources.

No model fitting, Stage011 prediction scoring, market data, target outcomes, production changes, or betting logic were used.

## Source Admission

Required sources passed admission:

- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\october_graphql_field_identities.csv`
- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\caulfield_browser_form.csv`
- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\public_race_snapshot_20261012T051330Z.json`
- `C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_WAREHOUSE_RUNNER_LVS.csv`
- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_026\edgeiq_certified_flat_walk_forward_epi_026.csv`

The LAB245B warehouse matched the expected SHA-256 `169652f38b830a4d2337975d65d9cead16fe306373ac4802bc57b7b33793a8fb`.

The optional `ISSUE23_LIVE_HISTORY_FEATURE_CANDIDATES_V3.csv` was absent and was reported as `MISSING_OPTIONAL_SOURCE`; it was not substituted or promoted.

## Live Field Coverage

- Declared runners: 104
- Races: 8
- Racing.com-native historical form available: 98 runners
- Live EIQ horse ID provenance: 104 / 104 matched the GraphQL `horse_code + ".0"` hash convention.
- Duplicate live runner keys: none.
- Duplicate LAB245B prior race records for certified identities: none.
- Ambiguous prior race matches: none.

Historical identity status:

- `LAB245B_IDENTITY_BRIDGE_CERTIFIED`: 81
- `RACINGCOM_NATIVE_FORM_AVAILABLE`: 17
- `FIRST_STARTER_OR_INSUFFICIENT_HISTORY`: 6

LAB245B bridge status:

- `CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH`: 81
- `NO_STRICT_PRIOR_LAB245B_HISTORY`: 18
- `ONE_PRIOR_MATCH_INSUFFICIENT`: 5

## Feature Coverage

| Family | Features | Populated cells | Total cells | Rows complete | Coverage |
|---|---:|---:|---:|---:|---:|
| Current context | 3 | 312 | 312 | 104 | 100.00% |
| Racing.com-native history | 17 | 1668 | 1768 | 94 | 94.34% |
| LVS timing | 9 | 715 | 936 | 74 | 76.39% |
| Personnel full history | 6 | 603 | 624 | 97 | 96.63% |

Feature certification status:

- `POPULATED_CERTIFIED_LAB245B_BRIDGE`: 1,930
- `POPULATED_CERTIFIED_RCOM_NATIVE`: 765
- `POPULATED_CERTIFIED_PERSONNEL`: 603
- `CERTIFIED_MISSING_ALLOWED`: 35
- `MISSING`: 307

Score-eligible feature rows: 78 / 104. These rows are feature/provenance eligible only; the script does not score the Stage011 model.

## Personnel Priors

The six jockey/trainer features are now rebuilt from the D45 full-history source universe in PERF026, using strict-prior dates and the frozen D45 formulas:

- Starts: cumulative prior starts.
- Win rate: `(wins + 1) / (starts + 10)`.
- Top-3 rate: `(top3 + 3) / (starts + 10)`.

Coverage:

- Jockey prior available: 100 / 104; no-prior certified missing: 4 / 104.
- Trainer prior available: 101 / 104; no-prior certified missing: 3 / 104.
- Personnel feature cells populated: 603 / 624.

## Timing Recovery

- Direct LVS timing available: 81 / 104.
- Missing direct LVS due to no certified LAB245B identity: 23 / 104.
- Distance-near LVS available: 74 / 104.
- Certified identity but no distance-near LVS history: 7 / 104.
- Missing distance-near LVS due to no certified LAB245B identity: 23 / 104.

The seven no-distance-near cases are recorded as certified missing values, not fabricated timing substitutes.

## Score Eligibility

The 78 score-eligible rows have certified provenance for all 35 Stage011 feature slots, allowing legitimate historical NaNs where the Stage011 missing-value contract can carry them. Three certified identity rows are not score-eligible: two scratched runners and one active runner (`Zourain`) with an uncertified missing `margin_per_runner_last1`.

The remaining 23 active blockers are identity/timing failures:

- 18 runners have no strict-prior LAB245B history.
- 5 runners have only one matching strict-prior record and fail the two-distinct-race certification threshold.

## Tests Run

```powershell
python -m py_compile scripts\research\run_edgeiq_stage011_live_feature_pipeline.py scripts\research\test_edgeiq_stage011_live_feature_pipeline.py
python scripts\research\test_edgeiq_stage011_live_feature_pipeline.py
python scripts\research\run_edgeiq_stage011_live_feature_pipeline.py
```

Result: PASS. Tests include false EIQ identity provenance, duplicate historical race records, strict same-day exclusion for personnel priors, optional-source fail-closed behaviour, no market/outcome fields, and live Caulfield contract checks.

## Outputs

- `outputs\research\stage011_live_completion\EDGEIQ_STAGE011_SOURCE_RESOLUTION_AUDIT.json`
- `outputs\research\stage011_live_completion\EDGEIQ_STAGE011_LIVE_FEATURE_MATRIX.csv`
- `outputs\research\stage011_live_completion\EDGEIQ_STAGE011_LIVE_FEATURE_COVERAGE_BY_FAMILY.csv`
- `outputs\research\stage011_live_completion\EDGEIQ_STAGE011_LIVE_FEATURE_STATUS_LONG.csv`
- `outputs\research\stage011_live_completion\EDGEIQ_STAGE011_LIVE_IDENTITY_BRIDGE_AUDIT.csv`
- `outputs\research\stage011_live_completion\STAGE011_RUNNER_FEATURE_BLOCKERS.csv`
- `outputs\research\stage011_live_completion\EDGEIQ_STAGE011_LIVE_FEATURE_AUDIT.json`
- `outputs\research\stage011_live_completion\EDGEIQ_STAGE011_LIVE_SCORE_ELIGIBLE_INPUT.csv`

## Readiness Decision

Stage011 live feature recovery readiness: PARTIAL PASS.

The builder now produces 78 certified, active, score-eligible rows for the Caulfield dry run without scoring them. The run remains research-only and fail-closed: 26 runners are withheld from scoring because they are scratched or still have unresolved feature provenance blockers.

## Exact Command

```powershell
Set-Location "C:\EDGEIQ_ISSUE23"
python scripts\research\run_edgeiq_stage011_live_feature_pipeline.py
```
