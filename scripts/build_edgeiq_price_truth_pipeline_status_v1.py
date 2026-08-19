from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PRICE_TRUTH_HISTORY = DATA / "edgeiq_price_truth_history_v1.csv"
HEALTH_SUMMARY = DATA / "edgeiq_price_truth_history_v1_health_summary.csv"
DEDUPE_SUMMARY = DATA / "edgeiq_price_truth_snapshot_dedupe_v1_summary.csv"
DAILY_SNAPSHOT_SUMMARY = DATA / "edgeiq_price_truth_daily_snapshot_v1_summary.csv"
SETTLEMENT_AUDIT = DATA / "edgeiq_price_truth_settlement_v1_audit.csv"

OUTPUT = DATA / "edgeiq_price_truth_pipeline_status_v1.csv"
SUMMARY = DATA / "edgeiq_price_truth_pipeline_status_v1_summary.csv"

SAFE_SETTLED_STATUSES = {"FINAL", "FAILED_TO_FINISH", "CONFIRMED_SCRATCHED"}

PANEL_COLUMNS = [
    "built_at",
    "price_truth_pipeline_status",
    "price_truth_health_status",
    "dedupe_status",
    "latest_snapshot_status",
    "settlement_write_status",
    "settlement_ready",
    "calibration_possible",
    "total_history_rows",
    "unique_snapshots",
    "races_per_snapshot",
    "runners_per_snapshot",
    "settled_rows",
    "pending_result_rows",
    "blank_result_fields",
    "result_fields_populated",
    "final_rows",
    "failed_to_finish_rows",
    "confirmed_scratched_rows",
    "winner_rows",
    "starting_price_populated_rows",
    "next_action",
    "next_action_reason",
]

SUMMARY_COLUMNS = ["section", "metric", "value", "source_path", "notes", "built_at"]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def clean(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "nan", "none", "null", "undefined", "n/a"}:
        return ""
    return text


def norm(value: object) -> str:
    return " ".join(clean(value).upper().split())


def clean_race_no(value: object) -> str:
    text = clean(value)
    if text.endswith(".0"):
        text = text[:-2]
    return text


def has_text(value: object) -> bool:
    return bool(clean(value))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def latest_value(rows: list[dict[str, str]], section: str, metric: str) -> str:
    value = ""
    for row in rows:
        if row.get("section") == section and row.get("metric") == metric:
            value = clean(row.get("value"))
    return value


def metric_int(rows: list[dict[str, str]], section: str, metric: str, default: int = 0) -> int:
    raw = latest_value(rows, section, metric)
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return default


def first_metric_by_section(rows: list[dict[str, str]], section: str, preferred: list[str]) -> str:
    for metric in preferred:
        value = latest_value(rows, section, metric)
        if value:
            return value
    return ""


def derive_health_status(health_rows: list[dict[str, str]]) -> str:
    if not health_rows:
        return "MISSING_HEALTH_SUMMARY"
    health_counts = [
        row for row in health_rows if row.get("section") == "health_status_counts" and has_text(row.get("metric"))
    ]
    if health_counts:
        ranked = sorted(
            health_counts,
            key=lambda row: int(float(clean(row.get("value")) or "0")),
            reverse=True,
        )
        return clean(ranked[0].get("metric"))
    if metric_int(health_rows, "results", "blank_result_fields_count") == 0:
        return "PASS_HEALTH_FIELDS"
    return "HEALTH_REVIEW_REQUIRED"


def derive_dedupe_status(dedupe_rows: list[dict[str, str]]) -> str:
    if not dedupe_rows:
        return "MISSING_DEDUPE_SUMMARY"
    return latest_value(dedupe_rows, "status", "dedupe_status") or "UNKNOWN_DEDUPE_STATUS"


def derive_settlement_write_status(settlement_rows: list[dict[str, str]]) -> str:
    if not settlement_rows:
        return "MISSING_SETTLEMENT_AUDIT"
    return latest_value(settlement_rows, "status", "settlement_write_status") or "UNKNOWN_SETTLEMENT_WRITE_STATUS"


def derive_latest_snapshot_status(daily_rows: list[dict[str, str]], settled_rows: int, blank_result_fields: int) -> str:
    if settled_rows > 0 and blank_result_fields == 0:
        return "PRICE_TRUTH_SETTLED"
    if not daily_rows:
        return "MISSING_DAILY_SNAPSHOT_SUMMARY"
    return first_metric_by_section(daily_rows, "final", ["final_status", "snapshot_status"]) or "UNKNOWN_DAILY_SNAPSHOT_STATUS"


