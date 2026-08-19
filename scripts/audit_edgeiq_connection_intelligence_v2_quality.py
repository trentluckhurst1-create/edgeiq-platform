import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_FILE = DATA / "edgeiq_connection_intelligence_v2.csv"
ACTIVE_FILE = DATA / "edgeiq_live_runner_board_v1.csv"
AUDIT_FILE = DATA / "edgeiq_connection_intelligence_v2_quality_audit.csv"
SUMMARY_FILE = DATA / "edgeiq_connection_intelligence_v2_quality_summary.csv"

VALID_BANDS = {"ELITE", "STRONG", "POSITIVE", "NEUTRAL", "LIMITED", "NO_EVIDENCE"}
VALID_STATUS = {"STRONG_CONNECTION", "DEVELOPING_CONNECTION", "LIMITED_CONNECTION", "NO_CONNECTION"}


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def text(value):
    return str(value or "").strip()


def key(value):
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def is_active(row):
    status = text(row.get("runner_status") or row.get("scratch_status")).upper()
    scratched = text(row.get("is_scratched")).upper()
    return status not in {"SCR", "SCRATCHED"} and scratched not in {"TRUE", "YES", "1"}


def main():
    rows = read_csv(INPUT_FILE)
    active_rows = [row for row in read_csv(ACTIVE_FILE) if is_active(row)]
    built_at = datetime.now(timezone.utc).isoformat()

    duplicate_counter = Counter(
        (text(row.get("current_race_date")), key(row.get("track")), text(row.get("race_no")), key(row.get("horse")))
        for row in rows
    )
    duplicates = [item for item, count in duplicate_counter.items() if count > 1]
    band_counts = Counter(text(row.get("connection_band")) for row in rows)
    status_counts = Counter(text(row.get("connection_evidence_status")) for row in rows)
    bendigo_rows = [row for row in rows if key(row.get("track")) == "BENDIGO"]
    invalid_bands = [row for row in rows if text(row.get("connection_band")) not in VALID_BANDS]
    invalid_status = [row for row in rows if text(row.get("connection_evidence_status")) not in VALID_STATUS]
    no_narrative = [
        row for row in rows
        if text(row.get("connection_band")) != "NO_EVIDENCE" and not text(row.get("connection_narrative"))
    ]
    trainer_wet_usage = [
        row for row in rows
        if "trainer" in text(row.get("connection_angle_1") + row.get("connection_angle_2") + row.get("connection_angle_3")).lower()
        and "wet" in text(row.get("connection_angle_1") + row.get("connection_angle_2") + row.get("connection_angle_3")).lower()
    ]

    active_heavy = {
        (text(row.get("race_date")), key(row.get("track")), text(row.get("race_no")), key(row.get("horse"))):
        ("HEAVY" in text(row.get("track_condition")).upper())
        for row in active_rows
    }
    heavy_bad = []
    for row in rows:
        row_key = (text(row.get("current_race_date")), key(row.get("track")), text(row.get("race_no")), key(row.get("horse")))
        heavy_read = text(row.get("jockey_heavy_read")).lower()
        if "jockey on heavy tracks:" in heavy_read and not active_heavy.get(row_key, False):
            heavy_bad.append(row)

    checks = [
        {
            "check": "active_rows",
            "status": "PASS" if len(rows) == 370 and len(active_rows) == 370 else "FAIL",
            "detail": f"output_rows={len(rows)} active_universe_rows={len(active_rows)} expected=370",
        },
        {
            "check": "duplicates",
            "status": "PASS" if not duplicates else "FAIL",
            "detail": f"duplicate_keys={len(duplicates)}",
        },
        {
            "check": "bendigo_coverage",
            "status": "PASS" if len(bendigo_rows) > 0 else "FAIL",
            "detail": f"bendigo_rows={len(bendigo_rows)}",
        },
        {
            "check": "band_validity",
            "status": "PASS" if not invalid_bands else "FAIL",
            "detail": f"invalid_band_rows={len(invalid_bands)}",
        },
        {
            "check": "status_validity",
            "status": "PASS" if not invalid_status else "FAIL",
            "detail": f"invalid_status_rows={len(invalid_status)}",
        },
        {
            "check": "narrative_coverage",
            "status": "PASS" if not no_narrative else "FAIL",
            "detail": f"missing_narrative_non_no_evidence={len(no_narrative)}",
        },
        {
            "check": "no_trainer_wet_track_factor",
            "status": "PASS" if not trainer_wet_usage else "FAIL",
            "detail": f"trainer_wet_rows={len(trainer_wet_usage)}",
        },
        {
            "check": "heavy_jockey_only_on_heavy",
            "status": "PASS" if not heavy_bad else "FAIL",
            "detail": f"bad_heavy_jockey_rows={len(heavy_bad)}",
        },
    ]

    failures = [row for row in checks if row["status"] == "FAIL"]
    no_evidence = band_counts.get("NO_EVIDENCE", 0)
    limited = band_counts.get("LIMITED", 0)
    if failures:
        verdict = "NOT_READY"
    elif no_evidence + limited > len(rows) * 0.75:
        verdict = "READY_WITH_WARNINGS"
    else:
        verdict = "READY_FOR_UI"

    audit_rows = [
        {"built_at": built_at, **row}
        for row in checks
    ]
    write_csv(AUDIT_FILE, audit_rows, ["built_at", "check", "status", "detail"])

    summary_rows = [
        {"metric": "built_at", "value": built_at},
        {"metric": "readiness_verdict", "value": verdict},
        {"metric": "active_rows", "value": str(len(rows))},
        {"metric": "bendigo_rows", "value": str(len(bendigo_rows))},
        {"metric": "evidence_counts", "value": "; ".join(f"{k}={v}" for k, v in sorted(status_counts.items()))},
        {"metric": "band_counts", "value": "; ".join(f"{k}={v}" for k, v in sorted(band_counts.items()))},
        {"metric": "failed_checks", "value": "; ".join(row["check"] for row in failures) or "NONE"},
    ]
    write_csv(SUMMARY_FILE, summary_rows, ["metric", "value"])
    print(f"quality verdict={verdict} rows={len(rows)} bendigo={len(bendigo_rows)}")


if __name__ == "__main__":
    main()
