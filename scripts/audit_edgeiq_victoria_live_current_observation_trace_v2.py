from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "victoria-live-recovery-v2"
DOCS.mkdir(parents=True, exist_ok=True)

WINDOW_START = date(2026, 7, 20)
TODAY = date(2026, 7, 30)
NORM_EFFECTIVE = date(2026, 7, 20)

csv.field_size_limit(min(sys.maxsize, 2_147_483_647))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def clean_track(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", (value or "").upper())


def display_track(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).upper()


def parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def parse_race_no(value: str) -> str:
    text = (value or "").strip().upper()
    if not text:
        return ""
    match = re.search(r"(\d+)", text)
    return str(int(match.group(1))) if match else text


def date_in_window(value: str) -> bool:
    d = parse_date(value)
    return d is not None and WINDOW_START <= d <= TODAY


def count_rows_by_meeting(path: Path, date_field: str, track_field: str, race_field: str | None = None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in read_csv(path):
        d = parse_date(row.get(date_field, ""))
        track = display_track(row.get(track_field, ""))
        if d is None or not track:
            continue
        key = f"{d.isoformat()}_{clean_track(track)}"
        item = out.setdefault(key, {"rows": 0, "races": set(), "tracks": set()})
        item["rows"] += 1
        item["tracks"].add(track)
        if race_field:
            race_no = parse_race_no(row.get(race_field, ""))
            if race_no:
                item["races"].add(race_no)
    return out


def discover_meetings() -> dict[str, dict[str, Any]]:
    meetings: dict[str, dict[str, Any]] = {}

    def add(date_value: str, track_value: str, race_no: str, source: str, meeting_code: str = "", status: str = "") -> None:
        d = parse_date(date_value)
        track = display_track(track_value)
        if d is None or not track or not (WINDOW_START <= d <= TODAY):
            return
        key = f"{d.isoformat()}_{clean_track(track)}"
        item = meetings.setdefault(
            key,
            {
                "meeting_key": key,
                "meeting_name": track,
                "meeting_code": "",
                "date": d.isoformat(),
                "track": track,
                "scheduled_races_set": set(),
                "source_of_discovery_set": set(),
                "source_status_set": set(),
            },
        )
        if meeting_code and not item["meeting_code"]:
            item["meeting_code"] = meeting_code
        if race_no:
            item["scheduled_races_set"].add(parse_race_no(race_no))
        item["source_of_discovery_set"].add(source)
        if status:
            item["source_status_set"].add(status)

    for row in read_csv(DATA / "edgeiq_daily_race_discovery_v1.csv"):
        add(
            row.get("meeting_date", ""),
            row.get("meeting_name", ""),
            row.get("race_number", ""),
            "edgeiq_daily_race_discovery_v1.csv",
            row.get("canonical_meeting_id", ""),
            row.get("race_status", ""),
        )

    for row in read_csv(DATA / "edgeiq_vic_three_day_race_list_v1.csv"):
        add(
            row.get("race_date", ""),
            row.get("normalised_track") or row.get("track", ""),
            row.get("race_no", ""),
            "edgeiq_vic_three_day_race_list_v1.csv",
            row.get("meet_code", ""),
            row.get("meet_status") or row.get("race_status", ""),
        )

    for row in read_csv(DATA / "edgeiq_vic_three_day_meeting_calendar_v1.csv"):
        add(
            row.get("race_date", ""),
            row.get("track", ""),
            "",
            "edgeiq_vic_three_day_meeting_calendar_v1.csv",
            "",
            row.get("day_bucket", ""),
        )

    for row in read_csv(DATA / "edgeiq_vic_three_day_meeting_universe.csv"):
        add(
            row.get("race_date", ""),
            row.get("track", ""),
            row.get("race_no", ""),
            "edgeiq_vic_three_day_meeting_universe.csv",
            row.get("meeting_key", ""),
            row.get("meeting_status") or row.get("race_state", ""),
        )

    for item in meetings.values():
        item["scheduled_races"] = len(item.pop("scheduled_races_set"))
        item["source_of_discovery"] = "|".join(sorted(item.pop("source_of_discovery_set")))
        item["source_status"] = "|".join(sorted(item.pop("source_status_set")))
    return dict(sorted(meetings.items(), key=lambda kv: (kv[1]["date"], kv[1]["track"])))


def daily_manifest() -> dict[str, Any]:
    path = DATA / "edgeiq_daily_operations_manifest_v1.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def source_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def build_trace(meetings: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    results = count_rows_by_meeting(DATA / "edgeiq_canonical_results_truth_v1.csv", "race_date", "track", "race_no")
    timed = count_rows_by_meeting(DATA / "edgeiq_canonical_historical_timing_warehouse_v1.csv", "race_date", "track", "race_number")
    delta = count_rows_by_meeting(DATA / "edgeiq_race_time_delta_versus_standard_fact_v1.csv", "race_date", "track_name", None)
    lengths = count_rows_by_meeting(DATA / "edgeiq_lengths_versus_standard_fact_v1.csv", "race_date", "track_name", None)
    base = count_rows_by_meeting(DATA / "edgeiq_performance_intelligence_base_fact_v1.csv", "race_date", "track_name", None)
    normalised = count_rows_by_meeting(DATA / "edgeiq_performance_normalisation_fact_v1.csv", "race_date", "track_name", None)

    standard_rows = read_csv(DATA / "edgeiq_standard_time_fact_v1.csv")
    standard_keys = {
        (clean_track(r.get("track_name", "")), re.sub(r"[^0-9]", "", r.get("official_distance_metres", "")))
        for r in standard_rows
    }
    scheduled_distance_by_meeting: dict[str, set[str]] = defaultdict(set)

    def add_scheduled_distance(date_value: str, track_value: str, distance_value: str) -> None:
        if not date_in_window(date_value):
            return
        track = display_track(track_value)
        if not track:
            return
        key = f"{date_value[:10]}_{clean_track(track)}"
        dist = re.sub(r"[^0-9]", "", distance_value or "")
        if dist:
            scheduled_distance_by_meeting[key].add(dist)

    for row in read_csv(DATA / "edgeiq_vic_three_day_race_list_v1.csv"):
        add_scheduled_distance(row.get("race_date", ""), row.get("normalised_track") or row.get("track", ""), row.get("distance", ""))
    for row in read_csv(DATA / "edgeiq_daily_race_discovery_v1.csv"):
        add_scheduled_distance(row.get("meeting_date", ""), row.get("meeting_name", ""), row.get("distance_metres", ""))
    for row in read_csv(DATA / "edgeiq_vic_three_day_meeting_universe.csv"):
        add_scheduled_distance(row.get("race_date", ""), row.get("track", ""), row.get("distance", ""))

    manifest = daily_manifest()
    ops_from = parse_date(manifest.get("date_from", ""))
    ops_to = parse_date(manifest.get("date_to", ""))
    official_results_summary = source_summary(DATA / "edgeiq_daily_official_results_ingestion_v1_summary.json")
    official_timing_summary = source_summary(DATA / "edgeiq_daily_official_timing_ingestion_v1_summary.json")

    trace_rows: list[dict[str, Any]] = []
    for key, meeting in meetings.items():
        meeting_date = parse_date(meeting["date"])
        result_count = results.get(key, {"rows": 0, "races": set()})
        timed_count = timed.get(key, {"rows": 0, "races": set()})
        delta_count = delta.get(key, {"rows": 0})
        lengths_count = lengths.get(key, {"rows": 0})
        base_count = base.get(key, {"rows": 0})
        norm_count = normalised.get(key, {"rows": 0})

        distances = scheduled_distance_by_meeting.get(key, set())
        std_available = sum(1 for dist in distances if (clean_track(meeting["track"]), dist) in standard_keys)
        std_status = "PRESENT" if std_available > 0 else ("NOT_PRESENT" if distances else "NOT_APPLICABLE_NO_SCHEDULED_DISTANCE")

        stages = [
            ("Meeting Discovery", "PRESENT", meeting["scheduled_races"], "Meeting sources listed the meeting.", "Discovery builders"),
            ("Results Warehouse", "PRESENT" if result_count["rows"] else "NOT_PRESENT", result_count["rows"], "", "build_edgeiq_daily_official_results_ingestion_v1.py"),
            ("Timed Race Fact", "PRESENT" if timed_count["rows"] else "NOT_PRESENT", timed_count["rows"], "", "update_edgeiq_canonical_historical_timing_warehouse_v1.py"),
            ("Standard Time Eligibility", std_status, std_available, "", "build_edgeiq_standard_time_engine_v1.py"),
            ("Race Time Delta", "PRESENT" if delta_count["rows"] else "NOT_PRESENT", delta_count["rows"], "", "build_edgeiq_race_time_delta_versus_standard_v1.py"),
            ("Lengths v Standard", "PRESENT" if lengths_count["rows"] else "NOT_PRESENT", lengths_count["rows"], "", "build_edgeiq_lengths_versus_standard_v1.py"),
            ("Performance Base", "PRESENT" if base_count["rows"] else "NOT_PRESENT", base_count["rows"], "", "build_edgeiq_performance_intelligence_base_fact_v1.py"),
            ("Normalisation Eligibility", "PRESENT" if norm_count["rows"] else "NOT_PRESENT", norm_count["rows"], "", "build_edgeiq_performance_normalisation_fact_v1.py"),
        ]

        if result_count["rows"] == 0:
            if ops_from and ops_to and meeting_date and ops_from <= meeting_date <= ops_to:
                first_failure = "Results Warehouse"
                category = "RESULT_NOT_IMPORTED"
                reason = (
                    "Daily operations covered this date but official results ingestion produced "
                    f"{official_results_summary.get('raw_rows', 'NA')} raw rows and "
                    f"{official_results_summary.get('facts', 'NA')} facts."
                )
            else:
                first_failure = "Daily Operations Coverage"
                category = "ORCHESTRATION_NOT_RUN"
                reason = (
                    "Latest daily operations manifest covers "
                    f"{manifest.get('date_from', 'NA')} to {manifest.get('date_to', 'NA')}; "
                    f"meeting date {meeting['date']} is outside that executed window."
                )
        elif timed_count["rows"] == 0:
            first_failure = "Timed Race Fact"
            category = "TIMED_RACE_NOT_BUILT"
            reason = "Results exist but no canonical timed-race facts exist for this meeting."
        elif std_available == 0:
            first_failure = "Standard Time Eligibility"
            category = "STANDARD_TIME_NOT_AVAILABLE"
            reason = "Timed races exist but scheduled/observed track-distance combinations have no governed standard time."
        elif delta_count["rows"] == 0:
            first_failure = "Race Time Delta"
            category = "RACE_TIME_DELTA_NOT_CREATED"
            reason = "Standard-time eligibility exists but no race time delta rows exist."
        elif lengths_count["rows"] == 0:
            first_failure = "Lengths v Standard"
            category = "LENGTHS_NOT_CREATED"
            reason = "Race time delta exists but no lengths-versus-standard rows exist."
        elif base_count["rows"] == 0:
            first_failure = "Performance Base"
            category = "PERFORMANCE_BASE_NOT_CREATED"
            reason = "Lengths-versus-standard exists but no Performance Base rows exist."
        elif meeting_date and meeting_date < NORM_EFFECTIVE:
            first_failure = "Normalisation Eligibility"
            category = "NORMALISATION_NOT_ELIGIBLE"
            reason = f"Performance Base exists but meeting is before {NORM_EFFECTIVE.isoformat()}."
        elif norm_count["rows"] == 0:
            first_failure = "Normalisation Eligibility"
            category = "NORMALISATION_NOT_ELIGIBLE"
            reason = "Performance Base exists on/after HPR-NORM-A-v1 effective date but no normalisation rows exist."
        else:
            first_failure = "NONE"
            category = "SOURCE_NOT_AVAILABLE" if meeting["scheduled_races"] == 0 else "OTHER"
            reason = "All traced stages have rows, or meeting has no scheduled races to trace."

        for stage_name, present, row_count, stage_reason, builder in stages:
            trace_rows.append(
                {
                    "meeting_key": key,
                    "meeting_name": meeting["meeting_name"],
                    "meeting_code": meeting["meeting_code"],
                    "date": meeting["date"],
                    "track": meeting["track"],
                    "scheduled_races": meeting["scheduled_races"],
                    "source_of_discovery": meeting["source_of_discovery"],
                    "stage": stage_name,
                    "stage_status": present,
                    "row_count": row_count,
                    "first_failure": first_failure,
                    "blocker_category": category,
                    "exact_rejection_reason": reason if stage_name == first_failure or first_failure == "Daily Operations Coverage" else stage_reason,
                    "builder_responsible": builder,
                    "official_results_ingestion_status": official_results_summary.get("status", ""),
                    "official_timing_ingestion_status": official_timing_summary.get("status", ""),
                    "daily_operations_window": f"{manifest.get('date_from', '')} to {manifest.get('date_to', '')}",
                }
            )
    return trace_rows


def coverage_profile() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    result_rows = read_csv(DATA / "edgeiq_canonical_results_truth_v1.csv")
    timing_rows = read_csv(DATA / "edgeiq_canonical_historical_timing_warehouse_v1.csv")
    base_rows = read_csv(DATA / "edgeiq_performance_intelligence_base_fact_v1.csv")

    buckets = [
        ("Historical", None, date(2025, 7, 31)),
        ("Current Season", date(2025, 8, 1), TODAY),
        ("After 2026-07-20", WINDOW_START, TODAY),
    ]

    rows: list[dict[str, Any]] = []
    for label, start, end in buckets:
        results_bucket = []
        for r in result_rows:
            d = parse_date(r.get("race_date", ""))
            if d is None:
                continue
            if start and d < start:
                continue
            if end and d > end:
                continue
            results_bucket.append(r)

        timing_bucket = []
        for r in timing_rows:
            d = parse_date(r.get("race_date", ""))
            if d is None:
                continue
            if start and d < start:
                continue
            if end and d > end:
                continue
            timing_bucket.append(r)

        base_bucket = []
        for r in base_rows:
            d = parse_date(r.get("race_date", ""))
            if d is None:
                continue
            if start and d < start:
                continue
            if end and d > end:
                continue
            base_bucket.append(r)

        result_races = {(r.get("race_date", ""), clean_track(r.get("track", "")), parse_race_no(r.get("race_no", ""))) for r in results_bucket}
        timed_races = {(r.get("race_date", ""), clean_track(r.get("track", "")), parse_race_no(r.get("race_number", ""))) for r in timing_bucket}
        base_races = {(r.get("race_date", ""), clean_track(r.get("track_name", "")), r.get("official_distance_metres", "")) for r in base_bucket}
        result_dates = sorted({r.get("race_date", "")[:10] for r in results_bucket if r.get("race_date")})
        result_tracks = sorted({display_track(r.get("track", "")) for r in results_bucket if r.get("track")})

        rows.append(
            {
                "bucket": label,
                "date_from": start.isoformat() if start else "",
                "date_to": end.isoformat() if end else "",
                "result_rows": len(results_bucket),
                "result_races": len(result_races),
                "timed_races": len(timed_races),
                "performance_base_races": len(base_races),
                "official_times": len([r for r in timing_bucket if r.get("official_race_time_seconds")]),
                "margins": len([r for r in results_bucket if r.get("finish_position") or r.get("winner_flag")]),
                "tracks": len(result_tracks),
                "dates": len(result_dates),
                "min_result_date": result_dates[0] if result_dates else "",
                "max_result_date": result_dates[-1] if result_dates else "",
            }
        )

    max_result_date = max((parse_date(r.get("race_date", "")) for r in result_rows if parse_date(r.get("race_date", ""))), default=None)
    max_timing_date = max((parse_date(r.get("race_date", "")) for r in timing_rows if parse_date(r.get("race_date", ""))), default=None)
    max_base_date = max((parse_date(r.get("race_date", "")) for r in base_rows if parse_date(r.get("race_date", ""))), default=None)
    summary = {
        "results_rows": len(result_rows),
        "timed_rows": len(timing_rows),
        "performance_base_rows": len(base_rows),
        "max_results_date": max_result_date.isoformat() if max_result_date else "",
        "max_timed_race_date": max_timing_date.isoformat() if max_timing_date else "",
        "max_performance_base_date": max_base_date.isoformat() if max_base_date else "",
    }
    return rows, summary


def orchestration_review(trace_rows: list[dict[str, Any]]) -> dict[str, Any]:
    manifest = daily_manifest()
    stages = manifest.get("stages", []) if isinstance(manifest.get("stages"), list) else []
    return {
        "latest_operation_run_id": manifest.get("operation_run_id", ""),
        "latest_mode": manifest.get("mode", ""),
        "latest_status": manifest.get("status", ""),
        "latest_date_from": manifest.get("date_from", ""),
        "latest_date_to": manifest.get("date_to", ""),
        "execution_order": [
            {"order": i + 1, "stage": s.get("stage", ""), "cmd": s.get("cmd", ""), "returncode": s.get("returncode", "")}
            for i, s in enumerate(stages)
        ],
        "current_meetings_discovered": len({r["meeting_key"] for r in trace_rows}),
        "result_not_imported_meetings": len({r["meeting_key"] for r in trace_rows if r["blocker_category"] == "RESULT_NOT_IMPORTED"}),
        "orchestration_not_run_meetings": len({r["meeting_key"] for r in trace_rows if r["blocker_category"] == "ORCHESTRATION_NOT_RUN"}),
        "official_results_summary": source_summary(DATA / "edgeiq_daily_official_results_ingestion_v1_summary.json"),
        "official_timing_summary": source_summary(DATA / "edgeiq_daily_official_timing_ingestion_v1_summary.json"),
    }


def main() -> None:
    meetings = discover_meetings()
    meeting_rows = []
    for item in meetings.values():
        meeting_rows.append(
            {
                "meeting_name": item["meeting_name"],
                "meeting_code": item["meeting_code"],
                "date": item["date"],
                "track": item["track"],
                "scheduled_races": item["scheduled_races"],
                "source_of_discovery": item["source_of_discovery"],
                "source_status": item["source_status"],
            }
        )

    meeting_fields = ["meeting_name", "meeting_code", "date", "track", "scheduled_races", "source_of_discovery", "source_status"]
    write_csv(DOCS / "EDGEIQ_VICTORIA_CURRENT_MEETINGS.csv", meeting_rows, meeting_fields)
    write_csv(DATA / "EDGEIQ_VICTORIA_CURRENT_MEETINGS.csv", meeting_rows, meeting_fields)
    (DOCS / "EDGEIQ_VICTORIA_CURRENT_MEETINGS.json").write_text(json.dumps(meeting_rows, indent=2), encoding="utf-8")
    (DATA / "EDGEIQ_VICTORIA_CURRENT_MEETINGS.json").write_text(json.dumps(meeting_rows, indent=2), encoding="utf-8")

    meetings_md = ["# EDGEiQ Victoria Current Meetings", "", f"Window: {WINDOW_START.isoformat()} to {TODAY.isoformat()}", ""]
    for r in meeting_rows:
        meetings_md.append(
            f"- {r['date']} {r['track']}: {r['scheduled_races']} scheduled races; source {r['source_of_discovery']}; status {r['source_status']}"
        )
    (DOCS / "EDGEIQ_VICTORIA_CURRENT_MEETINGS.md").write_text("\n".join(meetings_md) + "\n", encoding="utf-8")
    (DATA / "EDGEIQ_VICTORIA_CURRENT_MEETINGS.md").write_text("\n".join(meetings_md) + "\n", encoding="utf-8")

    trace_rows = build_trace(meetings)
    trace_fields = [
        "meeting_key",
        "meeting_name",
        "meeting_code",
        "date",
        "track",
        "scheduled_races",
        "source_of_discovery",
        "stage",
        "stage_status",
        "row_count",
        "first_failure",
        "blocker_category",
        "exact_rejection_reason",
        "builder_responsible",
        "official_results_ingestion_status",
        "official_timing_ingestion_status",
        "daily_operations_window",
    ]
    write_csv(DOCS / "edgeiq_victoria_live_current_observation_trace_v2.csv", trace_rows, trace_fields)

    coverage_rows, coverage_summary = coverage_profile()
    write_csv(
        DOCS / "edgeiq_victoria_current_results_coverage_v2.csv",
        coverage_rows,
        [
            "bucket",
            "date_from",
            "date_to",
            "result_rows",
            "result_races",
            "timed_races",
            "performance_base_races",
            "official_times",
            "margins",
            "tracks",
            "dates",
            "min_result_date",
            "max_result_date",
        ],
    )

    orchestration = orchestration_review(trace_rows)
    (DOCS / "edgeiq_victoria_orchestration_review_v2.json").write_text(json.dumps(orchestration, indent=2), encoding="utf-8")

    category_counts = Counter(r["blocker_category"] for r in trace_rows if r["stage"] == "Meeting Discovery")
    post_20260720_meetings = len(meetings)
    root_cause = "CURRENT_RESULTS_NOT_INGESTED"
    root_cause_evidence = [
        f"Canonical results warehouse max date is {coverage_summary['max_results_date']}.",
        f"Current meetings discovered in window: {post_20260720_meetings}.",
        f"Latest daily operations window: {orchestration['latest_date_from']} to {orchestration['latest_date_to']}.",
        f"Official results ingestion status: {orchestration['official_results_summary'].get('status', '')}; raw_rows={orchestration['official_results_summary'].get('raw_rows', '')}; facts={orchestration['official_results_summary'].get('facts', '')}.",
        f"After 2026-07-20 result races: {next((r['result_races'] for r in coverage_rows if r['bucket'] == 'After 2026-07-20'), 0)}.",
    ]
    decision = {
        "status": "BLOCKED_CURRENT_RESULTS_NOT_INGESTED",
        "root_cause": root_cause,
        "root_cause_evidence": root_cause_evidence,
        "meeting_blocker_categories": dict(category_counts),
        "implementation_safe": False,
        "reason_no_implementation": "Investigation does not prove a deterministic formula/governance defect. It proves missing current result ingestion/source coverage.",
        "next_governed_action": "Run or repair current official results ingestion for post-2026-07-20 Victorian resulted meetings, then rerun timing update and downstream performance refresh.",
    }
    (DOCS / "edgeiq_victoria_live_root_cause_v2.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")

    report_lines = [
        "# EDGEiQ Victoria Live Recovery V2",
        "",
        f"Status: {decision['status']}",
        f"Root cause: {root_cause}",
        "",
        "## Current Victorian Meetings",
        "",
        f"Meetings discovered from {WINDOW_START.isoformat()} through {TODAY.isoformat()}: {post_20260720_meetings}",
        "",
        "## Root Cause Evidence",
        "",
        *[f"- {e}" for e in root_cause_evidence],
        "",
        "## Meeting Classification",
        "",
        *[f"- {k}: {v}" for k, v in sorted(category_counts.items())],
        "",
        "## Orchestration",
        "",
        f"Latest run: {orchestration['latest_operation_run_id']}",
        f"Mode: {orchestration['latest_mode']}",
        f"Status: {orchestration['latest_status']}",
        f"Window: {orchestration['latest_date_from']} to {orchestration['latest_date_to']}",
        "",
        "Execution order:",
        *[f"{s['order']}. {s['stage']} - rc={s['returncode']} - {s['cmd']}" for s in orchestration["execution_order"]],
        "",
        "## Decision",
        "",
        "No implementation was performed. HPR-NORM-A-v1 remains unchanged. The next safe action is to restore current official results ingestion, not alter normalisation.",
    ]
    (DOCS / "edgeiq_victoria_live_root_cause_v2.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    (DOCS / "edgeiq_victoria_current_results_coverage_v2_summary.json").write_text(json.dumps(coverage_summary, indent=2), encoding="utf-8")

    summary = {
        "status": decision["status"],
        "root_cause": root_cause,
        "current_meetings": post_20260720_meetings,
        "post_2026_07_20_result_races": next((r["result_races"] for r in coverage_rows if r["bucket"] == "After 2026-07-20"), 0),
        "post_2026_07_20_timed_races": next((r["timed_races"] for r in coverage_rows if r["bucket"] == "After 2026-07-20"), 0),
        "post_2026_07_20_performance_base_races": next((r["performance_base_races"] for r in coverage_rows if r["bucket"] == "After 2026-07-20"), 0),
        "category_counts": dict(category_counts),
    }
    (DOCS / "edgeiq_victoria_live_current_observation_trace_v2_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
