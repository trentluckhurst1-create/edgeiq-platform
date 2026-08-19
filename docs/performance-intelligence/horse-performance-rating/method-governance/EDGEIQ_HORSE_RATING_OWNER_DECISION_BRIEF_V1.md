# EDGEiQ Horse Rating Owner Decision Brief V1

## Executive Summary

Current status: `EDGEIQ_PERFORMANCE_INTELLIGENCE_BLOCKED_BY_NORMALISATION_METHOD`

The horse identity governance source has been recovered and validated. Historical identities are mapped `24/24`, and the identity audit is `PASS`. Identity governance should not be revisited for the current 24 historical source identifiers.

The remaining blockers are methodological, not data-join blockers:

1. Performance normalisation methodology.
2. Historical horse-performance aggregation methodology.

No normalisation parameters, aggregation parameters, horse ratings, live projected performance values, EPI values, pricing, probability values, V6.1 values, V7.2G2 values, or UI outputs may be created until the product owner explicitly approves both methods.

## Current Blocker

The first unresolved zero-row stage is performance normalisation.

The active normalisation builder requires governed parameter rows containing `centre_value` and `scale_value`. Those values were not recovered from repository evidence, Git history, active config, or supporting reports. The active formula is recovered, but the governed parameter values and their approval provenance are not.

The aggregation builder is also blocked because its policy source is missing. Its executable formula branches are recovered, but the selected policy values are not.

## Verified Evidence

### Proven current counts

- Historical performance intelligence base rows: `168`
- Historical runner identities eligible for rating aggregation: `24`
- Horses/race-entry IDs with 5+ eligible segments: `24/24`
- Identity map coverage after recovery: `24/24`
- Normalisation parameter source rows: `0`
- Aggregation parameter source rows: `0`
- Normalisation fact rows: `0`
- Horse observation rows: `0`
- Horse aggregate rows: `0`
- Horse performance rating rows: `0`

### Active source files inspected

- `EDGEIQ_HORSE_RATING_GOVERNANCE_DECISION_PACKAGE_V1.md`
- `EDGEIQ_PERFORMANCE_NORMALISATION_METHOD_RECOVERY_V1.md`
- `EDGEIQ_HORSE_PERFORMANCE_AGGREGATION_METHOD_RECOVERY_V1.md`
- `scripts/build_edgeiq_performance_normalisation_fact_v1.py`
- `scripts/build_edgeiq_performance_rating_base_fact_v1.py`
- `scripts/build_edgeiq_horse_performance_aggregate_fact_v1.py`
- `contracts/performance-intelligence/edgeiq_performance_normalisation_parameter_fact_v1_contract.json`
- `contracts/performance-intelligence/edgeiq_horse_performance_aggregation_parameter_fact_v1_contract.json`
- `contracts/performance-intelligence/edgeiq_horse_performance_aggregate_fact_v1_contract.json`

## Raw Normalisation Input

| Field | Value |
|---|---|
| raw input field | `raw_performance_lengths` |
| raw input grain | one governed performance-intelligence base row per runner segment/result-derived performance observation carried from `edgeiq_lengths_versus_standard_fact_v1.csv` into `edgeiq_performance_intelligence_base_fact_v1.csv` |
| raw input sign convention | positive means `FASTER_THAN_STANDARD`; negative means `SLOWER_THAN_STANDARD`; zero is standard/par |
| raw input units | lengths versus governed standard time, using governed seconds-per-length conversion |
| observed minimum | `-12.342000` |
| observed maximum | `3.822000` |
| observed median | `0.000000` |
| observed p05 | `-2.478150` |
| observed p95 | `2.050200` |
| observed rows | `168` |
| grouping dimensions currently available in carried data | `race_date`, `race_key`, `track_name`, `official_distance_metres`, `standard_time_seconds`, `seconds_per_length`, source evidence hashes; upstream sectional/segment dimensions exist in prior facts but are not consumed by the active normalisation lookup |
| grouping dimensions consumed by active normalisation builder | effective date range, `normalisation_method`, `parameter_status` only |

## Normalisation Choices

### NORM-A: Historical Population Linear Centre and Scale

