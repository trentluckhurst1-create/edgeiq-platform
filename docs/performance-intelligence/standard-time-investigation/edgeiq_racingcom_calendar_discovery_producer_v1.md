# EDGEiQ Racing.com Calendar Discovery Producer Trace V1

Generated UTC: `2026-07-22T08:18:25.316817+00:00`

## Decision

- Decision: `PRODUCER_IDENTIFIED`
- Exact producer: `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py`
- Race schedule source mode: `FABRICATED_FROM_FIXED_LOOP`

## Target Artifact Facts

- Target file exists: `True`
- Target rows: `568`
- Target columns: `race_date, track, state, meeting_url, race_no, race_url, speed_data_url, source_url, discovery_status`
- Exact 1-12 meeting groups: `44`
- Future rows: `144`
- Future exact 1-12 groups: `12`
- SHA-256: `87b53ea2420dbd1f24b694aefaba2b6e3823032596589adf3b93ad421ceb7a59`

## Exact Evidence Lines

### Fixed Race Expansion
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:308` - `for rno in range(1, default_races + 1): race_url = f"{meeting_url}/race/{rno}" next_row = dict(row) next_row["race_no"] = str(rno) next_row["race_url"] = race_url next_row["speed_data_url"] = f"{race_url}/speed-data" next_row["discovery_status"] = f"{row.get('discovery_status', 'MEETING')}_EXPANDED" expanded.append(next_row)`

### Race URL Construction
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:153` - `race_url = f"{meeting_url}/race/{rno}"`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:153` - `race_url = f"{meeting_url}/race/{rno}"`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:160` - `"race_url": race_url,`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:214` - `race_url = f"{meeting_url}/race/{rno}" if meeting_url else ""`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:214` - `race_url = f"{meeting_url}/race/{rno}" if meeting_url else ""`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:221` - `"race_url": race_url,`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:233` - `"race_url": "",`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:290` - `"race_url": "",`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:309` - `race_url = f"{meeting_url}/race/{rno}"`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:309` - `race_url = f"{meeting_url}/race/{rno}"`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:153` - `race_url = f"{meeting_url}/race/{rno}"`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:214` - `race_url = f"{meeting_url}/race/{rno}" if meeting_url else ""`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:309` - `race_url = f"{meeting_url}/race/{rno}"`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:312` - `next_row["race_url"] = race_url`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:154` - `rows.append({ "race_date": race_date, "track": track, "state": "VIC", "meeting_url": meeting_url, "race_no": rno, "race_url": race_url, "speed_data_url": f"{race_url}/speed-data", "source_url": str(RACE_FIELDS.relative_to(PROJECT_ROOT)), "discovery_status": "LIVE_RACE_FIELDS_CANDIDATE", })`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:284` - `rows.append({ "race_date": date, "track": track, "state": "VIC", "meeting_url": meeting_url, "race_no": "", "race_url": "", "speed_data_url": "", "source_url": CALENDAR_URL, "discovery_status": "CALENDAR_PAGE_LINK", })`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:215` - `rows.append({ "race_date": date, "track": track, "state": state, "meeting_url": meeting_url, "race_no": rno, "race_url": race_url, "speed_data_url": f"{race_url}/speed-data" if race_url else "", "source_url": source_url, "discovery_status": "MEETS_BY_MONTH_RACE", })`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:227` - `rows.append({ "race_date": date, "track": track, "state": state, "meeting_url": meeting_url, "race_no": "", "race_url": "", "speed_data_url": "", "source_url": source_url, "discovery_status": "MEETS_BY_MONTH_MEETING", })`

### Speed Data URL Construction
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:30` - `"speed_data_url",`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:161` - `"speed_data_url": f"{race_url}/speed-data",`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:161` - `"speed_data_url": f"{race_url}/speed-data",`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:222` - `"speed_data_url": f"{race_url}/speed-data" if race_url else "",`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:222` - `"speed_data_url": f"{race_url}/speed-data" if race_url else "",`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:234` - `"speed_data_url": "",`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:234` - `"speed_data_url": "",`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:291` - `"speed_data_url": "",`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:291` - `"speed_data_url": "",`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:313` - `next_row["speed_data_url"] = f"{race_url}/speed-data"`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:336` - `output = output.drop_duplicates(subset=["race_date", "track", "race_no", "speed_data_url"], keep="first")`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:343` - `{"metric": "speed_data_urls", "value": str(int(output["speed_data_url"].astype(str).map(has_value).sum()) if not output.empty else 0), "notes": "Candidate speed-data URLs"},`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:352` - `log(f"speed-data URLs generated: {diag.loc[diag['metric'] == 'speed_data_urls', 'value'].iloc[0]}")`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:313` - `next_row["speed_data_url"] = f"{race_url}/speed-data"`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:154` - `rows.append({ "race_date": race_date, "track": track, "state": "VIC", "meeting_url": meeting_url, "race_no": rno, "race_url": race_url, "speed_data_url": f"{race_url}/speed-data", "source_url": str(RACE_FIELDS.relative_to(PROJECT_ROOT)), "discovery_status": "LIVE_RACE_FIELDS_CANDIDATE", })`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:284` - `rows.append({ "race_date": date, "track": track, "state": "VIC", "meeting_url": meeting_url, "race_no": "", "race_url": "", "speed_data_url": "", "source_url": CALENDAR_URL, "discovery_status": "CALENDAR_PAGE_LINK", })`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:215` - `rows.append({ "race_date": date, "track": track, "state": state, "meeting_url": meeting_url, "race_no": rno, "race_url": race_url, "speed_data_url": f"{race_url}/speed-data" if race_url else "", "source_url": source_url, "discovery_status": "MEETS_BY_MONTH_RACE", })`
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:227` - `rows.append({ "race_date": date, "track": track, "state": state, "meeting_url": meeting_url, "race_no": "", "race_url": "", "speed_data_url": "", "source_url": source_url, "discovery_status": "MEETS_BY_MONTH_MEETING", })`

### Target Write Operation
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py:348` - `output.to_csv(OUT, index=False, encoding="utf-8")`

