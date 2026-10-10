# CODEX Winning Model Plan — Issue #5

Status: **PLAN ONLY / AWAITING RESEARCH APPROVAL**

Branch: `codex/issue-5-winning-model-plan-20261010`

GitHub issue: `#5 — CODEX: decisive historical winner-probability model bake-off (no market data)`

## 1. Scope And Non-Negotiable Boundaries

This plan responds to Issue #5 by defining one bounded historical winner-probability bake-off. It does **not** authorise execution by itself.

Hard boundaries:

- Use only 2021-2024 historical non-market racing data already present in `C:\EDGEIQ_PROFITABILITY_RESEARCH`.
- Treat all 2022-2024 metrics as `REUSED_DEVELOPMENT`, not independent validation.
- Keep 2025-2026 sealed at source admission: no reads, row loads, counts, feature access, outcomes, scoring, evaluation, or excluded-count metadata from sealed years.
- Do not search for, read, join, or evaluate SP/BSP/odds/market/price files.
- Do not simulate bets, returns, thresholds, staking, or profitability.
- Do not reopen closed LAB245B identity hunting, EPI, rating, fuzzy identity, or price-source routes.
- Do not modify production or merge anything automatically.
- Preserve the scoring-artifact protocol: runner-level predictions must contain the required provenance fields and forbidden columns must be absent.

Minimum approval required before execution:

1. Explicit approval to run the bounded bake-off on reused 2022-2024 development evidence.
2. Explicit approval to create new scripts and output artifacts under the paths named below.
3. Explicit approval that this does not override the sealed-year or price-source stop.

## 2. Current Evidence To Reuse

### Stage011 frozen comparison baseline

Source script:

- `scripts/research/run_v2_stage011_clean_placing.py`

Reproduced runner-probability artifacts:

- `outputs/research/model_v2/stage011_reproduction/STAGE011_RUNNER_PROBABILITIES_2022.csv`
- `outputs/research/model_v2/stage011_reproduction/STAGE011_RUNNER_PROBABILITIES_2023.csv`
- `outputs/research/model_v2/stage011_reproduction/STAGE011_RUNNER_PROBABILITIES_2024.csv`
- `outputs/research/model_v2/stage011_reproduction/STAGE011_REPRODUCTION_REPORT.json`

Known reproduced Stage011 metrics:

| Year | Races | Runners | Race LL | Top1 |
|---:|---:|---:|---:|---:|
| 2022 | 612 | 7,459 | 2.125060402398 | 0.225490 |
| 2023 | 2,396 | 30,163 | 2.131427427909 | 0.206594 |
| 2024 | 2,402 | 31,234 | 2.102222925037 | 0.229808 |

Stage011 feature manifest from reproduction report:

- Current race context: `current_distance`, `represented_field_size`
- Horse historical depth/form: `hist_runs`, `days_since_last`, `last_distance`
- Lengths-versus-standard history: `lvs_last1`, `lvs_mean3`, `lvs_mean5`, `lvs_median5`, `lvs_std5`, `lvs_peak`, `lvs_worst5`
- Margin history: `margin_mean5`, `margin_std5`, `margin_worst5`, `margin_last1`, `margin_last2`, `margin_change_l1_l2`, `margin_per_runner_last1`, `margin_per_runner_last2`
- Distance history: `dist200_runs`, `dist200_lvs_mean`, `dist200_lvs_best`
- Barrier/connection context: `barrier_position_pct`, `jockey_prior_starts`, `jockey_prior_win_rate`, `jockey_prior_top3_rate`, `trainer_prior_starts`, `trainer_prior_win_rate`, `trainer_prior_top3_rate`
- Strict-prior clean placing: `clean_finish_mean5`, `clean_last_finish`, `clean_last_won`, `clean_last_top3`, `clean_finish_hist_n`

Stage011 HGB settings:

```text
HistGradientBoostingClassifier(
  max_iter=200,
  learning_rate=0.05,
  max_leaf_nodes=5,
  l2_regularization=1,
  random_state=42
)
```

### Stage016 retained challenger

Source script:

- `scripts/research/run_v2_stage016_context_family.py`

Stage016 reuses Stage011 construction and adds the exact current-race context family:

- `current_weight_kg`
- `weight_change_kg`
- `distance_change_metres`
- `abs_distance_change_metres`
- `prior_same_class_starts`
- `prior_exact_distance_starts_031`
- `context_authority_missing`
- `weight_change_missing`
- `distance_change_missing`

