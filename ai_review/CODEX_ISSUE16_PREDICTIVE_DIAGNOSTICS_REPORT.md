# CODEX Issue #16 Predictive Diagnostics Report

Date: 2026-10-11  
Branch: `codex/issue-16-predictive-diagnostics`  
Scope: read-only diagnostics on frozen Issue #14 OOS predictions. No fitting, tuning, recalibration, market/SP/BSP/odds access, sealed-year access, Stage011 change, production change, or profitability analysis.

## Inputs

- Predictions: `outputs/research/issue14_final_experiment_gate/ISSUE14_FROZEN_HGB_OOS_PREDICTIONS.csv`
- Prediction SHA256: `c4fa265eaee0c2caf58f51ae6e7fb5ed014611070e7cdd6f4905f845b5fd14dd`
- PIT matrix SHA256: `34add48ff515cd53237c8d83238ea69cc5a9d108ee0f39dadd3bc594e17ba3c1`
- Runner partition SHA256: `07f52642028934be058a91899534e0192960da18628f0e7996ca2bf6dfcd75b2`

Rows analysed: **55,200**  
Races analysed: **5,346**

## Commands

```powershell
cd C:\EDGEIQ_PROFITABILITY_RESEARCH
python -m py_compile .\scripts\research\run_issue16_predictive_diagnostics.py .\tests\test_issue16_predictive_diagnostics.py
python -m unittest .\tests\test_issue16_predictive_diagnostics.py
.\scripts\research\run_issue16_predictive_diagnostics.ps1
```

## Reliability

The model improved over uniform in both years. Race-block bootstrap confidence intervals are positive for log-loss and Brier improvement in both evaluation years.

| Year | LL gain vs uniform | 95% CI | Brier gain vs uniform | 95% CI | Top1 | 95% CI | Top3 | 95% CI |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2019 | 0.16398 | 0.14916 to 0.17847 | 0.003592 | 0.003177 to 0.004019 | 21.16% | 19.69% to 22.78% | 51.89% | 50.00% to 53.78% |
| 2020 | 0.14773 | 0.13342 to 0.16202 | 0.003336 | 0.002920 to 0.003758 | 20.28% | 18.83% to 21.73% | 47.90% | 46.01% to 49.75% |

Interpretation: the frozen model has stable predictive signal in both years, with 2020 ranking weaker than 2019 but still positive against uniform.

## Missing-Field Integrity

The 2019 missing barrier/jockey/weight rows are localized:

- Barrier missing: 313 rows, 8 races, 0 winners.
- Jockey ID missing: 313 rows, 8 races, 0 winners.
- Weight missing: 324 rows, 8 races, 0 winners.
- All affected rows joined to the runner partition as eligible, non-scratched starters.
- All affected rows came from `edgeiq_graphql_may_2019_results_v1.csv`.
- No affected rows failed the runner-partition join.

The affected races are `5187719` through `5187726`. Missing rows represent 51.85% to 85.71% of each affected field, but not the entire field. The winners in those races were not in the missing cohort.

Interpretation: this is a source-provenance gap concentrated in one monthly file and eight races, not evidence of scratch leakage or broken winner labels. It should still be carried as a review flag because the missingness perfectly avoided winners in those races.

## Calibration

The model is directionally calibrated in middle bands but shows structured error:

- Low-probability bands generally overpredict winners.
- Mid/high bands underpredict winners, especially 2020 in the `0.20-0.30` and `0.30-0.50` bands.
- Extreme `>0.50` band has only 2 rows in 2019 and 1 row in 2020, too sparse to interpret.

Examples:

- 2019 `0.02-0.05`: mean p 3.75%, win rate 2.36%.
- 2019 `0.15-0.20`: mean p 17.01%, win rate 19.62%.
- 2020 `0.20-0.30`: mean p 23.13%, win rate 27.32%.
- 2020 `0.30-0.50`: mean p 34.65%, win rate 45.21%, but only 73 rows.

## Ranking

Top-ranked runner win rate:

- 2019: 21.16%, mean top-rank probability 18.42%.
- 2020: 20.28%, mean top-rank probability 18.08%.

The top-ranked runners are underconfident on average in both years. Lower ranks, especially rank >10, are overpredicted relative to observed wins.

## Racing Cohorts

Field size:

- Signal is positive across all field-size bands.
- Best LL gains appear in large fields of 11-14 runners.
- Very large fields have smaller gains and thinner race counts.

Distance:

- Signal is positive across sprint, mile-ish, middle-distance and staying cohorts.
- 2019 staying races show strong LL gain, but only 129 races.
- 2020 distance gains are more even and modest.

Horse history:

- No-prior and prior-history cohorts have similar Brier in 2019.
- In 2020, no-prior horses are weaker than prior-history horses.
- Horse prior availability remains a useful diagnostic dimension but is not a blocker.

## Integrity Red Flags

No evidence found of:

- Market/SP/BSP/odds access.
- Sealed 2025-2026 access.
- Race probability mass failure.
- Broken one-winner labels in the frozen prediction set.
- Scratched runners in the 2019 missing-field cohort.

Review flags:

1. The May 2019 missing-field concentration should be audited at source-file level before future modelling changes.
2. Calibration suggests low-probability runners are overpredicted and higher-probability runners may be underconfident, but recalibration is not authorised by Issue #16.
3. Very large fields remain harder and should stay a prespecified diagnostic cohort.

## One Pre-Registered Hypothesis

Before any new model experiment, audit the May 2019 source-file missingness and, if Grok approves, add **source-provenance missingness flags** for barrier/weight/jockey fields rather than silently relying on raw missing values. This is predictive-only and must not use market data, odds, profitability, or hyperparameter tuning.

## Artifacts

- `outputs/research/issue14_predictive_diagnostics/ISSUE16_DIAGNOSTIC_MANIFEST.json`
- `outputs/research/issue14_predictive_diagnostics/ISSUE16_YEAR_SUMMARY.csv`
- `outputs/research/issue14_predictive_diagnostics/ISSUE16_RACE_BLOCK_BOOTSTRAP.csv`
- `outputs/research/issue14_predictive_diagnostics/ISSUE16_CALIBRATION_BY_PROB_BAND.csv`
- `outputs/research/issue14_predictive_diagnostics/ISSUE16_RANKING_DIAGNOSTICS.csv`
- `outputs/research/issue14_predictive_diagnostics/ISSUE16_COHORT_PERFORMANCE.csv`
- `outputs/research/issue14_predictive_diagnostics/ISSUE16_MISSING_FIELD_INTEGRITY.csv`
- `outputs/research/issue14_predictive_diagnostics/ISSUE16_MISSING_FIELD_AFFECTED_RACES.csv`
- `outputs/research/issue14_predictive_diagnostics/ISSUE16_MISSING_FIELD_PROVENANCE.csv`

## Handoff

Request Grok independent review of this diagnostic report before authorising any further experiment. The frozen historical model remains the research benchmark; this report does not promote a model.