## Upstream Inputs Mentioned By Producer

- `edgeiq_racingcom_calendar_diagnostics_v1.csv`
- `edgeiq_racingcom_calendar_discovery_v1.csv`
- `https://www.racing.com`
- `https://www.racing.com/`
- `https://www.racing.com/calendar`
- `https://www.racing.com/form/{date}/{track_slug(track`
- `https://www.racing.com/form/{meeting_url}`
- `https://www.racing.com/form/{race_date}/{slug}`
- `https://www.racing.com/services/appv2/GetMeetsByMonth/{year}/{month}`

## Top Producer Candidates

| Rank | File | Assessment | Score | Target refs | Write hits | Fixed ranges | Race URL hits | Speed URL hits |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 1 | `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py` | `LIKELY_PRODUCER` | 292 | 1 | 2 | 1 | 18 | 18 |
| 2 | `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_race_discovery_contract_v2.csv` | `ARTIFACT_OR_DOC_REFERENCE` | 16491 | 1136 | 0 | 0 | 572 | 573 |
| 3 | `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_upstream_race_evidence_ledger_v1.csv` | `ARTIFACT_OR_DOC_REFERENCE` | 14492 | 1136 | 0 | 0 | 110 | 36 |
| 4 | `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_csv_candidate_population_v1.csv` | `LOW_SIGNAL` | 7474 | 0 | 0 | 0 | 1868 | 1869 |
| 5 | `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_candidate_legitimacy_ledger_v1.csv` | `LOW_SIGNAL` | 5186 | 0 | 0 | 0 | 1296 | 1297 |
| 6 | `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_url_admission_order_ledger_v1.csv` | `LOW_SIGNAL` | 5186 | 0 | 0 | 0 | 1296 | 1297 |
| 7 | `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_payload_selector_script_evidence_v1.csv` | `ARTIFACT_OR_DOC_REFERENCE` | 3043 | 18 | 2 | 0 | 149 | 1164 |
| 8 | `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_csv_admission_contract_v2.csv` | `LOW_SIGNAL` | 2858 | 0 | 0 | 0 | 572 | 573 |
| 9 | `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_acquisition_queue_v2.csv` | `LOW_SIGNAL` | 2290 | 0 | 0 | 0 | 572 | 573 |
| 10 | `public/data/edgeiq_racingcom_calendar_discovery_v1.csv` | `LOW_SIGNAL` | 2275 | 0 | 0 | 0 | 568 | 569 |
| 11 | `docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_meeting_discovery_contract_v2.csv` | `ARTIFACT_OR_DOC_REFERENCE` | 1226 | 98 | 0 | 0 | 0 | 0 |
| 12 | `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_payload_admission_gap_v1.json` | `ARTIFACT_OR_DOC_REFERENCE` | 886 | 7 | 0 | 0 | 40 | 354 |

## Finding

The calendar discovery producer fabricates race-level rows from a fixed race-number loop and constructs race/speed-data URLs rather than parsing a verified race schedule from observed source content.

## Artifacts

- `docs\performance-intelligence\standard-time-investigation\edgeiq_racingcom_calendar_discovery_reference_ledger_v1.csv`
- `docs\performance-intelligence\standard-time-investigation\edgeiq_racingcom_calendar_discovery_producer_candidates_v1.csv`
- `docs\performance-intelligence\standard-time-investigation\edgeiq_racingcom_calendar_discovery_logic_ledger_v1.csv`
- `docs\performance-intelligence\standard-time-investigation\edgeiq_racingcom_calendar_discovery_producer_excerpts_v1.txt`
- `docs\performance-intelligence\standard-time-investigation\edgeiq_racingcom_calendar_discovery_producer_audit_v1.csv`
- `docs\performance-intelligence\standard-time-investigation\edgeiq_racingcom_calendar_discovery_producer_v1.json`
- `docs\performance-intelligence\standard-time-investigation\edgeiq_racingcom_calendar_discovery_producer_v1.md`

