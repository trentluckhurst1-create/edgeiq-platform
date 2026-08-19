import csv
import json
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DOCS = ROOT / "docs" / "full-product-implementation"
RACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceIntelligenceWorkspace.tsx"
WRAPPER = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
BROWSER = DOCS / "EDGEIQ_RACE_WORKSPACE_V1_REPAIR_BROWSER_ACCEPTANCE.json"

def read(path):
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""

def main():
    race = read(RACE)
    wrapper = read(WRAPPER)
    css = read(CSS)
    browser = json.loads(BROWSER.read_text(encoding="utf-8")) if BROWSER.exists() else {}
    checks = [
        ("checkpoint_script_exists", (ROOT / "scripts" / "checkpoint_edgeiq_race_workspace_v1_repair.py").exists()),
        ("apply_script_exists", (ROOT / "scripts" / "apply_edgeiq_race_workspace_v1_repair.py").exists()),
        ("browser_acceptance_script_exists", (ROOT / "scripts" / "audit_edgeiq_race_workspace_v1_repair_browser_acceptance.mjs").exists()),
        ("forensic_report_exists", (DOCS / "EDGEIQ_RACE_WORKSPACE_V1_FAILURE_FORENSIC_REPORT.md").exists()),
        ("mounted_component_race", 'RACE: "RaceIntelligenceWorkspace"' in wrapper),
        ("race_component_attr", 'data-edgeiq-race-workspace-v1="repair-v1"' in race),
        ("live_shell_scope_css", ".eiq-approved-shell .eiq-race-v1" in css),
        ("race_tabs_unhidden", ".eiq-race-workspace--race > .eiq-context-tabs" in css and "display: grid" in css),
        ("four_summary_cards_source", "model.cards.map" in race and "eiq-race-v1__summary-card" in race),
        ("what_matters_source", "WHAT MATTERS TODAY" in race),
        ("speed_map_preview_source", "SPEED MAP PREVIEW" in race),
        ("epi_top3_source", "EPI TOP 3" in race),
        ("runner_board_headers", "<th>SPD</th>" in race and "<th>EDGEIQ</th>" in race),
        ("old_headers_removed", "EARLY SPEED" not in race and "EDGEIQ PRICE" not in race),
        ("mojibake_removed", not any(token in race for token in ["â", "Â", "œ", "™"])),
        ("browser_acceptance_pass", browser.get("overall_status") == "PASS"),
        ("responsive_1920_pass", bool(browser.get("viewports", [{}])[0].get("pass")) if browser.get("viewports") else False),
        ("responsive_1600_pass", bool(browser.get("viewports", [{}, {}])[1].get("pass")) if len(browser.get("viewports", [])) > 1 else False),
        ("responsive_1440_pass", bool(browser.get("viewports", [{}, {}, {}])[2].get("pass")) if len(browser.get("viewports", [])) > 2 else False),
        ("responsive_1366_pass", bool(browser.get("viewports", [{}, {}, {}, {}])[3].get("pass")) if len(browser.get("viewports", [])) > 3 else False),
        ("home_regression_pass", browser.get("home_regression_status") == "PASS"),
        ("meetings_regression_pass", browser.get("meetings_regression_status") == "PASS"),
        ("field_regression_pass", browser.get("field_regression_status") == "PASS"),
        ("r1_r2_r3_switching_pass", browser.get("race_switching_status") == "PASS"),
    ]
    rows = [{"check": name, "status": "PASS" if ok else "FAIL"} for name, ok in checks]
    overall = "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL"
    (DOCS / "EDGEIQ_RACE_WORKSPACE_V1_REPAIR_AUDIT.json").write_text(json.dumps({"overall_status": overall, "checks": rows}, indent=2), encoding="utf-8")
    with (DOCS / "EDGEIQ_RACE_WORKSPACE_V1_REPAIR_AUDIT.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status"])
        writer.writeheader()
        writer.writerows(rows)
    md = ["# EDGEiQ Race Workspace V1 Repair Audit", "", f"Overall status: **{overall}**", ""]
    md.extend(f"- {row['check']}: {row['status']}" for row in rows)
    (DOCS / "EDGEIQ_RACE_WORKSPACE_V1_REPAIR_AUDIT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"overall_status": overall, "failed": [r for r in rows if r["status"] != "PASS"]}, indent=2))

if __name__ == "__main__":
    main()
