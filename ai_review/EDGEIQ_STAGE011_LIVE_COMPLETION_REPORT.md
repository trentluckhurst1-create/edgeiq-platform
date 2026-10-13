# EDGEiQ Stage011 Live Completion Report

Status: RESEARCH-ONLY FAIL-CLOSED

## Scope

Built a consolidated Stage011 live feature builder for the Caulfield 2026-10-14 dry run. The script reconstructs the exact 35 Stage011 feature columns from:

- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\october_graphql_field_identities.csv`
- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\caulfield_browser_form.csv`
- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\public_race_snapshot_20261012T051330Z.json`
- `C:\EDGEIQ_ISSUE23\outputs\research\ISSUE23_LIVE_HISTORY_FEATURE_CANDIDATES_V3.csv`

No model fitting, Stage011 scoring, market data, target outcomes, production changes, or betting logic were used.

## Live Field Coverage

- Declared runners: 104
- Races: 8
- Race sizes: 7, 11, 16, 11, 16, 16, 12, 15
- Racing.com-native historical form available: 98 runners
- Historical identity status:
  - `RACINGCOM_NATIVE_FORM_AVAILABLE`: 56
  - `HISTORICAL_LVS_CANDIDATE_UNCERTIFIED`: 42
  - `FIRST_STARTER_OR_INSUFFICIENT_HISTORY`: 6

## Feature Coverage

| Family | Features | Populated cells | Total cells | Rows complete | Coverage |
|---|---:|---:|---:|---:|---:|
| Current context | 3 | 312 | 312 | 104 | 100.00% |
| Racing.com-native history | 17 | 1669 | 1768 | 95 | 94.40% |
| LVS timing | 9 | 0 | 936 | 0 | 0.00% |
| Personnel partial | 6 | 603 | 624 | 97 | 96.63% |

Score-eligible rows: 0 / 104.

## Primary Blockers

1. The nine Stage011 LVS/timing features have no certified live reconstruction path from Racing.com numeric horse IDs into the LAB245B timing namespace.
2. The six jockey/trainer prior features are reconstructed only from the 98 captured Caulfield-form horses, not from a certified full historical jockey/trainer universe, so they remain populated but uncertified.
3. The 42 LAB245B candidate links are preserved as evidence only and are not promoted to certified identity.
4. Six runners have no Racing.com-native historical form in the captured source and remain first-starter/no-history cases.

## Tests Run

```powershell
python -m py_compile scripts\research\run_edgeiq_stage011_live_feature_pipeline.py scripts\research\test_edgeiq_stage011_live_feature_pipeline.py
python scripts\research\test_edgeiq_stage011_live_feature_pipeline.py
python scripts\research\run_edgeiq_stage011_live_feature_pipeline.py
```

Result: PASS for compile and targeted tests. The live builder completed and intentionally produced an empty score-eligible input because the 35-feature matrix is incomplete/uncertified.

## Outputs

- `outputs\research\stage011_live_completion\EDGEIQ_STAGE011_LIVE_FEATURE_MATRIX.csv`
- `outputs\research\stage011_live_completion\EDGEIQ_STAGE011_LIVE_FEATURE_COVERAGE_BY_FAMILY.csv`
- `outputs\research\stage011_live_completion\EDGEIQ_STAGE011_LIVE_FEATURE_STATUS_LONG.csv`
- `outputs\research\stage011_live_completion\EDGEIQ_STAGE011_LIVE_FEATURE_AUDIT.json`
- `outputs\research\stage011_live_completion\EDGEIQ_STAGE011_LIVE_SCORE_ELIGIBLE_INPUT.csv`

## Readiness Decision

Stage011 live scoring readiness: NO.

The pipeline now builds a defensible live feature matrix and fails closed correctly. It must not be scored until the LVS timing identity bridge and full-history personnel priors are certified.

## Exact Command

```powershell
Set-Location "C:\EDGEIQ_ISSUE23"
python scripts\research\run_edgeiq_stage011_live_feature_pipeline.py
```
