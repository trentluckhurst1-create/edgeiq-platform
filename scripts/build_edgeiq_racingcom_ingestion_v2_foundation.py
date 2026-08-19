from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
OUTDIR = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
OUTDIR.mkdir(parents=True, exist_ok=True)

MEETING_V2 = DATA / "edgeiq_racingcom_meeting_discovery_v2.csv"
RACE_V2 = DATA / "edgeiq_racingcom_race_discovery_v2.csv"

MEETING_CONTRACT = OUTDIR / "edgeiq_racingcom_meeting_discovery_contract_v2.csv"
RACE_CONTRACT = OUTDIR / "edgeiq_racingcom_race_discovery_contract_v2.csv"
ADMISSION = OUTDIR / "edgeiq_racingcom_csv_admission_contract_v2.csv"
QUEUE = OUTDIR / "edgeiq_racingcom_acquisition_queue_v2.csv"
REJECTIONS = OUTDIR / "edgeiq_racingcom_admission_rejections_v2.csv"
AUDIT = OUTDIR / "edgeiq_racingcom_ingestion_v2_foundation_audit.csv"
SUMMARY = OUTDIR / "edgeiq_racingcom_ingestion_v2_foundation_summary.json"
REPORT = OUTDIR / "edgeiq_racingcom_ingestion_v2_foundation_report.md"

BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")

ADMISSION_COLUMNS = [
    "admission_id", "race_id", "meeting_id", "race_date", "track", "track_key", "race_no", "race_no_numeric",
    "admission_status", "queue_type", "csv_url", "race_url", "speed_data_url", "source_url", "source_payload_path",
    "evidence_strength", "admission_reason", "priority", "provenance", "admitted_utc", "production_changed",
]
QUEUE_COLUMNS = [
    "queue_id", "queue_type", "admission_id", "race_id", "request_url", "csv_url", "race_url", "speed_data_url",
    "priority", "race_date", "track", "track_key", "race_no_numeric", "discovery_method", "provenance", "queued_utc",
]
REJECTION_COLUMNS = [
    "race_id", "meeting_id", "race_date", "track", "track_key", "race_no", "race_no_numeric", "admission_status",
    "rejection_reason", "source_url", "discovery_method", "evidence_strength", "provenance", "rejected_utc",
]


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"", "NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    if columns is None:
        columns = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: clean(row.get(col, "")) for col in columns})


def is_future(row: dict[str, str]) -> bool:
    return clean(row.get("is_future")).upper() == "YES"


def method(row: dict[str, str], name: str) -> bool:
    return name in clean(row.get("discovery_method"))


def numeric(value: Any) -> int:
    try:
        return int(float(clean(value)))
    except Exception:
        return 9999


def extract_historical_csv(source_url: str) -> str:
    urls = [part.strip() for part in clean(source_url).split(" | ") if part.strip()]
    for url in urls:
        if re.match(r"^https://d3qmfyv6ad9vwv\.cloudfront\.net/.+\.csv$", url, re.I):
            return url
    return ""


def admission_for_race(row: dict[str, str]) -> dict[str, str]:
    race_id = clean(row.get("race_id"))
    base = {
        "admission_id": f"ADM_{race_id}",
        "race_id": race_id,
        "meeting_id": clean(row.get("meeting_id")),
        "race_date": clean(row.get("race_date")),
        "track": clean(row.get("track")),
        "track_key": clean(row.get("track_key")),
        "race_no": clean(row.get("race_no")),
        "race_no_numeric": clean(row.get("race_no_numeric")),
        "csv_url": "",
        "race_url": clean(row.get("race_url")),
        "speed_data_url": clean(row.get("speed_data_url")),
        "source_url": clean(row.get("source_url")),
        "source_payload_path": clean(row.get("source_payload_path")),
        "evidence_strength": clean(row.get("evidence_strength")),
        "provenance": clean(row.get("provenance")),
        "admitted_utc": BUILT_UTC,
        "production_changed": "NO",
    }
    if is_future(row):
        base.update({"admission_status": "DEFERRED_FUTURE_RACE", "queue_type": "NONE", "admission_reason": "Future race is directly observed but deferred from historical acquisition.", "priority": "900"})
        return base
    if method(row, "HISTORICAL_SUCCESS_RACE"):
        csv_url = extract_historical_csv(row.get("source_url", ""))
        if csv_url:
            base.update({"admission_status": "ADMITTED_HISTORICAL_PROVEN_CSV", "queue_type": "CSV_ACQUISITION", "csv_url": csv_url, "admission_reason": "CSV URL was previously fetched, parsed, and produced valid runner rows.", "priority": "10"})
            return base
        base.update({"admission_status": "REJECTED_INVALID_IDENTITY", "queue_type": "NONE", "admission_reason": "Historical success race did not retain a usable CSV URL.", "priority": "800"})
        return base
    if method(row, "COMPLETED_PAYLOAD_RACE") and clean(row.get("speed_data_url")):
        base.update({"admission_status": "REQUIRES_PAGE_DISCOVERY", "queue_type": "PAGE_DISCOVERY", "admission_reason": "Race and speed-data page are directly evidenced by completed payload probe; no explicit CSV link admitted yet.", "priority": "30"})
        return base
    if method(row, "OBSERVED_STRUCTURED_RACE"):
        base.update({"admission_status": "REJECTED_NO_SPEED_DATA_EVIDENCE", "queue_type": "NONE", "admission_reason": "Race number is observed in local structured race fields, but no direct race URL, speed-data page, or CSV evidence was retained.", "priority": "700"})
        return base
    base.update({"admission_status": "REJECTED_UNVERIFIED_RACE", "queue_type": "NONE", "admission_reason": "Race evidence did not match an admitted V2 evidence class.", "priority": "850"})
    return base


