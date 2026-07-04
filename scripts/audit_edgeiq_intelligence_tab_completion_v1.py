from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_intelligence_tab_completion_v1.csv"
SUMMARY = DATA / "edgeiq_intelligence_tab_completion_v1_summary.csv"

FILES_TO_SCAN = [
    SRC / "components" / "RaceIntelligenceScreen.tsx",
    SRC / "components" / "SpeedMapTab.tsx",
    SRC / "terminal" / "tabs" / "MarketTab.tsx",
    SRC / "App.tsx",
    SRC / "components" / "race-intelligence-screen.css",
    SRC / "edgeiq-speedmap-v2.css",
    SRC / "terminal" / "layout" / "racing-terminal-overrides.css",
    SRC / "styles" / "terminal-primitives.css",
]

DATA_FILES_TO_SCAN = [
    DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
    DATA / "edgeiq_current_field_projection_v5_2.csv",
    DATA / "edgeiq_current_fair_prices_review_v5_2.csv",
    DATA / "sportsbet_live_market_full_day_v5_2.csv",
    DATA / "edgeiq_price_truth_history_v1.csv",
    DATA / "edgeiq_starter_only_calibration_v2.csv",
]

DETAIL_COLUMNS = [
    "section",
    "requirement",
    "status",
    "evidence",
    "file_path",
    "notes",
    "built_at",
]

