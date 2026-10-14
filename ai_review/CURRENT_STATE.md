# EDGEiQ Research - Current Decision

Date: 2026-10-13

## Champion

Stage011 remains the frozen research champion.

## Issue #23 Winner-Selection Experiment

Objective: improve race-level Top-1 winner selection without pricing, betting, market, SP/BSP, profitability research, production changes, or sealed 2025-2026 access.

Evidence class: REUSED_DEVELOPMENT. The experiment used existing admitted 2022-2024 Issue5 runner scores and Stage006 race-state diagnostics only.

Primary metric: one deterministic highest-probability runner per race, ties broken by probability descending then horse id ascending.

### Stage011 vs Stage016

- 2022 Stage011 Top-1: 0.236928; Stage016 Top-1: 0.228758.
- 2023 Stage011 Top-1: 0.201586; Stage016 Top-1: 0.212020.
- 2023 Stage016 paired Top-1 difference vs Stage011: 0.010434 [-0.001252, 0.022120].
- 2023 Stage016 LL gain vs Stage011: 0.009073 [0.004065, 0.013976].

Candidate G had the highest weighted Top-1 across 2022-2024 (0.223475), but failed the log-loss guardrail badly: weighted LL 2.198334 versus Stage011 2.120390. It is not a defensible champion replacement.

### Controlled Challenger

Challenger: `ISSUE23_TOP1_ROUTER_2022_LOCKED`.

Predeclared rule: use Stage016 for a race-state slice only when 2022 development evidence has at least 50 races, Stage016 Top-1 exceeds Stage011 by at least 0.03, and Stage016 race log loss is no worse than Stage011 by more than 0.03. Otherwise use Stage011.

Router selected Stage016 in 1 race-state slices.

- 2023 router Top-1: 0.202003.
- 2023 router paired Top-1 difference vs Stage011: 0.000417 [-0.002922, 0.003756].
- 2023 router LL gain vs Stage011: 0.000638 [-0.001190, 0.002414].

## Verdict

NO-GO for champion replacement.

Stage016 improved 2023 Top-1 and log loss on reused development evidence, but it lost Top-1 in 2022 and was already below the prior promotion threshold. The Issue23 router did not produce a robust enough 2023 Top-1 improvement to justify replacing Stage011.

## Files

- `scripts/research/run_issue23_top1_winner_selection.py`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_TOP1_MODEL_SUMMARY.csv`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_TOP1_BY_YEAR.csv`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_TOP1_CI.csv`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_PAIRED_BOOTSTRAP.csv`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_ROUTER_POLICY.csv`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_PER_RACE_SELECTIONS.csv`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_STAGE011_TOP1_ERROR_SLICES.csv`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_CALIBRATION.csv`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_AUDIT.json`

## Reproduction Command

`python scripts/research/run_issue23_top1_winner_selection.py`

## Next Work

Do not run another learner comparison on the same feature set. A future approved experiment should require a specifically named non-market, point-in-time feature family with certified coverage, or a genuinely unexposed evaluation window.
