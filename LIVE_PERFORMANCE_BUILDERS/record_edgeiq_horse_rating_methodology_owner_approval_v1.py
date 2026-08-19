from __future__ import annotations
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating" / "method-governance" / "EDGEIQ_HORSE_RATING_METHODOLOGY_OWNER_APPROVAL_V1.md"
CONTENT = """# EDGEiQ Horse Rating Methodology Owner Approval V1

Approval status: OWNER APPROVED

## Approved Methods

- Normalisation method: NORM_A_HISTORICAL_POPULATION_LINEAR_CENTRE_SCALE_V1
- Normalisation executable method: LINEAR_CENTRE_AND_SCALE
- Normalisation version: HPR-NORM-A-v1
- Aggregation method: AGG_B_WEIGHTED_ARITHMETIC_MEAN_EXPONENTIAL_HALF_LIFE_V1
- Aggregation executable method: WEIGHTED_ARITHMETIC_MEAN
- Aggregation version: HPR-AGG-B-v1

## Complete Formal Approval Block

```text
EDGEIQ HORSE PERFORMANCE RATING METHODOLOGY APPROVAL

NORMALISATION METHOD:
NORM_A_HISTORICAL_POPULATION_LINEAR_CENTRE_SCALE_V1

NORMALISATION VERSION:
HPR-NORM-A-v1

NORMALISATION GROUPING:
GLOBAL_ALL_GOVERNED_HISTORICAL_PERFORMANCE_POPULATION

NORMALISATION FORMULA:
normalised_performance_value =
(raw_performance_lengths - centre_value) / scale_value

CENTRE CALCULATION:
Arithmetic mean of all eligible governed historical
raw_performance_lengths observations in the approved parameter population.

SCALE CALCULATION:
Population standard deviation of all eligible governed historical
raw_performance_lengths observations in the approved parameter population.

PARAMETER POPULATION:
All eligible governed historical Performance Intelligence base observations
available at parameter build time that pass the existing source, identity,
race, surface, distance, temporal and evidence audits.

MINIMUM PARAMETER POPULATION:
100 eligible governed observations.

CURRENT BOOTSTRAP POPULATION:
The currently governed 168 eligible observations are explicitly approved
as the HPR-NORM-A-v1 bootstrap parameter population.

BOOTSTRAP GOVERNANCE:
The 168-row population is approved to activate the governed architecture.
It is not to be silently recalibrated on every normal production run.

Parameter values must be generated once from the governed bootstrap
population, versioned, hashed, audited and promoted as an immutable
effective-dated parameter set.

Future recalibration requires:
- a new candidate parameter version;
- a population audit;
- comparison against the active version;
- deterministic testing;
- explicit governed promotion;
- no retroactive mutation of HPR-NORM-A-v1.

NORMALISATION MISSING-PARAMETER RULE:
FAIL_CLOSED_NO_FALLBACK_UNLESS_APPROVED

NORMALISATION DIRECTION:
Higher normalised values represent better performance.

NORMALISATION OUTLIER RULE:
NONE_IN_HPR_NORM_A_V1

Do not trim, winsorise, cap or otherwise alter eligible observations.
Retain transparent provenance and allow later methodology versions to
introduce separately approved robust treatment if required.

NORMALISATION SCALE SAFETY:
scale_value must be finite and strictly greater than zero.
If it is zero, null, non-finite or invalid, fail closed.

AGGREGATION METHOD:
AGG_B_WEIGHTED_ARITHMETIC_MEAN_EXPONENTIAL_HALF_LIFE_V1

AGGREGATION VERSION:
HPR-AGG-B-v1

AGGREGATION FORMULA:
aggregate_rating_value =
sum(rating_base_value * observation_weight)
/
sum(observation_weight)

where:

observation_weight =
0.5 ** (age_days / recency_half_life_days)

MINIMUM OBSERVATIONS:
5

MAXIMUM OBSERVATIONS:
20

OBSERVATION SELECTION:
The 20 most recent eligible governed observations within the lookback
window, ordered deterministically by observation date and canonical source key.

LOOKBACK WINDOW:
730 days

RECENCY HALF-LIFE:
120 days

RECENCY INTERPRETATION:
An otherwise equivalent performance 120 days old receives half the
weight of a performance occurring on the aggregate as-of date.

BEST-RUN RULE:
No special best-run selection or boosting.

POOR-RUN RULE:
Eligible poor performances remain included under the same recency rule.

OUTLIER RULE:
NONE_IN_HPR_AGG_B_V1

SURFACE RULE:
No additional surface weighting in the horse aggregation layer.
Surface governance and comparability remain upstream in Standard Time,
Lengths v Standard and the governed performance construction chain.

DISTANCE RULE:
No additional distance weighting in the horse aggregation layer.
Distance governance and comparability remain upstream.

AS-OF-DATE RULE:
Historical aggregate construction may use observations on or before its
historical aggregate as-of date as required by the existing fact contract.

For every live predictive use:
only observations and rating facts strictly prior to the target race
date and time may contribute.

Same-race and future information are prohibited.

DEBUTANT RULE:
No fabricated rating.

LIGHTLY RACED RULE:
No horse rating until the approved minimum of five eligible observations
is satisfied.

MISSING-HISTORY RULE:
Return an explicit governed availability status rather than zero,
field average, market substitution or manual estimate.

STATUS:
OWNER APPROVED
```

## Approval Summary

- Approved population rule: GLOBAL_ALL_GOVERNED_HISTORICAL_PERFORMANCE_POPULATION.
- Bootstrap waiver: the governed 168-row bootstrap population is approved only for HPR-NORM-A-v1 activation and must not be silently recalibrated.
- Minimum population: 100 eligible governed observations.
- Normalisation formula: `(raw_performance_lengths - centre_value) / scale_value`.
- Centre calculation: arithmetic mean over the approved bootstrap population.
- Scale calculation: population standard deviation over the approved bootstrap population.
- Aggregation formula: weighted arithmetic mean using exponential half-life weights.
- Minimum observations: 5.
- Maximum observations: 20.
- Lookback: 730 days.
- Half-life: 120 days.
- Outlier policy: NONE for HPR-NORM-A-v1 and HPR-AGG-B-v1.
- Surface policy: no additional aggregation-layer surface weighting.
- Distance policy: no additional aggregation-layer distance weighting.
- Temporal policy: live predictive use must be strictly prior to target race date/time.
- Recalibration policy: new candidate version, audit, comparison, testing, governed promotion, no retroactive mutation.
- Fail-closed rules: no fallback parameters, no fabricated ratings, no zero/field-average/market substitution.
"""
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(CONTENT, encoding="utf-8")
print(f"approval_document={OUT}")