Stage016 is retained as an unpromoted challenger and must be rerun only under the approved bake-off protocol so that results are in the same scored-artifact format as all challengers.

### Prior learner bake-off

Source script:

- `scripts/research/run_v2_stage023_learner_bakeoff.py`

Stage023 already compared HGB, L2 logistic regression, and random forest on the Stage011 matrix. It is prior reused-development evidence and will be cited as prior work, not treated as fresh confirmation.

## 3. Initial Feature/Data Inventory To Produce

The first approved script will create a compact inventory without market/price columns and without 2025-2026 data. Source admission is part of the inventory gate and happens before any row-level load:

1. Read candidate file headers only first.
2. Reject any path, filename, or column name containing forbidden market/price/SP/BSP/odds/betting fields.
3. Require a filterable year/date field or prior certified proof that the file contains only 2021-2024 rows.
4. Read only projected key/date/feature columns, with a `year <= 2024` filter applied during chunked admission before concatenation.
5. Block any source that cannot be filtered without materializing, counting, or logging 2025-2026 rows.

Output:

- `outputs/research/codex_issue5_winning_model/CODEX_FEATURE_INVENTORY_20261010.csv`
- `outputs/research/codex_issue5_winning_model/CODEX_FEATURE_INVENTORY_20261010.json`

Inventory inputs:

- `outputs/research/model_v2/stage004/V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv` after source-admission gates pass
- `outputs/research/model_v2/stage006/V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv` after source-admission gates pass
- `outputs/research/profitability_program/d45/D45_FROZEN_PIT_FEATURE_MATRIX.csv` after source-admission gates pass
- `outputs/research/model_v2/stage011_reproduction/STAGE011_REPRODUCTION_REPORT.json`
- `outputs/research/profitability_program/lab238c/LAB238C_LAB239_CERTIFIED_MANIFEST.csv` only after header/path source-admission gates pass
- `outputs/research/profitability_program/lab239/LAB239_PIT_FEATURE_MATRIX.csv` only after header/path source-admission gates pass and rows can be admitted with `year <= 2024` without materializing sealed years
- Existing ai-review governance files named in this plan

Inventory fields:

- Source path
- Row count and race count by year, using years <= 2024 only
- Exact runner identity fields
- Candidate feature columns
- Non-null coverage by year
- First-starter / no-history handling
- PIT evidence class
- Leakage risk classification: `CERTIFIED`, `REQUIRES_LINEAGE_REVIEW`, `BLOCKED`
- Reason for exclusion where blocked

Explicit exclusions:

- Any column whose name indicates market, SP, BSP, odds, price, bet, stake, return, market rank, or EPI.
- Any source requiring fuzzy identity or unproven EIQ_HORSE mint reconstruction.
- Any source that would require reading, counting, materializing, or logging 2025-2026 rows for any purpose.

## 4. Pre-Registered Model Candidates

The bake-off will be bounded to these candidates. No one-variable searches or threshold mining.

### Candidate A — Stage011 reproduced baseline

Use existing Stage011 runner probabilities as the comparison baseline. If a rebuilt scored artifact is required for common output schema, rebuild Stage011 exactly once with the source script settings above and record hashes.

### Candidate B — Stage016 HGB

Stage011 features plus the predeclared exact context family from `run_v2_stage016_context_family.py`, same HGB settings as Stage011.

### Candidate C — Certified dense non-market HGB

Only if the inventory confirms an existing dense manifest is legal and point-in-time:

- Base matrix: Stage011 feature set.
- Add only `CERTIFIED` fields from `LAB238C_LAB239_CERTIFIED_MANIFEST.csv` / `LAB239_PIT_FEATURE_MATRIX.csv`.
- HGB settings fixed to Stage011 settings unless the manifest already records a stricter fixed setting.
- No features are added after seeing metrics.

If the dense manifest fails inventory, Candidate C is marked `NOT_RUN_BLOCKED_BY_INVENTORY`.

### Candidate D — Regularized race-normalized GLM/logit

Feature set: exactly the certified Stage011 35-feature manifest listed in Section 2, on the exact Stage011 race universe and winner labels. Candidate D is frozen before results are observed and is a learner contrast against Stage011 only, not an adaptive reuse of the strongest A-C matrix.

