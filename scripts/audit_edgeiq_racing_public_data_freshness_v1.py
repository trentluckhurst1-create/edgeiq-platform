from __future__ import annotations

import csv
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"
SCRIPTS_DIR = ROOT / "scripts"

AUDIT_OUT = PUBLIC / "edgeiq_racing_public_data_freshness_v1.csv"
SUMMARY_OUT = PUBLIC / "edgeiq_racing_public_data_freshness_summary_v1.csv"
STALE_OUT = PUBLIC / "edgeiq_racing_public_data_stale_feeds_v1.csv"
MISSING_OUT = PUBLIC / "edgeiq_racing_public_data_missing_feeds_v1.csv"
SCRIPT_MAP_OUT = PUBLIC / "edgeiq_racing_feed_refresh_script_map_v1.csv"

SUMMARY_FIELDS = ["metric", "value"]
MAP_FIELDS = ["feed_name", "candidate_script", "exists", "confidence", "notes"]
AUDIT_FIELDS = [
    "feed_name",
    "path",
    "exists",
    "rows",
    "last_modified_local",
    "age_minutes",
    "freshness_status",
    "reason",
    "tab_area",
    "required_for_surface",
    "recommended_action",
]

NOW = datetime.now().astimezone()
TODAY = NOW.date()

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

