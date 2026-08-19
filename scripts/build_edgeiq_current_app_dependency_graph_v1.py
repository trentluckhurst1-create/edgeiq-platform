from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "engineering" / "EDGEIQ_CURRENT_APP_DEPENDENCY_GRAPH_20260715.md"
DATA_DIR = ROOT / "public" / "data"
COMPONENT_DIR = ROOT / "src" / "edgeiq-os" / "race" / "components"
SERVICE_DIR = ROOT / "src" / "edgeiq-os" / "race" / "services"
COVERAGE_JSON = DATA_DIR / "edgeiq_data_coverage_report_v1.json"
E2E_JSON = DATA_DIR / "edgeiq_end_to_end_validation_v1.json"


@dataclass(frozen=True)
class Dependency:
    field: str
    workspace: str
    component: str
    service: str
    builder: str
    feed: str
    upstream_source: str
    race_key: str
    runner_key: str
    matching_function: str
    displayed: str
    failure_reason: str


DEPENDENCIES: list[Dependency] = [
    Dependency(
        "EPI",
        "Form Guide / Field / Market / EPI",
        "RaceFormGuideWorkspace.tsx; EpiWorkspaceWorkspace.tsx; MarketWorkspace.tsx",
        "formGuideEnrichedFeed.ts; formGuideNormaliser.ts; epiWorkspaceFeed.ts; marketFeed.ts",
        "build_edgeiq_form_guide_enriched_v2.py; build_edgeiq_epi_workspace_terminal_feed_v1.py; build_edgeiq_market_terminal_feed_v1.py",
        "edgeiq_form_guide_enriched_v2.json; edgeiq_epi_workspace_terminal_feed_v1.csv; edgeiq_market_terminal_feed_v1.csv",
        "approved current intelligence / form-guide enriched feed",
        "form enrichment uses date|normalised track|race number; terminal feeds use race_key exact match",
        "runner_id, normalised runner name, no/saddlecloth fallback",
        "findEnrichedFormGuideRace; normaliseFormGuideRace; buildEpiWorkspaceViewModel; buildMarketViewModel",
        "yes",
        "partial coverage remains where current-date governed EPI is absent or runner identity is unmatched",
    ),
    Dependency(
        "EDGEiQ Price",
        "Form Guide / Market",
        "RaceFormGuideWorkspace.tsx; MarketWorkspace.tsx",
        "formGuideEnrichedFeed.ts; formGuideNormaliser.ts; marketFeed.ts",
        "build_edgeiq_form_guide_enriched_v2.py; build_edgeiq_market_terminal_feed_v1.py",
        "edgeiq_form_guide_enriched_v2.json; edgeiq_market_terminal_feed_v1.csv",
        "approved pricing output already present in enriched and market feeds",
        "form enrichment uses date|normalised track|race number; market terminal uses race_key exact match",
        "normalised runner name and runner number",
        "normaliseFormGuideRace; buildMarketViewModel",
        "yes",
        "remaining gaps are missing governed price rows, scratched runners, or unmatched current-race identity",
    ),
    Dependency(
        "early speed",
        "Form Guide / MAP",
        "RaceFormGuideWorkspace.tsx; MapWorkspace.tsx",
        "formGuideNormaliser.ts; mapFeed.ts",
        "build_edgeiq_current_early_speed_v1.py; build_edgeiq_map_terminal_feed_v1.py",
        "edgeiq_form_guide_enriched_v2.json; edgeiq_map_terminal_feed_v1.csv",
        "approved current speed projection and map terminal feed",
        "form enrichment key or race_key exact match for map terminal",
        "normalised runner name, runner number",
        "normaliseFormGuideRace; matchTerminalRow",
        "yes where present",
        "map terminal exact race_key can miss when current raceKey format differs from generated terminal feed",
    ),
    Dependency(
        "late speed",
        "Form Guide",
        "RaceFormGuideWorkspace.tsx",
        "formGuideNormaliser.ts",
        "build_edgeiq_current_late_speed_v1.py; build_edgeiq_form_guide_enriched_v2.py",
        "edgeiq_form_guide_enriched_v2.json",
        "approved current late-speed projection",
        "date|normalised track|race number",
        "runner_id, strict composite, normalised runner name",
        "findEnrichedFormGuideRace; normaliseFormGuideRace",
        "yes where present",
        "missing where no governed late-speed value exists for current runner or enrichment join fails",
    ),
    Dependency(
        "suitability",
        "Form Guide / Insights",
        "RaceFormGuideWorkspace.tsx; InsightsWorkspace.tsx",
        "formGuideNormaliser.ts; insightsFeed.ts",
        "build_edgeiq_current_suitability_v1.py; build_edgeiq_insights_terminal_feed_v1.py",
        "edgeiq_form_guide_enriched_v2.json; edgeiq_insights_terminal_feed_v1.csv",
        "approved suitability feed and governed insights feed",
        "date|normalised track|race number for form; exact race_key for insights",
        "runner_id, normalised runner name, no",
        "normaliseFormGuideRace; buildInsightsViewModel",
        "yes where present",
        "insights remain empty when terminal race_key has no exact selected-race match or evidence category missing",
    ),
    Dependency(
        "form momentum",
        "Form Guide / Insights",
        "RaceFormGuideWorkspace.tsx; InsightsWorkspace.tsx",
        "formGuideNormaliser.ts; insightsFeed.ts",
        "build_edgeiq_current_form_momentum_v1.py; build_edgeiq_insights_terminal_feed_v1.py",
        "edgeiq_form_guide_enriched_v2.json; edgeiq_insights_terminal_feed_v1.csv",
        "approved current form momentum and governed insights feed",
        "date|normalised track|race number for form; exact race_key for insights",
        "runner_id, normalised runner name, no",
        "normaliseFormGuideRace; buildInsightsViewModel",
        "yes where present",
        "missing where no governed momentum exists or insights evidence is unmatched",
    ),
    Dependency(
        "ERI",
        "Form Guide recent form / Results",
        "RaceFormGuideWorkspace.tsx; ResultsWorkspace.tsx",
        "formGuideNormaliser.ts; resultsFeed.ts",
        "build_edgeiq_form_guide_enriched_v2.py; build_edgeiq_meeting_results_terminal_feed_v1.py",
        "edgeiq_form_guide_enriched_v2.json; edgeiq_meeting_results_terminal_feed_v1.csv",
        "governed historical race index / post-race result feed where available",
        "date|normalised track|race number or meeting_key+race_key",
        "historical runner identity from enriched full form",
        "normaliseFormGuideRace; matchRow",
        "displayed as blank when absent",
        "current report shows no governed ERI coverage in current app feeds",
    ),
    Dependency(
        "market",
        "Form Guide / Market",
        "RaceFormGuideWorkspace.tsx; MarketWorkspace.tsx",
        "formGuideNormaliser.ts; marketFeed.ts",
        "build_edgeiq_form_guide_enriched_v2.py; build_edgeiq_market_terminal_feed_v1.py",
        "edgeiq_form_guide_enriched_v2.json; edgeiq_market_terminal_feed_v1.csv",
        "current market feed when supplied",
        "date|normalised track|race number for form; exact race_key for market terminal",
        "normalised runner name, no",
        "normaliseFormGuideRace; matchTerminalRow",
        "yes when present; Pending Market when absent",
        "partial because live market values are unavailable, stale, scratched, suspended, or unmatched",
    ),
    Dependency(
        "market fluctuation",
        "Market",
        "MarketWorkspace.tsx",
        "marketFeed.ts",
        "build_edgeiq_market_terminal_feed_v1.py",
        "edgeiq_market_terminal_feed_v1.csv",
        "current market terminal feed",
        "exact race_key",
        "normalised runner name, no",
        "matchTerminalRow",
        "yes where move is supplied",
        "not shown when move field is blank or terminal row is unmatched",
    ),
    Dependency(
        "map lane/order",
        "MAP",
        "MapWorkspace.tsx",
        "mapFeed.ts",
        "build_edgeiq_map_terminal_feed_v1.py",
        "edgeiq_map_terminal_feed_v1.csv",
        "current map terminal feed and race context fallback for listed runners",
        "exact race_key",
        "normalised runner name, no",
        "matchTerminalRow; raceRows",
        "race-context fallback displays runners; governed map evidence only when present",
        "matched_current_map_rows can remain zero when exact race_key or governed map evidence does not align",
    ),
    Dependency(
        "runner style",
        "MAP / Insights",
        "MapWorkspace.tsx; InsightsWorkspace.tsx",
        "mapFeed.ts; insightsFeed.ts",
        "build_edgeiq_map_terminal_feed_v1.py; build_edgeiq_insights_terminal_feed_v1.py",
        "edgeiq_map_terminal_feed_v1.csv; edgeiq_insights_terminal_feed_v1.csv",
        "governed map/intelligence evidence",
        "exact race_key",
        "normalised runner name, no",
        "matchTerminalRow; buildInsightsViewModel",
        "yes where run_style exists",
        "blank/pending when no governed style row is present",
    ),
    Dependency(
        "historical EPI tiles",
        "EPI",
        "EpiWorkspaceWorkspace.tsx",
        "epiWorkspaceFeed.ts",
        "build_edgeiq_epi_workspace_terminal_feed_v1.py",
        "edgeiq_epi_workspace_terminal_feed_v1.csv",
        "governed historical EPI tile columns start_10..start_1",
        "exact race_key",
        "horse/no within terminal row",
        "buildEpiWorkspaceViewModel; rowFromTerminal",
        "yes where tile values are supplied",
        "current summary reports historical_tiles=0, likely missing governed historical EPI source or join",
    ),
    Dependency(
        "runner insights",
        "Insights",
        "InsightsWorkspace.tsx",
        "insightsFeed.ts",
        "build_edgeiq_insights_terminal_feed_v1.py",
        "edgeiq_insights_terminal_feed_v1.csv",
        "approved governed insights categories",
        "exact race_key",
        "no/horse in terminal row",
        "buildInsightsViewModel",
        "yes where card/runner evidence rows match",
        "matched_intelligence=0 indicates no governed evidence rows matched current selected race",
    ),
    Dependency(
        "race overview",
        "Overview",
        "OverviewWorkspace.tsx",
        "overviewFeed.ts",
        "build_edgeiq_overview_terminal_feed_v1.py",
        "edgeiq_overview_terminal_feed_v1.csv",
        "governed race overview terminal feed",
        "exact race_key",
        "race-level only",
        "buildOverviewViewModel",
        "yes where overview rows match",
        "overview rows are unavailable when exact selected race_key is not present in terminal feed",
    ),
    Dependency(
        "scratchings",
        "Meeting Scratchings / Form Guide",
        "MeetingScratchingsWorkspace.tsx; RaceFormGuideWorkspace.tsx",
        "scratchingsFeed.ts; formGuideNormaliser.ts",
        "current catalogue and scratchings builders",
        "edgeiq_form_guide_enriched_v2.json; three-day catalogue",
        "current three-day catalogue and scratchings feed where supplied",
        "meeting/race keys from catalogue",
        "runner_id, runner name, no",
        "normaliseFormGuideRace",
        "yes where supplied",
        "partial where source catalogue has no scratching status for runner",
    ),
    Dependency(
        "barriers",
        "Field / Form Guide / MAP",
        "RaceFormGuideWorkspace.tsx; MapWorkspace.tsx",
        "formGuideNormaliser.ts; mapFeed.ts; threeDayCatalog.ts",
        "three-day catalogue builders; form-guide enrichment",
        "edgeiq_form_guide_enriched_v2.json; edgeiq_map_terminal_feed_v1.csv; three-day catalogue JSON",
        "official race field and form-guide enriched feed",
        "raceKey or date|track|raceNo",
        "runner_id, no, runner name",
        "normaliseFormGuideRace; raceRows",
        "yes where source has barrier",
        "remaining gaps usually source omissions or stale current catalogue identity",
    ),
    Dependency(
        "weights",
        "Field / Form Guide / MAP",
        "RaceFormGuideWorkspace.tsx; MapWorkspace.tsx",
        "formGuideNormaliser.ts; mapFeed.ts",
        "three-day catalogue builders; form-guide enrichment",
        "edgeiq_form_guide_enriched_v2.json; edgeiq_map_terminal_feed_v1.csv",
        "official race field and form-guide enriched feed",
        "raceKey or date|track|raceNo",
        "runner_id, no, runner name",
        "normaliseFormGuideRace; runnerWeight",
        "yes where source has weight",
        "remaining gaps are current source omissions, not calculated in React",
    ),
    Dependency(
        "jockey",
        "Field / Form Guide / MAP / Results",
        "RaceFormGuideWorkspace.tsx; MapWorkspace.tsx; ResultsWorkspace.tsx",
        "formGuideNormaliser.ts; mapFeed.ts; resultsFeed.ts",
        "three-day catalogue builders; form-guide enrichment; results terminal builder",
        "edgeiq_form_guide_enriched_v2.json; edgeiq_map_terminal_feed_v1.csv; edgeiq_meeting_results_terminal_feed_v1.csv",
        "official race field, form-guide enriched feed and results feed where available",
        "raceKey or date|track|raceNo",
        "runner_id, no, runner name",
        "normaliseFormGuideRace; runnerJockey; matchRow",
        "yes where source has jockey",
        "remaining gaps are source omissions or race-key mismatch",
    ),
    Dependency(
        "trainer",
        "Field / Form Guide / MAP / Results",
        "RaceFormGuideWorkspace.tsx; MapWorkspace.tsx; ResultsWorkspace.tsx",
        "formGuideNormaliser.ts; mapFeed.ts; resultsFeed.ts",
        "three-day catalogue builders; form-guide enrichment; results terminal builder",
        "edgeiq_form_guide_enriched_v2.json; edgeiq_map_terminal_feed_v1.csv; edgeiq_meeting_results_terminal_feed_v1.csv",
        "official race field, form-guide enriched feed and results feed where available",
        "raceKey or date|track|raceNo",
        "runner_id, no, runner name",
        "normaliseFormGuideRace; runnerTrainer; matchRow",
        "yes where source has trainer",
        "remaining gaps are source omissions or race-key mismatch",
    ),
    Dependency(
        "gear",
        "Meeting Gear / Form Guide",
        "MeetingGearChangesWorkspace.tsx; RaceFormGuideWorkspace.tsx",
        "gearChangesFeed.ts; formGuideNormaliser.ts",
        "build_edgeiq_gear_terminal_feed_v1.py; build_edgeiq_form_guide_enriched_v2.py",
        "edgeiq_gear_terminal_feed_v1.csv; edgeiq_form_guide_enriched_v2.json",
        "current gear terminal feed and current gear field where supplied",
        "race_key / date|track|raceNo depending feed",
        "normalised runner name, no, runner_id where present",
        "gearChangesFeed service; normaliseFormGuideRace",
        "current gear only where supplied",
        "current terminal gear feed reports source_confidence=current_gear_not_supplied for most/all rows",
    ),
    Dependency(
        "race results",
        "Results / Review",
        "ResultsWorkspace.tsx; MeetingResultsWorkspace.tsx; RaceWorkspace.tsx REVIEW",
        "resultsFeed.ts",
        "build_edgeiq_meeting_results_terminal_feed_v1.py",
        "edgeiq_meeting_results_terminal_feed_v1.csv",
        "meeting results terminal feed",
        "meeting_key+race_key, then date+normalised track+raceNo fallback",
        "result runner rows when individual results exist",
        "matchRow; buildMeetingResultsViewModel",
        "pending/unavailable for future races",
        "current/future races correctly withhold result rows until official result feed arrives",
    ),
    Dependency(
        "historical form",
        "Form Guide",
        "RaceFormGuideWorkspace.tsx",
        "formGuideEnrichedFeed.ts; formGuideNormaliser.ts",
        "build_edgeiq_form_guide_enriched_v2.py",
        "edgeiq_form_guide_enriched_v2.json",
        "canonical historical form enrichment",
        "date|normalised track|race number",
        "runner_id, strict composite, normalised runner name",
        "findEnrichedFormGuideRace; normaliseFormGuideRace",
        "yes",
        "reported as ready in beta coverage",
    ),
    Dependency(
        "recent form",
        "Form Guide",
        "RaceFormGuideWorkspace.tsx",
        "formGuideNormaliser.ts",
        "build_edgeiq_form_guide_enriched_v2.py",
        "edgeiq_form_guide_enriched_v2.json",
        "canonical fullForm array in enriched feed",
        "date|normalised track|race number",
        "runner_id, strict composite, normalised runner name",
        "normaliseFormGuideRace",
        "yes",
        "reported as ready in beta coverage",
    ),
    Dependency(
        "sectionals",
        "Form Guide / Results",
        "RaceFormGuideWorkspace.tsx; ResultsWorkspace.tsx",
        "formGuideNormaliser.ts; resultsFeed.ts",
        "build_edgeiq_form_guide_enriched_v2.py; build_edgeiq_meeting_results_terminal_feed_v1.py",
        "edgeiq_form_guide_enriched_v2.json; edgeiq_meeting_results_terminal_feed_v1.csv",
        "standardised sectional feed already wired into form enrichment where available",
        "date|normalised track|race number",
        "historical runner identity",
        "normaliseFormGuideRace",
        "yes where supplied",
        "some split segments remain blank where governed benchmark evidence is absent",
    ),
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def count_csv(path: Path) -> tuple[int, list[str]]:
    if not path.exists():
        return 0, []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            headers = next(reader)
        except StopIteration:
            return 0, []
        return sum(1 for _ in reader), headers


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {}


def feed_summary(feeds: Iterable[str]) -> list[dict[str, object]]:
    seen: set[str] = set()
    output: list[dict[str, object]] = []
    for feed_group in feeds:
        for feed in [part.strip() for part in feed_group.split(";")]:
            if not feed or feed in seen:
                continue
            seen.add(feed)
            path = DATA_DIR / feed
            if feed.endswith(".csv"):
                rows, headers = count_csv(path)
                output.append({"feed": feed, "exists": path.exists(), "rows": rows, "columns": headers})
            elif feed.endswith(".json"):
                payload = load_json(path)
                races = payload.get("races") if isinstance(payload, dict) else None
                runner_count = 0
                if isinstance(races, list):
                    for race in races:
                        runners = race.get("runners") if isinstance(race, dict) else None
                        if isinstance(runners, list):
                            runner_count += len(runners)
                output.append(
                    {
                        "feed": feed,
                        "exists": path.exists(),
                        "rows": len(races) if isinstance(races, list) else 0,
                        "columns": ["json:races", f"json:runners={runner_count}"] if payload else [],
                    }
                )
            else:
                output.append({"feed": feed, "exists": path.exists(), "rows": 0, "columns": []})
    return output


def service_fetch_summary() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(SERVICE_DIR.glob("*.ts")):
        text = read_text(path)
        urls = re.findall(r'const URL = "([^"]+)"', text)
        builders = sorted(set(re.findall(r"build[A-Za-z0-9_]+ViewModel|findEnrichedFormGuideRace|normaliseFormGuideRace", text)))
        matches = sorted(set(re.findall(r"function (match[A-Za-z0-9_]+|raceKeyFromParts|normaliseTrack|normaliseRunnerName|runnerName|runnerNo)", text)))
        if urls or builders or matches:
            rows.append(
                {
                    "service": path.name,
                    "loads": ", ".join(urls) if urls else "",
                    "builders": ", ".join(builders) if builders else "",
                    "matching": ", ".join(matches) if matches else "",
                }
            )
    return rows


def coverage_lookup() -> dict[str, str]:
    coverage = load_json(COVERAGE_JSON)
    items = coverage.get("coverage") or coverage.get("items") or coverage.get("fields") or []
    output: dict[str, str] = {}
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("field") or item.get("name") or item.get("metric") or "").strip()
            if not name:
                continue
            total = item.get("total") or item.get("eligible") or item.get("eligible_rows")
            covered = item.get("covered") or item.get("covered_rows")
            pct = item.get("coverage_pct") or item.get("percentage") or item.get("coverage")
            status = item.get("status") or ""
            output[name.upper()] = f"{covered}/{total} ({pct}%) {status}".strip()
    return output


