# EDGEIQ Racing.com Cache Root Escape V1

Generated UTC: `2026-07-22T07:33:41.093084+00:00`

## Governance boundary

- Read-only forensic diagnostic.
- No network access.
- Production builder not executed.
- Builder not modified.
- Cache files not modified or moved.
- Governed outputs not modified.

## Path resolution

- Repository root: `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM`
- Builder `APP_ROOT`: `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM`
- Builder `PROJECT_ROOT`: `C:\Users\trent\OneDrive`
- Builder `RAW_CACHE`: `C:\Users\trent\OneDrive\outputs\sectionals\raw\VIC\racingcom_csv`
- Intended repository cache: `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\sectionals\raw\VIC\racingcom_csv`

## Path findings

- `PROJECT_ROOT` matches repository: **False**
- Builder cache matches intended cache: **False**
- Builder cache is inside repository: **False**

## Builder-resolved cache

- All files: **0**
- CSV files: **0**
- Unique CSV contents: **0**
- Parsed CSV files: **0**
- Parsed runner rows: **0**
- Complete distinct races: **0**

### Parser statuses

- No CSV files found.

## Intended repository cache

- All files: **0**
- CSV files: **0**
- Unique CSV contents: **0**
- Parsed CSV files: **0**
- Parsed runner rows: **0**
- Complete distinct races: **0**

### Parser statuses

- No CSV files found.

## Cross-root comparison

- Duplicate CSV contents across both roots: **0**

## Architectural interpretation

The production builder derives `PROJECT_ROOT` from `Path(__file__).resolve().parents[3]`.

For a builder stored under the repository `scripts` directory, this resolves above the EDGEIQ repository. Any output path derived from that value is therefore capable of escaping the governed repository boundary.

No remediation has been applied in this diagnostic.

## Decision

**CACHE_ROOT_ESCAPE_CONFIRMED**

## Artifacts

- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_cache_root_escape_ledger_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_cache_root_escape_v1.json`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_cache_root_escape_v1.md`
