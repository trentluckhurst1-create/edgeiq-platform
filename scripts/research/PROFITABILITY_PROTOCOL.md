# EDGEiQ profitability research protocol

Goal: test whether pre-race EDGEiQ edges can be filtered into a repeatably profitable BET/PASS policy.

Rules:
- STRICT281 remains the frozen scientific reference.
- Production is not modified.
- Final SP and result are evaluation labels only.
- Final-SP POT is a historical forensic screen, not evidence that the same price was obtainable pre-race.
- A deployable profitability claim requires timestamped pre-race offered odds with nonnegative minutes-before-jump and identity-certified runner joins.
- Current timestamp-safe offered-odds evidence is sparse and must be reported separately from the long historical final-SP universe.
- Final SP is not a gate feature.
- Weight features are not attributed or interpreted.
- Canonical race and horse IDs remain strings.
- Same-day history must be point-in-time certified or excluded.

Historical evaluation:
- Development: 2021-2023
- Validation: 2024
- Pseudo-holdout: 2025-2026
- 2025-2026 is not called untouched because prior economics have already been inspected.
- True untouched confirmation requires later races not used in rule discovery.

Primary metrics:
- bets, wins, strike rate, profit, POT
- maximum drawdown and longest losing run
- year and odds-band stability
- comparison with ungated positive-edge and 100-percent-plus-overlay policies

Pre-race reliability concepts:
- evidence depth
- recent EPI quality
- low-tail / worst-run protection
- distance evidence
- performance stability
- peak staleness and recency
- HGB/logistic agreement when available
- model rank robustness
- missingness / extrapolation burden

Required compact runner extract:
_race, _horse, date/year, winner, final_sp, STRICT281 probability, component probabilities when available, model rank, field size, and governed reliability features.

A candidate is not promoted unless thresholds are fixed before pseudo-holdout evaluation and positive returns are not driven by one year, odds band, or a handful of winners.

PRODUCTION_MODIFIED=NO
MARKET_AS_FEATURE=NO
FINAL_SP_EVALUATION_ONLY=YES

DEPLOYABLE_POT_REQUIRES_PRE_RACE_OFFERED_ODDS=YES
FINAL_SP_POT_IS_FORENSIC_ONLY=YES

## LAB245B next-performance chain

Purpose: test whether forecasting actual next-race runner performance creates a more reliable probability architecture than direct winner fitting.

Data governance:
- Frozen warehouse authority: 879,784 rows; 416,143,437 bytes; SHA-256 bcdcef1c7cb9144feae5783ca2fa83b1dc2b8dc07a42ac31c31fd7bd12b53107.
- Historical 533,387-row runner-LVS authority is parity/reference evidence only because its production standard times used all-history observations.
- Forecasting labels are reconstructed with standards using races strictly before the target race date.
- Standard-time implementation key recovered from the original producer: canonical track ID + distance + condition + jurisdiction; median; minimum 20 prior races; no trimming/winsorisation/outlier removal. The grouping contract described track + distance + condition, while the actual producer index also keyed jurisdiction; LAB245B follows the executable producer contract and applies strict date-PIT history.
- Runner LVS algebra: race LVS minus finish margin. Positive is faster/better than standard. The historical producer used a governed flat 0.17 seconds/length; LAB245B1 baseline reproduces that 0.17 conversion so the only intentional target change is strict date-PIT benchmark construction. Condition-dependent conversion is reserved for a separately named challenger.
- Centisecond conversion is fail-closed against official_race_time / 100.
- Baseline seconds-per-length is frozen at the recovered producer value 0.17. Any surface/condition conversion experiment must be separately named and may not silently replace the baseline.

Stage gates:
1. LAB245B1: predict next-race runner LVS. Architecture/model selection uses 2022-23 OOF only; the challenger must beat the selected simple baseline separately in 2022 and 2023, pooled development, and fixed 2024 on MAE, RMSE and within-race Spearman.
2. LAB245B2: convert the selected performance forecast to race probabilities. Probability evaluation is restricted to races where B1-eligible runners cover the complete valid-target field; subset-field softmax is prohibited. Temperature is selected on 2022-23 only and fixed for 2024; ML probabilities must beat the simple baseline separately in 2022 and 2023, pooled development, and fixed 2024 on winner log loss and runner Brier, with at least 200 complete-field development races and 100 complete-field 2024 races.
3. LAB245B3: final-SP betting forensics only. 2022 selects a policy; the same policy must confirm in 2023 and validate in 2024 with minimum volume.
4. LAB245B4: 2025-26 remains sealed unless LAB245B3 survives. Opening requires an explicit manual holdout dispatch; normal workflow/local-chain execution cannot invoke B4. On opening, architecture, hyperparameters, temperature and betting policy are frozen; no holdout reselection is allowed.

Final-SP limitation:
- LAB245B3/4 final-SP economics are historical forensic tests.
- They are not deployable betting claims.
- Any surviving policy must later be tested against actual timestamped pre-race offered odds.

LAB245B_HOLDOUT_RESELECTION=NO
LAB245B_HISTORICAL_LVS_AUTHORITY_AS_TARGET=NO

### LAB245B rejection routing

- If LAB245B1 fails predictive survival, reject the mature-runner performance architecture as tested; do not rescue it by threshold mining or opening 2025-26.
- If LAB245B1 predictive metrics survive but complete-field coverage is inadequate, the next named challenger is LOW_HISTORY_FULL_FIELD_RECOVERY: explicitly model first starters and 1-2 prior-run horses using pre-race-only evidence, then repeat B1/B2 gates. Do not renormalise probabilities over partial fields.
- If LAB245B2 fails, reject the probability mapping/architecture before any betting-policy search.
- If LAB245B3 fails, do not open 2025-26; return to probability/reliability architecture rather than mine more final-SP thresholds.
- Feature-family mining after a rejection requires a separately named experiment and development-only selection.

LAB245B_PARTIAL_FIELD_SOFTMAX=PROHIBITED
LAB245B_LOW_HISTORY_RECOVERY_IF_COVERAGE_BLOCKS=YES
