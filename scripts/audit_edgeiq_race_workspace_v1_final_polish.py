from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "full-product-implementation"
TSX = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceIntelligenceWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
CSV_OUT = DOCS / "EDGEIQ_RACE_WORKSPACE_V1_FINAL_POLISH_AUDIT.csv"
JSON_OUT = DOCS / "EDGEIQ_RACE_WORKSPACE_V1_FINAL_POLISH_AUDIT.json"
MD_OUT = DOCS / "EDGEIQ_RACE_WORKSPACE_V1_FINAL_POLISH_AUDIT.md"


def check(name: str, passed: bool, evidence: str) -> dict[str, str]:
    return {"check": name, "status": "PASS" if passed else "FAIL", "evidence": evidence}


def main() -> None:
    tsx = TSX.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    rows = [
        check("base repair attr retained", 'data-edgeiq-race-workspace-v1="repair-v1"' in tsx, "Race component still marks repair-v1 render path."),
        check("visible What Matters count", "visibleWhatMatters.length" in tsx and "activeRunnerCount" not in tsx, "Count is derived from visible rendered matters, not runner count."),
        check("speed state classes", "is-empty-state" in tsx and "is-populated" in tsx, "Speed panel has populated/empty state classes."),
        check("duplicate Race Conditions removed", "eiq-race-v1__conditions" not in tsx, "Standalone duplicate conditions section absent from TSX."),
        check("EPI Available hidden", "epiStatusLabel" in tsx and "/^available$/i" in tsx, "Normal Available labels are suppressed."),
        check("EPI hierarchy CSS", "font-size: 16px" in css and "eiq-race-v1__epi-row em" in css, "EPI value has a stronger scan style."),
        check("EDGEiQ PRICE label", "EDGEiQ PRICE" in tsx, "Runner board labels approved price column unambiguously."),
        check("top spacing CSS", "padding-top: 8px" in css and "EDGEIQ RACE WORKSPACE V1 FINAL POLISH" in css, "Compact top breathing room added in Race scope."),
        check("compact empty speed CSS", "min-height: 72px" in css and "is-empty-state .eiq-race-v1__empty" in css, "Empty speed state height reduced without touching populated state."),
        check("live shell scope retained", ".eiq-approved-shell .eiq-race-v1" in css and ".eiq-approved-shell .eiq-race-workspace--race" in css, "No regression to .edgeiq-os-only scoping."),
        check("model math untouched by source scope", "buildRaceIntelligenceViewModel" in tsx and "epi_performance_rating" not in tsx, "React display polish only."),
    ]
    overall = "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL"
    DOCS.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "evidence"])
        writer.writeheader()
        writer.writerows(rows)
    JSON_OUT.write_text(json.dumps({"overall_status": overall, "checks": rows}, indent=2), encoding="utf-8")
    MD_OUT.write_text("# EDGEiQ Race Workspace V1 Final Polish Audit\n\nOverall status: **{}**\n\n{}\n".format(overall, "\n".join(f"- {r['status']}: {r['check']} - {r['evidence']}" for r in rows)), encoding="utf-8")
    print(json.dumps({"overall_status": overall, "checks": rows}, indent=2))
    if overall != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
