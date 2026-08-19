from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

CALIBRATION = DATA / "edgeiq_starter_only_calibration_v2.csv"
AUDIT_IN = DATA / "edgeiq_starter_only_calibration_v2_audit.csv"

OUT = DATA / "edgeiq_calibration_history_v1.csv"
AUDIT_OUT = DATA / "edgeiq_calibration_history_v1_audit.csv"

OUT_COLUMNS = [
    "meeting_date",
    "track",
    "races",
    "starters",
    "expected_winners",
    "actual_winners",
    "actual_minus_expected",
    "actual_to_expected_ratio",
    "calibration_status",
    "sample_warning",
    "snapshot_timestamp",
    "created_at",
]

AUDIT_COLUMNS = [
    "section",
    "metric",
    "value",
    "notes",
    "built_at",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def audit(section: str, metric: str, value: object, notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "notes": notes,
        "built_at": now_utc(),
    }


def metric_value(rows: list[dict[str, str]], metric: str) -> str:
    for row in rows:
        if str(row.get("metric", "")).strip() == metric:
            return str(row.get("value", "")).strip()
    return ""


def main() -> None:
    calibration_rows = read_csv(CALIBRATION)
    audit_rows_in = read_csv(AUDIT_IN)
    existing_rows = read_csv(OUT)

    if not calibration_rows:
        raise RuntimeError(f"Missing or empty input: {CALIBRATION}")

    cal = calibration_rows[0]

    snapshot_timestamp = metric_value(audit_rows_in, "latest_snapshot_timestamp")
    calibration_status = metric_value(audit_rows_in, "calibration_status")
    sample_warning = metric_value(audit_rows_in, "sample_warning")

    meeting_date = ""
    track = ""

    for row in audit_rows_in:
        if str(row.get("section", "")).strip() == "race_probability":
            metric = str(row.get("metric", "")).strip()
            parts = metric.split("|")
            if len(parts) >= 3:
                meeting_date = parts[0]
                track = parts[1]
                break

    if not meeting_date:
        meeting_date = "UNKNOWN"
    if not track:
        track = "UNKNOWN"

    new_row = {
        "meeting_date": meeting_date,
        "track": track,
        "races": cal.get("races", ""),
        "starters": cal.get("runners", ""),
        "expected_winners": cal.get("expected_winners", ""),
        "actual_winners": cal.get("actual_winners", ""),
        "actual_minus_expected": cal.get("actual_minus_expected", ""),
        "actual_to_expected_ratio": cal.get("actual_to_expected_ratio", ""),
        "calibration_status": calibration_status or "STARTER_ONLY_CALIBRATION_READY",
        "sample_warning": sample_warning,
        "snapshot_timestamp": snapshot_timestamp,
        "created_at": now_utc(),
    }

    key = (
        new_row["meeting_date"],
        new_row["track"],
        new_row["snapshot_timestamp"],
    )

    existing_keys = {
        (
            row.get("meeting_date", ""),
            row.get("track", ""),
            row.get("snapshot_timestamp", ""),
        )
        for row in existing_rows
    }

    rows_written_this_run = 0
    duplicate_skipped = 0

    output_rows = list(existing_rows)

    if key in existing_keys:
        duplicate_skipped = 1
    else:
        output_rows.append(new_row)
        rows_written_this_run = 1

    write_csv(OUT, output_rows, OUT_COLUMNS)

    audit_rows = [
        audit("input", "calibration_input_rows", len(calibration_rows), str(CALIBRATION)),
        audit("input", "audit_input_rows", len(audit_rows_in), str(AUDIT_IN)),
        audit("history", "existing_history_rows", len(existing_rows), str(OUT)),
        audit("history", "rows_written_this_run", rows_written_this_run),
        audit("history", "duplicate_rows_skipped", duplicate_skipped),
        audit("history", "total_history_rows", len(output_rows), str(OUT)),
        audit("history", "meeting_date", meeting_date),
        audit("history", "track", track),
        audit("history", "snapshot_timestamp", snapshot_timestamp),
        audit("history", "expected_winners", new_row["expected_winners"]),
        audit("history", "actual_winners", new_row["actual_winners"]),
        audit("history", "actual_to_expected_ratio", new_row["actual_to_expected_ratio"]),
        audit("status", "history_status", "CALIBRATION_HISTORY_APPEND_PASS"),
    ]

    write_csv(AUDIT_OUT, audit_rows, AUDIT_COLUMNS)

    print("=" * 96)
    print("EDGEIQ CALIBRATION HISTORY ENGINE V1")
    print("=" * 96)
    print(f"wrote: {OUT}")
    print(f"wrote: {AUDIT_OUT}")
    print("")
    for row in audit_rows:
        print(f"{row['section']},{row['metric']},{row['value']},{row['notes']}")
    print("=" * 96)


if __name__ == "__main__":
    main()
