# EDGEiQ Stage011 Live Completion Report

Status: RESEARCH-ONLY FAIL-CLOSED, WITH PARTIAL CERTIFIED LAB245B IDENTITY BRIDGE

## Scope

Built a consolidated Stage011 live feature builder for the Caulfield 2026-10-14 dry run. The script reconstructs the exact 35 Stage011 feature columns from:

- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\october_graphql_field_identities.csv`
- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\caulfield_browser_form.csv`
- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\public_race_snapshot_20261012T051330Z.json`
- `C:\EDGEIQ_ISSUE23\outputs\research\ISSUE23_LIVE_HISTORY_FEATURE_CANDIDATES_V3.csv`
- `C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_WAREHOUSE_RUNNER_LVS.csv`

No model fitting, Stage011 scoring, market data, target outcomes, production changes, or betting logic were used.

## Live Field Coverage

- Declared runners: 104
- Races: 8
- Race sizes: 7, 11, 16, 11, 16, 16, 12, 15
- Racing.com-native historical form available: 98 runners
- Historical identity status:
  - `LAB245B_IDENTITY_BRIDGE_CERTIFIED`: 81
  - `RACINGCOM_NATIVE_FORM_AVAILABLE`: 15
  - `HISTORICAL_LVS_CANDIDATE_UNCERTIFIED`: 2
  - `FIRST_STARTER_OR_INSUFFICIENT_HISTORY`: 6
- LAB245B bridge status:
  - `CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH`: 81
  - `NO_STRICT_PRIOR_LAB245B_HISTORY`: 18
  - `ONE_PRIOR_MATCH_INSUFFICIENT`: 5

## Feature Coverage

| Family | Features | Populated cells | Total cells | Rows complete | Coverage |
|---|---:|---:|---:|---:|---:|
| Current context | 3 | 312 | 312 | 104 | 100.00% |
| Racing.com-native history | 17 | 1668 | 1768 | 94 | 94.34% |
| LVS timing | 9 | 715 | 936 | 74 | 76.39% |
| Personnel partial | 6 | 603 | 624 | 97 | 96.63% |

Score-eligible rows: 0 / 104.

## Semantics Corrections

- Winner margins are preserved from source. A warehouse audit found `39,900` winner rows and `8,437` non-zero winner margins, so the builder no longer forces winner margins to zero.
- Historical aggregate semantics now follow `build_lab245b_compact_performance_bridge.py`: finite historical values are used for aggregate/last margin and LVS features, while `margin_per_runner_last1/2` use the most recent raw prior starts and can remain missing when that prior start lacks field size or margin.
- Personnel prior formulas are source-backed from `build_d45_frozen_pit_feature_matrix.py`: `(wins + 1) / (starts + 10)` and `(top3 + 3) / (starts + 10)`. They remain uncertified live because the current source is partial, not because the formula is unknown.

## Primary Blockers

1. Twenty-three runners still lack certified direct `lvs_*` features; thirty lack certified distance-near LVS features.
2. The six jockey/trainer prior features are reconstructed only from the 98 captured Caulfield-form horses, not from a certified full historical jockey/trainer universe, so they remain populated but uncertified.
3. Five runners have one matching prior record but fail the multi-prior identity threshold; eighteen have no strict-prior LAB245B history.
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
- `outputs\research\stage011_live_completion\EDGEIQ_STAGE011_LIVE_IDENTITY_BRIDGE_AUDIT.csv`
- `outputs\research\stage011_live_completion\EDGEIQ_STAGE011_LIVE_FEATURE_AUDIT.json`
- `outputs\research\stage011_live_completion\EDGEIQ_STAGE011_LIVE_SCORE_ELIGIBLE_INPUT.csv`

## Readiness Decision

Stage011 live scoring readiness: NO.

The pipeline now builds a defensible live feature matrix, certifies 81 LAB245B historical identities using exact EIQ identity plus multiple matching strict-prior race records, and fails closed correctly. It must not be scored until full Stage011 feature certification is complete, especially full-history jockey/trainer priors and remaining timing gaps.

## Exact Command

```powershell
Set-Location "C:\EDGEIQ_ISSUE23"
python scripts\research\run_edgeiq_stage011_live_feature_pipeline.py
```
