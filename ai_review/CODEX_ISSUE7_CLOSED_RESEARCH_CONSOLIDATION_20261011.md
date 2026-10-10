# CODEX Issue #7 Closed Research Consolidation

Status: **CLOSED / DOCUMENTATION ONLY / NO NEW EXPERIMENTS**

Repository state reviewed: PR #6 branch `codex/issue-5-winning-model-plan-20261010`, current head `b098c164` (`Repair Stage011 drift audit winner schema`).

This report consolidates the already closed EDGEiQ historical probability research record. No feature search, source inventory, fitting, scoring, backtest, profitability test, price-source inspection, or sealed-year access was performed for this report.

## Executive Decision

Stage011 remains the champion. Candidate B, the Stage016 HGB challenger, is preserved only as an unpromoted development challenger.

The decisive numerical reason is materiality: Candidate B's log-loss improvement against the frozen Stage011 champion is `0.002652764756`, below the required `0.005` gate. The evidence is reused 2022-2024 development evidence, not independent validation. No profitable betting model has been demonstrated.

## Evidence Classes

### Verified From Repository Artifacts

- Frozen Stage011 reproduction metrics and governance are recorded in `outputs/research/model_v2/stage011_reproduction/STAGE011_REPRODUCTION_REPORT.json` and summarized in `ai_review/CODEX_ISSUE5_FINAL_RESEARCH_DISPOSITION.md`.
- Issue #5 source-admission repair is documented in `ai_review/CODEX_ISSUE5_SOURCE_ADMISSION_REPAIR_20261010.md`.
- The final Issue #5 disposition is documented in `ai_review/CODEX_ISSUE5_FINAL_RESEARCH_DISPOSITION.md`.
- Stage011 calibration stop is documented in `ai_review/STAGE011_CALIBRATION_FINAL_DISPOSITION_20261010.md`.
- LAB239 dense-feature closure is documented by `outputs/research/profitability_program/lab239/LAB239_AUDIT.json` and `outputs/research/profitability_program/lab239/LAB239_FROZEN_ARCHITECTURE.json`.
- Historical price-source stops are documented in:
  - `ai_review/HISTORICAL_PRICE_SOURCE_INVENTORY_STOP_20261010.md`
  - `ai_review/PRICE_PATH_RESOLUTION_FINAL_20261010.md`
  - `ai_review/PRICE_RECOVERABLE_EXISTENCE_GATE_20261010.md`
  - `ai_review/PRICE_SEVEN_FILE_SCHEMA_GATE_FINAL_20261010.md`
- The Stage011 `y` schema repair and synthetic regression test are documented in `ai_review/CODEX_ISSUE5_STAGE011_DRIFT_AUDIT_SCHEMA_FIX.md`.

### User/Grok-Supplied Closure Findings Recorded Without Modification

- A-G is closed.
- Stage011 remains champion.
- Candidate B remains unpromoted.
- Schema audit passed.
- Reported log-loss gain is `0.002653`, below the `0.005` promotion gate.
- No newly named source with a certified point-in-time builder exists.
- 2022-2024 evidence is `REUSED_DEVELOPMENT`.
- 2025-2026 remain `SEALED`.
- Historical profitability is unknown because no certified executable pre-off price source exists.

### Unknown Or Not Independently Reverified In This Report

- This report did not rerun the real Stage011 score-file drift audit. The committed schema-fix document records `SCHEMA FIX READY` and synthetic-only test success; any separate real score-file audit result is treated as supplied governance context unless independently committed elsewhere.
- Original Stage023 console metrics are not present as a committed closure table in the reviewed Markdown artifacts. Stage023 is therefore summarized by its recorded disposition: HGB remained stronger than logit and random forest on reused-development evidence.
- No independent holdout or prospective window has been opened.
- No executable pre-off price authority has been certified.

## Stage011 Champion Record

Frozen Stage011 reproduction:

