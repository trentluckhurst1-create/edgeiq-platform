# EDGEIQ Racing.com CSV Admission Ledger V1

Generated UTC: `2026-07-22T07:30:56.443560+00:00`

## Governance boundary

- Read-only forensic diagnostic.
- No network access performed.
- Production ingestion builder not executed.
- No cache file modified.
- No governed output modified.
- No fetch threshold modified.
- Existing builder functions reused only for local discovery and parsing.

## Proven builder boundary

- Configured `MAX_FETCHES`: **50**
- Existing diagnostic candidate rows: **1876**
- Existing diagnostic direct CSV candidates: **1368**
- Existing ingestion runner rows: **80**
- Existing ingestion distinct races: **8**
- Existing ingestion distinct source URLs: **8**

## Reconstructed candidate population

- Candidate rows: **1868**
- Candidate discovery error: **NONE**
- Candidate rows with CSV URL: **1296**
- Unique CSV URLs: **1296**
- Candidate CSV URLs ending in `.csv`: **1296**
- Unique candidate URLs with an existing cache file: **0**

## Cache population

- Cached CSV files: **0**
- Unique cached contents: **0**
- Parsed cached files: **0**
- Zero-row cached files: **0**
- Parser-exception files: **0**
- Parsed runner rows before output deduplication: **0**
- Complete race identities represented in cache: **0**

### Parser statuses

- No cache files inspected.

## Cache filename collision test

- Cache names representing multiple distinct URLs: **0**
- Maximum distinct URLs sharing one cache name: **1**

## Existing diagnostics

- `run_timestamp_utc`: **2026-05-15T04:09:05+00:00** ? UTC run timestamp
- `candidate_rows`: **1876** ? Candidate speed pages/direct CSV rows considered
- `direct_csv_candidates`: **1368** ? CSV URLs derived before page-link discovery
- `page_fetches_for_discovery`: **10** ? Speed-data pages fetched to find embedded CSV links
- `page_csv_links_discovered`: **0** ? Explicit CSV href/cloudfront links discovered in HTML
- `unique_csv_urls`: **1368** ? Unique direct CSV URLs available to fetch
- `fetch_attempts`: **50** ? Max fetches 50
- `csvs_fetched_or_cached`: **8** ? {"200": 8, "HTTP_403": 42}
- `csv_fetch_failures`: **42** ? HTTP/network failures
- `csvs_parsed`: **8** ? CSV files with at least one parsed runner
- `rows_parsed`: **80** ? Normalised runner sectional rows
- `last200_coverage_pct`: **100.00** ? Racing.com CSV rows with final 200m split
- `last400_coverage_pct`: **100.00** ? Racing.com CSV rows with final 400m aggregate
- `last600_coverage_pct`: **100.00** ? Racing.com CSV rows with final 600m aggregate
- `raw_cache_dir`: **outputs/sectionals/raw/VIC/racingcom_csv** ? Raw CSV cache directory

## Decision

**CSV_ADMISSION_EVIDENCE_CREATED**

The next governed decision must be based on the exact admission ledger. The fetch cap must not be changed until candidate coverage, cache coverage, parser rejection, cache collision, and race identity counts are established.

## Artifacts

- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_csv_cache_admission_ledger_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_csv_candidate_population_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_csv_cache_filename_collisions_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_csv_admission_ledger_v1.json`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_csv_admission_ledger_v1.md`