FEEDS = [
    {
        "feed_name": "edgeiq_active_race_selector",
        "path": "public/data/edgeiq_active_race_selector.csv",
        "tab_area": "OVERVIEW|RACE",
        "required_for_surface": "YES",
        "mtime_max_minutes": 240,
        "check": "active_window",
        "date_columns": ["race_date", "date"],
        "allowed_past_days": 0,
        "allowed_future_days": 3,
    },
    {
        "feed_name": "edgeiq_pipeline_health",
        "path": "public/data/edgeiq_pipeline_health.csv",
        "tab_area": "OVERVIEW|MARKET|RESULTS|LEARNING",
        "required_for_surface": "YES",
        "mtime_max_minutes": 240,
        "check": "timestamp_recency",
        "timestamp_columns": ["timestamp"],
        "content_max_minutes": 240,
    },
    {
        "feed_name": "sportsbet_live_market_v1",
        "path": "public/data/sportsbet_live_market_v1.csv",
        "tab_area": "RACE|MARKET",
        "required_for_surface": "YES",
        "mtime_max_minutes": 240,
        "check": "mtime_only",
    },
    {
        "feed_name": "edgeiq_vic_live_terminal_feed_v1",
        "path": "public/data/edgeiq_vic_live_terminal_feed_v1.csv",
        "tab_area": "OVERVIEW|RACE|MARKET",
        "required_for_surface": "YES",
        "mtime_max_minutes": 240,
        "check": "active_window",
        "date_columns": ["race_date", "date"],
        "allowed_past_days": 1,
        "allowed_future_days": 3,
    },
    {
        "feed_name": "edgeiq_live_runner_board_v1",
        "path": "public/data/edgeiq_live_runner_board_v1.csv",
        "tab_area": "RACE",
        "required_for_surface": "YES",
        "mtime_max_minutes": 240,
        "check": "active_window",
        "date_columns": ["race_date", "date"],
        "allowed_past_days": 1,
        "allowed_future_days": 3,
    },
    {
        "feed_name": "edgeiq_execution_board_live",
        "path": "public/data/edgeiq_execution_board_live.csv",
        "tab_area": "RACE|MARKET",
        "required_for_surface": "YES",
        "mtime_max_minutes": 360,
        "check": "active_window",
        "date_columns": ["race_date", "date"],
        "allowed_past_days": 1,
        "allowed_future_days": 3,
    },
    {
        "feed_name": "edgeiq_execution_board_terminal",
        "path": "public/data/edgeiq_execution_board_terminal.csv",
        "tab_area": "RACE|MARKET",
        "required_for_surface": "YES",
        "mtime_max_minutes": 360,
        "check": "active_window",
        "date_columns": ["race_date", "date"],
        "allowed_past_days": 1,
        "allowed_future_days": 3,
    },
    {
        "feed_name": "edgeiq_master_runner_table",
        "path": "public/data/edgeiq_master_runner_table.csv",
        "tab_area": "RACE",
        "required_for_surface": "NO",
        "mtime_max_minutes": 720,
        "check": "active_window",
        "date_columns": ["race_date", "date"],
        "allowed_past_days": 1,
        "allowed_future_days": 3,
    },
    {
        "feed_name": "edgeiq_execution_engine_v4",
        "path": "public/data/edgeiq_execution_engine_v4.csv",
        "tab_area": "RACE|LEARNING",
        "required_for_surface": "YES",
        "mtime_max_minutes": 360,
        "check": "active_window",
        "date_columns": ["race_date", "date"],
        "allowed_past_days": 1,
        "allowed_future_days": 3,
    },
    {
        "feed_name": "edgeiq_market_tape",
        "path": "public/data/edgeiq_market_tape.csv",
        "tab_area": "MARKET",
        "required_for_surface": "YES",
        "mtime_max_minutes": 360,
        "check": "timestamp_recency",
        "timestamp_columns": ["timestamp", "built_at", "last_seen"],
        "content_max_minutes": 360,
    },
    {
        "feed_name": "edgeiq_market_tape_summary",
        "path": "public/data/edgeiq_market_tape_summary.csv",
        "tab_area": "MARKET|RESULTS|LEARNING",
        "required_for_surface": "YES",
        "mtime_max_minutes": 360,
        "check": "timestamp_recency",
        "timestamp_columns": ["last_seen", "first_seen", "built_at", "timestamp"],
        "content_max_minutes": 360,
    },
    {
        "feed_name": "edgeiq_clv_memory",
        "path": "public/data/edgeiq_clv_memory.csv",
        "tab_area": "RACE|RESULTS|LEARNING",
        "required_for_surface": "YES",
        "mtime_max_minutes": 720,
        "check": "timestamp_recency",
        "timestamp_columns": ["timestamp", "captured_at", "built_at"],
        "content_max_minutes": 720,
    },
    {
        "feed_name": "edgeiq_execution_accountability",
        "path": "public/data/edgeiq_execution_accountability.csv",
        "tab_area": "RESULTS|LEARNING",
        "required_for_surface": "YES",
        "mtime_max_minutes": 1440,
        "check": "mtime_only",
    },
    {
        "feed_name": "edgeiq_results_truth_loop",
        "path": "public/data/edgeiq_results_truth_loop.csv",
        "tab_area": "RESULTS|LEARNING",
        "required_for_surface": "YES",
        "mtime_max_minutes": 1440,
        "check": "timestamp_recency",
        "timestamp_columns": ["execution_timestamp", "settlement_timestamp", "timestamp"],
        "content_max_minutes": 1440,
    },
    {
        "feed_name": "edgeiq_results_master",
        "path": "public/data/edgeiq_results_master.csv",
        "tab_area": "RESULTS",
        "required_for_surface": "YES",
        "mtime_max_minutes": 1440,
        "check": "timestamp_recency",
        "timestamp_columns": ["settlement_timestamp", "execution_timestamp", "timestamp"],
        "content_max_minutes": 1440,
    },
    {
        "feed_name": "edgeiq_results_summary",
        "path": "public/data/edgeiq_results_summary.csv",
        "tab_area": "RESULTS",
        "required_for_surface": "YES",
        "mtime_max_minutes": 1440,
        "check": "mtime_only",
    },
    {
        "feed_name": "edgeiq_ecology_daily_report",
        "path": "public/data/edgeiq_ecology_daily_report.md",
        "tab_area": "LEARNING",
        "required_for_surface": "YES",
        "mtime_max_minutes": 1440,
        "check": "markdown_generated",
        "content_max_minutes": 1440,
    },
]