def compact_counts(values: list[int]) -> str:
    if not values:
        return ""
    unique = []
    for value in values:
        if value not in unique:
            unique.append(value)
    if len(unique) == 1:
        return str(unique[0])
    return "|".join(str(value) for value in unique)


def history_status(history_rows: list[dict[str, str]]) -> dict[str, object]:
    snapshots = defaultdict(list)
    races_by_snapshot: dict[str, set[str]] = defaultdict(set)
    runners_by_snapshot: dict[str, set[str]] = defaultdict(set)
    status_counts: Counter[str] = Counter()
    blank_result_fields = 0
    settled_rows = 0
    winner_rows = 0
    starting_price_rows = 0

    for row in history_rows:
        snapshot = clean(row.get("snapshot_timestamp"))
        race_key = "|".join([clean(row.get("race_date")), norm(row.get("track")), clean_race_no(row.get("race_no"))])
        runner_key = "|".join([race_key, norm(row.get("horse_key")) or norm(row.get("horse"))])
        snapshots[snapshot].append(row)
        races_by_snapshot[snapshot].add(race_key)
        runners_by_snapshot[snapshot].add(runner_key)

        status = clean(row.get("result_status"))
        finish_position = clean(row.get("finish_position"))
        won = clean(row.get("won"))
        settlement_source = clean(row.get("settlement_source"))
        status_counts[status] += 1

        core_fields_populated = bool(status and finish_position and won and settlement_source)
        if not core_fields_populated:
            blank_result_fields += 1
        if status in SAFE_SETTLED_STATUSES and core_fields_populated:
            settled_rows += 1
        if norm(won) == "TRUE":
            winner_rows += 1
        if has_text(row.get("starting_price")):
            starting_price_rows += 1

    total_rows = len(history_rows)
    pending_result_rows = total_rows - settled_rows
    race_counts = [len(races) for _, races in sorted(races_by_snapshot.items())]
    runner_counts = [len(runners) for _, runners in sorted(runners_by_snapshot.items())]

    return {
        "total_history_rows": total_rows,
        "unique_snapshots": len([snapshot for snapshot in snapshots if snapshot]),
        "races_per_snapshot": compact_counts(race_counts),
        "runners_per_snapshot": compact_counts(runner_counts),
        "settled_rows": settled_rows,
        "pending_result_rows": pending_result_rows,
        "blank_result_fields": blank_result_fields,
        "result_fields_populated": total_rows - blank_result_fields,
        "final_rows": status_counts.get("FINAL", 0),
        "failed_to_finish_rows": status_counts.get("FAILED_TO_FINISH", 0),
        "confirmed_scratched_rows": status_counts.get("CONFIRMED_SCRATCHED", 0),
        "winner_rows": winner_rows,
        "starting_price_populated_rows": starting_price_rows,
    }


def derive_pipeline_status(history_stats: dict[str, object]) -> str:
    settled_rows = int(history_stats["settled_rows"])
    blank_result_fields = int(history_stats["blank_result_fields"])
    total_rows = int(history_stats["total_history_rows"])
    if total_rows > 0 and settled_rows == total_rows and blank_result_fields == 0:
        return "PRICE_TRUTH_SETTLED"
    if settled_rows > 0:
        return "PRICE_TRUTH_PARTIALLY_SETTLED"
    return "PRICE_TRUTH_PENDING_RESULTS"


def derive_next_action(history_stats: dict[str, object], health_status: str, dedupe_status: str) -> tuple[str, str, str, str]:
    settled_rows = int(history_stats["settled_rows"])
    blank_result_fields = int(history_stats["blank_result_fields"])
    total_rows = int(history_stats["total_history_rows"])

    if dedupe_status != "DEDUPE_PASS":
        return "FALSE", "FALSE", "FIX_DUPLICATE_SNAPSHOTS", f"Dedupe status is {dedupe_status}."
    if health_status.startswith("MISSING") or health_status == "HEALTH_REVIEW_REQUIRED":
        return "FALSE", "FALSE", "FIX_PRICE_TRUTH_HISTORY", f"Health status is {health_status}."
    if settled_rows > 0 and blank_result_fields == 0 and settled_rows == total_rows:
        return "TRUE", "TRUE", "BUILD_CALIBRATION_ENGINE", f"{settled_rows} settled result rows are populated with no blank core settlement fields."
    if blank_result_fields > 0:
        return "FALSE", "FALSE", "MONITOR_RESULTS", f"{blank_result_fields} rows still have blank core settlement fields."
    return "FALSE", "FALSE", "MONITOR_RESULTS", "Price truth is not fully settled yet."


