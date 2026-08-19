from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TXT_OUT = ROOT / "public" / "data" / "edgeiq_race_workspace_baseline_v1_audit.txt"
JSON_OUT = ROOT / "public" / "data" / "edgeiq_race_workspace_baseline_v1_audit.json"
DOC_PATH = ROOT / "docs" / "engineering" / "EDGEIQ_RACE_WORKSPACE_BASELINE_20260715.md"
PASS_MARKER = "EDGEIQ_RACE_WORKSPACE_BASELINE_V1_AUDIT_PASS"


REQUIRED_FILES = {
    "orchestrator": "src/edgeiq-os/race/RaceFileV3.tsx",
    "shell": "src/edgeiq-os/race/components/WorkspaceShell.tsx",
    "race_workspace": "src/edgeiq-os/race/components/RaceWorkspace.tsx",
    "form_guide": "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx",
    "map": "src/edgeiq-os/race/components/MapWorkspace.tsx",
    "market": "src/edgeiq-os/race/components/MarketWorkspace.tsx",
    "overview": "src/edgeiq-os/race/components/OverviewWorkspace.tsx",
    "insights": "src/edgeiq-os/race/components/InsightsWorkspace.tsx",
    "epi": "src/edgeiq-os/race/components/EpiWorkspaceWorkspace.tsx",
    "results": "src/edgeiq-os/race/components/ResultsWorkspace.tsx",
    "runner_workspace": "src/edgeiq-os/race/components/RunnerProfileWorkspace.tsx",
    "three_day_catalog": "src/edgeiq-os/race/services/threeDayCatalog.ts",
    "form_enriched": "src/edgeiq-os/race/services/formGuideEnrichedFeed.ts",
    "form_normaliser": "src/edgeiq-os/race/services/formGuideNormaliser.ts",
    "map_feed": "src/edgeiq-os/race/services/mapFeed.ts",
    "market_feed": "src/edgeiq-os/race/services/marketFeed.ts",
    "overview_feed": "src/edgeiq-os/race/services/overviewFeed.ts",
    "insights_feed": "src/edgeiq-os/race/services/insightsFeed.ts",
    "epi_feed": "src/edgeiq-os/race/services/epiWorkspaceFeed.ts",
    "race_file_service": "src/edgeiq-os/services/RaceFileService.ts",
    "css": "src/edgeiq-os/styles/edgeiqOsV2.css",
}


REQUIRED_DATA = {
    "three_day_catalog": "public/data/edgeiq_three_day_product_catalog_v1.json",
    "form_guide_enriched": "public/data/edgeiq_form_guide_enriched_v2.json",
    "map_terminal": "public/data/edgeiq_map_terminal_feed_v1.csv",
    "market_terminal": "public/data/edgeiq_market_terminal_feed_v1.csv",
    "overview_terminal": "public/data/edgeiq_overview_terminal_feed_v1.csv",
    "insights_terminal": "public/data/edgeiq_insights_terminal_feed_v1.csv",
    "epi_terminal": "public/data/edgeiq_epi_workspace_terminal_feed_v1.csv",
}


EXPECTED_RACE_TABS = ["FORM GUIDE", "MAP", "MARKET", "OVERVIEW", "INSIGHTS", "EPI", "REVIEW"]
EXPECTED_RUNNER_TABS = ["profile", "compare", "results", "dna", "market", "map"]


def rel(path: str) -> Path:
    return ROOT / path


def read(path: str) -> str:
    return rel(path).read_text(encoding="utf-8", errors="replace")


def fail(checks: list[dict[str, object]], name: str, detail: str) -> None:
    checks.append({"name": name, "status": "FAIL", "detail": detail})


def warn(checks: list[dict[str, object]], name: str, detail: str) -> None:
    checks.append({"name": name, "status": "WARN", "detail": detail})


def ok(checks: list[dict[str, object]], name: str, detail: str) -> None:
    checks.append({"name": name, "status": "PASS", "detail": detail})


def parse_tabs(source: str) -> list[str]:
    match = re.search(r"const\s+tabs\s*=\s*\[(.*?)\]\s+as\s+const", source, flags=re.S)
    if not match:
        return []
    return re.findall(r'"([^"]+)"', match.group(1))


def parse_runner_tabs(source: str) -> list[str]:
    match = re.search(r"const\s+tabs:\s*RunnerWorkspaceMode\[\]\s*=\s*\[(.*?)\]", source, flags=re.S)
    if not match:
        return []
    return re.findall(r'"([^"]+)"', match.group(1))


