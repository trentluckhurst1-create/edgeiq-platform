from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
REPORT_STEM = DATA / "edgeiq_final_beta_repository_state_v1"
RUN_STAMP = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
CHECKPOINT_DIR = ROOT / "checkpoints" / f"edgeiq_final_beta_consolidation_v1_{RUN_STAMP}"

WORKSPACE_FILES = {
    "MEETINGS": "src/edgeiq-os/race/components/MeetingsWorkspace.tsx",
    "MEETING_DETAIL": "src/edgeiq-os/race/components/MeetingWorkspace.tsx",
    "FORM_GUIDE": "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx",
    "MAP": "src/edgeiq-os/race/components/MapWorkspace.tsx",
    "MARKET": "src/edgeiq-os/race/components/MarketWorkspace.tsx",
    "OVERVIEW": "src/edgeiq-os/race/components/OverviewWorkspace.tsx",
    "INSIGHTS": "src/edgeiq-os/race/components/InsightsWorkspace.tsx",
    "EPI": "src/edgeiq-os/race/components/EpiWorkspaceWorkspace.tsx",
    "RESULTS": "src/edgeiq-os/race/components/MeetingResultsWorkspace.tsx",
    "TRACK": "src/edgeiq-os/race/components/MeetingTrackWorkspace.tsx",
    "WEATHER": "src/edgeiq-os/race/components/MeetingWeatherWorkspace.tsx",
    "SCRATCHINGS": "src/edgeiq-os/race/components/MeetingScratchingsWorkspace.tsx",
    "GEAR_CHANGES": "src/edgeiq-os/race/components/MeetingGearChangesWorkspace.tsx",
}

PROTECTED_FILES = [
    "src/edgeiq-os/styles/edgeiqOsV2.css",
    "src/edgeiq-os/race/components/MeetingsWorkspace.tsx",
    "src/edgeiq-os/race/components/MeetingWorkspace.tsx",
    "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx",
    "src/edgeiq-os/race/components/MapWorkspace.tsx",
    "src/edgeiq-os/race/components/MarketWorkspace.tsx",
    "src/edgeiq-os/race/components/OverviewWorkspace.tsx",
    "src/edgeiq-os/race/components/InsightsWorkspace.tsx",
    "src/edgeiq-os/race/components/EpiWorkspaceWorkspace.tsx",
    "src/edgeiq-os/race/components/MeetingResultsWorkspace.tsx",
    "src/edgeiq-os/race/components/MeetingTrackWorkspace.tsx",
    "src/edgeiq-os/race/components/MeetingWeatherWorkspace.tsx",
    "src/edgeiq-os/race/services/weatherFeed.ts",
    "src/edgeiq-os/race/services/threeDayCatalog.ts",
    "src/edgeiq-os/race/services/formGuideNormaliser.ts",
    "src/edgeiq-os/race/services/formGuideEnrichedFeed.ts",
    "src/edgeiq-os/race/services/marketFeed.ts",
    "src/edgeiq-os/race/services/mapFeed.ts",
    "src/edgeiq-os/race/services/resultsFeed.ts",
    "src/edgeiq-os/shell/EdgeiqOsShell.tsx",
    "src/components/shell/edgeiqOsShell.css",
]

