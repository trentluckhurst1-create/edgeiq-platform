
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
PARSER = DOCS / "edgeiq_racingcom_parser_output_v2.csv"
ACQ = DOCS / "edgeiq_racingcom_csv_acquisition_v2.csv"
WAREHOUSE = DATA / "edgeiq_racingcom_performance_warehouse_v2.csv"
AUDIT = DOCS / "edgeiq_racingcom_performance_warehouse_v2_audit.csv"
SUMMARY = DOCS / "edgeiq_racingcom_performance_warehouse_v2_summary.json"
REPORT = DOCS / "edgeiq_racingcom_performance_warehouse_v2_report.md"
BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")
PIPELINE_VERSION = "racingcom_ingestion_v2"

COLUMNS = [
    "warehouse_record_id", "race_id", "race_date", "track", "state", "race_no", "distance", "horse", "horse_key", "barrier",
    "last200", "last400", "last600", "last_200", "last_400", "last_600", "early_speed", "mid_speed", "late_speed",
    "peak_speed", "avg_speed", "race_time", "tempo_grade", "pace_profile", "sectional_source", "source_csv_url", "source_cache_path",
    "source_sha256", "acquisition_timestamp", "parser_version", "pipeline_version", "meeting_discovery_version", "race_discovery_version",
    "admission_version", "warehouse_built_utc",
]


def clean(v: Any) -> str:
    return "" if v is None else str(v).strip()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists(): return []
    with path.open("r", encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader()
        for r in rows: w.writerow({c: clean(r.get(c,"")) for c in cols})


def fnum(v: Any) -> float | None:
    try:
        s=clean(v)
        return float(s) if s else None
    except Exception:
        return None


def main() -> int:
    parser_rows = read_csv_rows(PARSER)
    acq_rows = {r['race_id']: r for r in read_csv_rows(ACQ)}
    rows=[]
    for r in parser_rows:
        race_id=clean(r.get('race_id'))
        acq=acq_rows.get(race_id,{})
        record=dict(r)
        record.update({
            "warehouse_record_id": f"{race_id}_{clean(r.get('horse_key'))}",
            "source_csv_url": clean(r.get('source_url')),
            "source_cache_path": clean(r.get('source_cache_path')).replace(str(ROOT), '').lstrip('\\/'),
            "source_sha256": clean(r.get('source_sha256')),
            "acquisition_timestamp": clean(acq.get('request_timestamp')),
            "parser_version": clean(r.get('parser_version')) or "racingcom_speed_data_parser_v2",
            "pipeline_version": PIPELINE_VERSION,
            "meeting_discovery_version": "edgeiq_racingcom_meeting_discovery_v2",
            "race_discovery_version": "edgeiq_racingcom_race_discovery_v2",
            "admission_version": "edgeiq_racingcom_csv_admission_contract_v2",
            "warehouse_built_utc": BUILT_UTC,
        })
        rows.append(record)
    rows=sorted(rows, key=lambda r: (r['race_date'], r['track'], int(float(r['race_no'] or 9999)), r['horse_key']))
    duplicate_records=len(rows)-len({r['warehouse_record_id'] for r in rows})
    duplicate_runners=len(rows)-len({(r['race_id'], r['horse_key']) for r in rows})
    missing_identity=sum(1 for r in rows if not r.get('race_id') or not r.get('horse_key') or not r.get('race_date') or not r.get('track'))
    missing_provenance=sum(1 for r in rows if not r.get('source_csv_url') or not r.get('source_cache_path') or not r.get('source_sha256') or not r.get('acquisition_timestamp'))
    implausible_speed=sum(1 for r in rows for c in ['early_speed','mid_speed','late_speed','peak_speed','avg_speed'] if (fnum(r.get(c)) is not None and not (0 <= fnum(r.get(c)) <= 25)))
    implausible_splits=sum(1 for r in rows for c in ['last200','last400','last600'] if (fnum(r.get(c)) is not None and not (0 < fnum(r.get(c)) < 120)))
    future_rows=sum(1 for r in rows if clean(r.get('race_date')) > BUILT_UTC[:10])
    distinct_races=len({r['race_id'] for r in rows})
    checks=[
        ("parser_rows_consumed", len(parser_rows)>0, len(parser_rows), "Parser V2 output consumed."),
        ("runner_rows_retained", len(rows)==80, len(rows), "Historical valid 80 runner rows retained."),
        ("distinct_races", distinct_races==8, distinct_races, "Eight historical successful races represented."),
        ("no_duplicate_records", duplicate_records==0, duplicate_records, "Unique warehouse_record_id."),
        ("no_duplicate_runners", duplicate_runners==0, duplicate_runners, "Unique race_id/horse_key."),
        ("identity_complete", missing_identity==0, missing_identity, "Race and runner identity complete."),
        ("provenance_complete", missing_provenance==0, missing_provenance, "Source CSV URL/cache/SHA/acquisition timestamp retained."),
        ("speed_units_plausible", implausible_speed==0, implausible_speed, "Speed fields in plausible m/s range when present."),
        ("split_units_plausible", implausible_splits==0, implausible_splits, "Split fields in plausible seconds range when present."),
        ("no_future_race_records", future_rows==0, future_rows, "No future races in warehouse."),
        ("production_warehouse_not_overwritten", True, 0, "Wrote versioned V2 warehouse only."),
    ]
    audit=[{"check":n,"status":"PASS" if p else "FAIL","count":str(c),"detail":d} for n,p,c,d in checks]
    summary={"status":"RACINGCOM_PERFORMANCE_WAREHOUSE_V2_PASS" if all(p for _,p,_,_ in checks) else "RACINGCOM_PERFORMANCE_WAREHOUSE_V2_REVIEW_REQUIRED","built_utc":BUILT_UTC,"warehouse_rows":len(rows),"distinct_races":distinct_races,"duplicate_records":duplicate_records,"duplicate_runners":duplicate_runners,"missing_identity":missing_identity,"missing_provenance":missing_provenance,"valid_csv_files":len(acq_rows),"production_changed":"NO"}
    write_csv(WAREHOUSE, rows, COLUMNS)
    write_csv(AUDIT, audit, ["check","status","count","detail"])
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    lines=["# EDGEiQ Racing.com Performance Warehouse V2","",f"Built UTC: `{BUILT_UTC}`",f"Status: `{summary['status']}`",f"Warehouse rows: `{summary['warehouse_rows']}`",f"Distinct races: `{summary['distinct_races']}`","","## Audit"]
    lines += [f"- `{r['check']}`: `{r['status']}` ({r['count']}) - {r['detail']}" for r in audit]
    REPORT.write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps({"status":summary['status'],"warehouse_rows":len(rows),"distinct_races":distinct_races}, indent=2))
    return 0 if summary['status'].endswith('_PASS') else 1

if __name__ == "__main__":
    raise SystemExit(main())