SUMMARY_COLUMNS = [
    "section",
    "complete",
    "partial",
    "missing",
    "section_status",
    "notes",
    "built_at",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except Exception:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_csv_header(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.reader(handle)
        try:
            return next(reader)
        except StopIteration:
            return []


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def has_any(text: str, patterns: list[str]) -> bool:
    low = text.lower()
    return any(pattern.lower() in low for pattern in patterns)


def header_has_any(headers: list[str], patterns: list[str]) -> bool:
    joined = " ".join(headers).lower()
    return any(pattern.lower() in joined for pattern in patterns)


def evidence_for_text(patterns: list[str], scanned: dict[Path, str]) -> tuple[str, str]:
    for path, text in scanned.items():
        if has_any(text, patterns):
            found = [p for p in patterns if p.lower() in text.lower()]
            return ", ".join(found[:5]), rel(path)
    return "", ""


def evidence_for_data(patterns: list[str], scanned_headers: dict[Path, list[str]]) -> tuple[str, str]:
    for path, headers in scanned_headers.items():
        if header_has_any(headers, patterns):
            found = [h for h in headers if any(p.lower() in h.lower() for p in patterns)]
            return ", ".join(found[:8]), rel(path)
    return "", ""


def make_row(section: str, requirement: str, status: str, evidence: str = "", file_path: str = "", notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "requirement": requirement,
        "status": status,
        "evidence": evidence,
        "file_path": file_path,
        "notes": notes,
        "built_at": now_utc(),
    }


def judge_requirement(
    section: str,
    requirement: str,
    text_patterns: list[str],
    data_patterns: list[str],
    scanned_text: dict[Path, str],
    scanned_headers: dict[Path, list[str]],
    notes: str = "",
) -> dict[str, object]:
    text_evidence, text_file = evidence_for_text(text_patterns, scanned_text) if text_patterns else ("", "")
    data_evidence, data_file = evidence_for_data(data_patterns, scanned_headers) if data_patterns else ("", "")

    if text_evidence and data_evidence:
        return make_row(section, requirement, "COMPLETE", f"UI: {text_evidence} | DATA: {data_evidence}", f"{text_file} | {data_file}", notes)
    if text_evidence or data_evidence:
        return make_row(section, requirement, "PARTIAL", text_evidence or data_evidence, text_file or data_file, notes)
    return make_row(section, requirement, "MISSING", "", "", notes)


def section_status(rows: list[dict[str, object]]) -> str:
    statuses = [str(row["status"]) for row in rows]
    if statuses and all(status == "COMPLETE" for status in statuses):
        return "COMPLETE"
    if any(status in {"COMPLETE", "PARTIAL"} for status in statuses):
        return "PARTIAL"
    return "MISSING"


def main() -> None:
    scanned_text = {path: read_text(path) for path in FILES_TO_SCAN}
    scanned_headers = {path: read_csv_header(path) for path in DATA_FILES_TO_SCAN}

    details: list[dict[str, object]] = []

    checks = [
        ("Race Header", "Track displayed", ["track", "venue"], ["track", "track_name"], "Header should show track."),
        ("Race Header", "Race number/time displayed", ["race_no", "race_time", "jump"], ["race_no", "race_time", "minutes_to_jump"], "Header should show race number/time."),
        ("Race Header", "Distance displayed", ["distance"], ["distance", "distance_m"], "Header should show distance."),
        ("Race Header", "Class displayed", ["class", "race_class"], ["race_class", "class_clean", "race_class_clean"], "Header should show race class."),
        ("Race Header", "Track condition displayed", ["condition", "track_condition"], ["track_condition", "condition"], "Header should show track condition."),

        ("Decision Board", "Saddlecloth / number", ["saddlecloth", "runner_no", "cloth", "number"], ["saddlecloth", "runner_no", "number"], "Decision board needs saddlecloth order."),
        ("Decision Board", "Runner name", ["runner", "horse"], ["horse", "runner", "runner_name"], "Decision board needs runner name."),
        ("Decision Board", "Barrier", ["barrier", "bar"], ["barrier", "bar"], "Decision board needs barrier."),
        ("Decision Board", "Jockey", ["jockey"], ["jockey"], "Decision board needs jockey."),
        ("Decision Board", "Trainer", ["trainer"], ["trainer"], "Decision board needs trainer."),
        ("Decision Board", "Live market price", ["sportsbet_price", "live", "market_price"], ["sportsbet_price", "market_price"], "Decision board needs live market price."),
        ("Decision Board", "Fair / rated price", ["rated_price", "fair", "edgeiq_price"], ["rated_price", "edgeiq_price", "fair_price"], "Decision board needs fair price."),
        ("Decision Board", "Edge / overlay", ["overlay", "edge"], ["overlay_pct", "edge"], "Decision board needs edge/overlay."),
        ("Decision Board", "Decision label", ["decision", "action", "watch", "lean"], ["decision", "execution_action", "action"], "Decision board needs a decision label."),

        ("Speed Map", "Right-to-left racing direction", ["right", "left", "right-to-left", "right → left", "right-to-left"], ["map_x_pct"], "Speed map should show runners moving right to left."),
        ("Speed Map", "Dark theme", ["background", "#0", "dark", "terminal"], [], "Speed map should match EDGEiQ dark terminal style."),
        ("Speed Map", "Leader green", ["leader", "green", "#34d399", "emerald"], ["speed_map_bucket", "run_style"], "Leaders should be green/emerald."),
        ("Speed Map", "Midfield yellow", ["midfield", "yellow", "#facc15", "amber"], ["speed_map_bucket", "settling_band"], "Midfield should be yellow/amber."),
        ("Speed Map", "Backmarker red", ["backmarker", "red", "#f87171", "rose"], ["speed_map_bucket", "settling_band"], "Backmarkers should be red/rose."),
        ("Speed Map", "Barrier labels", ["barrier", "bar"], ["barrier", "map_y_px"], "Barrier labels should be visible on the right side."),
        ("Speed Map", "Scratchings compression", ["scratch", "is_scratched", "scratched"], ["is_scratched", "result_status"], "Scratchings should not leave dead lanes."),

        ("Ratings + Pricing", "EDGEiQ rating/projection", ["projection", "rating", "score"], ["projection_score", "rating"], "Ratings panel should show rating/projection."),
        ("Ratings + Pricing", "Probability", ["probability", "win %", "win_pct"], ["edgeiq_probability", "rated_probability"], "Ratings panel should show probability."),
        ("Ratings + Pricing", "Fair price", ["fair", "rated_price", "edgeiq_price"], ["edgeiq_price", "rated_price", "fair_price"], "Ratings panel should show fair price."),
        ("Ratings + Pricing", "Market price", ["sportsbet", "market"], ["sportsbet_price", "market_price"], "Ratings panel should show market price."),
        ("Ratings + Pricing", "Overlay", ["overlay", "edge"], ["overlay_pct"], "Ratings panel should show overlay/edge."),

        ("Race Read", "Projected tempo", ["tempo", "projected_tempo", "race_shape"], ["projected_tempo_shape", "race_shape"], "Race read should show tempo."),
        ("Race Read", "Pace pressure", ["pressure", "pace_pressure"], ["pace_pressure", "pressure_index"], "Race read should show pressure."),
        ("Race Read", "Likely leader", ["leader", "likely leader"], ["speed_map_bucket", "run_style"], "Race read should identify likely leader."),
        ("Race Read", "Likely closer", ["closer", "backmarker"], ["settling_band", "speed_map_bucket"], "Race read should identify closer/backmarker."),
        ("Race Read", "Narrative race shape", ["race read", "tactical", "shape", "market read"], ["race_shape", "projected_race_shape"], "Race read should translate data into a tactical summary."),
    ]

    for section, requirement, text_patterns, data_patterns, notes in checks:
        details.append(
            judge_requirement(
                section,
                requirement,
                text_patterns,
                data_patterns,
                scanned_text,
                scanned_headers,
                notes,
            )
        )

    summary_rows: list[dict[str, object]] = []
    sections = sorted({row["section"] for row in details})

    for section in sections:
        section_rows = [row for row in details if row["section"] == section]
        complete = sum(1 for row in section_rows if row["status"] == "COMPLETE")
        partial = sum(1 for row in section_rows if row["status"] == "PARTIAL")
        missing = sum(1 for row in section_rows if row["status"] == "MISSING")
        summary_rows.append(
            {
                "section": section,
                "complete": complete,
                "partial": partial,
                "missing": missing,
                "section_status": section_status(section_rows),
                "notes": "READ_ONLY_AUDIT",
                "built_at": now_utc(),
            }
        )

    total_complete = sum(1 for row in details if row["status"] == "COMPLETE")
    total_partial = sum(1 for row in details if row["status"] == "PARTIAL")
    total_missing = sum(1 for row in details if row["status"] == "MISSING")

    summary_rows.append(
        {
            "section": "OVERALL",
            "complete": total_complete,
            "partial": total_partial,
            "missing": total_missing,
            "section_status": "PARTIAL" if total_missing else "COMPLETE",
            "notes": "No files modified except audit outputs.",
            "built_at": now_utc(),
        }
    )

    write_csv(OUT, details, DETAIL_COLUMNS)
    write_csv(SUMMARY, summary_rows, SUMMARY_COLUMNS)

    print("=" * 96)
    print("EDGEIQ INTELLIGENCE TAB COMPLETION AUDIT V1 - READ ONLY")
    print("=" * 96)
    print(f"wrote: {OUT}")
    print(f"wrote: {SUMMARY}")
    print("")
    for row in summary_rows:
        print(
            f"{row['section']}, complete={row['complete']}, partial={row['partial']}, "
            f"missing={row['missing']}, status={row['section_status']}"
        )
    print("=" * 96)


if __name__ == "__main__":
    main()
