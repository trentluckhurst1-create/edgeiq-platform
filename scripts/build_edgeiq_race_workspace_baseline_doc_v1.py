from __future__ import annotations

from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "engineering" / "EDGEIQ_RACE_WORKSPACE_BASELINE_20260715.md"


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def line_count(path: str) -> int:
    return len(read_text(path).splitlines())


def file_size(path: str) -> int:
    target = ROOT / path
    return target.stat().st_size if target.exists() else 0


def build_doc() -> str:
    generated = datetime.now().isoformat(timespec="seconds")
    component_rows = [
        ("RaceFileV3", "src/edgeiq-os/race/RaceFileV3.tsx", "Global orchestrator; builds active race file from meeting/race state and mounts race or runner workspaces."),
        ("WorkspaceShell", "src/edgeiq-os/race/components/WorkspaceShell.tsx", "Shared shell, app nav, page header and footer."),
        ("RaceWorkspace", "src/edgeiq-os/race/components/RaceWorkspace.tsx", "Race-level tab container: FORM GUIDE, MAP, MARKET, OVERVIEW, INSIGHTS, EPI, REVIEW."),
        ("RaceFormGuideWorkspace", "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx", "Full race form guide table, metric guide, runner profile stack and recent form rows."),
        ("MapWorkspace", "src/edgeiq-os/race/components/MapWorkspace.tsx", "Race and runner map view using map terminal feed plus race-context fallback."),
        ("MarketWorkspace", "src/edgeiq-os/race/components/MarketWorkspace.tsx", "Race market board using market terminal feed plus Pending Market fallback."),
        ("OverviewWorkspace", "src/edgeiq-os/race/components/OverviewWorkspace.tsx", "Race overview cards and evidence table using overview terminal feed."),
        ("InsightsWorkspace", "src/edgeiq-os/race/components/InsightsWorkspace.tsx", "Nexus-style insights workspace currently labelled INSIGHTS."),
        ("EpiWorkspaceWorkspace", "src/edgeiq-os/race/components/EpiWorkspaceWorkspace.tsx", "Performance/EPI matrix using current race EPI terminal feed."),
        ("ResultsWorkspace", "src/edgeiq-os/race/components/ResultsWorkspace.tsx", "Runner-level historical results workspace; race-level REVIEW is currently a pending shell."),
        ("RunnerProfileWorkspace", "src/edgeiq-os/race/components/RunnerProfileWorkspace.tsx", "Runner-level workspace container for profile/compare/results/dna/market/map."),
    ]

    service_rows = [
        ("Three-day catalogue", "src/edgeiq-os/race/services/threeDayCatalog.ts", "/data/edgeiq_three_day_product_catalog_v1.json"),
        ("Form guide enrichment", "src/edgeiq-os/race/services/formGuideEnrichedFeed.ts", "/data/edgeiq_form_guide_enriched_v2.json"),
        ("Form guide normaliser", "src/edgeiq-os/race/services/formGuideNormaliser.ts", "Normalises raceBook + field + enriched JSON into display rows"),
        ("MAP", "src/edgeiq-os/race/services/mapFeed.ts", "/data/edgeiq_map_terminal_feed_v1.csv"),
        ("MARKET", "src/edgeiq-os/race/services/marketFeed.ts", "/data/edgeiq_market_terminal_feed_v1.csv"),
        ("OVERVIEW", "src/edgeiq-os/race/services/overviewFeed.ts", "/data/edgeiq_overview_terminal_feed_v1.csv"),
        ("INSIGHTS", "src/edgeiq-os/race/services/insightsFeed.ts", "/data/edgeiq_insights_terminal_feed_v1.csv"),
        ("EPI", "src/edgeiq-os/race/services/epiWorkspaceFeed.ts", "/data/edgeiq_epi_workspace_terminal_feed_v1.csv"),
        ("Fallback race book", "src/edgeiq-os/services/RaceFileService.ts", "Builds in-memory fallback race book from race-file-v2 services"),
    ]

    data_files = [
        "public/data/edgeiq_three_day_product_catalog_v1.json",
        "public/data/edgeiq_form_guide_enriched_v2.json",
        "public/data/edgeiq_map_terminal_feed_v1.csv",
        "public/data/edgeiq_market_terminal_feed_v1.csv",
        "public/data/edgeiq_overview_terminal_feed_v1.csv",
        "public/data/edgeiq_insights_terminal_feed_v1.csv",
        "public/data/edgeiq_epi_workspace_terminal_feed_v1.csv",
    ]

    lines: list[str] = []
    lines.append("# EDGEiQ Race Workspace Baseline - 2026-07-15")
    lines.append("")
    lines.append(f"Generated: {generated}")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("This baseline records the current Race Workspace implementation before the gated beta lock work continues. It is an inspection artifact only; no race-workspace UI source is changed by this task.")
    lines.append("")
    lines.append("## Active Navigation")
    lines.append("")
    lines.append("- Global sections: MEETINGS, RESULTS, LAB, SETTINGS.")
    lines.append("- Race-level tabs: FORM GUIDE, MAP, MARKET, OVERVIEW, INSIGHTS, EPI, REVIEW.")
    lines.append("- Runner-level tabs: PROFILE, COMPARE, RESULTS, DNA, MARKET, MAP.")
    lines.append("- Race state is selected in `RaceFileV3.tsx` and passed into `RaceWorkspace.tsx` as `raceBook`, `field`, `meetingRaces`, and `selectedRaceKey`.")
    lines.append("")
    lines.append("## Active Components")
    lines.append("")
    lines.append("| Component | File | Lines | Role |")
    lines.append("| --- | --- | ---: | --- |")
    for name, path, role in component_rows:
        lines.append(f"| {name} | `{path}` | {line_count(path)} | {role} |")
    lines.append("")
    lines.append("## Active Services And Feeds")
    lines.append("")
    lines.append("| Area | Service | Feed / Purpose |")
    lines.append("| --- | --- | --- |")
    for area, path, feed in service_rows:
        lines.append(f"| {area} | `{path}` | `{feed}` |")
    lines.append("")
    lines.append("## Current Data Surface")
    lines.append("")
    lines.append("| File | Size bytes | Exists |")
    lines.append("| --- | ---: | --- |")
    for path in data_files:
        exists = (ROOT / path).exists()
        lines.append(f"| `{path}` | {file_size(path)} | {'yes' if exists else 'no'} |")
    lines.append("")
    lines.append("## Inspection Findings")
    lines.append("")
    lines.append("- FORM GUIDE is the most complete race workspace surface. It uses `edgeiq_form_guide_enriched_v2.json`, displays summary metrics, all-runner profiles, recent form, profile records, jockey/class/preparation sections, and ESI split columns.")
    lines.append("- MAP, MARKET, OVERVIEW, INSIGHTS and EPI all use small terminal feed loaders with frontend guards that reject parsed CSV feeds above 10,000 rows.")
    lines.append("- Race-level REVIEW is currently a pre-race pending shell; the richer `ResultsWorkspace.tsx` is mounted only inside the runner-level RESULTS tab.")
    lines.append("- Current visible race-level MAP/MARKET/OVERVIEW/EPI/INSIGHTS surfaces still expose operational/developer language such as workspace ids, feed rows, loaded rows, matched rows, feed status, source names, and model information.")
    lines.append("- Current race-level MAP table columns are `NO / HORSE / BARRIER / EFFECTIVE BARRIER / RUN STYLE / EARLY SPEED / PROJECTED POSITION`, not the locked customer-facing MAP table.")
    lines.append("- Current race-level MARKET table columns include HIGH, LOW, MOVE and STATUS, not the locked customer-facing MARKET table.")
    lines.append("- `RaceWorkspace.tsx` tab labels currently include INSIGHTS and EPI rather than the brief's NEXUS / PERFORMANCE naming.")
    lines.append("- No Meeting workspace source files were modified for this baseline task. The existing weather v1.2 integration must remain authoritative in later visual polish.")
    lines.append("")
    lines.append("## Baseline Gate")
    lines.append("")
    lines.append("Task 1 requires the audit marker `EDGEIQ_RACE_WORKSPACE_BASELINE_V1_AUDIT_PASS` and a passing `npm run build` before feature or visual changes continue.")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(build_doc(), encoding="utf-8")
    print(f"Wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
