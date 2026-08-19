# EDGEiQ Performance Intelligence
## Phase 1.0 Raw Warehouse Snapshot and Reproducibility Audit

Generated UTC: `2026-07-15T18:45:48.583183+00:00`

Snapshot ID: `eiq_warehouse_snapshot_3bc4b51211e159279ddaf32c48cc2b97`

Status: **SNAPSHOT_REPRODUCIBILITY_FAIL**

## Snapshot assets

- Canonical performances: **879,784**
- Canonical sectional evidence: **103,766**
- Performance date coverage: **2000-08-02 to 2026-06-24**
- Sectional date coverage: **2023-01-01 to 2026-06-04**

## Mandatory checks

| Check | Passed | Observed |
|---|---|---|
| PERFORMANCE_SCHEMA | True | NO_MISSING_COLUMNS |
| SECTIONAL_SCHEMA | True | NO_MISSING_COLUMNS |
| PERFORMANCE_PRIMARY_KEY_UNIQUE | False | duplicates=89;blank=0 |
| SECTIONAL_PRIMARY_KEY_UNIQUE | True | duplicates=0;blank=0 |
| PERFORMANCE_REQUIRED_VALUES | True | {} |
| SECTIONAL_REQUIRED_VALUES | True | {} |
| PERFORMANCE_ID_REPRODUCIBILITY | True | reproducible=879784;mismatches=0;unresolved=0 |
| SECTIONAL_ID_REPRODUCIBILITY | True | reproducible=103766;mismatches=0;unresolved=0 |
| SOURCE_HASH_REPRODUCIBILITY | True | stored=c29c69c378fdb6a5c4b794946722a28653927e1d680045d8607f0fda740e4192;actual=c29c69c378fdb6a5c4b794946722a28653927e1d680045d8607f0fda740e4192 |
| SECTIONAL_PERFORMANCE_FOREIGN_KEY | True | matched=103766;missing=0 |
| QUALITY_STATE_CONTRACT | True | {"performance_unknown_states": [], "sectional_unknown_states": [], "status": "PASS"} |

## Production state

Production data was not modified.

This snapshot remains a governed prototype until an explicit promotion phase passes.
