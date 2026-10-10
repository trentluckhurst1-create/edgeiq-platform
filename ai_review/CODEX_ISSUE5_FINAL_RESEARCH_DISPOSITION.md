# CODEX Issue #5 Final Research Disposition

Status: **REJECT FURTHER EXPERIMENTS / RETAIN STAGE011**

Final decision:

- Stage011 remains the champion.
- Candidate B, Stage016 HGB, is preserved as a reproducible but **unpromoted** development challenger.
- No candidate is approved for promotion.
- All evidence is `REUSED_DEVELOPMENT`, not independent validation.
- No profitability, betting edge, SP/BSP/odds, or market-price claim has been demonstrated.

No new model fitting, scoring, learner swap, feature search, market investigation, or sealed-year access was performed for this disposition.

## Evidence Reviewed

Reviewed existing Issue #5 materials only:

- `ai_review/CODEX_WINNING_MODEL_PLAN_20261010.md`
- `ai_review/CODEX_ISSUE5_EXECUTION_GOVERNANCE_AUDIT_20261010.md`
- `ai_review/CODEX_ISSUE5_SOURCE_ADMISSION_REPAIR_20261010.md`
- `scripts/research/run_codex_issue5_bounded_bakeoff_20261010.py`
- `scripts/research/run_codex_issue5_source_partition_export_20261010.py`
- `outputs/research/codex_issue5_source_admission/*`
- `outputs/research/codex_issue5_winning_model/CODEX_BAKEOFF_MODEL_SUMMARY_20261010.csv`
- `outputs/research/codex_issue5_winning_model/CODEX_BAKEOFF_YEAR_METRICS_20261010.csv`
- `outputs/research/codex_issue5_winning_model/CODEX_BAKEOFF_MODEL_MANIFEST_20261010.csv`
- `outputs/research/codex_issue5_winning_model/CODEX_BAKEOFF_BOOTSTRAP_CI_20261010.csv`
- `outputs/research/codex_issue5_winning_model/CODEX_BAKEOFF_AUDIT_20261010.json`
- `outputs/research/model_v2/stage011_reproduction/STAGE011_REPRODUCTION_REPORT.json`

## Source Admission

The original Issue #5 execution was governance-invalid because it read mixed-year LAB026 rows before applying the 2024 cutoff. That result remains quarantined.

The later source repair created manifest-admitted 2021-2024 partitions:

| Source | Rows | Date bounds | SHA256 | Status |
| --- | ---: | --- | --- | --- |
| LAB026 clean placing partition | 149,242 | 2021-01-01 to 2024-12-31 | `efa216c87854c001560e672452a7f2a180f8477dc0ec96fc24f0e409d8fb251e` | PASS |
| LAB031 context partition | 109,946 | 2021-01-01 to 2024-12-31 | `3af6bd924b510267ae1b45a252b2aa6d9ea9b65d67084eac9e515cbdaf383c09` | PASS |

The repaired bake-off run used manifest-admitted partitions and records `market_access=false`, `profitability_tested=false`, and `sealed_2025_2026_access_in_successful_scoring=false`.

## Frozen Baseline

The frozen Stage011 reproduction report remains the governing baseline:

| Year | Races | Runners | Frozen Stage011 LL |
| ---: | ---: | ---: | ---: |
| 2022 | 612 | 7,459 | 2.125060402398 |
| 2023 | 2,396 | 30,163 | 2.131427427909 |
| 2024 | 2,402 | 31,234 | 2.102222925037 |

Weighted by race count, frozen Stage011 LL is:

`2.117740582158`

The bake-off output also contains an internal Candidate A rerun with weighted LL `2.120390200509`. That rerun is useful as a reproducibility diagnostic, but it is **not** the frozen Stage011 champion comparator for promotion.

## Candidate Comparison

Primary comparison against the frozen Stage011 baseline:

| Candidate | Matrix / learner | Weighted LL | Delta LL vs frozen Stage011 | Weighted Brier | Weighted Top1 | Disposition |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Stage011 frozen | frozen Stage011 HGB | 2.117740582158 | 0.000000000000 | unavailable in frozen report | see Stage011 report | Champion retained |
| A | Stage011 35 / HGB rerun | 2.120390200509 | -0.002649618351 | 0.067466193587 | 0.217744916821 | Diagnostic only |
| B | Stage016 44 / HGB | 2.115087817402 | +0.002652764756 | 0.067403896689 | 0.218669131238 | Unpromoted challenger |
| C | Stage011 35 / logit | 2.334733326382 | -0.216992744223 | 0.069583111322 | 0.182809611830 | Reject |
| D | Stage011 35 / random forest | 2.208249910597 | -0.090509328439 | 0.068102730560 | 0.209611829945 | Reject |
| E | Stage016 44 / logit | 2.325458482852 | -0.207717900694 | 0.069470073971 | 0.185212569316 | Reject |
| F | Stage016 44 / random forest | 2.208453376654 | -0.090712794495 | 0.068034865305 | 0.208872458410 | Reject |
| G | B/E/F equal ensemble | 2.198333591407 | -0.080593009248 | 0.067807112979 | 0.223475046211 | Reject |

