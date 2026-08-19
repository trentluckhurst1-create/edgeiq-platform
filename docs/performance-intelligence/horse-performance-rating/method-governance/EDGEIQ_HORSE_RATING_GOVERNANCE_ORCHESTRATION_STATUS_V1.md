# EDGEiQ Horse Rating Governance Orchestration Status V1

Status: EDGEIQ_PERFORMANCE_INTELLIGENCE_BLOCKED_BY_NORMALISATION_METHOD

## Gate Order

1. Historical PI base: PASS (168 rows)
2. Performance normalisation parameter source: BLOCKED (governed source rows not recovered)
3. Performance normalisation fact: BLOCKED (0 rows)
4. Performance rating base fact: BLOCKED (0 rows)
5. Horse identity map: PASS (24 rows recovered and validated)
6. Horse observations: BLOCKED (0 rows; waits on rating base)
7. Horse aggregates: BLOCKED (0 rows; waits on observations and aggregation parameters)
8. Horse performance ratings: BLOCKED (0 rows)
9. Live projection/EPI downstream: BLOCKED by horse performance rating fact

## Do Not Run Downstream

Do not rebuild live projected performance, EPI, pricing, probability, V6.1, V7.2G2, or UI from this chain until owner-approved normalisation and aggregation parameter sources exist.
