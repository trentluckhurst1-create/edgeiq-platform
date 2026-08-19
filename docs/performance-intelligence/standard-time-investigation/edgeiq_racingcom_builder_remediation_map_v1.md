# EDGEIQ Racing.com Builder Remediation Map V1

Generated UTC: `2026-07-22T07:43:38.172418+00:00`

## Governance boundary

- Read-only source inspection.
- Production builder not executed.
- Production builder not modified.
- No network access.
- No cache or governed output modified.

## Builder

- Path: `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\scripts\build_edgeiq_racingcom_csv_ingestion_v1.py`
- Source lines: **584**

## Governed assignments

- `APP_ROOT`: lines **16?16**
- `PROJECT_ROOT`: lines **17?17**
- `RAW_CACHE`: lines **20?20**
- `MAX_FETCHES`: lines **27?27**
- `CLOUDFRONT_BASE`: lines **29?29**

## Relevant functions

- `read_csv`: lines **79?89**; patterns: `name-selected`
- `race_no_key`: lines **103?105**; patterns: `race_number`
- `fetch_text`: lines **114?130**; patterns: `name-selected`
- `local_payload_files`: lines **133?144**; patterns: `sort_values`
- `csv_links_from_text`: lines **147?155**; patterns: `name-selected`
- `calendar_entries_from_payloads`: lines **158?213**; patterns: `meetcode`
- `race_number_from_url`: lines **216?218**; patterns: `race_number`
- `discover_candidates`: lines **221?298**; patterns: `twelve_race_expansion, csv_url, drop_duplicates, sort_values, race_number, meetcode, discovery_method`
- `discover_page_csv_links`: lines **301?334**; patterns: `csv_url, race_number, discovery_method`
- `parse_metadata`: lines **371?387**; patterns: `race_number`
- `parse_racingcom_csv`: lines **390?485**; patterns: `race_number`
- `main`: lines **488?580**; patterns: `max_fetches_reference, fetch_break, csv_url, drop_duplicates, race_number`

## Defect-pattern hits

- `csv_url`: **10** hits
- `discovery_method`: **6** hits
- `drop_duplicates`: **3** hits
- `fetch_break`: **1** hits
- `max_fetches_reference`: **4** hits
- `meetcode`: **10** hits
- `parent_resolution`: **2** hits
- `race_number`: **22** hits
- `sort_values`: **2** hits
- `twelve_race_expansion`: **2** hits

## Remediation constraints

The production remediation must:

1. resolve all repository-owned paths from the actual repository root;
2. stop generating a fixed twelve-race cohort;
3. admit only race numbers supported by meeting or race evidence;
4. sort race numbers numerically;
5. deduplicate by canonical race identity before URL fetch;
6. retain provenance for direct versus derived URLs;
7. write source caches inside the governed repository;
8. avoid using a global first-N URL cap as the population boundary;
9. preserve the existing CSV parser until contrary evidence exists;
10. produce explicit admission and rejection diagnostics.

## Decision

**BUILDER_REMEDIATION_SOURCE_MAP_CREATED**

## Artifacts

- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_builder_remediation_map_v1.json`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_builder_remediation_map_v1.md`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_builder_remediation_excerpts_v1.txt`