| Item | Decision Detail |
|---|---|
| option name | `NORM_A_HISTORICAL_POPULATION_LINEAR_CENTRE_SCALE_V1` |
| formula | `normalised_performance_value = (raw_performance_lengths - centre_value) / scale_value` |
| parameters required | `centre_value`, `scale_value`, `normalisation_model_version`, `parameter_status`, `effective_from_date`, `effective_to_date`, `evidence_reference`, `evidence_sha256` |
| grouping dimensions | governed historical population; active builder currently supports global/effective-date lookup only unless extended |
| minimum sample requirement | not recovered; must be owner-approved before parameter creation |
| output scale | unitless normalised performance value; positive remains better if `scale_value` is positive |
| centre value | not recovered; owner must approve how this is calculated from the governed historical population |
| better-performance direction | higher is better when `scale_value > 0` because positive raw lengths are faster than standard |
| missing-group behaviour | active builder fails if no available parameter covers the race date; no fallback is recovered |
| outlier treatment | none recovered in active builder; any trimming, winsorisation, robust centre, or robust spread rule requires owner approval as part of the parameter provenance |
| advantages | compatible with the active normalisation contract; keeps ratings comparable on a single scale; transparent linear interpretation; easiest path to unblock without redesign |
| disadvantages | current 168 rows are too small to certify a stable production population by themselves; global normalisation may under-handle surface/distance/class differences |
| risks | if centre/scale are approved from a weak population, ratings may be unstable or biased; no recovered outlier protection exists in code |
| impact with current 168 rows | can technically cover the 168 base rows once approved parameters exist, but the current population should be treated as insufficient for production-grade parameter derivation without owner waiver or larger source population |
| implementation complexity | low if owner approves global/effective-date parameters; no builder redesign required |
| status | `SUPPORTED NEW METHODOLOGY`; formula is recovered, values/provenance are not |

### NORM-B: Segment-Class Linear Centre and Scale

| Item | Decision Detail |
|---|---|
| option name | `NORM_B_SEGMENT_CLASS_LINEAR_CENTRE_SCALE_V1` |
| formula | `normalised_performance_value = (raw_performance_lengths - centre_value[group]) / scale_value[group]` |
| parameters required | all NORM-A parameters plus owner-approved grouping keys and grouped centre/scale provenance |
| grouping dimensions | segment, distance, surface, class, condition, or benchmark-group buckets as approved by owner; these are conceptually available upstream but not consumed by the current parameter-source contract or active lookup |
| minimum sample requirement | not recovered; must be owner-approved per group before parameter creation |
| output scale | unitless grouped normalised performance value |
| centre value | not recovered; owner must approve grouped centre calculation |
| better-performance direction | higher is better when every group `scale_value > 0` |
| missing-group behaviour | not recovered; active code has no grouped fallback path; owner must approve fallback hierarchy before implementation |
| outlier treatment | not recovered; any group-level trimming or robust spread rule requires owner approval |
| advantages | better comparability across materially different race types if groups are well populated; future-scalable when historical population is large |
| disadvantages | not directly supported by the current active lookup; sparse groups can destabilise ratings; needs schema and builder extension |
| risks | with only 168 current rows, grouped parameters would be fragile; missing-group fallback could introduce hidden bias if not governed |
| impact with current 168 rows | poor as a production parameter source; likely too sparse for segment/class buckets |
| implementation complexity | high; requires owner approval plus contract/builder changes before use |
| status | `SUPPORTED NEW METHODOLOGY` in the decision package, but not a recovered existing semantic and not compatible with the current active lookup without extension |

### NORM-C: Direct Raw-Length Aggregate

| Item | Decision Detail |
|---|---|
| option name | `NORM_C_DIRECT_RAW_LENGTH_AGGREGATE_V1` |
| formula | skip normalisation; aggregate `raw_performance_lengths` directly |
| parameters required | replacement rating-base and aggregation semantics would need approval; current normalisation parameters would not be used |
| grouping dimensions | none recovered |
| minimum sample requirement | not recovered |
| output scale | raw lengths versus standard |
| centre value | not applicable |
| better-performance direction | higher raw lengths are better |
| missing-group behaviour | not applicable to normalisation, but downstream behaviour is unrecovered |
| outlier treatment | none recovered |
| advantages | simple to explain in raw lengths |
| disadvantages | contradicts the active normalisation/rating-base chain; bypasses `DIRECT_NORMALISED_PERFORMANCE_VALUE`; not permitted under the current recovery directive |
| risks | would redesign the EPI/horse-rating method and weaken comparability across contexts |
| impact with current 168 rows | could only be a new research method, not a recovered governed method |
| implementation complexity | high because active builders/contracts would need redesign |
| status | `UNSUPPORTED` for this directive; package marks it as new methodology requiring active builder redesign |

