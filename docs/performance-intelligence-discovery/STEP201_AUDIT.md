# STEP201 Repository Performance Intelligence Census Audit

- Generated UTC: 2026-07-27T17:24:51.259560+00:00
- Overall status: **PASS**

## Metrics

| Metric | Count |
|---|---:|
| CSV assets | 18,692 |
| JSON assets | 18,692 |
| Duplicate asset IDs | 0 |
| Duplicate repository paths | 0 |
| Duplicate file names | 4,185 |
| Unknown domains | 0 |
| Unknown statuses | 8,216 |
| Datasets with unresolved producers | 4,441 |
| Assets with unresolved consumers | 18,598 |
| Builders without inferred outputs | 4,761 |
| Fully orphaned datasets | 4,402 |
| Missing referenced repository assets | 0 |
| Structural failures | 0 |

## Findings

- Duplicate file names across different paths: 4,185.
- Unknown domains requiring later classification: 0.
- Unknown statuses requiring later classification: 8,216.
- Datasets with unresolved producers: 4,441.
- Assets with unresolved consumers: 18,598.
- Builders without inferred outputs: 4,761.
- Datasets with neither inferred producer nor consumer: 4,402.

## Governance Interpretation

Unknown producers, consumers, domains and statuses are permitted discovery findings.
They must remain explicit and must not be replaced with assumptions.
