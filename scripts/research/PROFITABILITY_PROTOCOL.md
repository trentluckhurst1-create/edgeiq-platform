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
- Standard-time governed downstream key: canonical track ID + distance + condition + jurisdiction; median; minimum 20 prior races; no trimming/winsorisation/outlier removal.
- Runner LVS algebra: race LVS minus finish margin. Positive is faster/better than standard. The historical producer used a flat 0.17 seconds/length; LAB245B intentionally uses the later governed surface/condition conversion authority.
- Centisecond conversion is fail-closed against official_race_time / 100.
- Governed surface/condition seconds-per-length parameters are frozen and checked before target construction.

Stage gates:
1. LAB245B1: predict next-race runner LVS. Architecture/model selection uses 2022-23 OOF only; 2024 is fixed confirmation.
2. LAB245B2: convert the selected performance forecast to race probabilities. Temperature is selected on 2022-23 only and fixed for 2024.
3. LAB245B3: final-SP betting forensics only. 2022 selects a policy; the same policy must confirm in 2023 and validate in 2024 with minimum volume.
4. LAB245B4: 2025-26 remains sealed unless LAB245B3 survives. On opening, architecture, hyperparameters, temperature and betting policy are frozen; no holdout reselection is allowed.

Final-SP limitation:
- LAB245B3/4 final-SP economics are historical forensic tests.
- They are not deployable betting claims.
- Any surviving policy must later be tested against actual timestamped pre-race offered odds.

LAB245B_HOLDOUT_RESELECTION=NO
LAB245B_HISTORICAL_LVS_AUTHORITY_AS_TARGET=NO
