# CODEX Issue #12 Grok Conditions Report

Date: 2026-10-11  
Branch: `codex/issue-12-grok-readiness-gates`  
Scope: readiness diagnostics and design-only protocol. No model fitting, scoring, market access, production change, or sealed-year access.

## Decision

**PASS for readiness review. NOT authorised for modelling.**

The Issue #10 local dataset was reused without rebuilding the 550,720-row PIT matrix. Grok's three requested conditions were measured and a fixed 2019-2020 historical evaluation protocol is now frozen for review.

## Commands

```powershell
cd C:\EDGEIQ_PROFITABILITY_RESEARCH
python -m py_compile .\scripts\research\run_issue12_grok_readiness_gates.py .\tests\test_issue12_grok_readiness_gates.py
python -m unittest .\tests\test_issue12_grok_readiness_gates.py
.\scripts\research\run_issue12_grok_readiness_gates.ps1
```

Equivalent direct command:

```powershell
cd C:\EDGEIQ_PROFITABILITY_RESEARCH
python .\scripts\research\run_issue12_grok_readiness_gates.py --issue10-dir outputs/research/issue10_pre2022_partition --out outputs/research/issue12_grok_readiness
```

## Horse Identity

All Issue #10 runner-partition rows used source `horse_code`; normalized-name fallback was not used.

| Identity method | Rows | Share |
|---|---:|---:|
| CODE | 678,857 | 100.000% |
| NORMALISED_NAME fallback | 0 | 0.000% |

Collision diagnostics:

| Collision type | Groups | Max group size |
|---|---:|---:|
| Normalized horse name maps to multiple horse codes | 632 | 3 codes |
| Horse code maps to multiple normalized names | 0 | 0 |
| Constructed horse key maps to multiple normalized names | 0 | 0 |
| Explicit row quarantine records | 0 |  |

Interpretation: source horse code is internally stable in this partition. Same-name/multiple-code groups exist, so name-only fallback would be unsafe, but the current partition did not rely on fallback. This is still a standalone source-key identity, not a certified Stage011 canonical crosswalk.

## Missingness

Eligible PIT rows: **550,720**.

| Cohort | Rows | Barrier missing | Weight missing | Distance missing | Jockey completely missing | Trainer completely missing |
|---|---:|---:|---:|---:|---:|---:|
| Train eligible complete years <=2018 | 465,622 | 2,810 (0.6035%) | 14 (0.0030%) | 0 | 70 (0.0150%) | 1,749 (0.3756%) |
| Sparse 2016 history-only | 3,927 | 0 | 0 | 0 | 0 | 0 |
| Eval 2019 | 26,652 | 313 (1.1744%) | 324 (1.2157%) | 0 | 313 (1.1744%) | 0 |
| Eval 2020 | 28,548 | 0 | 0 | 0 | 0 | 0 |
| Reused 2021, not independent | 25,971 | 0 | 0 | 0 | 0 | 0 |

Identity-name/code distinctions:

- Train cohort: jockey name missing but code present = 317; trainer name missing but code present = 4,892.
- Eval 2019: jockey name missing but code present = 1; trainer name missing but code present = 74.
- No cohort had missing jockey code with valid jockey name, or missing trainer code with valid trainer name.

Strict-prior history coverage:

| Year | Horse prior available | Trainer prior available | Jockey prior available |
|---:|---:|---:|---:|
| 2018 | 76.901% | 99.497% | 99.316% |
| 2019 | 86.331% | 99.692% | 98.552% |
| 2020 | 87.887% | 99.804% | 99.926% |
| 2021 | 86.762% | 99.777% | 99.792% |

## Field Consistency

Issue #12 rechecked the Issue #10 year counts against the PIT rows and runner-partition eligible starters. All years were internally consistent: eligible starters equals PIT rows equals runner-partition eligible starters for every emitted year.

Issue #10 race exclusions remain:

