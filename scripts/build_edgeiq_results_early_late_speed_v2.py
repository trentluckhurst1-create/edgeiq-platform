from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard"
SECTIONAL = DATA / "edgeiq_runner_sectional_performance_v2.csv"
EARLY_OUT = DATA / "edgeiq_results_early_speed_v2.csv"
LATE_OUT = DATA / "edgeiq_results_late_speed_v2.csv"
SUMMARY = DOCS / "edgeiq_results_early_late_speed_v2_summary.json"
REPORT = DOCS / "edgeiq_results_early_late_speed_v2_report.md"

FIELDS = ["canonical_race_id", "canonical_runner_id", "race_date", "track", "race_number", "race_distance_metres", "canonical_surface_group", "speed_phase", "lengths_vs_standard", "coverage_status", "source_feed", "method_version"]


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: clean(row.get(field, "")) for field in FIELDS})


def build(rows: list[dict[str, str]], phase: str, field: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:
        out.append({
            "canonical_race_id": clean(row.get("canonical_race_id")),
            "canonical_runner_id": clean(row.get("canonical_runner_id")),
            "race_date": clean(row.get("race_date")),
            "track": clean(row.get("track")),
            "race_number": clean(row.get("race_number")),
            "race_distance_metres": clean(row.get("race_distance_metres")),
            "canonical_surface_group": clean(row.get("canonical_surface_group")),
            "speed_phase": phase,
            "lengths_vs_standard": clean(row.get(field)),
            "coverage_status": "CALCULATED" if clean(row.get(field)) else "MISSING_PHASE",
            "source_feed": "edgeiq_runner_sectional_performance_v2.csv",
            "method_version": clean(row.get("method_version")),
        })
    return out


def main() -> int:
    sectional = read_csv(SECTIONAL)
    early = build(sectional, "EARLY", "early_lengths_vs_standard")
    late = build(sectional, "LATE", "late_lengths_vs_standard")
    write_csv(EARLY_OUT, early)
    write_csv(LATE_OUT, late)
    payload = {
        "sectional_input_rows": len(sectional),
        "runner_input_rows": len(sectional),
        "early_speed_output_rows": len(early),
        "late_speed_output_rows": len(late),
        "historical_rows_retained": len(read_csv(DATA / "edgeiq_current_early_speed_v1.csv")) + len(read_csv(DATA / "edgeiq_current_late_speed_v1.csv")),
        "fresh_rows_added": sum(1 for row in early + late if row["coverage_status"] == "CALCULATED"),
        "rejected_rows": sum(1 for row in early + late if row["coverage_status"] != "CALCULATED"),
        "status": "EARLY_LATE_SPEED_V2_BUILT",
    }
    SUMMARY.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text("# Results Early/Late Speed V2\n\n" + "\n".join(f"{k}: `{v}`" for k, v in payload.items()) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
