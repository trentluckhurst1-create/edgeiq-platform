from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard"
SECTIONAL = DATA / "edgeiq_runner_sectional_performance_v1.csv"
EARLY_OUT = DATA / "edgeiq_results_early_speed_v1.csv"
LATE_OUT = DATA / "edgeiq_results_late_speed_v1.csv"
SUMMARY = DOCS / "edgeiq_results_early_late_speed_v1_summary.json"
REPORT = DOCS / "edgeiq_results_early_late_speed_v1_report.md"

FIELDS = [
    "canonical_race_id",
    "canonical_runner_id",
    "race_date",
    "track",
    "race_number",
    "race_distance_metres",
    "speed_phase",
    "lengths_vs_standard",
    "matched_segment_count",
    "calculated_segment_count",
    "coverage_status",
    "coverage_reason",
    "source_feed",
]


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


def build_rows(rows: list[dict[str, str]], phase: str, value_field: str) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for row in rows:
        calculated = clean(row.get("coverage_status")) == "CALCULATED" and clean(row.get(value_field))
        output.append({
            "canonical_race_id": clean(row.get("canonical_race_id")),
            "canonical_runner_id": clean(row.get("canonical_runner_id")),
            "race_date": clean(row.get("race_date")),
            "track": clean(row.get("track")),
            "race_number": clean(row.get("race_number")),
            "race_distance_metres": clean(row.get("race_distance_metres")),
            "speed_phase": phase,
            "lengths_vs_standard": clean(row.get(value_field)) if calculated else "",
            "matched_segment_count": clean(row.get("matched_segment_count")),
            "calculated_segment_count": clean(row.get("calculated_segment_count")),
            "coverage_status": "CALCULATED" if calculated else "SECTIONAL_PERFORMANCE_SCOPE_BLOCKED",
            "coverage_reason": clean(row.get("coverage_reason")),
            "source_feed": "edgeiq_runner_sectional_performance_v1.csv",
        })
    return output


def main() -> int:
    sectional = read_csv(SECTIONAL)
    early_rows = build_rows(sectional, "EARLY", "early_lengths_vs_standard")
    late_rows = build_rows(sectional, "LATE", "late_lengths_vs_standard")
    write_csv(EARLY_OUT, early_rows, FIELDS)
    write_csv(LATE_OUT, late_rows, FIELDS)
    summary = {
        "input_sectional_rows": len(sectional),
        "historical_current_early_rows_retained": len(read_csv(DATA / "edgeiq_current_early_speed_v1.csv")),
        "historical_current_late_rows_retained": len(read_csv(DATA / "edgeiq_current_late_speed_v1.csv")),
        "fresh_runner_rows": len(sectional),
        "early_speed_rows": len(early_rows),
        "late_speed_rows": len(late_rows),
        "early_calculated_rows": sum(1 for row in early_rows if row["coverage_status"] == "CALCULATED"),
        "late_calculated_rows": sum(1 for row in late_rows if row["coverage_status"] == "CALCULATED"),
        "rejections": sum(1 for row in early_rows + late_rows if row["coverage_status"] != "CALCULATED"),
        "status": "EARLY_LATE_SPEED_SCOPE_BLOCKED_FOR_CURRENT_ROWS",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# Results Early/Late Speed V1\n\n"
        f"Status: `{summary['status']}`\n\n"
        f"Early rows: `{summary['early_speed_rows']}`\n\n"
        f"Late rows: `{summary['late_speed_rows']}`\n\n"
        f"Existing current early rows retained: `{summary['historical_current_early_rows_retained']}`\n\n"
        f"Existing current late rows retained: `{summary['historical_current_late_rows_retained']}`\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
