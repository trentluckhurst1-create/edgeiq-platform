# EDGEiQ Horse Rating Parameter Provenance Decision V1

Status: EDGEIQ_PERFORMANCE_INTELLIGENCE_BLOCKED_BY_NORMALISATION_METHOD

## Decision Summary

- Identity governance source: recovered and validated from authoritative Racing.com payloads.
- Performance normalisation source: not recovered; methodological approval required.
- Horse performance aggregation source: not recovered; methodological approval required after normalisation is approved.

No normalisation or aggregation parameter candidate was built because doing so would require inventing centre/scale and aggregation policy values. That would violate the governance directive.

## Current First Blocking Stage

The first unresolved zero-row stage remains performance normalisation: the active formula cannot calculate `normalised_performance_value` without governed `centre_value` and `scale_value` rows.

## Production Safety

No pricing, probability, V6.1, V7.2G2, UI, EPI redesign, or production runner warehouse changes were made.
