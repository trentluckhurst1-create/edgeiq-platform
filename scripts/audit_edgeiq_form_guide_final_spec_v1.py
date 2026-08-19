from __future__ import annotations

from pathlib import Path
import csv
import re


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx"
NORMALISER = ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideNormaliser.ts"
VIEW_MODEL = ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideWorkspaceViewModel.ts"
DOCS = ROOT / "docs" / "full-product-implementation"
OUT_CSV = DOCS / "edgeiq_form_guide_final_spec_audit_v1.csv"
OUT_MD = DOCS / "EDGEIQ_FORM_GUIDE_FINAL_SPEC_AUDIT_V1.md"


APPROVED_MAIN_COLUMNS = [
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
    "LATE SPEED",
    "SUITABILITY",
    "FORM MOMENTUM",
    "MARKET",
    "EDGEiQ PRICE",
]

APPROVED_RECENT_COLUMNS = [
    "DATE",
    "TRACK",
    "DIST",
    "CLASS",
    "GOING",
    "JOCKEY",
    "BARRIER",
    "WEIGHT",
    "EPI",
    "ERI",
    "POS",
    "POSITION IN RUNNING",
    "MARGIN",
    "SP",
    "8-6",
    "6-4",
    "4-2",
    "2-F",
]

REQUIRED_PROFILE_LABELS = [
    "Career",
    "Track",
    "Distance",
    "Track/Dist",
    "Firm",
    "Good",
    "Soft",
    "Heavy",
    "Jockey",
    "Class",
    "1st Up",
    "2nd Up",
    "3rd Up",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def has_array(text: str, name: str, values: list[str]) -> bool:
    pattern = re.compile(rf"const\s+{re.escape(name)}\s*=\s*\[(.*?)\]\s+as\s+const", re.S)
    match = pattern.search(text)
    if not match:
        return False
    block = match.group(1)
    found = re.findall(r'"([^"]+)"', block)
    return found == values


def main() -> None:
    component = read(COMPONENT)
    normaliser = read(NORMALISER)
    view_model = read(VIEW_MODEL)
    combined = "\n".join([component, normaliser, view_model])

    checks: list[dict[str, str]] = []

    def add(check: str, passed: bool, detail: str) -> None:
        checks.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})

    add("APPROVED_MAIN_COLUMNS", has_array(component, "summaryColumns", APPROVED_MAIN_COLUMNS), "Main table column order matches locked FORM GUIDE spec.")
    add("NO_CONFIDENCE_COLUMN", "Confidence" not in component and "CONFIDENCE" not in component, "Component contains no product-facing Confidence label.")
    add("NO_RACE_SHAPE_OR_AVG_FINISH_COLUMNS", "Race Shape" not in component and "Avg Finish" not in component, "Main table excludes Race Shape and Avg Finish.")
    add("RECENT_FORM_COLUMNS", has_array(component, "recentFormColumns", APPROVED_RECENT_COLUMNS), "Recent Form uses approved V2 columns including POSITION IN RUNNING and 8-6/6-4/4-2/2-F.")
    add("RECENT_FORM_LAST_EIGHT", ".slice(0, 8)" in normaliser, "Normaliser limits dossier recent form to up to eight starts.")
    add("HISTORICAL_JOCKEY_BARRIER", "jockey: safeText(run.jockey)" in normaliser and "barrier: safeText(run.barrier)" in normaliser, "Historical jockey and barrier are wired from enriched fullForm.")
    add("POSITION_FINISH_FIELD", "`${n}/${field}`" in normaliser, "Historical position formats as finish/field when field size exists.")
    add("POSITION_IN_RUNNING_PATH", "positionInRunning" in normaliser and "POSITION IN RUNNING" in component, "Position-in-running column and service path exist; source may be unavailable.")
    add("NUMERIC_ERI_PATH", "eri: metricText(run.raceRating, 1)" in normaliser, "ERI is numeric from run.raceRating path.")
    add("ESI_LABELS_ONLY", all(label in component for label in ["8-6", "6-4", "4-2", "2-F"]), "Standardised-length segment labels are present.")
    add("PROFILE_REQUIRED_LABELS", all(f'"{label}"' in view_model for label in REQUIRED_PROFILE_LABELS), "Horse Profile includes required generic categories.")
    add("TODAYS_MATCH_REPLACES_FLAGS", "TODAY'S MATCH" in component and "EDGEIQ FLAGS" not in combined and "FLAGS" not in component, "Today Match panel replaces flags language.")
    add("NO_MOCK_DEMO_SAMPLE", not re.search(r"\b(mock|demo|sample|placeholder)\b", combined, re.I), "Touched FORM GUIDE files contain no mock/demo/sample/placeholder strings.")
    add("NO_REACT_MODEL_CALC_KEYWORDS", not re.search(r"calculate|reverse|probability|edgePercent|fairPriceFrom", component, re.I), "Component remains display-only for model/pricing metrics.")

    DOCS.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(checks)

    failed = [row for row in checks if row["status"] != "PASS"]
    lines = ["# EDGEIQ FORM GUIDE Final Spec Audit V1", ""]
    for row in checks:
        lines.append(f"- {row['status']}: {row['check']} - {row['detail']}")
    lines.append("")
    lines.append("EDGEIQ_FORM_GUIDE_FINAL_SPEC_AUDIT_PASS" if not failed else "EDGEIQ_FORM_GUIDE_FINAL_SPEC_AUDIT_FAIL")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("EDGEIQ_FORM_GUIDE_FINAL_SPEC_AUDIT_PASS" if not failed else "EDGEIQ_FORM_GUIDE_FINAL_SPEC_AUDIT_FAIL")
    if failed:
        for row in failed:
            print(f"FAIL {row['check']}: {row['detail']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