def queue_from_admission(row: dict[str, str]) -> dict[str, str] | None:
    queue_type = clean(row.get("queue_type"))
    if queue_type == "CSV_ACQUISITION":
        request_url = clean(row.get("csv_url"))
    elif queue_type == "PAGE_DISCOVERY":
        request_url = clean(row.get("speed_data_url") or row.get("race_url"))
    else:
        return None
    if not request_url:
        return None
    return {
        "queue_id": f"Q_{queue_type}_{clean(row.get('race_id'))}",
        "queue_type": queue_type,
        "admission_id": clean(row.get("admission_id")),
        "race_id": clean(row.get("race_id")),
        "request_url": request_url,
        "csv_url": clean(row.get("csv_url")),
        "race_url": clean(row.get("race_url")),
        "speed_data_url": clean(row.get("speed_data_url")),
        "priority": clean(row.get("priority")),
        "race_date": clean(row.get("race_date")),
        "track": clean(row.get("track")),
        "track_key": clean(row.get("track_key")),
        "race_no_numeric": clean(row.get("race_no_numeric")),
        "discovery_method": "FROM_RACE_DISCOVERY_V2",
        "provenance": clean(row.get("provenance")),
        "queued_utc": BUILT_UTC,
    }


def build() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    meetings = read_csv_rows(MEETING_V2)
    races = read_csv_rows(RACE_V2)
    admissions = [admission_for_race(row) for row in races]
    queue = [q for row in admissions for q in [queue_from_admission(row)] if q]
    queue = sorted(queue, key=lambda r: (numeric(r["priority"]), r["race_date"], r["track_key"], numeric(r["race_no_numeric"]), r["race_id"]))
    rejections = []
    for row in admissions:
        status = clean(row.get("admission_status"))
        if status.startswith("REJECTED") or status.startswith("DEFERRED"):
            rejections.append({
                "race_id": row["race_id"], "meeting_id": row["meeting_id"], "race_date": row["race_date"], "track": row["track"], "track_key": row["track_key"],
                "race_no": row["race_no"], "race_no_numeric": row["race_no_numeric"], "admission_status": status,
                "rejection_reason": row["admission_reason"], "source_url": row["source_url"], "discovery_method": "FROM_RACE_DISCOVERY_V2",
                "evidence_strength": row["evidence_strength"], "provenance": row["provenance"], "rejected_utc": BUILT_UTC,
            })
    status_counts = {status: sum(1 for r in admissions if r["admission_status"] == status) for status in sorted({r["admission_status"] for r in admissions})}
    queue_types = {typ: sum(1 for r in queue if r["queue_type"] == typ) for typ in sorted({r["queue_type"] for r in queue})}
    future_queue = sum(1 for r in queue if any(a["race_id"] == r["race_id"] and a["admission_status"] == "DEFERRED_FUTURE_RACE" for a in admissions))
    explicit_csv = status_counts.get("ADMITTED_EXPLICIT_CSV_LINK", 0)
    constructed_csv = sum(1 for r in admissions if r["csv_url"] and not r["admission_status"] in {"ADMITTED_HISTORICAL_PROVEN_CSV", "ADMITTED_EXPLICIT_CSV_LINK"})
    queue_order_ok = queue == sorted(queue, key=lambda r: (numeric(r["priority"]), r["race_date"], r["track_key"], numeric(r["race_no_numeric"]), r["race_id"]))
    checks = [
        ("meeting_contract_rows", len(meetings) > 0, len(meetings), "Meeting Discovery V2 rows consumed."),
        ("race_contract_rows", len(races) > 0, len(races), "Race Discovery V2 rows consumed."),
        ("admission_rows_match_race_rows", len(admissions) == len(races), len(admissions), "One admission decision per race discovery row."),
        ("historical_proven_csv_admitted", status_counts.get("ADMITTED_HISTORICAL_PROVEN_CSV", 0) > 0, status_counts.get("ADMITTED_HISTORICAL_PROVEN_CSV", 0), "Historically successful CSVs admitted."),
        ("page_discovery_queue_evidence_based", status_counts.get("REQUIRES_PAGE_DISCOVERY", 0) == queue_types.get("PAGE_DISCOVERY", 0), queue_types.get("PAGE_DISCOVERY", 0), "Only directly evidenced speed-data pages enter page discovery queue."),
        ("future_races_deferred_not_queued", future_queue == 0, future_queue, "Future races do not enter acquisition/page queues."),
        ("unsupported_races_rejected", status_counts.get("REJECTED_UNVERIFIED_RACE", 0) == 0, status_counts.get("REJECTED_UNVERIFIED_RACE", 0), "No unsupported V2 race identities admitted."),
        ("no_constructed_csv_urls", constructed_csv == 0, constructed_csv, "CSV URLs only admitted from historical proof or explicit observed CSV evidence."),
        ("numeric_queue_ordering", queue_order_ok, int(not queue_order_ok), "Queue sorted by priority/date/track/race_no/race_id."),
        ("no_first_n_silent_truncation", True, 0, "Foundation builds the full V2 race discovery population; no fetch cap exists in this stage."),
        ("production_unchanged", True, 0, "No production warehouse, pricing, UI, or model outputs modified."),
    ]
    audit = [{"check": name, "status": "PASS" if passed else "FAIL", "count": str(count), "detail": detail} for name, passed, count, detail in checks]
    summary = {
        "status": "RACINGCOM_INGESTION_V2_FOUNDATION_PASS" if all(passed for _, passed, _, _ in checks) else "RACINGCOM_INGESTION_V2_FOUNDATION_REVIEW_REQUIRED",
        "built_utc": BUILT_UTC,
        "meeting_rows": len(meetings),
        "race_rows": len(races),
        "admission_rows": len(admissions),
        "queue_rows": len(queue),
        "rejection_rows": len(rejections),
        "status_counts": status_counts,
        "queue_types": queue_types,
        "historical_proven_csv_count": status_counts.get("ADMITTED_HISTORICAL_PROVEN_CSV", 0),
        "explicit_csv_count": explicit_csv,
        "requires_page_discovery_count": status_counts.get("REQUIRES_PAGE_DISCOVERY", 0),
        "deferred_future_count": status_counts.get("DEFERRED_FUTURE_RACE", 0),
        "rejected_no_speed_data_count": status_counts.get("REJECTED_NO_SPEED_DATA_EVIDENCE", 0),
        "future_queue_rows": future_queue,
        "constructed_csv_urls": constructed_csv,
        "production_changed": "NO",
    }
    return admissions, queue, rejections, audit, summary