SAFE_ACTIONS = {
    "sportsbet_live_market_v1": "TRACE_UPSTREAM_SOURCE",
    "edgeiq_vic_live_terminal_feed_v1": "TRACE_UPSTREAM_SOURCE",
    "edgeiq_master_runner_table": "TRACE_UPSTREAM_SOURCE",
    "edgeiq_execution_board_live": "TRACE_UPSTREAM_SOURCE",
    "edgeiq_execution_board_terminal": "TRACE_UPSTREAM_SOURCE",
    "edgeiq_market_tape": "TRACE_UPSTREAM_SOURCE",
    "edgeiq_active_race_selector": "RUN scripts/build_edgeiq_active_race_selector.py",
    "edgeiq_pipeline_health": "RUN scripts/build_edgeiq_pipeline_health_monitor.py",
    "edgeiq_live_runner_board_v1": "RUN scripts/build_edgeiq_live_runner_board_v1.py",
    "edgeiq_execution_engine_v4": "RUN scripts/build_edgeiq_execution_engine_v4.py",
    "edgeiq_market_tape_summary": "RUN scripts/build_edgeiq_market_tape_memory.py",
    "edgeiq_clv_memory": "RUN scripts/build_edgeiq_clv_memory_engine.py",
    "edgeiq_results_truth_loop": "RUN scripts/build_edgeiq_results_truth_loop.py",
    "edgeiq_execution_accountability": "RUN scripts/build_edgeiq_results_truth_loop.py",
    "edgeiq_results_master": "RUN scripts/build_edgeiq_results_master.py",
    "edgeiq_results_summary": "RUN scripts/build_edgeiq_results_summary.py",
    "edgeiq_ecology_daily_report": "RUN scripts/build_edgeiq_ecology_daily_report_v1.py",
}


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "-", "nan", "none", "null", "undefined"} else text


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def parse_datetime(value: object) -> datetime | None:
    text = clean(value)
    if not text:
        return None
    candidates = [text, text.replace("Z", "+00:00")]
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.astimezone().replace(tzinfo=NOW.tzinfo)
            return parsed.astimezone()
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(text, fmt).astimezone()
        except ValueError:
            pass
    match = DATE_RE.search(text)
    if match:
        try:
            return datetime.fromisoformat(match.group(0)).astimezone()
        except ValueError:
            return None
    return None


def parse_date(value: object) -> datetime.date | None:
    text = clean(value)
    if not text:
        return None
    match = DATE_RE.search(text)
    if match:
        text = match.group(0)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone().date()
    except ValueError:
        return None


def file_age_minutes(path: Path) -> float | None:
    if not path.exists():
        return None
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=NOW.tzinfo)
    return round((NOW - modified).total_seconds() / 60, 1)


def safe_rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def script_candidates() -> list[Path]:
    candidates: list[Path] = []
    for extension in ("*.py", "*.ps1", "*.bat"):
        candidates.extend(sorted(ROOT.glob(extension)))
        candidates.extend(sorted(SCRIPTS_DIR.glob(extension)))
    seen: set[Path] = set()
    ordered: list[Path] = []
    for item in candidates:
        if item not in seen and item.is_file():
            seen.add(item)
            ordered.append(item)
    return ordered


def confidence_rank(value: str) -> int:
    return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(value, 0)


