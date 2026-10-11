# CODEX Issue #14 Frozen Historical Experiment Results

Date: 2026-10-11  
Branch: `codex/issue-14-final-experiment-gate`  
Execution approval: PR #15 comment `https://github.com/trentluckhurst1-create/edgeiq-platform/pull/15#issuecomment-6105376655`

## Governance

Status: **PASS_ONE_FROZEN_EXPERIMENT_COMPLETE**

This was exactly one frozen HGB fit and two separate evaluations, 2019 and 2020. No parameter tuning, repeated fitting, market/SP/BSP/odds data, 2025-2026 access, Stage011 change, production change, or model promotion was performed.

Research-use attestation passed. Execution approval passed.

## Command

```powershell
cd C:\EDGEIQ_PROFITABILITY_RESEARCH
python .\scripts\research\run_issue14_frozen_historical_experiment.py --pit-matrix outputs/research/issue10_pre2022_partition/ISSUE10_PRE2022_PIT_FEATURE_MATRIX.csv --attestation outputs/research/issue14_final_experiment_gate/ISSUE14_RESEARCH_USE_ATTESTATION.json --execution-approval outputs/research/issue14_final_experiment_gate/ISSUE14_EXECUTION_APPROVAL.json --out outputs/research/issue14_final_experiment_gate --execute
```

## Model

`HistGradientBoostingClassifier(loss="log_loss", learning_rate=0.05, max_leaf_nodes=5, l2_regularization=1.0, max_iter=200, random_state=42)`

Training:

- Rows: **465,622**
- Races: **44,465**
- Years: `2000-2010`, `2012-2015`, `2018`
- Sparse 2016: history-only, excluded from train/eval
- Missing years 2011 and 2017: excluded

Evaluation:

- 2019: **26,652 runners / 2,590 races**
- 2020: **28,548 runners / 2,756 races**

Probability:

```text
z_i = HistGradientBoostingClassifier.decision_function(X_i)
p_i = exp(z_i - max_r(z)) / sum_j exp(z_j - max_r(z))
```

Maximum race probability mass error: **2.220446049250313e-16** in both years.

## Results

| Year | Race LL | Uniform Race LL | LL Gain vs Uniform | Runner Brier | Uniform Brier | Top1 | Top3 | MRR | Mean Winner Rank | Mean Winner Prob |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2019 | 2.130150777806972 | 2.294134050670593 | 0.163983272863621 | 0.08377699670170673 | 0.08703032445742474 | 21.1583% | 51.8919% | 42.7369% | 4.0282 | 13.1317% |
| 2020 | 2.165098517502743 | 2.3128285357596075 | 0.147730018256865 | 0.08374916333161955 | 0.08670959959183373 | 20.2830% | 47.8955% | 41.0733% | 4.2467 | 12.6933% |

## Cohort Checks

2019:

- Horse no prior history: 3,643 rows, 347 winners, Brier 0.08354866549475057.
- Horse prior history: 23,009 rows, 2,243 winners, Brier 0.0838131482331484.
- Jockey/barrier missing cohort: 313 rows, 0 winners, mean probability 0.018637833376312554.
- Weight missing cohort: 324 rows, 0 winners, mean probability 0.018901725248569153.

2020:

- Horse no prior history: 3,458 rows, 338 winners, Brier 0.08543942493184227.
- Horse prior history: 25,090 rows, 2,418 winners, Brier 0.08351620499708108.
- No missing jockey/barrier/weight rows in the evaluated 2020 cohort.

## Artifacts

- `outputs/research/issue14_final_experiment_gate/ISSUE14_FROZEN_HGB_RESULTS.json`
- `outputs/research/issue14_final_experiment_gate/ISSUE14_FROZEN_HGB_YEAR_METRICS.csv`
- `outputs/research/issue14_final_experiment_gate/ISSUE14_FROZEN_HGB_CALIBRATION.csv`
- `outputs/research/issue14_final_experiment_gate/ISSUE14_FROZEN_HGB_COHORT_METRICS.csv`
- `outputs/research/issue14_final_experiment_gate/ISSUE14_FROZEN_HGB_OOS_PREDICTIONS.csv`
- `outputs/research/issue14_final_experiment_gate/ISSUE14_PREFLIGHT_REPORT.json`

Prediction SHA256: `c4fa265eaee0c2caf58f51ae6e7fb5ed014611070e7cdd6f4905f845b5fd14dd`

Feature manifest SHA256: `619b413dff4b545b0aa7b4778896342bf9ee5cb66c7bcd0b0cdae47ce0d2fa5c`

## Interpretation

The frozen historical model beats the uniform baseline materially in both 2019 and 2020 on race log loss and runner Brier. The direction is stable across the two evaluation years, with slightly weaker ranking performance in 2020.

This is **not** a Stage011 promotion result and not a profitability result. It is a standalone historical source-key model result. Remaining limitations are the missing 2011/2017 histories, sparse 2016 history contribution, lack of Stage011 canonical crosswalk, and no historical market-price evaluation.