TERMINAL_FEEDS = [
    "edgeiq_three_day_window_v1.json",
    "edgeiq_three_day_product_catalog_v1.json",
    "edgeiq_form_guide_enriched_v2.csv",
    "edgeiq_map_terminal_feed_v1.csv",
    "edgeiq_market_terminal_feed_v1.csv",
    "edgeiq_overview_terminal_feed_v1.csv",
    "edgeiq_insights_terminal_feed_v1.csv",
    "edgeiq_epi_workspace_terminal_feed_v1.csv",
    "edgeiq_meeting_results_terminal_feed_v1.csv",
    "edgeiq_gear_terminal_feed_v1.csv",
    "edgeiq_on_track_weather_governed_v1_2.json",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except FileNotFoundError:
        return ""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def csv_header_and_count(path: Path) -> tuple[list[str], int]:
    if not path.exists():
        return [], 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            return [], 0
        return header, sum(1 for _ in reader)


def json_keys_and_count(value: Any) -> tuple[list[str], int]:
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value[:50]:
            if isinstance(item, dict):
                keys.update(item.keys())
        return sorted(keys), len(value)
    if isinstance(value, dict):
        for key in ("meetings", "races", "runners", "records", "rows", "data"):
            child = value.get(key)
            if isinstance(child, list):
                keys, count = json_keys_and_count(child)
                return keys, count
        return sorted(value.keys()), 1
    return [], 0


def git_status() -> list[str]:
    try:
        result = subprocess.run(["git", "status", "--short"], cwd=ROOT, text=True, capture_output=True, check=False)
        return result.stdout.splitlines()
    except Exception as exc:
        return [f"GIT_STATUS_ERROR: {exc}"]


def copy_checkpoint() -> list[dict[str, str]]:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    copied = []
    for item in PROTECTED_FILES:
        source = ROOT / item
        if not source.exists():
            copied.append({"category": "checkpoint", "item": Path(item).name, "path": item, "source": item, "checkpoint": "", "status": "MISSING", "notes": "Protected file missing at checkpoint time"})
            continue
        target = CHECKPOINT_DIR / item
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append({"category": "checkpoint", "item": Path(item).name, "path": item, "source": item, "checkpoint": rel(target), "status": "COPIED", "notes": "Protected file copied before final consolidation outputs"})
    return copied


def inventory_specs() -> list[dict[str, Any]]:
    rows = []
    spec_root = ROOT / "docs" / "beta-specifications"
    for path in sorted(spec_root.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".docx"}:
            rows.append({
                "category": "specification",
                "item": path.name,
                "path": rel(path),
                "status": "FOUND",
                "notes": f"{path.stat().st_size} bytes",
            })
    return rows


def inventory_files() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    categories = [
        ("component", SRC / "edgeiq-os" / "race" / "components", "*.tsx"),
        ("service", SRC / "edgeiq-os", "*.ts"),
        ("builder", SCRIPTS, "build_edgeiq_*.py"),
        ("audit_script", SCRIPTS, "audit_edgeiq_*.py"),
        ("capture_script", SCRIPTS, "capture_edgeiq_*.mjs"),
        ("governed_feed", DATA, "edgeiq_*"),
        ("audit_output", DATA, "*audit*"),
        ("report_output", DATA, "*report*"),
    ]
    for category, base, pattern in categories:
        if not base.exists():
            continue
        for path in sorted(base.glob(pattern)):
            if path.is_file():
                rows.append({
                    "category": category,
                    "item": path.name,
                    "path": rel(path),
                    "status": "FOUND",
                    "notes": f"{path.stat().st_size} bytes; modified {datetime.fromtimestamp(path.stat().st_mtime).isoformat()}",
                })
    visual_root = DATA / "visual_audits"
    if visual_root.exists():
        for path in sorted(visual_root.iterdir()):
            if path.is_dir():
                rows.append({
                    "category": "visual_audit_folder",
                    "item": path.name,
                    "path": rel(path),
                    "status": "FOUND",
                    "notes": f"{sum(1 for _ in path.rglob('*') if _.is_file())} files",
                })
    return rows


def extract_visible_fields() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    tag_re = re.compile(r"<(?:th|dt|strong|span|h[1-4])[^>]*>([^<>{}]{2,80})<", re.IGNORECASE)
    for workspace, file_name in WORKSPACE_FILES.items():
        path = ROOT / file_name
        text = read_text(path)
        fields: list[str] = []
        for match in tag_re.finditer(text):
            value = re.sub(r"\s+", " ", match.group(1)).strip()
            if value and not value.startswith("{") and value not in fields:
                fields.append(value)
        rows.append({
            "category": "workspace_fields_rendered",
            "item": workspace,
            "path": file_name,
            "status": "COMPONENT_FOUND" if path.exists() else "COMPONENT_MISSING",
            "notes": " | ".join(fields[:80]),
            "field_count": len(fields),
        })
    return rows


def inventory_feed_fields() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for feed in TERMINAL_FEEDS:
        path = DATA / feed
        if not path.exists():
            rows.append({"category": "feed_fields_supplied", "item": feed, "path": rel(path), "status": "MISSING", "notes": "", "row_count": 0})
            continue
        if path.suffix.lower() == ".csv":
            header, count = csv_header_and_count(path)
        else:
            header, count = json_keys_and_count(read_json(path))
        rows.append({
            "category": "feed_fields_supplied",
            "item": feed,
            "path": rel(path),
            "status": "FOUND",
            "notes": " | ".join(header[:120]),
            "row_count": count,
        })
    return rows


def current_totals() -> dict[str, Any]:
    totals = {"meetings": 0, "races": 0, "runners": 0, "source": ""}
    catalog = read_json(DATA / "edgeiq_three_day_product_catalog_v1.json")
    if isinstance(catalog, dict):
        meetings = catalog.get("meetings")
        if isinstance(meetings, list):
            totals["meetings"] = len(meetings)
            for meeting in meetings:
                races = meeting.get("races") if isinstance(meeting, dict) else []
                if isinstance(races, list):
                    totals["races"] += len(races)
                    for race in races:
                        runners = race.get("runners") if isinstance(race, dict) else []
                        if isinstance(runners, list):
                            totals["runners"] += len(runners)
            totals["source"] = "edgeiq_three_day_product_catalog_v1.json"
            return totals
    window = read_json(DATA / "edgeiq_three_day_window_v1.json")
    if isinstance(window, dict):
        meetings = window.get("meetings") or window.get("days")
        if isinstance(meetings, list):
            totals["meetings"] = len(meetings)
            totals["source"] = "edgeiq_three_day_window_v1.json"
    return totals


def classify_workspaces() -> list[dict[str, Any]]:
    rows = []
    audit_map = {
        "MEETINGS": "edgeiq_meetings_engineering_build_v1_audit.json",
        "MEETING_DETAIL": "edgeiq_meeting_detail_engineering_build_v1_audit.json",
        "FORM_GUIDE": "edgeiq_form_guide_engineering_build_v1_audit.json",
        "MAP": "edgeiq_map_engineering_build_v1_audit.json",
        "MARKET": "edgeiq_market_engineering_build_v1_audit.json",
        "OVERVIEW": "edgeiq_overview_engineering_build_v1_audit.json",
        "INSIGHTS": "edgeiq_insights_engineering_build_v1_audit.json",
        "EPI": "edgeiq_epi_workspace_engineering_build_v1_audit.json",
        "RESULTS": "edgeiq_results_engineering_build_v1_audit.json",
        "TRACK": "edgeiq_track_engineering_build_v1_audit.json",
        "WEATHER": "edgeiq_weather_engineering_build_v1_audit.json",
        "SCRATCHINGS": "edgeiq_scratchings_engineering_build_v1_audit.json",
        "GEAR_CHANGES": "edgeiq_gear_changes_engineering_build_v1_audit.json",
    }
    for workspace, audit_name in audit_map.items():
        component = ROOT / WORKSPACE_FILES.get(workspace, "")
        audit_path = DATA / audit_name
        audit_text = read_text(audit_path)
        audit_json = read_json(audit_path)
        has_pass = "PASS" in audit_text.upper() or (isinstance(audit_json, dict) and str(audit_json.get("status", "")).upper() == "PASS")
        if not component.exists():
            status = "DATA_WIRING_REQUIRED"
        elif has_pass:
            status = "COMPLETE_VERIFIED"
        elif audit_path.exists():
            status = "MANUAL_REVIEW_REQUIRED"
        else:
            status = "PARTIAL_GOVERNED_COVERAGE"
        rows.append({
            "category": "workspace_classification",
            "item": workspace,
            "path": rel(component) if component.exists() else WORKSPACE_FILES.get(workspace, ""),
            "status": status,
            "notes": rel(audit_path) if audit_path.exists() else "No current engineering audit found",
        })
    return rows


def unresolved_gaps() -> list[dict[str, Any]]:
    rows = []
    gap_files = [
        "edgeiq_remaining_beta_governed_data_gaps_v1.csv",
        "edgeiq_bom_search_location_resolver_v1_audit.txt",
        "edgeiq_bom_track_location_registry_v1_audit.txt",
        "edgeiq_track_conditions_source_audit_v1.txt",
    ]
    for name in gap_files:
        path = DATA / name
        text = read_text(path)
        rows.append({
            "category": "unresolved_source_gap",
            "item": name,
            "path": rel(path),
            "status": "FOUND" if path.exists() else "MISSING",
            "notes": text[:500].replace("\n", " | "),
        })
    return rows


def write_outputs(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "summary": summary, "rows": rows}
    (REPORT_STEM.with_suffix(".json")).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    fields = sorted({key for row in rows for key in row.keys()})
    with REPORT_STEM.with_suffix(".csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "EDGEIQ FINAL BETA REPOSITORY STATE V1",
        f"Generated: {payload['generated_at']}",
        f"Checkpoint: {summary['checkpoint_dir']}",
        f"Current totals: meetings={summary['current_totals'].get('meetings')} races={summary['current_totals'].get('races')} runners={summary['current_totals'].get('runners')} source={summary['current_totals'].get('source')}",
        f"Rows inventoried: {len(rows)}",
        "",
        "Workspace classifications:",
    ]
    for row in rows:
        if row.get("category") == "workspace_classification":
            lines.append(f"- {row['item']}: {row['status']} ({row['notes']})")
    lines.extend(["", "Git status sample:"])
    lines.extend(summary["git_status"][:200])
    REPORT_STEM.with_suffix(".txt").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    checkpoint_rows = copy_checkpoint()
    rows: list[dict[str, Any]] = []
    rows.extend(checkpoint_rows)
    rows.extend(inventory_specs())
    rows.extend(inventory_files())
    rows.extend(extract_visible_fields())
    rows.extend(inventory_feed_fields())
    rows.extend(classify_workspaces())
    rows.extend(unresolved_gaps())
    totals = current_totals()
    rows.append({"category": "current_totals", "item": "catalog", "path": totals.get("source", ""), "status": "INVENTORIED", "notes": json.dumps(totals), "row_count": totals.get("runners", 0)})
    summary = {
        "checkpoint_dir": rel(CHECKPOINT_DIR),
        "current_totals": totals,
        "counts_by_category": Counter(row["category"] for row in rows),
        "git_status": git_status(),
    }
    write_outputs(rows, summary)
    print(f"EDGEIQ_FINAL_BETA_REPOSITORY_STATE_V1_WRITTEN checkpoint={rel(CHECKPOINT_DIR)} rows={len(rows)}")


if __name__ == "__main__":
    main()
