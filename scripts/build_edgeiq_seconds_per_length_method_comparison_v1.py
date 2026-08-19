from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DOCS = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard"
DATA = ROOT / "public" / "data"

METHODS = DOCS / "edgeiq_seconds_per_length_method_comparison_v1.csv"
SENSITIVITY = DOCS / "edgeiq_seconds_per_length_sensitivity_v1.csv"
AUDIT = DOCS / "edgeiq_seconds_per_length_method_audit_v1.csv"
REPORT = DOCS / "edgeiq_seconds_per_length_method_report_v1.md"
DECISION = DOCS / "EDGEIQ_SECONDS_PER_LENGTH_METHOD_DECISION_V1.md"


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: clean(row.get(field, "")) for field in fields})


def main() -> int:
    forensics = read_csv(DOCS / "edgeiq_seconds_per_length_forensics_audit_v1.csv")
    implied = read_csv(DOCS / "edgeiq_historical_implied_seconds_per_length_v1.csv")
    params = read_csv(DATA / "edgeiq_length_conversion_parameter_fact_v1.csv")
    standards = read_csv(DATA / "edgeiq_results_standard_times_v1.csv")
    standard_speeds = [float(row["standard_speed_mps"]) for row in standards if clean(row.get("standard_speed_mps"))]
    avg_speed = sum(standard_speeds) / len(standard_speeds) if standard_speeds else 0.0

    rows = [
        {
            "method": "Candidate A - Speed-derived physical length",
            "provenance": "Requires governed physical horse-length distance parameter.",
            "coverage": "0",
            "determinism": "YES_IF_PARAMETER_EXISTS",
            "distance_behaviour": "speed dependent",
            "speed_behaviour": "seconds_per_length = length_distance_metres / standard_speed_mps",
            "historical_compatibility": "UNTESTED",
            "rating_stability": "UNKNOWN",
            "outlier_sensitivity": "MEDIUM",
            "rounding_sensitivity": "LOW",
            "implementation_risk": "BLOCKED: no governed physical length-distance parameter found.",
            "governance_decision": "BLOCKED_BY_MISSING_METHODOLOGY_EVIDENCE",
        },
        {
            "method": "Candidate B - Historical output calibrated",
            "provenance": "Algebraic recovery from existing authoritative outputs.",
            "coverage": str(len(implied)),
            "determinism": "NO_USABLE_ROWS",
            "distance_behaviour": "not recoverable",
            "speed_behaviour": "not recoverable",
            "historical_compatibility": "NO_RECOVERABLE_ROWS",
            "rating_stability": "UNKNOWN",
            "outlier_sensitivity": "UNKNOWN",
            "rounding_sensitivity": "UNKNOWN",
            "implementation_risk": "BLOCKED: no rows had usable time delta and lengths values.",
            "governance_decision": "BLOCKED_BY_MISSING_METHODOLOGY_EVIDENCE",
        },
        {
            "method": "Candidate C - Existing EDGEIQ rating convention",
            "provenance": "Repository forensics over active/archived EPI and ratings scripts.",
            "coverage": "references found, no parameter values",
            "determinism": "NO_PARAMETER_ROWS",
            "distance_behaviour": "DISTANCE_EXACT expected by active builder",
            "speed_behaviour": "not explicit",
            "historical_compatibility": "not proven",
            "rating_stability": "UNKNOWN",
            "outlier_sensitivity": "UNKNOWN",
            "rounding_sensitivity": "UNKNOWN",
            "implementation_risk": "BLOCKED: active contract expects source parameters, source file absent.",
            "governance_decision": "BLOCKED_BY_MISSING_METHODOLOGY_EVIDENCE",
        },
        {
            "method": "Candidate D - Fixed conversion",
            "provenance": "Numeric search terms only; no governed internal contract.",
            "coverage": "0 approved rows",
            "determinism": "YES_BUT_UNGOVERNED",
            "distance_behaviour": "fixed",
            "speed_behaviour": "none",
            "historical_compatibility": "not proven",
            "rating_stability": "UNKNOWN",
            "outlier_sensitivity": "HIGH",
            "rounding_sensitivity": "LOW",
            "implementation_risk": "REJECTED: would be an arbitrary constant.",
            "governance_decision": "REJECTED_UNGOVERNED_CONSTANT",
        },
    ]
    sensitivity_rows = []
    for length_distance in ["MISSING_PARAMETER"]:
        for speed in standard_speeds:
            sensitivity_rows.append({
                "candidate": "Speed-derived physical length",
                "length_distance_metres": length_distance,
                "standard_speed_mps": f"{speed:.6f}",
                "seconds_per_length": "",
                "status": "BLOCKED_MISSING_PHYSICAL_LENGTH_PARAMETER",
            })
    if not sensitivity_rows:
        sensitivity_rows.append({
            "candidate": "Speed-derived physical length",
            "length_distance_metres": "MISSING_PARAMETER",
            "standard_speed_mps": "",
            "seconds_per_length": "",
            "status": "BLOCKED_NO_STANDARD_SPEEDS",
        })
    selected_status = "NO_GOVERNED_METHOD_EXISTS"
    governance = "BLOCKED_BY_MISSING_METHODOLOGY_EVIDENCE"
    audit_rows = [
        {"check": "existing_parameter_rows", "status": "FAIL" if not params else "PASS", "value": len(params), "detail": "Published governed parameter rows."},
        {"check": "historical_recovery_rows", "status": "FAIL" if not implied else "PASS", "value": len(implied), "detail": "Usable implied seconds-per-length rows."},
        {"check": "standard_speed_rows_available", "status": "PASS" if standard_speeds else "FAIL", "value": len(standard_speeds), "detail": "Standard speeds available for sensitivity, but no length-distance parameter."},
        {"check": "governance_decision", "status": "FAIL", "value": governance, "detail": "No method can be promoted without methodology evidence."},
    ]
    write_csv(METHODS, rows, [
        "method", "provenance", "coverage", "determinism", "distance_behaviour", "speed_behaviour",
        "historical_compatibility", "rating_stability", "outlier_sensitivity", "rounding_sensitivity",
        "implementation_risk", "governance_decision",
    ])
    write_csv(SENSITIVITY, sensitivity_rows, [
        "candidate", "length_distance_metres", "standard_speed_mps", "seconds_per_length", "status",
    ])
    write_csv(AUDIT, audit_rows, ["check", "status", "value", "detail"])
    REPORT.write_text(
        "# Seconds Per Length Method Comparison V1\n\n"
        f"Method selection status: `{selected_status}`\n\n"
        f"Governance decision: `{governance}`\n\n"
        f"Published parameter rows: `{len(params)}`\n\n"
        f"Historical implied rows: `{len(implied)}`\n\n"
        f"Standard speed rows available for sensitivity: `{len(standard_speeds)}`\n\n"
        "No candidate is promoted. The fixed-conversion path is explicitly rejected because no governed contract or historical recovery supports it.\n",
        encoding="utf-8",
    )
    DECISION.write_text(
        "# EDGEiQ Seconds Per Length Method Decision V1\n\n"
        "## Status\n\n"
        "`NO_GOVERNED_METHOD_EXISTS`\n\n"
        "## Selected Method\n\n"
        "None. Lengths v Standard remains blocked.\n\n"
        "## Formula\n\n"
        "No formula selected. The active EDGEiQ convention expects `lengths_versus_standard = -time_delta_seconds / seconds_per_length`, but no governed `seconds_per_length` parameter is available.\n\n"
        "## Units\n\n"
        "Seconds per length. Length unit is not recoverable from current governed evidence.\n\n"
        "## Parameter Source\n\n"
        "`config/performance-intelligence/edgeiq_length_conversion_parameter_source_v1.csv` is expected by the active builder, but it is absent. `public/data/edgeiq_length_conversion_parameter_fact_v1.csv` has zero rows.\n\n"
        "## Scope\n\n"
        "The active builder expects `DISTANCE_EXACT` conversion parameters.\n\n"
        "## Distance Treatment\n\n"
        "Blocked. Distance-exact parameter rows are absent.\n\n"
        "## Speed Treatment\n\n"
        "Blocked. A speed-derived method would require a governed physical horse-length distance parameter, which is absent.\n\n"
        "## Surface And Condition Treatment\n\n"
        "No governed dependency found.\n\n"
        "## Rounding And Null Handling\n\n"
        "Null or missing parameters block calculation. No default constant is applied.\n\n"
        "## Evidence Strength\n\n"
        "`BLOCKED_BY_MISSING_METHODOLOGY_EVIDENCE`\n\n"
        "## Known Limitations\n\n"
        "Standard Times can be built, but Lengths v Standard, sectional performance and downstream EPI cannot be rebuilt without a governed conversion parameter or recoverable methodology.\n\n"
        "## Affected Downstream Engines\n\n"
        "Lengths v Standard, runner sectional performance, EPI, Performance Intelligence consumers.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "method_selection_status": selected_status,
        "governance_decision": governance,
        "published_parameter_rows": len(params),
        "historical_implied_rows": len(implied),
        "standard_speed_rows": len(standard_speeds),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
