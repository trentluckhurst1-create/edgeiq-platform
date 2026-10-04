# EDGEiQ profitability research protocol

Goal: test whether pre-race EDGEiQ edges can be filtered into a repeatably profitable BET/PASS policy.

Rules:
- STRICT281 remains the frozen scientific reference.
- Production is not modified.
- Final SP and result are evaluation labels only.
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
