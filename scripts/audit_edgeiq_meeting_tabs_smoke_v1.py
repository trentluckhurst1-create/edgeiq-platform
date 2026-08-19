from __future__ import annotations

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src" / "edgeiq-os"
RACE = SRC / "race"
COMPONENTS = RACE / "components"
SERVICES = RACE / "services"
CSS = SRC / "styles" / "edgeiqOsV2.css"
PUBLIC_DATA = PROJECT_ROOT / "public" / "data"
TRACK_MAP_DIR = PROJECT_ROOT / "public" / "track-maps"


COMPONENT_EXPORTS = {
    "MeetingWorkspace.tsx": "MeetingWorkspace",
    "MeetingScratchingsWorkspace.tsx": "MeetingScratchingsWorkspace",
    "MeetingGearChangesWorkspace.tsx": "MeetingGearChangesWorkspace",
    "MeetingTrackWorkspace.tsx": "MeetingTrackWorkspace",
    "MeetingWeatherWorkspace.tsx": "MeetingWeatherWorkspace",
    "MeetingResultsWorkspace.tsx": "MeetingResultsWorkspace",
}


def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def check(checks: list[dict[str, object]], name: str, ok: bool, detail: str) -> None:
    checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})


def rendered_export(source: str, export_name: str) -> str:
    marker = f"export function {export_name}"
    start = source.find(marker)
    return source[start:] if start >= 0 else ""


def imported_components(meeting_source: str) -> set[str]:
    names = set()
    for match in re.finditer(r'import\s+\{\s*([^}]+)\s*\}\s+from\s+"\.\/([^"]+)";', meeting_source):
        for name in match.group(1).split(","):
            names.add(name.strip())
    return names


def track_map_asset_paths(source: str) -> list[str]:
    return sorted(set(re.findall(r'assetPath:\s*"(/track-maps/[^"]+)"', source)))