## Aggregation Grain

Active grain: `ROLLING_HORSE_AS_OF_DATE_RATING_FACT`

The aggregate fact contract defines one row per canonical horse, as-of date, and effective aggregation parameter when minimum observations are met.

The active aggregation builder groups observations by `canonical_horse_id`. Unique observation race dates become aggregate as-of dates. For each as-of date, eligible observations for that horse are selected by:

1. `rating_status = OBSERVED_NORMALISED_GOVERNED`
2. `identity_status = IDENTIFIED_GOVERNED`
3. observation `race_date` within the governed lookback window
4. observation `race_date <= aggregate_as_of_date` in the historical aggregate builder
5. newest observations included up to `maximum_observations`
6. minimum observation count must be met

Important predictive rule: for predictive use against a target race, only observations strictly prior to the target race may contribute. Same-race observations must not be used as predictive features.

The downstream rating fact builder then uses:

`horse_performance_rating_value = aggregate_rating_value`

with method:

`DIRECT_HISTORICAL_AGGREGATE_VALUE`

This means the rating value is directly inherited from the governed aggregate. It does not prove that the aggregate is a simple average; the active aggregate code proves the supported aggregate branches below.

## Aggregation Choices

### AGG-A: Arithmetic Mean Historical Average

| Item | Decision Detail |
|---|---|
| option name | `AGG_A_ARITHMETIC_MEAN_HISTORICAL_AVERAGE_V1` |
| formula | `aggregate_rating_value = sum(rating_base_value) / count(included_observations)` |
| minimum observations | not recovered; owner must approve |
| maximum observations | not recovered; owner must approve |
| lookback window | not recovered; owner must approve |
| recency treatment | `NONE`; every included observation has weight `1` |
| best-run treatment | none recovered; best runs are not specially selected or boosted |
| poor-run treatment | none recovered; poor runs are included equally if eligible |
| surface treatment | none in active aggregate builder; upstream standard-time/performance chain carries surface context |
| distance treatment | none in active aggregate builder; upstream standard-time/performance chain carries distance context |
| as-of-date rule | historical aggregate uses observations on or before the aggregate as-of date; predictive consumers must use only aggregate dates strictly before target race |
| advantages | stable, simple, transparent, low variance if observation counts are sufficient |
| disadvantages | slow to respond to improving/declining form; sensitive to stale form if lookback is broad; one-off poor/good runs remain in the mean |
| risks | if minimum observations or lookback are poorly chosen, ratings can become stale or noisy |
| expected current coverage | up to 24 horses / 168 observations if approved windows and minimums fit current data; exact coverage depends on owner-approved `minimum_observations`, `maximum_observations`, and `lookback_days` |
| implementation complexity | low once parameter source is approved; active builder supports it |
| status | recovered executable semantic for formula branch; policy values unrecovered |

### AGG-B: Recency-Weighted Arithmetic Mean With Exponential Half-Life

