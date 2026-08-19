# EDGEiQ Performance Recovery Current Status V2

Status: NORMALISATION_TEMPORAL_AUTHORITY_RESOLVED_OUTCOME_D_DOWNSTREAM_REBUILT_BLOCKED_BY_GOVERNANCE
Normalisation temporal authority: OUTCOME_D_HISTORICAL_NORMALISATION_REMAINS_UNAVAILABLE
Parameter derivation cutoff: 2026-07-20
Historical application authorised: NO
Build status: PASS
EPI release status: BLOCKED_EMPTY_GOVERNED_PUBLICATION_POPULATION

Row counts:
- horse_aggregate: 0
- horse_observation: 0
- horse_rating: 0
- length_conversion_parameter_v2: 5
- lengths_versus_standard: 13
- lengths_versus_standard_rejections: 4
- normalisation: 0
- normalisation_rejections: 13
- performance_base: 13
- projected_performance: 0
- race_entry_snapshot: 0
- race_time_delta: 17
- rating_base: 0

Remaining blockers:
- No earlier governed normalisation parameter exists for 2026-05-30/31 observations.
- HPR-NORM-A-v1 was derived from the 2026-07-20 bootstrap population and cannot be applied to May observations without future leakage.
- Four July Sandown race-time deltas still lack authoritative condition evidence.
- Canonical timed observation population is currently 39 rows, limiting race-time delta coverage to 17 rows.
- EPI publication cannot release with zero projected performance rows.
