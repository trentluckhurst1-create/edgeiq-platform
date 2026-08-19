from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SRC = ROOT / "src" / "edgeiq-os"

COMPONENT = SRC / "race" / "components" / "RaceFormGuideWorkspace.tsx"
CSS = SRC / "styles" / "edgeiqOsV2.css"

AUDIT_TXT = DATA / "edgeiq_form_guide_v3_3_audit.txt"
AUDIT_JSON = DATA / "edgeiq_form_guide_v3_3_audit.json"

EXPECTED_COLUMNS = [
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

EXPECTED_RECENT_FORM_COLUMNS = [
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

REPORT_FILES = [
    DATA / "edgeiq_form_guide_v3_3_source_inventory.csv",
    DATA / "edgeiq_form_guide_v3_3_source_inventory_summary.txt",
    DATA / "edgeiq_form_guide_v3_3_join_audit.csv",
    DATA / "edgeiq_form_guide_v3_3_coverage.csv",
    DATA / "edgeiq_form_guide_v3_3_coverage_summary.txt",
]


def compact(text: str) -> str:
    return " ".join(text.split())


def extract_array(text: str, name: str) -> list[str]:
    start = text.index(f"const {name} = [")
    end = text.index("] as const;", start)
    block = text[start:end]
    values: list[str] = []
    for line in block.splitlines():
        line = line.strip().rstrip(",")
        if line.startswith('"') and line.endswith('"'):
            values.append(line.strip('"'))
    return values


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    failures: list[str] = []
    warnings: list[str] = []
    component = COMPONENT.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")

    if extract_array(component, "summaryColumns") != EXPECTED_COLUMNS:
        failures.append("Summary table columns do not match the V3.3 contract.")
    if extract_array(component, "recentFormColumns") != EXPECTED_RECENT_FORM_COLUMNS:
        failures.append("Recent Form columns do not match the V3.3 contract.")

    if "eiq-form-tooltip-trigger" in component:
        failures.append("Visible info-icon tooltip trigger remains in RaceFormGuideWorkspace.tsx.")
    if "createPortal" not in component or "eiq-form-header-tooltip" not in component:
        failures.append("Metric header tooltip is not rendered through the fixed portal implementation.")
    if "<details" in component or "<summary" in component:
        failures.append("Metric Guide still uses inline details/summary expansion.")
    if "Metric Guide" not in component or "eiq-form-metric-guide-popover" not in component:
        failures.append("Floating Metric Guide popover is missing.")
    if "scrollIntoView({ behavior: \"smooth\"" not in component:
        failures.append("Runner anchor smooth-scroll contract is missing.")
    if "aria-label={`View full profile and recent form for ${runner.horse}`}" not in component:
        failures.append("Runner horse anchor lacks explicit profile/recent-form aria label.")
    if "LatestRun" not in component:
        failures.append("Runner dossier Latest Run section is missing.")

    forbidden_labels = [
        "SUITABILITY ENGINE",
        "SHAPE FIT",
        "BARRIER SPEED",
        "CONFIDENCE",
        "Historical Reference",
        "Background Run",
    ]
    for label in forbidden_labels:
        if label in component:
            failures.append(f"Forbidden visible/internal label remains: {label}")

    if "--edgeiq-form-guide-columns" not in css:
        failures.append("Shared CSS column contract variable is missing.")
    if "--edgeiq-form-guide-min-width: 1640px" not in css:
        failures.append("Form guide min-width is not fixed at 1640px for the current OS shell.")
    if "--edgeiq-form-guide-row-height: 54px" not in css:
        failures.append("Summary table row height is not fixed at 54px.")
    if "position: fixed;" not in css or ".eiq-form-header-tooltip" not in css:
        failures.append("Header tooltip CSS is not fixed/portal safe.")
    if ".eiq-form-metric-guide-popover" not in css:
        failures.append("Floating Metric Guide popover CSS is missing.")

    for report in REPORT_FILES:
        if not report.exists():
            failures.append(f"Required report file missing: {report}")

    join_path = DATA / "edgeiq_form_guide_v3_3_join_audit.csv"
    if join_path.exists():
        rows = csv_rows(join_path)
        ambiguous = [row for row in rows if row.get("join_method") == "AMBIGUOUS"]
        duplicates = len(rows) - len({(row.get("race_date"), row.get("meeting"), row.get("race_number"), row.get("runner_number")) for row in rows})
        cross_race = [row for row in rows if not row.get("race_date") or not row.get("race_number")]
        if ambiguous:
            failures.append(f"Ambiguous joins accepted: {len(ambiguous)}")
        if duplicates:
            failures.append(f"Duplicate runner keys in join audit: {duplicates}")
        if cross_race:
            failures.append(f"Rows missing race identity in join audit: {len(cross_race)}")
        unmatched = [row for row in rows if row.get("join_method") == "UNMATCHED"]
        if unmatched:
            warnings.append(f"Unmatched runners remain for transparent display: {len(unmatched)}")

    coverage_path = DATA / "edgeiq_form_guide_v3_3_coverage.csv"
    if coverage_path.exists():
        coverage = csv_rows(coverage_path)
        zero_fields = sorted({row["field"] for row in coverage if row.get("covered") == "0"})
        if zero_fields:
            warnings.append(f"Zero-coverage fields are left blank rather than fabricated: {', '.join(zero_fields)}")

    status = "EDGEIQ_FORM_GUIDE_V3_3_AUDIT_PASS" if not failures else "EDGEIQ_FORM_GUIDE_V3_3_AUDIT_FAIL"
    payload = {
        "status": status,
        "failures": failures,
        "warnings": warnings,
        "component": str(COMPONENT),
        "css": str(CSS),
    }
    AUDIT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    AUDIT_TXT.write_text(
        "\n".join(
            [
                status,
                "",
                "Failures:",
                *(failures or ["None"]),
                "",
                "Warnings:",
                *(warnings or ["None"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(status)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        raise SystemExit(1)
    for warning in warnings:
        print(f"WARN: {warning}")


if __name__ == "__main__":
    main()
