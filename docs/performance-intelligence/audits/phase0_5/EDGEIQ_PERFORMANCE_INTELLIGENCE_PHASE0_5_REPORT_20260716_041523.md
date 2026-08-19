# EDGEiQ Performance Intelligence
## Phase 0.5 Canonical Identity and Source-Evidence Prototype

Generated UTC: `2026-07-15T18:15:23.358639+00:00`

## Status

**PROTOTYPE_PASS**

This prototype does not modify any production result, sectional, rating or frontend feed.

## Source evidence

- Source evidence records: **2**
- Results source: `public/data/edgeiq_historical_results_warehouse_v2_graphql.csv`
- Sectional source: `public/data/racingcom_sectional_warehouse_v2.csv`

## Canonical performance identity

- Source result rows: **879,784**
- Canonical meetings: **8,600**
- Canonical races: **71,019**
- Canonical horses: **879,695**
- Canonical performances: **879,695**
- Duplicate performance IDs: **89**
- Duplicate source rows: **89**
- Identity-unresolved rows: **0**
- Date coverage: **2000-08-02 to 2026-06-24**

## Sectional linkage

- Sectional source rows: **130,484**
- Linked rows: **0**
- Linkage: **0.0%**
- Provider-ID links: **0**
- Composite links: **0**
- Ambiguous rows: **0**
- Unlinked rows: **130,484**

## UTF-8 BOM correction

- Scripts rechecked: **9**
- Valid Python with UTF-8 BOM: **9**
- True syntax errors: **0**

The previous Phase 0.4 syntax report treated UTF-8 BOM markers as syntax errors because the files were parsed after plain UTF-8 decoding. This prototype rechecks them using `utf-8-sig`.

## Governance state

The prototype establishes deterministic IDs and immutable source-evidence records, but it is not yet the production warehouse.

Required before promotion:

1. Confirm provider runner IDs represent horses consistently through time.
2. Resolve duplicate performance evidence without deleting any source row.
3. Add formal horse alias and provider-identifier tables.
4. Validate sectional linkage quality.
5. Build evidence-version and supersession tests.
6. Create canonical migration audits before writing any production warehouse.