| Year | Races | Runners | Frozen Stage011 LL |
| ---: | ---: | ---: | ---: |
| 2022 | 612 | 7,459 | 2.125060402398 |
| 2023 | 2,396 | 30,163 | 2.131427427909 |
| 2024 | 2,402 | 31,234 | 2.102222925037 |

Weighted by race count, the frozen Stage011 LL is `2.117740582158`.

Stage011 is retained because no closed challenger satisfies the promotion criteria. It is still an unvalidated champion, not a demonstrated profitable strategy.

## Issue #5 A-G Candidate Comparison

The final controlling comparison is against the frozen Stage011 champion, not the internal Candidate A rerun.

| Candidate | Matrix / learner | Weighted LL | Delta LL vs frozen Stage011 | Weighted Brier | Weighted Top1 | Disposition |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Stage011 frozen | frozen Stage011 HGB | 2.117740582158 | 0.000000000000 | unavailable in frozen report | see frozen report | Champion retained |
| A | Stage011 35 / HGB rerun | 2.120390200509 | -0.002649618351 | 0.067466193587 | 0.217744916821 | Diagnostic only |
| B | Stage016 44 / HGB | 2.115087817402 | +0.002652764756 | 0.067403896689 | 0.218669131238 | Unpromoted challenger |
| C | Stage011 35 / logit | 2.334733326382 | -0.216992744223 | 0.069583111322 | 0.182809611830 | Reject |
| D | Stage011 35 / random forest | 2.208249910597 | -0.090509328439 | 0.068102730560 | 0.209611829945 | Reject |
| E | Stage016 44 / logit | 2.325458482852 | -0.207717900694 | 0.069470073971 | 0.185212569316 | Reject |
| F | Stage016 44 / random forest | 2.208453376654 | -0.090712794495 | 0.068034865305 | 0.208872458410 | Reject |
| G | B/E/F equal ensemble | 2.198333591407 | -0.080593009248 | 0.067807112979 | 0.223475046211 | Reject |

Candidate B year detail:

| Year | Frozen Stage011 LL | Candidate B LL | Delta LL |
| ---: | ---: | ---: | ---: |
| 2022 | 2.125060402398 | 2.122371860733 | +0.002688541666 |
| 2023 | 2.131427427909 | 2.127037120809 | +0.004390307100 |
| 2024 | 2.102222925037 | 2.101312477901 | +0.000910447136 |

Candidate B improves LL in sign across all three reused-development years, but the weighted gain is too small for promotion. The generated bake-off audit that labeled B as `PROMOTE_RESEARCH_CHALLENGER` is superseded because it compared B against the internal A rerun rather than the frozen Stage011 champion.

## Stage016 Context Route

Stage016 adds the predeclared current-race context family:

- `current_weight_kg`
- `weight_change_kg`
- `distance_change_metres`
- `abs_distance_change_metres`
- `prior_same_class_starts`
- `prior_exact_distance_starts_031`
- `context_authority_missing`
- `weight_change_missing`
- `distance_change_missing`

Source contract: `scripts/research/run_v2_stage016_context_family.py`.

Issue #5 repaired the sealed-year admission problem by creating manifest-admitted 2021-2024-only partitions for LAB026 clean placing history and LAB031 context. The repaired A-G evidence still does not justify promotion: the Stage016 HGB gain is `0.002652764756`, below the `0.005` gate. Stage016 remains viable as a reproducible, unpromoted challenger only.

## Stage023 Learner Route

Stage023 compared HGB, L2 logistic regression, and random forest on the Stage011 matrix. Source contract: `scripts/research/run_v2_stage023_learner_bakeoff.py`.

The closed record in `ai_review/VALIDATION_FIRST_STOP_20261009.md` states that Stage023 already compared those learner families and that logit and random forest lost in the reused development years. Issue #5 A-G is consistent with that closure: logit and random forest candidates C/D/E/F all lost materially to frozen Stage011.

No further learner comparison is authorised. Exact original Stage023 console metrics are not committed as a closure table in the reviewed evidence, so this report does not infer them.

## LAB239 Dense-Feature Route

LAB238C prepared a governed manifest:

