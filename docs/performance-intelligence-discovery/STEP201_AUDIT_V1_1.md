# STEP201 Repository Census V1.1 Audit

- Generated UTC: 2026-07-27T18:08:48.776658+00:00
- Overall status: **PASS**

## Metrics

| Metric | Count |
|---|---:|
| First-pass assets | 18,692 |
| Canonical assets retained | 3,680 |
| Assets excluded | 15,012 |
| CSV assets | 3,680 |
| JSON assets | 3,680 |
| Duplicate asset IDs | 0 |
| Duplicate repository paths | 0 |
| Duplicate filenames | 844 |
| Forbidden-root assets | 0 |
| Forbidden-prefix assets | 0 |
| Missing inclusion reasons | 0 |
| Missing repository assets | 0 |
| Unknown lifecycle statuses | 1,247 |
| Datasets with unresolved producers | 1,087 |
| Assets with unresolved consumers | 3,627 |
| Structural failures | 0 |

## Findings

- Duplicate filenames across distinct paths: 844.
- Unknown lifecycle statuses: 1,247.
- Datasets with unresolved producers: 1,087.
- Assets with unresolved consumers: 3,627.

## Interpretation

Unknown producer, consumer and lifecycle status values remain permitted
forensic findings. Scope exclusions are governed separately through
the V1.1 exclusion ledger.