def data_line_count(path: Path) -> int | None:
    if not path.exists():
        return None
    if path.suffix.lower() == ".json":
        return None
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        line_count = sum(1 for line in handle if line.strip())
    return max(0, line_count - 1)


def import_targets(source_path: str, source: str) -> list[tuple[str, str]]:
    base = rel(source_path).parent
    output: list[tuple[str, str]] = []
    for spec in re.findall(r'from\s+"([^"]+)"', source):
        if not spec.startswith("."):
            continue
        candidate = (base / spec).resolve()
        options = [
            candidate,
            candidate.with_suffix(".ts"),
            candidate.with_suffix(".tsx"),
            candidate / "index.ts",
            candidate / "index.tsx",
        ]
        found = next((item for item in options if item.exists()), None)
        output.append((spec, str(found if found else candidate)))
    return output


def main() -> int:
    checks: list[dict[str, object]] = []
    generated = datetime.now().isoformat(timespec="seconds")

    for key, path in REQUIRED_FILES.items():
        target = rel(path)
        if target.exists():
            ok(checks, f"file:{key}", f"{path} exists ({target.stat().st_size} bytes)")
        else:
            fail(checks, f"file:{key}", f"{path} missing")

    for key, path in REQUIRED_DATA.items():
        target = rel(path)
        if target.exists():
            count = data_line_count(target)
            suffix = f", rows={count}" if count is not None else ""
            ok(checks, f"data:{key}", f"{path} exists ({target.stat().st_size} bytes{suffix})")
        else:
            fail(checks, f"data:{key}", f"{path} missing")

    if DOC_PATH.exists():
        ok(checks, "doc", f"{DOC_PATH.relative_to(ROOT)} exists")
    else:
        fail(checks, "doc", f"{DOC_PATH.relative_to(ROOT)} missing")

    race_workspace = read(REQUIRED_FILES["race_workspace"])
    race_tabs = parse_tabs(race_workspace)
    if race_tabs == EXPECTED_RACE_TABS:
        ok(checks, "race_tabs", f"Race tabs match current baseline: {', '.join(race_tabs)}")
    else:
        fail(checks, "race_tabs", f"Expected {EXPECTED_RACE_TABS}, found {race_tabs}")

    if len(race_tabs) == len(set(race_tabs)):
        ok(checks, "race_tabs_unique", "Race tab keys are unique")
    else:
        fail(checks, "race_tabs_unique", f"Duplicate race tabs found: {race_tabs}")

    runner_tabs_source = read("src/edgeiq-os/race/components/RunnerTabs.tsx")
    runner_tabs = parse_runner_tabs(runner_tabs_source)
    if runner_tabs == EXPECTED_RUNNER_TABS:
        ok(checks, "runner_tabs", f"Runner tabs match current baseline: {', '.join(runner_tabs)}")
    else:
        fail(checks, "runner_tabs", f"Expected {EXPECTED_RUNNER_TABS}, found {runner_tabs}")

    orchestrator = read(REQUIRED_FILES["orchestrator"])
    required_mounts = [
        "MeetingsWorkspace",
        "MeetingWorkspace",
        "RaceWorkspace",
        "RunnerProfileWorkspace",
        "GlobalResultsWorkspace",
        "LabWorkspace",
        "SettingsWorkspace",
    ]
    for mount in required_mounts:
        if f"<{mount}" in orchestrator:
            ok(checks, f"mount:{mount}", f"{mount} is mounted by RaceFileV3")
        else:
            fail(checks, f"mount:{mount}", f"{mount} is not mounted by RaceFileV3")

    required_race_props = ["raceBook={activeFile.raceBook}", "field={activeFile.field}", "meetingRaces={selectedMeeting?.races ?? []}", "selectedRaceKey="]
    for prop in required_race_props:
        if prop in orchestrator:
            ok(checks, f"race_prop:{prop}", "RaceWorkspace receives current race context")
        else:
            fail(checks, f"race_prop:{prop}", "RaceWorkspace context prop missing")

    for path in [
        REQUIRED_FILES["race_workspace"],
        REQUIRED_FILES["form_guide"],
        REQUIRED_FILES["map"],
        REQUIRED_FILES["market"],
        REQUIRED_FILES["overview"],
        REQUIRED_FILES["insights"],
        REQUIRED_FILES["epi"],
        REQUIRED_FILES["runner_workspace"],
    ]:
        source = read(path)
        missing_imports = []
        for spec, resolved in import_targets(path, source):
            if not Path(resolved).exists():
                missing_imports.append(spec)
        if missing_imports:
            fail(checks, f"imports:{path}", f"Missing relative imports: {missing_imports}")
        else:
            ok(checks, f"imports:{path}", "Relative imports resolve")

    loader_guards = {
        "map_feed": "EDGEiQ rejected oversized map feed",
        "market_feed": "EDGEiQ rejected oversized market feed",
        "overview_feed": "EDGEiQ rejected oversized overview feed",
        "insights_feed": "EDGEiQ rejected oversized insights feed",
        "epi_feed": "EDGEiQ rejected oversized EPI workspace feed",
    }
    for key, marker in loader_guards.items():
        source = read(REQUIRED_FILES[key])
        if "rows.length > 10000" in source and marker in source:
            ok(checks, f"large_feed_guard:{key}", "Frontend loader rejects oversized terminal feed")
        else:
            fail(checks, f"large_feed_guard:{key}", "Oversized terminal feed guard missing")

    visible_language_sources = {
        "MapWorkspace": read(REQUIRED_FILES["map"]),
        "MarketWorkspace": read(REQUIRED_FILES["market"]),
        "OverviewWorkspace": read(REQUIRED_FILES["overview"]),
        "InsightsWorkspace": read(REQUIRED_FILES["insights"]),
        "EpiWorkspaceWorkspace": read(REQUIRED_FILES["epi"]),
    }
    flagged_terms = ["Feed Status", "Rows", "Matched", "Loaded", "Workspace", "Model Information", "Data State", "source"]
    flagged: list[str] = []
    for name, source in visible_language_sources.items():
        for term in flagged_terms:
            if term in source:
                flagged.append(f"{name}:{term}")
    if flagged:
        warn(checks, "visible_operational_language", "Customer-facing cleanup needed: " + ", ".join(flagged[:40]))
    else:
        ok(checks, "visible_operational_language", "No obvious operational language in checked workspace components")

    previous_audits = [
        ("meeting_polish", "public/data/edgeiq_meeting_races_final_polish_v2_audit.txt", "EDGEIQ_MEETING_RACES_FINAL_POLISH_V2_AUDIT_PASS"),
        ("recent_regression", "public/data/edgeiq_recent_workspace_regression_v1_audit.txt", "EDGEIQ_RECENT_WORKSPACE_REGRESSION_V1_AUDIT_PASS"),
        ("meeting_smoke", "public/data/edgeiq_meeting_tabs_smoke_v1_audit.txt", "EDGEIQ_MEETING_TABS_SMOKE_V1_AUDIT_PASS"),
    ]
    for key, path, marker in previous_audits:
        target = rel(path)
        if target.exists() and marker in target.read_text(encoding="utf-8", errors="replace"):
            ok(checks, f"previous_audit:{key}", marker)
        elif target.exists():
            warn(checks, f"previous_audit:{key}", f"{path} exists but marker not found")
        else:
            warn(checks, f"previous_audit:{key}", f"{path} not found in current workspace")

    fatal_count = sum(1 for check in checks if check["status"] == "FAIL")
    warning_count = sum(1 for check in checks if check["status"] == "WARN")
    pass_count = sum(1 for check in checks if check["status"] == "PASS")
    status = "PASS" if fatal_count == 0 else "FAIL"

    payload = {
        "audit": "edgeiq_race_workspace_baseline_v1",
        "generated_at": generated,
        "status": status,
        "pass_marker": PASS_MARKER if status == "PASS" else "",
        "counts": {
            "pass": pass_count,
            "warn": warning_count,
            "fail": fatal_count,
        },
        "race_tabs": race_tabs,
        "runner_tabs": runner_tabs,
        "checks": checks,
    }

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    text_lines = [
        "EDGEiQ Race Workspace Baseline V1 Audit",
        f"Generated: {generated}",
        f"Status: {status}",
        f"Counts: PASS={pass_count} WARN={warning_count} FAIL={fatal_count}",
    ]
    if status == "PASS":
        text_lines.append(PASS_MARKER)
    text_lines.append("")
    for check in checks:
        text_lines.append(f"[{check['status']}] {check['name']} - {check['detail']}")
    TXT_OUT.write_text("\n".join(text_lines) + "\n", encoding="utf-8")

    print(PASS_MARKER if status == "PASS" else "EDGEIQ_RACE_WORKSPACE_BASELINE_V1_AUDIT_FAIL")
    print(f"Wrote {TXT_OUT}")
    print(f"Wrote {JSON_OUT}")
    print(f"PASS={pass_count} WARN={warning_count} FAIL={fatal_count}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