def main() -> int:
    PUBLIC_DATA.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, object]] = []

    component_sources: dict[str, str] = {}
    for filename, export_name in COMPONENT_EXPORTS.items():
        path = COMPONENTS / filename
        exists = path.exists()
        source = read(path) if exists else ""
        component_sources[filename] = source
        check(checks, f"{filename}_exists", exists, f"{path}")
        check(
            checks,
            f"{filename}_exports_{export_name}",
            f"export function {export_name}" in source,
            f"{filename} should export {export_name}.",
        )

    meeting_source = component_sources["MeetingWorkspace.tsx"]
    meeting_detail_source = read(SERVICES / "meetingDetailFeed.ts")
    css = read(CSS)
    track_assets = read(SERVICES / "trackMapAssets.ts")
    results_source = component_sources["MeetingResultsWorkspace.tsx"]

    imports = imported_components(meeting_source)
    required_imports = {
        "MeetingScratchingsWorkspace",
        "MeetingGearChangesWorkspace",
        "MeetingTrackWorkspace",
        "MeetingWeatherWorkspace",
        "MeetingResultsWorkspace",
    }
    check(
        checks,
        "meeting_workspace_imports_tabs",
        required_imports.issubset(imports),
        f"MeetingWorkspace imports: {sorted(imports)}",
    )

    tab_keys = set(re.findall(r'\|\s+"([A-Z_]+)"', meeting_detail_source))
    expected_tabs = {"RACES", "SCRATCHINGS", "GEAR_CHANGES", "TRACK", "WEATHER", "RESULTS"}
    check(
        checks,
        "meeting_detail_tab_union_complete",
        expected_tabs.issubset(tab_keys),
        f"MeetingDetailTab keys: {sorted(tab_keys)}",
    )
    check(
        checks,
        "meeting_detail_tab_order_complete",
        all(f'key: "{tab}"' in meeting_detail_source for tab in expected_tabs),
        "MEETING_DETAIL_TAB_ORDER includes all expected meeting tabs.",
    )

    check(
        checks,
        "selected_race_builder_locked",
        "buildMeetingDetailSelectedRace(" in meeting_source
        and "model.races.find(" not in meeting_source
        and "SelectedRacePanel" not in meeting_source,
        "MeetingWorkspace must keep the repaired selected-race flow and no rejected selected-race panel.",
    )

    rendered_sections = {
        name: rendered_export(source, export_name)
        for name, export_name in COMPONENT_EXPORTS.items()
    }
    visible_forbidden = [
        "Loaded Rows",
        "Matched Rows",
        "Workspace ID",
        "DATA FRESHNESS",
        "Source State",
        "Weather Notes",
        "Selected Race Details",
    ]
    leaked = []
    for name, section in rendered_sections.items():
        for phrase in visible_forbidden:
            if phrase in section:
                leaked.append(f"{name}:{phrase}")
    check(
        checks,
        "removed_developer_phrases_not_rendered",
        not leaked,
        f"Rendered leaks: {leaked}",
    )

    check(
        checks,
        "meeting_final_css_marker_single",
        css.count("EDGEIQ MEETING RACES FINAL POLISH V2") == 1,
        f"Marker count: {css.count('EDGEIQ MEETING RACES FINAL POLISH V2')}",
    )
    check(
        checks,
        "meeting_condition_strip_seven_columns",
        "grid-template-columns: repeat(7, minmax(0, 1fr)) !important;" in css,
        "Final condition strip CSS should render seven compact tiles.",
    )
    check(
        checks,
        "meeting_table_seven_column_widths_locked",
        "width: 47% !important;" in css
        and "width: 13.5% !important;" in css
        and "width: 7.5% !important;" in css,
        "Final meeting table widths should match the seven-column lock.",
    )

    asset_paths = track_map_asset_paths(track_assets)
    missing_assets = [
        path for path in asset_paths
        if not (PROJECT_ROOT / "public" / path.lstrip("/").replace("/", "\\")).exists()
    ]
    check(
        checks,
        "track_map_assets_resolve",
        bool(asset_paths) and not missing_assets,
        f"{len(asset_paths)} assets referenced; missing: {missing_assets[:8]}",
    )

    check(
        checks,
        "weather_v12_live_states_preserved",
        "edgeiq_on_track_weather_governed_v1_2.json" in read(SERVICES / "weatherFeed.ts")
        and "freshness_status" in read(SERVICES / "weatherFeed.ts")
        and "governed_source_state" in read(SERVICES / "weatherFeed.ts"),
        "Weather service must keep v1.2 live-source freshness and governed source fields.",
    )

    check(
        checks,
        "results_modal_controls_preserved",
        "OfficialResultsIcon" in results_source
        and "eiq-results-v2-details-button" in results_source
        and "IndividualRaceResult" in results_source
        and "eiq-results-v2-modal" in css,
        "Results details modal and clipboard-style control should remain wired.",
    )
    check(
        checks,
        "results_missing_sectionals_dash",
        "Pending speed data" not in results_source and 'return "-";' in results_source,
        "Missing sectional table values should render a dash, not repeated pending copy.",
    )

    broken_fragments = []
    for name, source in component_sources.items():
        if re.search(r"return\s*\(\s*\);", source):
            broken_fragments.append(name)
    check(
        checks,
        "no_empty_return_fragments",
        not broken_fragments,
        f"Files with empty return fragments: {broken_fragments}",
    )

    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    output = {"status": status, "checks": checks}
    json_path = PUBLIC_DATA / "edgeiq_meeting_tabs_smoke_v1_audit.json"
    txt_path = PUBLIC_DATA / "edgeiq_meeting_tabs_smoke_v1_audit.txt"
    json_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    lines = [f"EDGEIQ_MEETING_TABS_SMOKE_V1_AUDIT_{status}"]
    lines.extend(f"{item['status']} {item['check']}: {item['detail']}" for item in checks)
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(lines[0])
    for item in checks:
        print(f"{item['status']} {item['check']}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