| Item | Decision Detail |
|---|---|
| option name | `AGG_B_WEIGHTED_ARITHMETIC_MEAN_EXPONENTIAL_HALF_LIFE_V1` |
| formula | `aggregate_rating_value = sum(rating_base_value * weight) / sum(weight)`, where `weight = 0.5 ** (age_days / recency_half_life_days)` |
| minimum observations | not recovered; owner must approve |
| maximum observations | not recovered; owner must approve |
| lookback window | not recovered; owner must approve |
| recency treatment | exponential half-life; newer observations receive larger weight |
| best-run treatment | none recovered; best runs are not specially selected or boosted |
| poor-run treatment | none recovered; poor runs are included with recency weighting if eligible |
| surface treatment | none in active aggregate builder; upstream standard-time/performance chain carries surface context |
| distance treatment | none in active aggregate builder; upstream standard-time/performance chain carries distance context |
| as-of-date rule | historical aggregate uses observations on or before the aggregate as-of date; predictive consumers must use only aggregate dates strictly before target race |
| advantages | balances stability with responsiveness; handles improving/declining form better than a flat average; supported by active builder |
| disadvantages | requires owner-approved half-life; still sensitive to outliers, especially recent outliers; less immediately transparent than simple average |
| risks | too-short half-life can overreact; too-long half-life behaves like simple average; current small population cannot prove optimal half-life |
| expected current coverage | up to 24 horses / 168 observations if approved windows and minimums fit current data; exact coverage depends on owner-approved policy values |
| implementation complexity | low to medium once parameter source is approved; active builder supports it |
| status | recovered executable semantic for formula branch; policy values unrecovered |

### Unsupported Aggregation Alternatives

| Option | Status | Reason |
|---|---|---|
| simple historical average | supported as `AGG_A_ARITHMETIC_MEAN_HISTORICAL_AVERAGE_V1` |
| median | `UNSUPPORTED` | no median branch exists in the active builder or decision package |
| best-N | `UNSUPPORTED` | no best-N selection branch exists in the active builder or decision package |
| recency-weighted average | supported as `AGG_B_WEIGHTED_ARITHMETIC_MEAN_EXPONENTIAL_HALF_LIFE_V1` |
| recency-weighted best-N | `UNSUPPORTED` | no best-N selection branch exists in the active builder or decision package |
| trimmed mean / winsorised mean | `UNSUPPORTED` | no outlier-trimming branch exists in the active builder or decision package |

## Combined Methodology Comparison

| Normalisation Option | Aggregation Option | Compatibility | Rating Scale | Rating Interpretation | Stability | Responsiveness | Outlier Sensitivity | Debutant Handling | Lightly Raced Handling | Current Expected Horse-Rating Coverage | Future Scalability |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NORM-A | AGG-A | valid with current contracts after owner-approved parameter rows | global linear normalised unit | average governed performance versus population centre | high if lookback/minimums are sensible | low to medium | medium to high; no outlier rule recovered | no rating until minimum observations are met | depends on owner-approved minimum observations | up to 24 horses if policy permits; otherwise lower | good, but may need grouped normalisation later |
| NORM-A | AGG-B | valid with current contracts after owner-approved parameter rows | global linear normalised unit | recency-weighted governed performance versus population centre | medium to high | medium to high | medium to high; recent outliers carry more weight | no rating until minimum observations are met | depends on owner-approved minimum observations and half-life | up to 24 horses if policy permits; otherwise lower | good; best current balance without redesign |
| NORM-B | AGG-A | conditionally valid only after owner-approved contract/builder extension | grouped linear normalised unit | average governed performance versus group centre | high if groups are well populated | low to medium | medium to high | no rating until minimum observations are met | likely lower coverage due grouped source requirements | poor with current 168 rows; future coverage depends on larger historical population | strong later, weak now |
| NORM-B | AGG-B | conditionally valid only after owner-approved contract/builder extension | grouped linear normalised unit | recency-weighted governed performance versus group centre | medium | high | medium to high; recent outliers carry more weight | no rating until minimum observations are met | likely lower coverage due grouped source requirements | poor with current 168 rows; future coverage depends on larger historical population | strong later, most complex |
| NORM-C | AGG-A or AGG-B | rejected | raw lengths | raw-length aggregate rather than recovered normalised rating-base value | unknown | unknown | high | unknown | unknown | not valid for current directive | requires redesign |
| NORM-A or NORM-B | median / best-N / recency-weighted best-N | rejected | not applicable | not supported by active builder | not applicable | not applicable | not applicable | not applicable | not applicable | not applicable | requires new aggregation methodology and builder redesign |

## Recommended Combination

### NORMALISATION METHOD

`NORM_A_HISTORICAL_POPULATION_LINEAR_CENTRE_SCALE_V1`

Status: `RECOMMENDED - OWNER APPROVAL REQUIRED`