- `NOT_FLAT_PROVISIONAL`: 1,494 races.
- `NOT_EXACTLY_ONE_WINNER`: 503 races.
- `NOT_FLAT_PROVISIONAL|NOT_EXACTLY_ONE_WINNER`: 5 races.
- `NOT_FLAT_PROVISIONAL|NO_STARTERS|NOT_EXACTLY_ONE_WINNER`: 1 race.

Source-file coverage:

- Selected monthly files: 257.
- Read monthly files: 220.
- Empty-like/schema-less skipped files: 37.
- Missing years: 2011 and 2017.
- Sparse year: 2016, only 3,927 eligible starters.

Impact on strict-prior aggregates: 2011 and 2017 histories are absent, and sparse 2016 contributes only the limited January/February available data. Later prior aggregates are strict-date safe but inherit those source coverage gaps.

## Frozen Historical Experiment Protocol

Status: **DESIGN_ONLY_NO_FIT_NO_SCORE**

Training years:

`2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2012, 2013, 2014, 2015, 2018`

History-only sparse year:

`2016`

Excluded missing years:

`2011, 2017`

Evaluation years:

`2019` and `2020`, reported separately.

Excluded from independent evaluation:

`2021`; it may be reported only as reused development context if separately authorised.

Learner:

`HistGradientBoostingClassifier(loss="log_loss", learning_rate=0.05, max_leaf_nodes=5, l2_regularization=1.0, max_iter=200, random_state=42)`

Fixed non-market feature set:

- `field_size`
- `barrier`
- `barrier_position_pct`
- `distance_metres`
- `weight`
- Horse prior starts/wins/top3/rates/mean finish/days since last/no-prior flag.
- Trainer missing flag and prior starts/wins/top3/rates/no-prior flag.
- Jockey missing flag and prior starts/wins/top3/rates/no-prior flag.

Missing treatment:

- Use HGB native missing-value handling.
- Preserve explicit missing identity flags.
- Do not impute market, odds, SP/BSP, profitability or outcome values.

Probability and metrics:

- Convert raw model scores to softmax probabilities within each race.
- Every race probability mass must sum to 1 within `1e-12`.
- Report race log loss, runner Brier, top-1, top-3, MRR, winner rank, 10-bin calibration, and identity/field cohort coverage.

Stop criteria:

- Stop on any market/SP/BSP/odds column.
- Stop on any 2025-2026 access.
- Stop if evaluation race has anything other than one winner.
- Stop if race probability mass fails.
- Stop if any model is refit after observing 2019 or 2020 metrics.

## Remaining Hard Blockers

1. Independent Grok review is required before any fitting or scoring.
2. Source rights/permissible-use status still requires owner/Grok acceptance.
3. This remains a standalone historical source-key model; joining to Stage011 remains forbidden without canonical crosswalk certification.

## Generated Diagnostic Artifacts

- `outputs/research/issue12_grok_readiness/ISSUE12_GROK_CONDITIONS_SUMMARY.json`
- `outputs/research/issue12_grok_readiness/ISSUE12_HORSE_IDENTITY_METHODS.csv`
- `outputs/research/issue12_grok_readiness/ISSUE12_HORSE_IDENTITY_COLLISION_SUMMARY.csv`
- `outputs/research/issue12_grok_readiness/ISSUE12_HORSE_IDENTITY_COLLISION_EXAMPLES.csv`
- `outputs/research/issue12_grok_readiness/ISSUE12_MISSINGNESS_BY_YEAR_AND_COHORT.csv`
- `outputs/research/issue12_grok_readiness/ISSUE12_FIELD_CONSISTENCY.csv`
- `outputs/research/issue12_grok_readiness/ISSUE12_PRIOR_HISTORY_COVERAGE.csv`
- `outputs/research/issue12_grok_readiness/ISSUE12_FROZEN_PROTOCOL.json`

## Conclusion

Grok's readiness conditions are now measured and the experiment is frozen, but training remains unauthorised. The next step is independent Grok review of these diagnostics and the protocol.