def detect_confidence(file_name: str, text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    escaped = re.escape(file_name)
    if re.search(rf"(OUT|SUMMARY_OUT|REPORT|LIVE_OUT|TERMINAL_OUT|DIAG|MISS)\s*=.*{escaped}", text):
        confidence = "HIGH"
    elif re.search(rf"Step\([^)]*{escaped}", text) or re.search(rf"primary_output.*{escaped}", text):
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    if "Path.cwd()" in text and "dashboard" in text and "racing-dashboard" in text:
        notes.append("cwd-sensitive path handling")
        if confidence == "HIGH":
            confidence = "MEDIUM"
    if "import pandas as pd" in text:
        notes.append("pandas dependency")
    if "subprocess.run" in text:
        notes.append("orchestrator wrapper")
    return confidence, notes


def build_script_map() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    candidates = script_candidates()
    for feed in FEEDS:
        file_name = Path(feed["path"]).name
        found = False
        for script_path in candidates:
            try:
                text = script_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if file_name not in text:
                continue
            found = True
            confidence, notes = detect_confidence(file_name, text)
            rows.append(
                {
                    "feed_name": feed["feed_name"],
                    "candidate_script": safe_rel(script_path),
                    "exists": "YES",
                    "confidence": confidence,
                    "notes": "; ".join(notes) if notes else "references feed",
                }
            )
        if not found:
            rows.append(
                {
                    "feed_name": feed["feed_name"],
                    "candidate_script": "",
                    "exists": "NO",
                    "confidence": "NONE",
                    "notes": "no candidate script reference found in scripts/ or repo root",
                }
            )
    rows.sort(
        key=lambda row: (
            row["feed_name"],
            -confidence_rank(str(row["confidence"])),
            str(row["candidate_script"]),
        )
    )
    return rows


def best_script_map_rows(map_rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    best: dict[str, dict[str, object]] = {}
    for row in map_rows:
        feed_name = str(row["feed_name"])
        current = best.get(feed_name)
        if current is None or confidence_rank(str(row["confidence"])) > confidence_rank(str(current["confidence"])):
            best[feed_name] = row
    return best


def latest_timestamp(rows: Iterable[dict[str, str]], columns: list[str]) -> datetime | None:
    latest: datetime | None = None
    for row in rows:
        for column in columns:
            parsed = parse_datetime(row.get(column))
            if parsed and (latest is None or parsed > latest):
                latest = parsed
    return latest


def latest_date(rows: Iterable[dict[str, str]], columns: list[str]) -> datetime.date | None:
    latest: datetime.date | None = None
    for row in rows:
        for column in columns:
            parsed = parse_date(row.get(column))
            if parsed and (latest is None or parsed > latest):
                latest = parsed
    return latest


def markdown_generated_at(path: Path) -> datetime | None:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    match = re.search(r"^Generated:\s*(.+)$", text, flags=re.MULTILINE)
    if not match:
        return None
    return parse_datetime(match.group(1))


def mtime_reason(path: Path, max_minutes: int) -> tuple[str, str]:
    age = file_age_minutes(path)
    if age is None:
        return "UNKNOWN", "file age unavailable"
    if age > max_minutes:
        return "STALE", f"file modified {age:.1f}m ago, above {max_minutes}m threshold"
    return "FRESH", f"file modified {age:.1f}m ago, within {max_minutes}m threshold"


def content_reason(feed: dict[str, object], path: Path, rows: list[dict[str, str]]) -> tuple[str, str]:
    check = str(feed.get("check"))
    if check == "mtime_only":
        return mtime_reason(path, int(feed["mtime_max_minutes"]))
    if check == "timestamp_recency":
        latest = latest_timestamp(rows, list(feed.get("timestamp_columns", [])))
        if latest is None:
            return mtime_reason(path, int(feed["mtime_max_minutes"]))
        age = round((NOW - latest).total_seconds() / 60, 1)
        threshold = int(feed.get("content_max_minutes", feed["mtime_max_minutes"]))
        if age > threshold:
            return "STALE", f"latest content timestamp {latest.isoformat(timespec='minutes')} is {age:.1f}m old"
        return "FRESH", f"latest content timestamp {latest.isoformat(timespec='minutes')} is within {threshold}m"
    if check == "active_window":
        latest = latest_date(rows, list(feed.get("date_columns", [])))
        if latest is None:
            return mtime_reason(path, int(feed["mtime_max_minutes"]))
        allowed_past = int(feed.get("allowed_past_days", 0))
        allowed_future = int(feed.get("allowed_future_days", 0))
        if latest < TODAY - timedelta(days=allowed_past):
            return "STALE", f"latest content race_date {latest.isoformat()} is outside active window"
        if latest > TODAY + timedelta(days=allowed_future):
            return "UNKNOWN", f"latest content race_date {latest.isoformat()} is beyond expected active window"
        return "FRESH", f"latest content race_date {latest.isoformat()} sits within active window"
    if check == "markdown_generated":
        generated = markdown_generated_at(path)
        if generated is None:
            return mtime_reason(path, int(feed["mtime_max_minutes"]))
        age = round((NOW - generated).total_seconds() / 60, 1)
        threshold = int(feed.get("content_max_minutes", feed["mtime_max_minutes"]))
        if age > threshold:
            return "STALE", f"report generated at {generated.isoformat(timespec='minutes')} is {age:.1f}m old"
        return "FRESH", f"report generated at {generated.isoformat(timespec='minutes')} is within {threshold}m"
    return "UNKNOWN", "no freshness rule configured"


def recommended_action(feed: dict[str, object], best_map: dict[str, dict[str, object]], status: str) -> str:
    if status == "FRESH":
        return "NO_ACTION"
    if str(feed["feed_name"]) in SAFE_ACTIONS:
        return SAFE_ACTIONS[str(feed["feed_name"])]
    candidate = best_map.get(str(feed["feed_name"]))
    if not candidate or str(candidate["exists"]) != "YES" or str(candidate["confidence"]) == "NONE":
        return "TRACE_UPSTREAM_SOURCE"
    confidence = str(candidate["confidence"])
    script_name = str(candidate["candidate_script"])
    if confidence == "HIGH":
        return f"RUN {script_name}"
    if confidence == "MEDIUM":
        return f"REVIEW_AND_RUN {script_name}"
    return f"LOW_CONFIDENCE_TRACE {script_name}"


def audit_feed(feed: dict[str, object], best_map: dict[str, dict[str, object]]) -> dict[str, object]:
    path = ROOT / str(feed["path"])
    exists = path.exists()
    age = file_age_minutes(path)
    last_modified = (
        datetime.fromtimestamp(path.stat().st_mtime, tz=NOW.tzinfo).isoformat(timespec="seconds")
        if exists
        else ""
    )

    if not exists:
        status = "MISSING"
        reason = "feed missing on disk"
        rows = 0
    elif path.suffix.lower() == ".md":
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            text = ""
            reason = f"markdown read failed: {type(exc).__name__}"
            status = "UNKNOWN"
            rows = 0
        else:
            rows = 1 if clean(text) else 0
            if rows == 0:
                status = "EMPTY"
                reason = "markdown file is empty"
            else:
                status, reason = content_reason(feed, path, [])
    else:
        rows_data = read_csv(path)
        rows = len(rows_data)
        if rows == 0:
            status = "EMPTY"
            reason = "csv has no data rows"
        else:
            status, reason = content_reason(feed, path, rows_data)

    row = {
        "feed_name": feed["feed_name"],
        "path": str(feed["path"]).replace("\\", "/"),
        "exists": "YES" if exists else "NO",
        "rows": rows,
        "last_modified_local": last_modified,
        "age_minutes": "" if age is None else age,
        "freshness_status": status,
        "reason": reason,
        "tab_area": feed["tab_area"],
        "required_for_surface": feed["required_for_surface"],
        "recommended_action": "",
    }

    if (
        status == "STALE"
        and age is not None
        and age <= int(feed["mtime_max_minutes"]) + 5
        and reason.startswith("latest content ")
    ):
        row["recommended_action"] = "TRACE_UPSTREAM_SOURCE"
    else:
        row["recommended_action"] = recommended_action(feed, best_map, status)
    return row


def build_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    counts = {
        "feeds_audited": len(rows),
        "fresh_count": sum(1 for row in rows if row["freshness_status"] == "FRESH"),
        "stale_count": sum(1 for row in rows if row["freshness_status"] == "STALE"),
        "empty_count": sum(1 for row in rows if row["freshness_status"] == "EMPTY"),
        "missing_count": sum(1 for row in rows if row["freshness_status"] == "MISSING"),
        "unknown_count": sum(1 for row in rows if row["freshness_status"] == "UNKNOWN"),
        "required_surface_blockers": sum(
            1
            for row in rows
            if row["required_for_surface"] == "YES" and row["freshness_status"] in {"STALE", "EMPTY", "MISSING", "UNKNOWN"}
        ),
    }
    stalest = sorted(
        [row for row in rows if row["freshness_status"] in {"STALE", "EMPTY", "MISSING", "UNKNOWN"}],
        key=lambda row: (row["freshness_status"] != "MISSING", -(float(row["age_minutes"]) if clean(row["age_minutes"]) else 0.0)),
    )
    summary_rows = [{"metric": key, "value": value} for key, value in counts.items()]
    if stalest:
        top = stalest[0]
        summary_rows.extend(
            [
                {"metric": "top_blocker_feed", "value": top["feed_name"]},
                {"metric": "top_blocker_status", "value": top["freshness_status"]},
                {"metric": "top_blocker_reason", "value": top["reason"]},
            ]
        )
    return summary_rows


def main() -> None:
    map_rows = build_script_map()
    write_csv(SCRIPT_MAP_OUT, map_rows, MAP_FIELDS)
    best_map = best_script_map_rows(map_rows)

    audit_rows = [audit_feed(feed, best_map) for feed in FEEDS]
    audit_rows.sort(key=lambda row: (row["tab_area"], row["feed_name"]))
    write_csv(AUDIT_OUT, audit_rows, AUDIT_FIELDS)
    write_csv(SUMMARY_OUT, build_summary(audit_rows), SUMMARY_FIELDS)
    write_csv(
        STALE_OUT,
        [row for row in audit_rows if row["freshness_status"] in {"STALE", "EMPTY", "UNKNOWN"}],
        AUDIT_FIELDS,
    )
    write_csv(
        MISSING_OUT,
        [row for row in audit_rows if row["freshness_status"] == "MISSING"],
        AUDIT_FIELDS,
    )

    print("=" * 96)
    print("EDGEIQ RACING PUBLIC DATA FRESHNESS AUDIT V1")
    print("=" * 96)
    for row in audit_rows:
        print(
            f"{row['feed_name']}: {row['freshness_status']} | rows={row['rows']} | "
            f"age_minutes={row['age_minutes']} | {row['reason']}"
        )
    print("-" * 96)
    print("AUDIT:", AUDIT_OUT)
    print("SUMMARY:", SUMMARY_OUT)
    print("STALE:", STALE_OUT)
    print("MISSING:", MISSING_OUT)
    print("SCRIPT MAP:", SCRIPT_MAP_OUT)


if __name__ == "__main__":
    main()