Rationale: this is the only normalisation path that preserves the recovered active formula and can be implemented without changing the current normalisation contract. It supports comparability across performances, has transparent interpretation, and can scale to larger historical populations. The current 168 rows should not be treated as sufficient production provenance by themselves unless the owner explicitly approves that limitation.

### AGGREGATION METHOD

`AGG_B_WEIGHTED_ARITHMETIC_MEAN_EXPONENTIAL_HALF_LIFE_V1`

Status: `RECOMMENDED - OWNER APPROVAL REQUIRED`

Rationale: this is supported by the active aggregate builder and offers the best balance between stability and responsiveness. It keeps the calculation evidence-first, avoids best-run cherry-picking, uses only prior/as-of observations for predictive consumers, and responds better to improving or declining form than a flat average. It still needs owner-approved values for minimum observations, maximum observations, lookback window, and half-life.

## Implementation Consequences

If the owner approves NORM-A and AGG-B:

1. Create `config/performance-intelligence/edgeiq_performance_normalisation_parameter_source_v1.csv` with approved centre/scale values and provenance.
2. Create `config/performance-intelligence/edgeiq_horse_performance_aggregation_parameter_source_v1.csv` with approved aggregation policy values and provenance.
3. Re-run the existing governed builders in order.
4. Confirm no same-race or future observations are used by predictive consumers.
5. Re-audit the row funnel before any live projection, EPI, or downstream use.

If the owner selects NORM-B, a contract/builder extension is required before parameter creation because the active normalisation lookup does not currently consume grouped dimensions.

If the owner selects NORM-C, active method redesign is required and the option is outside this recovery directive.

No horse rating production promotion should occur from this brief alone.

## Exact Approval Block

```text
EDGEIQ HORSE PERFORMANCE RATING METHODOLOGY APPROVAL

NORMALISATION METHOD:
[OWNER SELECT: NORM_A_HISTORICAL_POPULATION_LINEAR_CENTRE_SCALE_V1 recommended / NORM_B_SEGMENT_CLASS_LINEAR_CENTRE_SCALE_V1 requires builder extension / NORM_C_DIRECT_RAW_LENGTH_AGGREGATE_V1 unsupported for current recovery]

NORMALISATION VERSION:
[OWNER SELECT: e.g. HPR-NORM-A-v1]

NORMALISATION GROUPING:
[OWNER SELECT: recommended GLOBAL_ALL_GOVERNED_HISTORICAL_PERFORMANCE_POPULATION for NORM-A; grouped surface/distance/class buckets require NORM-B builder extension]

NORMALISATION FORMULA:
normalised_performance_value = (raw_performance_lengths - centre_value) / scale_value

NORMALISATION MISSING-GROUP RULE:
[OWNER SELECT: recommended FAIL_CLOSED_NO_FALLBACK_UNLESS_APPROVED]

AGGREGATION METHOD:
[OWNER SELECT: AGG_B_WEIGHTED_ARITHMETIC_MEAN_EXPONENTIAL_HALF_LIFE_V1 recommended / AGG_A_ARITHMETIC_MEAN_HISTORICAL_AVERAGE_V1 supported]

AGGREGATION VERSION:
[OWNER SELECT: e.g. HPR-AGG-B-v1]

MINIMUM OBSERVATIONS:
[OWNER SELECT VALUE]

MAXIMUM OBSERVATIONS:
[OWNER SELECT VALUE OR UNLIMITED]

LOOKBACK WINDOW:
[OWNER SELECT VALUE IN DAYS]

RECENCY RULE:
[OWNER SELECT: recommended EXPONENTIAL_HALF_LIFE with owner-approved recency_half_life_days for AGG-B; NONE for AGG-A]

OUTLIER RULE:
[OWNER SELECT: active builder currently has no outlier treatment; any trimming/winsorisation/robust rule requires explicit approval and may require builder extension]

SURFACE RULE:
[OWNER SELECT: active aggregate builder applies no surface-specific treatment; surface comparability must be governed upstream or approved as a future extension]

DISTANCE RULE:
[OWNER SELECT: active aggregate builder applies no distance-specific treatment; distance comparability must be governed upstream or approved as a future extension]

AS-OF-DATE RULE:
Only observations strictly prior to the target race may contribute.

STATUS:
OWNER APPROVED
```
