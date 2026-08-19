from __future__ import annotations

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src" / "edgeiq-os" / "race" / "components"
SERVICES = PROJECT_ROOT / "src" / "edgeiq-os" / "race" / "services"
PUBLIC_DATA = PROJECT_ROOT / "public" / "data"


FILES = {
    "scratchings": SRC / "MeetingScratchingsWorkspace.tsx",
    "gear": SRC / "MeetingGearChangesWorkspace.tsx",
    "track": SRC / "MeetingTrackWorkspace.tsx",
    "weather": SRC / "MeetingWeatherWorkspace.tsx",
    "weather_service": SERVICES / "weatherFeed.ts",
    "results": SRC / "MeetingResultsWorkspace.tsx",
    "meeting": SRC / "MeetingWorkspace.tsx",
    "track_assets": SERVICES / "trackMapAssets.ts",
}


def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def rendered_body(source: str, export_name: str) -> str:
    marker = f"export function {export_name}"
    start = source.find(marker)
    if start < 0:
        return ""
    return source[start:]


def function_body(source: str, function_name: str) -> str:
    marker = f"function {function_name}"
    start = source.find(marker)
    if start < 0:
        return ""
    next_function = source.find("\nfunction ", start + len(marker))
    next_export = source.find("\nexport function ", start + len(marker))
    candidates = [value for value in (next_function, next_export) if value > start]
    end = min(candidates) if candidates else len(source)
    return source[start:end]


def table_headings(function_source: str) -> list[str]:
    headings = re.findall(r"<th[^>]*>(.*?)</th>", function_source, flags=re.DOTALL)
    clean: list[str] = []
    for heading in headings:
        text = re.sub(r"<[^>]+>", "", heading)
        text = re.sub(r"\s+", " ", text).strip().upper()
        if text:
            clean.append(text)
    return clean


def pass_check(checks: list[dict[str, object]], key: str, ok: bool, detail: str) -> None:
    checks.append({"check": key, "status": "PASS" if ok else "FAIL", "detail": detail})


