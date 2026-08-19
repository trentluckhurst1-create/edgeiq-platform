# EDGEIQ Active Racing.com Payload Universe V1

Generated UTC: `2026-07-22T07:15:10.611422+00:00`

## Governance boundary

- Read-only forensic diagnostic.
- Checkpoints and documentation snapshots excluded.
- Active public data inspected separately.
- Active scripts inspected separately.
- No governed builder modified.
- No governed output modified.
- No threshold modified.
- No benchmark data fabricated.

## Active raw-looking payload population

- Files: **660**
- Unique content hashes: **293**
- Duplicate file copies: **367**

## Active raw directories

| Directory | Files | Unique content | Duplicates |
|---|---:|---:|---:|
| `outputs/sectionals/raw/VIC/racingcom_full_payloads` | 602 | 236 | 366 |
| `data/weather/bom-location-resolution/raw-search-pages` | 29 | 29 | 0 |
| `data/weather` | 7 | 7 | 0 |
| `data/weather-source-audit/live-turftrax` | 3 | 3 | 0 |
| `data/weather-source-audit/live-vrc` | 2 | 2 | 0 |
| `config` | 1 | 1 | 0 |
| `data/weather-source-audit/bom-live/87184` | 1 | 1 | 0 |
| `data/weather-source-audit/bom-live/89002` | 1 | 1 | 0 |
| `data/weather-source-audit/bom-live/90173` | 1 | 1 | 0 |
| `data/weather-source-audit/bom-live/94852` | 1 | 1 | 0 |
| `data/weather-source-live/caulfield/20260713T204355Z` | 1 | 1 | 0 |
| `data/weather-source-live/caulfield/20260713T205456Z` | 1 | 1 | 0 |
| `data/weather-source-live/caulfield/20260713T220906Z` | 1 | 1 | 0 |
| `data/weather-source-live/flemington/20260713T204355Z` | 1 | 1 | 0 |
| `data/weather-source-live/flemington/20260713T205456Z` | 1 | 1 | 0 |
| `data/weather-source-live/flemington/20260713T220906Z` | 1 | 1 | 0 |
| `data/weather-source-live/mornington/20260713T204355Z` | 1 | 1 | 0 |
| `data/weather-source-live/mornington/20260713T205456Z` | 1 | 1 | 0 |
| `data/weather-source-live/mornington/20260713T220906Z` | 1 | 1 | 0 |
| `data/weather-source-live/sandown/20260713T204355Z` | 1 | 1 | 0 |
| `data/weather-source-live/sandown/20260713T205456Z` | 1 | 1 | 0 |
| `data/weather-source-live/sandown/20260713T220906Z` | 1 | 1 | 0 |

## Active governed V1 datasets

- `edgeiq_racingcom_runner_speed_fact_v1.csv` ? FOUND ? rows=392 ? distinct references=39
- `edgeiq_racingcom_runner_sectional_fact_v1.csv` ? FOUND ? rows=2854 ? distinct references=39
- `edgeiq_racingcom_runner_split_fact_v1.csv` ? FOUND ? rows=2682 ? distinct references=39
- `edgeiq_racingcom_race_speed_summary_v1.csv` ? FOUND ? rows=39 ? distinct references=39

## Active ingestion chain

- `scripts/build_edgeiq_raw_sectional_payload_discovery_v1.py` ? FOUND ? syntax=PASS ? selector evidence lines=69
- `scripts/build_edgeiq_raw_sectional_payload_schema_parser_v1.py` ? FOUND ? syntax=PASS ? selector evidence lines=35
- `scripts/build_edgeiq_racingcom_csv_ingestion_v1.py` ? FOUND ? syntax=PASS ? selector evidence lines=28
- `scripts/build_edgeiq_vic_racingcom_speed_data_ingestion_v1.py` ? FOUND ? syntax=PASS ? selector evidence lines=4
- `scripts/build_edgeiq_racingcom_runner_speed_warehouse_v1.py` ? FOUND ? syntax=PASS ? selector evidence lines=48
- `scripts/build_edgeiq_racingcom_canonical_speed_warehouse_v2.py` ? FOUND ? syntax=PASS ? selector evidence lines=19
- `scripts/build_edgeiq_racingcom_canonical_speed_warehouse_v2_1.py` ? FOUND ? syntax=PASS ? selector evidence lines=41
- `scripts/build_racingcom_sectionals_from_downloads_v1.py` ? FOUND ? syntax=PASS ? selector evidence lines=37
- `scripts/build_racingcom_sectional_history_master_v1.py` ? FOUND ? syntax=PASS ? selector evidence lines=35
- `scripts/build_racingcom_sectional_warehouse_v1.py` ? FOUND ? syntax=PASS ? selector evidence lines=19
- `scripts/build_racingcom_sectional_warehouse_v2.py` ? FOUND ? syntax=PASS ? selector evidence lines=19

## Forensic decision

**ACTIVE_UNIQUE_RAW_POPULATION_EXCEEDS_39**

The active repository contains more than 39 unique raw-looking Racing.com payload artifacts after checkpoint and documentation copies are excluded.

The selector trace must identify which active ingestion stage does not consume that population.

## Artifacts

- `docs/performance-intelligence/standard-time-investigation/edgeiq_active_racingcom_payload_universe_v1.json`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_active_racingcom_raw_payload_inventory_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_active_racingcom_raw_directory_summary_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_active_racingcom_selector_trace_v1.csv`