def summary_row(section: str, metric: str, value: object, source_path: Path | str = "", notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "source_path": rel(source_path) if isinstance(source_path, Path) else source_path,
        "notes": notes,
        "built_at": now_utc(),
    }


def build_panel() -> tuple[dict[str, object], list[dict[str, object]]]:
    history_rows = read_csv(PRICE_TRUTH_HISTORY)
    health_rows = read_csv(HEALTH_SUMMARY)
    dedupe_rows = read_csv(DEDUPE_SUMMARY)
    daily_rows = read_csv(DAILY_SNAPSHOT_SUMMARY)
    settlement_rows = read_csv(SETTLEMENT_AUDIT)

    history_stats = history_status(history_rows)
    health_status = derive_health_status(health_rows)
    dedupe_status = derive_dedupe_status(dedupe_rows)
    settlement_write_status = derive_settlement_write_status(settlement_rows)
    latest_snapshot_status = derive_latest_snapshot_status(
        daily_rows,
        int(history_stats["settled_rows"]),
        int(history_stats["blank_result_fields"]),
    )
    pipeline_status = derive_pipeline_status(history_stats)
    settlement_ready, calibration_possible, next_action, next_action_reason = derive_next_action(
        history_stats,
        health_status,
        dedupe_status,
    )

    panel: dict[str, object] = {
        "built_at": now_utc(),
        "price_truth_pipeline_status": pipeline_status,
        "price_truth_health_status": health_status,
        "dedupe_status": dedupe_status,
        "latest_snapshot_status": latest_snapshot_status,
        "settlement_write_status": settlement_write_status,
        "settlement_ready": settlement_ready,
        "calibration_possible": calibration_possible,
        **history_stats,
        "next_action": next_action,
        "next_action_reason": next_action_reason,
    }

    summary_rows: list[dict[str, object]] = []
    for path in [PRICE_TRUTH_HISTORY, HEALTH_SUMMARY, DEDUPE_SUMMARY, DAILY_SNAPSHOT_SUMMARY, SETTLEMENT_AUDIT]:
        summary_rows.append(
            summary_row(
                "input",
                path.name,
                "FOUND" if path.exists() else "MISSING",
                path,
                f"rows={len(read_csv(path)) if path.exists() else 0}",
            )
        )

    for column in PANEL_COLUMNS:
        if column == "built_at":
            continue
        summary_rows.append(summary_row("panel", column, panel.get(column, "")))

    dedupe_unique_snapshots = metric_int(dedupe_rows, "overall", "unique_snapshots")
    if dedupe_unique_snapshots and dedupe_unique_snapshots != int(history_stats["unique_snapshots"]):
        summary_rows.append(
            summary_row(
                "diagnosis",
                "dedupe_summary_snapshot_count_stale",
                "TRUE",
                DEDUPE_SUMMARY,
                f"dedupe_summary={dedupe_unique_snapshots}; history_direct={history_stats['unique_snapshots']}",
            )
        )
    else:
        summary_rows.append(summary_row("diagnosis", "dedupe_summary_snapshot_count_stale", "FALSE", DEDUPE_SUMMARY))

    summary_rows.append(
        summary_row(
            "diagnosis",
            "result_readiness_source_used",
            "PRICE_TRUTH_HISTORY_DIRECT",
            PRICE_TRUTH_HISTORY,
            "Stale result-readiness diagnostics are ignored once history has settled rows.",
        )
    )
    return panel, summary_rows


def main() -> None:
    panel, summary_rows = build_panel()
    panel_public = {column: panel.get(column, "") for column in PANEL_COLUMNS}

    write_csv(OUTPUT, [panel_public], PANEL_COLUMNS)
    write_csv(SUMMARY, summary_rows, SUMMARY_COLUMNS)

    print("=" * 96)
    print("EDGEIQ PRICE TRUTH PIPELINE STATUS V1 - READ ONLY")
    print("=" * 96)
    print(f"wrote: {OUTPUT}")
    print(f"wrote: {SUMMARY}")
    print("")
    for column in PANEL_COLUMNS:
        print(f"{column}: {panel_public[column]}")
    print("=" * 96)


if __name__ == "__main__":
    main()