def format_table(headers: list[str], rows: list[list[object]]) -> str:
    escaped_headers = [str(header).replace("|", "\\|") for header in headers]
    lines = ["| " + " | ".join(escaped_headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell).replace("\n", " ").replace("|", "\\|") for cell in row) + " |")
    return "\n".join(lines)


def build_doc() -> str:
    coverage = coverage_lookup()
    feeds = feed_summary(dep.feed for dep in DEPENDENCIES)
    services = service_fetch_summary()
    generated = datetime.now().isoformat(timespec="seconds")

    field_rows = []
    for dep in DEPENDENCIES:
        coverage_key = dep.field.upper()
        if coverage_key == "MARKET FLUCTUATION":
            coverage_key = "MARKET"
        if coverage_key == "MAP LANE/ORDER":
            coverage_key = "SPEED MAP"
        if coverage_key == "RUNNER STYLE":
            coverage_key = "SPEED MAP"
        if coverage_key == "HISTORICAL EPI TILES":
            coverage_key = "HISTORICAL EPI TILES"
        if coverage_key == "RACE RESULTS":
            coverage_key = "RESULTS"
        field_rows.append(
            [
                dep.workspace,
                dep.field,
                dep.component,
                dep.service,
                dep.builder,
                dep.feed,
                dep.race_key,
                dep.runner_key,
                dep.matching_function,
                coverage.get(coverage_key, "not separately reported"),
                dep.displayed,
                dep.failure_reason,
            ]
        )

    feed_rows = [
        [feed["feed"], "yes" if feed["exists"] else "no", feed["rows"], ", ".join(list(feed["columns"])[:16])]
        for feed in feeds
    ]
    service_rows = [[row["service"], row["loads"], row["builders"], row["matching"]] for row in services]

    e2e = load_json(E2E_JSON)
    e2e_selected = e2e.get("selected_race") or e2e.get("race") or {}

    return "\n".join(
        [
            "# EDGEiQ Current App Dependency Graph",
            "",
            f"Generated: {generated}",
            "",
            "Scope: current production application dependency chain for visible racing intelligence. This is documentation only and does not modify feeds or UI.",
            "",
            "## Current Validation Context",
            "",
            f"- Coverage input: `{COVERAGE_JSON.relative_to(ROOT)}`",
            f"- End-to-end input: `{E2E_JSON.relative_to(ROOT)}`",
            f"- Selected E2E race: `{json.dumps(e2e_selected, ensure_ascii=True) if e2e_selected else 'not available'}`",
            "",
            "## Visible Field Dependency Graph",
            "",
            format_table(
                [
                    "Workspace",
                    "Field",
                    "Component",
                    "Service",
                    "Builder",
                    "Generated Feed",
                    "Race Identity Key",
                    "Runner Identity Key",
                    "Matching Function",
                    "Current Coverage",
                    "Displayed",
                    "Failure Reason",
                ],
                field_rows,
            ),
            "",
            "## Generated Feed Inventory",
            "",
            format_table(["Feed", "Exists", "Rows", "Available Columns / Shape"], feed_rows),
            "",
            "## Service Loader And Matching Inventory",
            "",
            format_table(["Service", "Loaded URL", "View Builder", "Matching / Normalisation Functions"], service_rows),
            "",
            "## Main Dependency Findings",
            "",
            "- Form Guide enrichment uses `findEnrichedFormGuideRace`, which compares `raceDate|normalised track|raceNumber`.",
            "- MAP, Market, Overview, Insights and EPI terminal services primarily use exact `race_key` matching.",
            "- The most likely zero-match class is exact `race_key` mismatch between selected current race keys and generated terminal feeds, not React calculation failure.",
            "- Race context fallback is present in MAP and Market so listed runners can render without fabricating governed values.",
            "- React fetch guards reject oversized CSV feeds over 10,000 rows in the terminal services inspected here.",
            "- Missing governed values should continue to display blank, pending or unavailable states rather than synthetic defaults.",
            "",
            "## Required Field Coverage",
            "",
            "Covered fields: EPI, EDGEiQ Price, early speed, late speed, suitability, form momentum, ERI, market, market fluctuation, map lane/order, runner style, historical EPI tiles, runner insights, scratchings, barriers, weights, jockey, trainer, gear, race results, historical form, recent form, sectionals.",
            "",
        ]
    )


def main() -> None:
    missing_sources = [path for path in [COMPONENT_DIR, SERVICE_DIR, DATA_DIR] if not path.exists()]
    if missing_sources:
        raise SystemExit(f"Missing required source paths: {missing_sources}")
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(build_doc(), encoding="utf-8")
    print(f"Wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