- `input_manifest_fields`: 150
- `blocked_fields`: 12
- `final_lab239_fields`: 138
- `final_information_families`: 12
- `model_fitting`: false
- `market_as_feature`: false
- `profitability_testing`: false
- `decision`: `LINEAGE_GOVERNED_MANIFEST_READY`

LAB239 then tested the governed dense-feature families:

- rows: 53,804
- races: 5,508
- certified manifest fields: 138
- families tested: 12
- pre-holdout surviving families: none
- frozen architecture: `NO_CHALLENGER`
- frozen new fields: 0
- final decision: `NO_INCREMENTAL_INFORMATION_SIGNAL`
- market/final-SP/profitability used for selection: false
- production modified: false

LAB239 does not supply a frozen nonempty dense challenger. It remains closed.

## Connection-Count Route

The connection route is closed under the validation-first stop:

- LAB031 same-jockey and same-trainer counts reached exact match `90,235 / 91,434` (`98.69%`), but original builder proof, strict-prior/same-day exclusion, and independence from Stage008 were not established.
- LAB037 residuals were rejected because of EPI/fitted-performance leakage concerns.
- Stage008, Stage013, and Stage019 already explored connection families; no further connection variants are authorised.

The reviewed code confirms that connection-family scripts exist, including `scripts/research/run_v2_stage019_shrunk_connections.py`, but this report did not run or score them. The closure state is governance-based: no certified new connection feature family remains available for another experiment.

## Historical Price-Source Route

The price-source route is closed for current research.

Existing scoped gates establish:

- Initial displayed inventory found paths only and did not certify timestamps, odds type, race keys, runner keys, or executable price eligibility.
- Path-resolution diagnostic reported `TOTAL_DISTINCT=6783`, `EXCLUDED_SP_BSP=72`, `OUT_OF_SCOPE=6711`, and zero in-scope existence-confirmed candidates.
- Recoverable-path gate reported `RECOVERABLE=471`, `EXISTING=7`, `MISSING=464`, but existence was not price-source eligibility.
- Seven-file schema gate found `0/7` qualifying on authorised top-level schema/header inspection.

Disposition: no historical pre-off executable price source is certified. SP/BSP and final-SP diagnostics are not substitutes. Historical profitability remains unknown.

## Reopen Conditions

Do not reopen this research for another learner sweep, feature hunt, price archive search, or profitability test.

Research can be reopened only under one of these conditions:

1. A specifically named non-market feature or feature family exists with:
   - certified point-in-time builder;
   - source-admission manifest;
   - exact runner identity or certified alternative;
   - coverage check against the retained Stage011 universe;
   - no market, SP, BSP, odds, price, bet, stake, return, EPI leakage, model-output leakage, or outcome leakage;
   - no sealed-year access during development.
2. A genuinely unexposed evaluation window is formally unsealed by governance and evaluated once under a frozen protocol.

A future profitability test additionally requires a collision-free, timestamped, executable pre-off price source. No such source is currently certified.

## Outstanding Reproducibility And Reporting Issues

- The generated Issue #5 bake-off audit/reporting verdict is misleading because it promoted Candidate B against the Candidate A rerun rather than the frozen Stage011 baseline.
- Candidate A rerun differs from frozen Stage011 and should remain diagnostic only.
- The Stage011 drift-audit schema repair exists, but this report did not execute the real score-file audit.
- Stage023 original exact console metrics are not preserved in the reviewed closure docs.
- Local output directories contain large historical research artifacts that should not be interpreted as production integration.
- Candidate B must not be consumed by production or labeled champion.

## PR Recommendation

Do not merge PR #6 as a model-promotion PR.

Acceptable outcomes:

1. Merge as a research archive only if the PR is clearly labeled non-production, Stage011 remains champion, Candidate B is marked unpromoted, no profitability is claimed, and this closure report plus the Issue #5 final disposition control the interpretation.
2. Close the PR if the repository should avoid carrying rejected bake-off scripts and outputs.

There is no basis in the closed record to replace Stage011 or claim a winning betting model.
