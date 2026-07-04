from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SOURCE = DATA / "edgeiq_gear_profile_feed_v1.csv"
RUNNER_BOARD = DATA / "edgeiq_live_runner_board_governed_v1.csv"
OUT = DATA / "edgeiq_gear_terminal_feed_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_gear_terminal_feed_summary_v1.csv"

FIELDS = [
    "race_date",
    "track",
    "race_no",
    "race_key",
    "runner",
    "normalized_runner",
    "gear_current",
    "gear_changes",
    "gear_added",
    "gear_removed",
    "first_time_gear",
    "gear_change_flag",
    "source_confidence",
]

DAY_BUCKETS = {"TODAY", "TOMORROW", "DAY+2", "DAY 2", "DAY_2", "DY+2"}
MAX_RUNS_PER_RUNNER = 5
WARN_ROWS = 5000
FAIL_ROWS = 10000


def text(value: object) -> str:
    return str(value or "").strip()


def norm_runner(value: object) -> str:
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def date_key(value: object) -> str:
    raw = text(value)
    try:
        return datetime.fromisoformat(raw[:10]).strftime("%Y%m%d")
    except ValueError:
        return "".join(ch for ch in raw if ch.isdigit())


def clean_gear_value(value: object) -> str:
    raw = text(value)
    upper = raw.upper()
    if not raw:
        return ""
    if "NO LISTED GEAR CHANGE" in upper or "NO_GEAR" in upper:
        return ""
    if raw.count(";") > 4 and not any(token in upper for token in ["BLINK", "VISOR", "WINK", "TONGUE", "GELD", "LUG", "SHOE", "BANDAGE", "PACIFIER"]):
        return ""
    return raw


def read_csv(path: Path):
    if not path.exists():
        return
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        yield from csv.DictReader(handle)


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def candidate_runners() -> set[str]:
    candidates: set[str] = set()
    for row in read_csv(RUNNER_BOARD) or []:
        day_bucket = text(row.get("day_bucket", "")).upper()
        if day_bucket and day_bucket not in DAY_BUCKETS:
            continue
        runner = norm_runner(row.get("horse") or row.get("runner") or row.get("runner_name"))
        if runner:
            candidates.add(runner)
    return candidates


def main() -> None:
    candidates = candidate_runners()
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    source_rows = 0
    matched_rows = 0

    for row in read_csv(SOURCE) or []:
        source_rows += 1
        runner_key = norm_runner(row.get("normalized_runner") or row.get("runner"))
        if runner_key not in candidates:
            continue
        matched_rows += 1
        kept = grouped[runner_key]
        output_row = {field: text(row.get(field)) for field in FIELDS}
        for gear_field in ["gear_current", "gear_changes", "gear_added", "gear_removed", "first_time_gear"]:
            output_row[gear_field] = clean_gear_value(output_row.get(gear_field))
        if not any(output_row.get(field) for field in ["gear_current", "gear_changes", "gear_added", "gear_removed", "first_time_gear"]):
            output_row["gear_change_flag"] = "NO"
        kept.append(output_row)
        kept.sort(key=lambda item: date_key(item.get("race_date")), reverse=True)
        del kept[MAX_RUNS_PER_RUNNER:]

    rows = [item for group in grouped.values() for item in group]
    rows.sort(key=lambda item: (item.get("normalized_runner", ""), date_key(item.get("race_date"))), reverse=True)

    status = "OK"
    if len(rows) > FAIL_ROWS:
        status = "FAILED_OVER_10000"
    elif len(rows) > WARN_ROWS:
        status = "WARN_OVER_5000"

    write_csv(OUT, rows, FIELDS)
    summary = {
        "source_file": str(SOURCE.relative_to(ROOT)),
        "output_file": str(OUT.relative_to(ROOT)),
        "source_rows_scanned": source_rows,
        "candidate_runners": len(candidates),
        "matched_source_rows": matched_rows,
        "terminal_rows": len(rows),
        "target_under_rows": WARN_ROWS,
        "hard_limit_rows": FAIL_ROWS,
        "status": status,
        "built_at": datetime.now().replace(microsecond=0).isoformat(),
    }
    write_csv(SUMMARY_OUT, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(rows)} rows)")
    print(f"Wrote {SUMMARY_OUT}")
    if len(rows) > FAIL_ROWS:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