def main() -> int:
    PUBLIC_DATA.mkdir(parents=True, exist_ok=True)

    sources = {name: read(path) for name, path in FILES.items()}
    checks: list[dict[str, object]] = []

    scratch_render = rendered_body(sources["scratchings"], "MeetingScratchingsWorkspace")
    scratch_table = function_body(sources["scratchings"], "ScratchingsTable")
    scratch_headings = table_headings(scratch_table)
    pass_check(
        checks,
        "scratchings_summary_strip_not_rendered",
        "<SummaryStrip" not in scratch_render,
        "Scratchings workspace must not render the rejected developer summary strip.",
    )
    pass_check(
        checks,
        "scratchings_data_freshness_not_rendered",
        "<DataStatusPanel" not in scratch_render and "DATA FRESHNESS" not in scratch_render,
        "Scratchings workspace must not render a data freshness/source diagnostics panel.",
    )
    pass_check(
        checks,
        "scratchings_main_table_columns_locked",
        scratch_headings == ["RACE", "NO", "SILK", "HORSE", "TRAINER", "JOCKEY"],
        f"Scratchings main table headings: {scratch_headings}",
    )

    gear_render = rendered_body(sources["gear"], "MeetingGearChangesWorkspace")
    pass_check(
        checks,
        "gear_summary_strip_not_rendered",
        "<SummaryStrip" not in gear_render,
        "Gear changes workspace must not render the rejected summary strip.",
    )
    pass_check(
        checks,
        "gear_data_freshness_not_rendered",
        "<DataStatusPanel" not in gear_render and "DATA FRESHNESS" not in gear_render,
        "Gear changes workspace must not render loaded/matched/workspace diagnostics.",
    )

    track_render = rendered_body(sources["track"], "MeetingTrackWorkspace")
    pattern_table = function_body(sources["track"], "PatternAnalysis")
    pattern_headings = table_headings(pattern_table)
    pass_check(
        checks,
        "track_map_assets_used",
        "resolveTrackMapPath" in sources["track"] and "TRACK_MAP_ASSETS" in sources["track_assets"],
        "Track workspace must use installed curated track map assets.",
    )
    pass_check(
        checks,
        "track_source_column_not_visible",
        "SOURCE" not in pattern_headings and "row.source" not in pattern_table,
        f"Track pattern table headings: {pattern_headings}",
    )
    pass_check(
        checks,
        "track_operational_source_rail_not_rendered",
        "<OperationalRail" not in track_render and "<TrackNotes" not in track_render,
        "Track workspace must not render source-state or operational note rails.",
    )
    pass_check(
        checks,
        "track_condition_labels_cleaned",
        "PENETROMETER AVERAGE" in sources["track"]
        and "RAIN 7 DAYS" in sources["track"]
        and "IRRIGATION 7 DAYS" in sources["track"],
        "Track condition labels include the required user-facing render mappings.",
    )

    weather_render = rendered_body(sources["weather"], "MeetingWeatherWorkspace")
    weather_service = sources["weather_service"]
    pass_check(
        checks,
        "weather_v12_service_path_preserved",
        "edgeiq_on_track_weather_governed_v1_2.json" in weather_service
        and "onTrackToMetropolitan" in weather_service
        and "loadWeatherTerminalFeeds" in weather_service,
        "Weather workspace must preserve the typed v1.2 on-track weather service path.",
    )
    pass_check(
        checks,
        "weather_source_diagnostics_not_rendered",
        "Source State" not in weather_render
        and "Weather Notes" not in weather_render
        and "DATA FRESHNESS" not in weather_render,
        "Weather workspace must not render source-state rails or developer diagnostics.",
    )

    results_render = rendered_body(sources["results"], "MeetingResultsWorkspace")
    results_table = function_body(sources["results"], "MeetingResultsTable")
    results_headings = table_headings(results_table)
    forbidden_result_labels = ["AVERAGE FIELD SIZE", "STATUS", "OPEN"]
    pass_check(
        checks,
        "results_summary_minimal",
        "Completed" in sources["results"] and "Official" in sources["results"] and all(label not in sources["results"] for label in forbidden_result_labels),
        "Results summary must stay limited to completed and official counts.",
    )
    pass_check(
        checks,
        "results_table_columns_locked",
        results_headings == [
            "RACE",
            "TIME",
            "WINNER",
            "JOCKEY",
            "TRAINER",
            "SP",
            "MARGIN",
            "OFFICIAL TIME",
            "TRACK",
            "STEWARDS",
            "DETAILS",
        ],
        f"Results table headings: {results_headings}",
    )
    pass_check(
        checks,
        "results_modal_preserved",
        "OfficialResultsIcon" in sources["results"]
        and "IndividualRaceResult" in sources["results"]
        and "eiq-results-v2-modal" in sources["results"],
        "Results details modal and official-results icon must remain available.",
    )
    pass_check(
        checks,
        "results_provider_names_not_rendered",
        not re.search(r"\b(Sportsbet|Racing\.com|PuntingForm|TAB)\b", results_render, flags=re.IGNORECASE),
        "Results controls must not expose third-party racing data provider names.",
    )

    meeting = sources["meeting"]
    pass_check(
        checks,
        "meeting_selected_race_builder_preserved",
        "buildMeetingDetailSelectedRace(" in meeting
        and "model.races.find(" not in meeting,
        "Meeting selected-race state must continue using the repaired selected-race builder.",
    )
    pass_check(
        checks,
        "meeting_selected_race_details_not_rendered",
        "SelectedRacePanel" not in meeting and "Selected Race Details" not in meeting,
        "Rejected Selected Race Details panel must not return.",
    )

    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    result = {"status": status, "checks": checks}

    json_path = PUBLIC_DATA / "edgeiq_recent_workspace_regression_v1_audit.json"
    txt_path = PUBLIC_DATA / "edgeiq_recent_workspace_regression_v1_audit.txt"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = [f"EDGEIQ_RECENT_WORKSPACE_REGRESSION_V1_AUDIT_{status}"]
    lines.extend(f"{item['status']} {item['check']}: {item['detail']}" for item in checks)
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(lines[0])
    for item in checks:
      print(f"{item['status']} {item['check']}")

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