Model:

- Median imputation fitted on training rows only.
- Standardization fitted on training rows only.
- `LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=2000, random_state=42)`.
- Convert raw `LogisticRegression.decision_function(X)` runner scores to within-race probabilities by race softmax: for each race, `exp(score - max_score_in_race) / sum(exp(score - max_score_in_race))`.
- Do not apply race softmax to binary `predict_proba` outputs.

This is included for calibration/ranking contrast, not hyperparameter search.

### Candidate E — Simple fixed ensemble

Only if Stage011 HGB and Candidate D logit are both valid on the exact Stage011 race universe:

- Fixed arithmetic ensemble of Stage011 HGB and Candidate D logit probabilities, `0.5 * p_hgb + 0.5 * p_logit`, followed by exact within-race renormalization.
- No weight tuning.

### Optional installed-family probe

LightGBM/XGBoost may be included only if already installed in the environment and only with one fixed conservative parameter set recorded in the script. If absent, record `NOT_INSTALLED` and do not install packages during the bake-off.

## 5. Chronological Evaluation

Use the Stage011/Stage016 chronological protocol:

- Train years `< 2022`, evaluate 2022.
- Train years `< 2023`, evaluate 2023.
- Train years `< 2024`, evaluate 2024.

Eligibility:

- Same certified single-winner race universe as Stage011 wherever possible.
- Primary comparisons must preserve the exact Stage011 `_race`, runner identity, winner labels, and race set. No challenger may alter winner labels, scratch handling, race eligibility, or the primary comparison universe.
- If a challenger has lower coverage, evaluate both:
  - full Stage011 universe with missing indicators/imputation if PIT-safe;
  - exact common-race intersection for secondary diagnostic comparison only.
- A lower-coverage common-race result cannot promote a challenger unless the primary Stage011-universe gate also passes.
- Any race must have exactly one winner and probability mass sum within `1e-12`.

Evidence label:

- All 2022-2024 rows are `REUSED_DEVELOPMENT`.
- Results cannot be called independent confirmation or production validation.

## 6. Metrics And Diagnostics

Primary:

- Race-normalized winner log loss by year and weighted over 2022-2024.

Secondary:

- Top1, Top2, Top3, MRR.
- Runner Brier score.
- Calibration bins by model probability.
- Winner rank and winner assigned probability.
- Race-cluster bootstrap confidence intervals for delta race LL vs Stage011, using fixed seed `42`, 10,000 race-level resamples, and year-stratified sampling over the exact Stage011 primary race universe.
- Cohort breakdowns: year, field size band, history depth, first-starter/no-history flag, probability band, and feature-missingness strata.

Forbidden diagnostics:

- No SP/BSP/market/odds comparisons.
- No profitability, edge, overlay, staking, threshold, or return outputs.

## 7. Promotion / Retention Rule

Because all evidence is reused development, promotion means **research challenger designation only**, not production promotion or independent validation.

A challenger can be named the best defensible candidate only if all gates pass:

1. Governance: no market/SP/odds/EPI/sealed-year access; exact identity; no post-race target leakage.
2. Coverage: primary scored comparison covers at least 95% of Stage011 races per evaluation year. Common-race intersections are diagnostic only and cannot satisfy this promotion gate.
3. Primary metric: lower race LL than Stage011 in at least two of three years.
4. Stability: no year has LL worse than Stage011 by more than `0.005`.
5. Materiality: define `delta_ll = Stage011 race LL - challenger race LL` on the exact Stage011 primary race universe. Weighted 2022-2024 `delta_ll` must be at least `0.005`, and the year-stratified race-cluster bootstrap 95% CI lower bound for `delta_ll` must be greater than `0.000`.
6. Secondary safety: Top1 does not fall by more than 1 percentage point weighted over 2022-2024.
7. Artifacts: runner-level scored outputs satisfy `ai_review/SCORING_ARTIFACT_PROTOCOL.md` plus the `evidence_class=REUSED_DEVELOPMENT` amendment.

If no challenger passes, retain Stage011.

## 8. Output Artifacts After Approval

Scripts:

- `scripts/research/run_codex_issue5_feature_inventory_20261010.py`
- `scripts/research/run_codex_issue5_bounded_bakeoff_20261010.py`

Outputs:

