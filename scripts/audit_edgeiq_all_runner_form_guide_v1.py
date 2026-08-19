from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx"
NORMALISER = ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideNormaliser.ts"
WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
ENRICHED = ROOT / "public" / "data" / "edgeiq_form_guide_enriched_v1.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_all_runner_form_guide_v1_audit.txt"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_all_runner_form_guide_v1_audit.json"

EXPECTED_SUMMARY_COLUMNS = [
    "NO",
    "SILK",
    "LAST 5",
    "HORSE",
    "TRAINER",
    "JOCKEY",
    "WT",
    "BAR",
    "DAYS",
    "EPI",
    "EARLY SPEED",
    "MARKET",
    "EDGEiQ PRICE",
    "SUITABILITY",
    "RACE SHAPE",
    "LATE SPEED",
    "FORM MOMENTUM",
]

EXPECTED_RECENT_COLUMNS = [
    "DATE",
    "TRACK",
    "DIST",
    "COND",
    "POS",
    "MARGIN",
    "WT",
    "BAR",
    "SP",
    "RATING",
    "EPI",
    "800-600",
    "600-400",
    "400-200",
    "200-F",
    "EARLY SPEED",
    "SUITABILITY",
    "FORM MOMENTUM",
]

REQUIRED_TOOLTIPS = [
    "LAST 5",
    "DAYS",
    "EPI",
    "EARLY SPEED",
    "MARKET",
    "EDGEiQ PRICE",
    "SUITABILITY",
    "RACE SHAPE",
    "LATE SPEED",
    "FORM MOMENTUM",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_columns(source: str, const_name: str) -> list[str]:
    match = re.search(rf"const\s+{re.escape(const_name)}\s*=\s*\[(.*?)\]", source, re.S)
    if not match:
        return []
    return re.findall(r'"([^"]+)"', match.group(1))


def add(checks: list[dict], name: str, passed: bool, detail: str) -> None:
    checks.append({"name": name, "status": "PASS" if passed else "FAIL", "detail": detail})


def feed_counts() -> dict[str, int]:
    if not ENRICHED.exists():
        return {}
    payload = json.loads(ENRICHED.read_text(encoding="utf-8"))
    races = payload.get("races", []) if isinstance(payload, dict) else []
    runners = [runner for race in races for runner in race.get("runners", [])]

    def has(value: object) -> bool:
        return value not in (None, "", [], {})

    return {
        "races": len(races),
        "official_runners": len(runners),
        "scratchings": sum(1 for runner in runners if runner.get("scratched")),
        "with_profile_data": sum(1 for runner in runners if has(runner.get("careerRecord"))),
        "with_historical_form": sum(1 for runner in runners if has(runner.get("fullForm"))),
        "with_market": sum(1 for runner in runners if has(runner.get("marketPrice"))),
        "with_epi": sum(1 for runner in runners if has(runner.get("epi"))),
        "with_edgeiq_price": sum(1 for runner in runners if has(runner.get("edgeiqPrice"))),
    }


def main() -> int:
    component = read(COMPONENT)
    normaliser = read(NORMALISER)
    workspace = read(WORKSPACE)
    css = read(CSS)
    checks: list[dict] = []
    summary_columns = extract_columns(component, "summaryColumns")
    recent_columns = extract_columns(component, "recentFormColumns")
    counts = feed_counts()

    add(checks, "field_column_order", summary_columns == EXPECTED_SUMMARY_COLUMNS, "Field table column order matches all-runner V1.")
    add(checks, "recent_form_column_order", recent_columns == EXPECTED_RECENT_COLUMNS, "Recent Form column order matches all-runner V1 and has no RACE column.")
    add(checks, "all_runner_profiles_rendered", "guide.runners.map((runner) =>" in component and "<RunnerProfile" in component, "Profiles are rendered by mapping every guide runner.")
    add(checks, "no_selected_runner_state", all(token not in component for token in ["selectedRunnerId", "setSelectedRunnerId", "selectedRunner =", "selectableDefault"]), "No selected-runner state remains in the Form Guide.")
    add(checks, "horse_anchor_scroll", "scrollToRunner(runner)" in component and "window.scrollTo" in component and "runnerProfileId" in component, "Horse names smooth-scroll to stable runner anchors.")
    add(checks, "horse_click_no_highlight", "setSelectedRunner" not in component and "className={`${active ? \"is-active\"" not in component, "Clicking horse names does not select or highlight field rows.")
    add(checks, "no_table_selected_row_css", ".eiq-form-summary-table--v3 tbody tr.is-active" not in css, "Selected-row styling removed from the Form Guide table.")
    add(checks, "no_zebra_striping_css", ".eiq-form-summary-table--v3 tbody tr:nth-child" not in css and ".eiq-form-summary-table--all-runner tbody tr:nth-child" not in css, "Zebra striping is absent from Form Guide table CSS.")
    add(checks, "consistent_row_background", ".eiq-form-summary-table--all-runner th," in css and "background: rgba(3, 8, 10, 0.58) !important;" in css, "Normal rows use one consistent table surface.")
    add(checks, "scratched_rows_faded", "is-scratched" in component and "text-decoration: line-through" in css and "opacity: 0.54" in css, "Scratchings are faded and struck through.")
    add(checks, "visible_heading_suitability_engine_removed", '"SUITABILITY ENGINE"' not in component, "SUITABILITY ENGINE is absent from visible headings.")
    add(checks, "visible_heading_suitability_present", '"SUITABILITY"' in component, "SUITABILITY heading is present.")
    add(checks, "visible_heading_shape_fit_removed", '"SHAPE FIT"' not in component, "SHAPE FIT is absent from visible headings.")
    add(checks, "visible_heading_race_shape_present", '"RACE SHAPE"' in component, "RACE SHAPE heading is present.")
    add(checks, "visible_heading_late_removed", '"LATE"' not in component, "Generic LATE heading is absent.")
    add(checks, "visible_heading_late_speed_present", '"LATE SPEED"' in component, "LATE SPEED heading is present.")
    add(checks, "barrier_speed_subheading_removed", "BARRIER SPEED" not in component and "Barrier Speed" not in normaliser, "BARRIER SPEED is not visible below EARLY SPEED.")
    add(checks, "stable_width_rules", "summaryColumnWidths" in component and "<colgroup>" in component and ".eiq-form-summary-table--all-runner table" in css, "Stable width rules exist.")
    add(checks, "metric_tooltips_exist", all(f"{label}:" in component or f'{label}":' in component for label in REQUIRED_TOOLTIPS), "Required metric tooltip definitions exist.")
    add(checks, "metric_tooltips_keyboard_accessible", 'type="button"' in component and 'className="eiq-form-tooltip-trigger"' in component and "onFocus={() => setActiveTooltip(column)}" in component and 'role="tooltip"' in component, "Tooltips are keyboard focusable.")
    add(checks, "metric_tooltips_not_clipped", ".eiq-form-tooltip" in css and "z-index: 1000" in css and "overflow-y: visible" in css, "Tooltip layer is above table content.")
    add(checks, "official_order_preserved", ".sort((a, b) => a.sortNo - b.sortNo)" in normaliser, "Runner profiles follow official runner-number order.")
    add(checks, "recent_form_under_runner_profile", "<RecentForm runner={runner}" in component, "Recent Form renders under every runner profile.")
    add(checks, "historical_sp_separate", "sp: safeText(run.startingPrice)" in normaliser and "marketPrice" in normaliser, "Historical SP remains separate from current Market.")
    add(checks, "current_values_not_copied_to_history", all(token in normaliser for token in ['suitability: ""', 'formMomentum: ""', 'epi: ""']), "Current Suitability, Momentum and EPI are not copied into prior runs.")
    add(checks, "no_model_logic_in_jsx", all(token not in component for token in ["Math.", "probability", "coefficient", "expectedValue", "fairOdds"]), "No model logic was added to JSX.")
    add(checks, "workspace_tabs_work", all(token in workspace for token in ['"FORM GUIDE"', '"MARKET"', '"MAP"', '"OVERVIEW"']), "FORM GUIDE, MARKET, MAP and OVERVIEW routing remains present.")
    add(checks, "feed_available", bool(counts), "Enriched form guide feed is available.")

    status = "EDGEIQ_ALL_RUNNER_FORM_GUIDE_V1_AUDIT_PASS" if all(check["status"] == "PASS" for check in checks) else "EDGEIQ_ALL_RUNNER_FORM_GUIDE_V1_AUDIT_FAIL"
    result = {
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "counts": counts,
        "summary_columns": summary_columns,
        "recent_form_columns": recent_columns,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [status, f"Generated: {result['generated_at']}", ""]
    for check in checks:
        lines.append(f"{check['status']}: {check['name']} - {check['detail']}")
    lines.extend(["", "Counts:"])
    for key, value in counts.items():
        lines.append(f"{key}: {value}")
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(status)
    print(f"Wrote {OUT_TXT}")
    print(f"Wrote {OUT_JSON}")
    return 0 if status.endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
