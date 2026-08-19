# Racing.com Standard Time Ingestion V2 Migration Report

Built UTC: 2026-07-22T08:49:38+00:00

## Decision

- E2E status: `RACINGCOM_INGESTION_V2_E2E_PASS`
- Migration decision: `DO_NOT_MIGRATE_YET`
- Legacy decision: `LEGACY_REMAINS_DEPRECATED_AS_SOURCE_BUT_NOT_REMOVED`
- Production changed: `NO`
- UI changed: `NO`
- Pricing/probability/rating changed: `NO`

## Counts

- Meeting discovery rows: 186
- Race discovery rows: 52
- Admission rows: 52
- Acquisition queue rows: 12
- Historical proven CSV rows admitted: 8
- CSV acquisition rows: 8
- Valid CSV files acquired: 8
- Page discovery rows: 4
- Page CSV links observed: 0
- Parser runner rows: 80
- Warehouse rows: 80
- Warehouse races: 8

## Findings

V2 fixes the core defect: it no longer consumes the contaminated legacy calendar rows, no longer fabricates race numbers 1-12, and no longer constructs CSV URLs from unsupported assumptions. The governed chain retains all eight historical Racing.com CSV files that had explicit evidence and reproduces the legacy-good 80 runner rows with full provenance.

The chain is not ready to replace live acquisition yet because page discovery inspected the four evidence-based race pages that required discovery and found no direct CSV links or structured CSV payloads. That means V2 is safe as a governed warehouse/replay pipeline, but it does not yet prove fresh Racing.com CSV discovery for new races.

## Audit Summary

- PASS checks: 15
- WARN checks: 1
- FAIL checks: 0

See `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_ingestion_v2_e2e_regression_audit.csv` for the detailed audit ledger.
