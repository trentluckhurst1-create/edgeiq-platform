from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from decimal import Decimal
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard"
SOURCE = DATA / "edgeiq_results_lengths_v_standard_v1_CANDIDATE.csv"
OUT = DOCS / "edgeiq_length_conversion_sensitivity_v1.csv"
SUMMARY = DOCS / "edgeiq_length_conversion_sensitivity_summary_v1.json"
REPORT = DOCS / "edgeiq_length_conversion_sensitivity_report_v1.md"


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


def quantile(values: list[float], pct: float) -> str:
    if not values:
        return ""
    ordered = sorted(values)
    idx = (len(ordered) - 1) * pct
    lo = int(idx)
    hi = min(lo + 1, len(ordered) - 1)
    if lo == hi:
        value = ordered[lo]
    else:
        value = ordered[lo] + ((ordered[hi] - ordered[lo]) * (idx - lo))
    return f"{value:.6f}"


def main() -> int:
    rows = read_csv(SOURCE)
    alternatives = [
        ("APPROVED_METHOD", None, "Production authoritative; blocked for unsupported current synthetic rows."),
        ("RESEARCH_FIXED_5_LPS", Decimal("5.0"), "Research-only fixed alternative."),
        ("RESEARCH_FIXED_5_5_LPS", Decimal("5.5"), "Research-only fixed alternative."),
        ("RESEARCH_FIXED_6_LPS", Decimal("6.0"), "Research-only fixed alternative."),
        ("RESEARCH_SPEED_DERIVED_PHYSICAL_LENGTH", None, "Blocked because no governed physical length distance parameter exists."),
    ]
    output: list[dict[str, object]] = []
    aggregate_by_method: dict[str, dict[tuple[str, str], Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for method, lps, note in alternatives:
        values: list[float] = []
        for row in rows:
            if lps is None:
                continue
            time_diff = Decimal(clean(row.get("time_difference_seconds")))
            value = time_diff * lps
            values.append(float(value))
            aggregate_by_method[method][(clean(row.get("canonical_race_id")), clean(row.get("canonical_runner_id")))] += value
        output.append({
            "method": method,
            "production_status": "AUTHORITATIVE" if method == "APPROVED_METHOD" else "RESEARCH_ONLY",
            "row_count": len(values),
            "minimum": f"{min(values):.6f}" if values else "",
            "maximum": f"{max(values):.6f}" if values else "",
            "median": f"{statistics.median(values):.6f}" if values else "",
            "p05": quantile(values, 0.05),
            "p95": quantile(values, 0.95),
            "extreme_abs_gt_10": sum(1 for value in values if abs(value) > 10),
            "condition_group_effects": "not production-applicable for current synthetic rows",
            "rank_stability": "not compared to approved output because approved method blocks unsupported rows",
            "note": note,
        })
    SUMMARY.write_text(json.dumps({
        "input_rows": len(rows),
        "approved_method_rows": 0,
        "research_alternatives_reported": 4,
        "production_authority_reopened": "NO",
        "status": "SENSITIVITY_COMPLETE_RESEARCH_ONLY",
    }, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    write_csv(OUT, output, [
        "method", "production_status", "row_count", "minimum", "maximum", "median", "p05", "p95",
        "extreme_abs_gt_10", "condition_group_effects", "rank_stability", "note",
    ])
    REPORT.write_text(
        "# Length Conversion Sensitivity V1\n\n"
        "Status: `SENSITIVITY_COMPLETE_RESEARCH_ONLY`\n\n"
        "The approved method remains authoritative. Research fixed-LPS alternatives were calculated only to show sensitivity on current time differences and are not production inputs.\n",
        encoding="utf-8",
    )
    print(json.dumps({"input_rows": len(rows), "status": "SENSITIVITY_COMPLETE_RESEARCH_ONLY"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