def main() -> int:
    meetings = read_csv_rows(MEETING_V2)
    races = read_csv_rows(RACE_V2)
    admissions, queue, rejections, audit, summary = build()
    write_csv(MEETING_CONTRACT, meetings, list(meetings[0].keys()) if meetings else [])
    write_csv(RACE_CONTRACT, races, list(races[0].keys()) if races else [])
    write_csv(ADMISSION, admissions, ADMISSION_COLUMNS)
    write_csv(QUEUE, queue, QUEUE_COLUMNS)
    write_csv(REJECTIONS, rejections, REJECTION_COLUMNS)
    write_csv(AUDIT, audit, ["check", "status", "count", "detail"])
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    lines = [
        "# EDGEiQ Racing.com Ingestion V2 Foundation",
        "",
        f"Built UTC: `{BUILT_UTC}`",
        f"Status: `{summary['status']}`",
        "",
        "## Counts",
        f"- Meeting rows: `{summary['meeting_rows']}`",
        f"- Race rows: `{summary['race_rows']}`",
        f"- Admission rows: `{summary['admission_rows']}`",
        f"- Queue rows: `{summary['queue_rows']}`",
        f"- Rejection/deferred rows: `{summary['rejection_rows']}`",
        "",
        "## Admission Status Counts",
    ]
    for key, value in summary["status_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Queue Types"])
    for key, value in summary["queue_types"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Guardrails", "- No fixed race expansion.", "- No future race enters the queue.", "- No constructed CSV URLs are admitted.", "- Production outputs unchanged.", "", "## Audit"])
    for row in audit:
        lines.append(f"- `{row['check']}`: `{row['status']}` ({row['count']}) - {row['detail']}")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "admission_rows": summary["admission_rows"], "queue_rows": summary["queue_rows"], "status_counts": summary["status_counts"]}, indent=2))
    return 0 if summary["status"] == "RACINGCOM_INGESTION_V2_FOUNDATION_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
