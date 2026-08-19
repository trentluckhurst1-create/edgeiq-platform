from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORY = DATA / "edgeiq_price_truth_history_v1.csv"
DEDUPE_SUMMARY = DATA / "edgeiq_price_truth_snapshot_dedupe_v1_summary.csv"
PIPELINE_SUMMARY = DATA / "edgeiq_price_truth_pipeline_status_v1_summary.csv"

OUTPUT = DATA / "edgeiq_snapshot_count_mismatch_v1.csv"
SUMMARY = DATA / "edgeiq_snapshot_count_mismatch_v1_summary.csv"

DETAIL_COLUMNS = [
    "snapshot_timestamp",
    "history_rows",
    "history_races",
    "history_runners",
    "dedupe_summary_rows",
    "dedupe_summary_races",
    "dedupe_summary_runners",
    "timestamp_present_in_dedupe_summary",
    "timestamp_duplicate_in_history",
    "diagnosis",
    "built_at",
]

SUMMARY_COLUMNS = [
    "section",
    "metric",
    "value",
    "source_path",
    "notes",
    "built_at",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def has_text(value: object) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and text.lower() != "nan"


def norm(value: object) -> str:
    if not has_text(value):
        return ""
    return " ".join(str(value).upper().strip().split())


def clean_race_no(value: object) -> str:
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def int_or_none(value: object) -> int | None:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def latest_summary_value(rows: list[dict[str, str]], section: str, metric: str) -> str:
    value = ""
    for row in rows:
        if row.get("section") == section and row.get("metric") == metric:
            value = str(row.get("value", "")).strip()
    return value


def summary_snapshot_metric(rows: list[dict[str, str]], metric: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in rows:
        if row.get("section") == "snapshot" and row.get("metric") == metric:
            result[str(row.get("snapshot_timestamp", "")).strip()] = str(row.get("value", "")).strip()
    return result


def history_counts(history_rows: list[dict[str, str]]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in history_rows:
        timestamp = str(row.get("snapshot_timestamp", "")).strip()
        grouped.setdefault(timestamp, []).append(row)

    counts: dict[str, dict[str, object]] = {}
    for timestamp, rows in grouped.items():
        race_keys = {
            "|".join(
                [
                    norm(row.get("race_date", "")),
                    norm(row.get("track", "")),
                    clean_race_no(row.get("race_no", "")),
                ]
            )
            for row in rows
        }
        runner_keys = {
            "|".join(
                [
                    timestamp,
                    norm(row.get("track", "")),
                    clean_race_no(row.get("race_no", "")),
                    norm(row.get("horse_key", "")),
                ]
            )
            for row in rows
        }
        counts[timestamp] = {
            "rows": len(rows),
            "races": len(race_keys),
            "runners": len(runner_keys),
        }
    return counts


def summary_row(
    section: str,
    metric: str,
    value: object,
    source_path: Path | str = "",
    notes: str = "",
) -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "source_path": rel(source_path) if isinstance(source_path, Path) else source_path,
        "notes": notes,
        "built_at": now_utc(),
    }


def determine_root_cause(
    correct_snapshot_count: int,
    dedupe_snapshot_count: int | None,
    pipeline_snapshot_count: int | None,
    missing_from_dedupe: list[str],
    timestamp_duplicate_count: int,
) -> str:
    if timestamp_duplicate_count:
        return "SNAPSHOT_TIMESTAMPS_DUPLICATED_IN_HISTORY"
    if dedupe_snapshot_count != correct_snapshot_count and pipeline_snapshot_count == dedupe_snapshot_count:
        return "DEDUPE_SUMMARY_STALE_AND_PIPELINE_INHERITED_STALE_COUNT"
    if dedupe_snapshot_count == correct_snapshot_count and pipeline_snapshot_count != correct_snapshot_count:
        return "PIPELINE_STATUS_STALE_OR_COUNT_LOGIC_DIFFERS"
    if missing_from_dedupe:
        return "DEDUPE_SUMMARY_STALE_MISSING_LATEST_TIMESTAMP"
    if dedupe_snapshot_count == correct_snapshot_count and pipeline_snapshot_count == correct_snapshot_count:
        return "NO_MISMATCH"
    return "SNAPSHOT_COUNT_LOGIC_DIFFERS"


def build_outputs() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    history = read_csv(HISTORY)
    dedupe = read_csv(DEDUPE_SUMMARY)
    pipeline = read_csv(PIPELINE_SUMMARY)

    counts = history_counts(history)
    timestamp_frequency = Counter(str(row.get("snapshot_timestamp", "")).strip() for row in history)
    duplicate_timestamps = [
        timestamp for timestamp, count in timestamp_frequency.items() if timestamp and count not in {0, 87}
    ]

    dedupe_rows_by_timestamp = summary_snapshot_metric(dedupe, "rows_per_snapshot")
    dedupe_races_by_timestamp = summary_snapshot_metric(dedupe, "races_per_snapshot")
    dedupe_runners_by_timestamp = summary_snapshot_metric(dedupe, "runners_per_snapshot")

    detail_rows: list[dict[str, object]] = []
    for timestamp in sorted(counts):
        present_in_dedupe = timestamp in dedupe_rows_by_timestamp
        history_row_count = int(counts[timestamp]["rows"])
        dedupe_row_count = int_or_none(dedupe_rows_by_timestamp.get(timestamp, ""))
        if not present_in_dedupe:
            diagnosis = "MISSING_FROM_DEDUPE_SUMMARY"
        elif dedupe_row_count != history_row_count:
            diagnosis = "DEDUPE_ROW_COUNT_DIFFERS"
        else:
            diagnosis = "MATCHED"

        detail_rows.append(
            {
                "snapshot_timestamp": timestamp,
                "history_rows": history_row_count,
                "history_races": counts[timestamp]["races"],
                "history_runners": counts[timestamp]["runners"],
                "dedupe_summary_rows": dedupe_rows_by_timestamp.get(timestamp, ""),
                "dedupe_summary_races": dedupe_races_by_timestamp.get(timestamp, ""),
                "dedupe_summary_runners": dedupe_runners_by_timestamp.get(timestamp, ""),
                "timestamp_present_in_dedupe_summary": "TRUE" if present_in_dedupe else "FALSE",
                "timestamp_duplicate_in_history": "TRUE" if timestamp in duplicate_timestamps else "FALSE",
                "diagnosis": diagnosis,
                "built_at": now_utc(),
            }
        )

    correct_snapshot_count = len(counts)
    correct_total_rows = len(history)
    dedupe_snapshot_count = int_or_none(latest_summary_value(dedupe, "overall", "unique_snapshots"))
    dedupe_total_rows = int_or_none(latest_summary_value(dedupe, "overall", "total_rows"))
    pipeline_snapshot_count = int_or_none(latest_summary_value(pipeline, "panel", "unique_snapshots"))
    pipeline_total_rows = int_or_none(latest_summary_value(pipeline, "panel", "total_history_rows"))
    missing_from_dedupe = [
        str(row["snapshot_timestamp"])
        for row in detail_rows
        if row["timestamp_present_in_dedupe_summary"] == "FALSE"
    ]
    root_cause = determine_root_cause(
        correct_snapshot_count,
        dedupe_snapshot_count,
        pipeline_snapshot_count,
        missing_from_dedupe,
        len(duplicate_timestamps),
    )

    summary_rows = [
        summary_row("input", "history_file_found", HISTORY.exists(), HISTORY),
        summary_row("input", "dedupe_summary_found", DEDUPE_SUMMARY.exists(), DEDUPE_SUMMARY),
        summary_row("input", "pipeline_status_summary_found", PIPELINE_SUMMARY.exists(), PIPELINE_SUMMARY),
        summary_row("history", "total_rows", correct_total_rows, HISTORY),
        summary_row("history", "distinct_timestamps", correct_snapshot_count, HISTORY),
        summary_row("history", "correct_snapshot_count", correct_snapshot_count, HISTORY),
        summary_row(
            "history",
            "timestamps",
            "|".join(sorted(counts)),
            HISTORY,
        ),
        summary_row(
            "history",
            "timestamps_with_non_87_row_count",
            "|".join(duplicate_timestamps),
            HISTORY,
            "This flags unexpected row counts per snapshot, not ordinary 87-row repeated snapshots.",
        ),
        summary_row(
            "history",
            "timestamp_duplicate_issue_count",
            len(duplicate_timestamps),
            HISTORY,
        ),
        summary_row("dedupe_summary", "total_rows", dedupe_total_rows if dedupe_total_rows is not None else "", DEDUPE_SUMMARY),
        summary_row(
            "dedupe_summary",
            "unique_snapshots",
            dedupe_snapshot_count if dedupe_snapshot_count is not None else "",
            DEDUPE_SUMMARY,
        ),
        summary_row(
            "dedupe_summary",
            "snapshot_timestamps",
            "|".join(sorted(dedupe_rows_by_timestamp)),
            DEDUPE_SUMMARY,
        ),
        summary_row(
            "dedupe_summary",
            "missing_history_timestamps",
            "|".join(missing_from_dedupe),
            DEDUPE_SUMMARY,
        ),
        summary_row(
            "pipeline_status",
            "total_history_rows",
            pipeline_total_rows if pipeline_total_rows is not None else "",
            PIPELINE_SUMMARY,
        ),
        summary_row(
            "pipeline_status",
            "unique_snapshots",
            pipeline_snapshot_count if pipeline_snapshot_count is not None else "",
            PIPELINE_SUMMARY,
        ),
        summary_row(
            "diagnosis",
            "history_vs_dedupe_snapshot_count_match",
            "TRUE" if dedupe_snapshot_count == correct_snapshot_count else "FALSE",
        ),
        summary_row(
            "diagnosis",
            "history_vs_pipeline_snapshot_count_match",
            "TRUE" if pipeline_snapshot_count == correct_snapshot_count else "FALSE",
        ),
        summary_row("diagnosis", "root_cause", root_cause),
        summary_row(
            "diagnosis",
            "recommended_action",
            "RERUN_DEDUPE_AUDIT_THEN_PIPELINE_STATUS"
            if root_cause != "NO_MISMATCH"
            else "NO_ACTION",
        ),
    ]
    return detail_rows, summary_rows


def main() -> None:
    detail_rows, summary_rows = build_outputs()
    write_csv(OUTPUT, detail_rows, DETAIL_COLUMNS)
    write_csv(SUMMARY, summary_rows, SUMMARY_COLUMNS)

    print("=" * 96)
    print("EDGEIQ SNAPSHOT COUNT MISMATCH DIAGNOSTIC V1 - READ ONLY")
    print("=" * 96)
    print(f"wrote: {OUTPUT}")
    print(f"wrote: {SUMMARY}")
    print("")
    for row in summary_rows:
        if row["section"] in {"history", "dedupe_summary", "pipeline_status", "diagnosis"}:
            print(f"{row['section']},{row['metric']},{row['value']},{row['notes']}")
    print("")
    for row in detail_rows:
        print(
            f"timestamp={row['snapshot_timestamp']} "
            f"history_rows={row['history_rows']} "
            f"dedupe_rows={row['dedupe_summary_rows']} "
            f"diagnosis={row['diagnosis']}"
        )
    print("=" * 96)


if __name__ == "__main__":
    main()