Candidate B is the only challenger with a positive LL delta against frozen Stage011, but the improvement is `0.002652764756`, below the required `0.005` materiality threshold.

## Candidate B Year Detail

Candidate B improves LL in all three reused-development years, but not enough to clear the promotion rule:

| Year | Frozen Stage011 LL | Candidate B LL | Delta LL |
| ---: | ---: | ---: | ---: |
| 2022 | 2.125060402398 | 2.122371860733 | +0.002688541666 |
| 2023 | 2.131427427909 | 2.127037120809 | +0.004390307100 |
| 2024 | 2.102222925037 | 2.101312477901 | +0.000910447136 |

The improvement is stable in sign, but small. It is reused-development evidence only and does not justify champion replacement.

## Promotion Criteria

Candidate B failed the governing promotion criteria:

- Materiality: **FAIL**. Required weighted LL improvement was at least `0.005`; observed improvement versus frozen Stage011 was `0.002652764756`.
- Independent validation: **FAIL / unavailable**. All evidence is `REUSED_DEVELOPMENT`; no untouched holdout or future-period validation was used.
- Profitability: **not tested / not demonstrated**. No market prices, SP/BSP/odds, betting thresholds, staking, or return evidence were used.

Candidate B passed only weaker diagnostic checks:

- It beat frozen Stage011 LL in 2022, 2023, and 2024.
- It used manifest-admitted 2021-2024 source partitions.
- It preserved the Stage011 race/runner universe in the completed bake-off outputs.

These diagnostics preserve Candidate B as a reproducible research challenger, not a promoted model.

## Reporting Reconciliation

The generated `CODEX_BAKEOFF_AUDIT_20261010.json` reports `PROMOTE_RESEARCH_CHALLENGER` for Candidate B. That verdict is superseded by this disposition.

Reason: the generated promotion calculation compared Candidate B against the bake-off's internal Candidate A rerun rather than the frozen Stage011 champion baseline. Candidate B's delta versus rerun A is `0.005302383107`, but its delta versus frozen Stage011 is only `0.002652764756`.

There is also a reporting-code issue in `run_codex_issue5_bounded_bakeoff_20261010.py`: the promotion gate should use the frozen Stage011 reference metrics as the comparator and should not label the rerun Candidate A as the canonical Stage011 baseline when a frozen reproduction report is available.

## Research Limitations

- 2022-2024 are reused development years, not an untouched validation window.
- 2025-2026 remain sealed and were not accessed for this disposition.
- No historical executable pre-off price source was used; therefore no profitability claim exists.
- The logit, random forest, and equal ensemble candidates materially underperformed the frozen Stage011 baseline.
- Candidate B's signal is plausible but small, and it does not clear the predeclared improvement threshold.

## Conditions To Reopen Research

Issue #5 should not be reopened for another learner sweep on the same features.

Research may be reopened only if one of the following exists:

1. A specifically named non-market feature or feature family with:
   - certified point-in-time builder;
   - source-admission manifest;
   - coverage check against the Stage011 race/runner universe;
   - no market/SP/BSP/odds/price fields;
   - no access to sealed years during development.
2. A genuinely unexposed evaluation window that is formally unsealed by governance and evaluated once under a frozen protocol.

Previously rejected or closed routes remain closed unless separately reauthorised.

## Outstanding Issues

- The generated bake-off audit/reporting verdict is misleading and should not be used as the final Issue #5 decision.
- The reporting logic should be corrected before any future bake-off runner is reused.
- Large runner-score outputs exist locally as completed evidence, but the final disposition should be the controlling record.
- No production integration should consume Candidate B.

## PR Recommendation

Recommendation: **do not merge as a model-promotion PR**.

Two acceptable paths:

1. Merge only as a research archive if PR #6 is clearly labelled as non-production, Candidate B is marked unpromoted, and this final disposition is treated as the controlling report.
2. Close PR #6 if the repository should avoid carrying the repaired bake-off runner and development artifacts after a reject decision.

Do not merge anything that implies Candidate B replaces Stage011. Stage011 remains champion.