- `outputs/research/codex_issue5_winning_model/CODEX_FEATURE_INVENTORY_20261010.csv`
- `outputs/research/codex_issue5_winning_model/CODEX_FEATURE_INVENTORY_20261010.json`
- `outputs/research/codex_issue5_winning_model/CODEX_BAKEOFF_MODEL_MANIFEST_20261010.csv`
- `outputs/research/codex_issue5_winning_model/CODEX_BAKEOFF_YEAR_METRICS_20261010.csv`
- `outputs/research/codex_issue5_winning_model/CODEX_BAKEOFF_CALIBRATION_20261010.csv`
- `outputs/research/codex_issue5_winning_model/CODEX_BAKEOFF_BOOTSTRAP_CI_20261010.csv`
- `outputs/research/codex_issue5_winning_model/CODEX_BAKEOFF_COHORTS_20261010.csv`
- `outputs/research/codex_issue5_winning_model/CODEX_BAKEOFF_RUNNER_SCORES_2022.csv`
- `outputs/research/codex_issue5_winning_model/CODEX_BAKEOFF_RUNNER_SCORES_2023.csv`
- `outputs/research/codex_issue5_winning_model/CODEX_BAKEOFF_RUNNER_SCORES_2024.csv`
- `outputs/research/codex_issue5_winning_model/CODEX_BAKEOFF_AUDIT_20261010.json`

Final report:

- `ai_review/CODEX_WINNING_MODEL_RESULTS.md`

## 9. Exact Command Sequence After Approval

From `C:\EDGEIQ_PROFITABILITY_RESEARCH` on branch `codex/issue-5-winning-model-plan-20261010` or its approved execution child branch:

```powershell
git status --short --branch
python -m py_compile scripts\research\run_codex_issue5_feature_inventory_20261010.py
python -m py_compile scripts\research\run_codex_issue5_bounded_bakeoff_20261010.py
python scripts\research\run_codex_issue5_feature_inventory_20261010.py --max-year 2024 --out outputs\research\codex_issue5_winning_model
python scripts\research\run_codex_issue5_bounded_bakeoff_20261010.py --max-year 2024 --evidence-class REUSED_DEVELOPMENT --out outputs\research\codex_issue5_winning_model
$required = @(
  "outputs\research\codex_issue5_winning_model\CODEX_FEATURE_INVENTORY_20261010.csv",
  "outputs\research\codex_issue5_winning_model\CODEX_BAKEOFF_YEAR_METRICS_20261010.csv",
  "outputs\research\codex_issue5_winning_model\CODEX_BAKEOFF_AUDIT_20261010.json",
  "ai_review\CODEX_WINNING_MODEL_RESULTS.md"
)
$missing = @($required | Where-Object { -not (Test-Path -LiteralPath $_) })
if ($missing.Count -gt 0) { throw ("missing required artifacts: " + ($missing -join ", ")) }
Write-Output "CODEX_ISSUE5_ARTIFACT_GATE=PASS"
git status --short --branch
```

No command in this sequence reads prices, opens 2025-2026, simulates bets, or promotes production.

## 10. PR Plan

After approval and execution:

1. Commit only:
   - `ai_review/CODEX_WINNING_MODEL_PLAN_20261010.md`
   - the two approved scripts;
   - the named `outputs/research/codex_issue5_winning_model/` artifacts;
   - `ai_review/CODEX_WINNING_MODEL_RESULTS.md`.
2. Push branch.
3. Open PR against `research/profitability-program-20261004`.
4. PR title: `Codex Issue #5 bounded winner-probability bake-off`.
5. PR body must state:
   - evidence is reused development;
   - no profitability tested;
   - no market/price/SP/BSP used;
   - 2025-2026 sealed;
   - promote challenger or retain Stage011 verdict.

## 11. Stop Conditions

Stop without fitting if:

- Inventory finds no legal candidate beyond Stage011/Stage016.
- Candidate C cannot be proven non-market and PIT-safe.
- Required Stage011 universe files are missing.
- Any script detects forbidden columns in candidate matrices.
- Any 2025-2026 row would be read, counted, materialized, or logged for any purpose.
- Any race has zero or multiple winners after eligibility filtering.
- Probability normalization fails `1e-12`.

Stop after results if:

- No challenger passes the promotion rule.
- Results depend on a single year or an uncovered race subset.
- Bootstrap/cohort diagnostics show the apparent gain is not robust enough for a defensible challenger designation.
