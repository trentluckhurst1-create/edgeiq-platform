from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard"
MAP_OUT = DOCS / "edgeiq_epi_dependency_map_v1.csv"
READINESS_OUT = DOCS / "edgeiq_epi_input_readiness_v1.csv"
REPORT = DOCS / "edgeiq_epi_dependency_report_v1.md"


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: clean(row.get(field, "")) for field in fields})


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    lvs = read_csv(DATA / "edgeiq_results_lengths_v_standard_v2.csv")
    canonical = read_csv(DATA / "edgeiq_lengths_versus_standard_fact_v1.csv")
    sectional = read_csv(DATA / "edgeiq_runner_sectional_performance_v2.csv")
    early = read_csv(DATA / "edgeiq_results_early_speed_v2.csv")
    late = read_csv(DATA / "edgeiq_results_late_speed_v2.csv")
    base = read_csv(DATA / "edgeiq_performance_intelligence_base_fact_v1.csv")
    projected = read_csv(DATA / "edgeiq_race_entry_projected_performance_fact_v1.csv")
    converted = [row for row in lvs if clean(row.get("audit_status")) == "CALCULATED"]
    deps = [
        {"dependency": "Lengths v Standard", "status": "READY" if converted else "MISSING", "rows": len(converted), "detail": "V2 calculated Results LVS rows."},
        {"dependency": "Canonical LVS fact", "status": "READY" if canonical else "MISSING", "rows": len(canonical), "detail": "Canonical-compatible LVS fact."},
        {"dependency": "Runner sectional performance", "status": "READY" if any(clean(row.get("coverage_status")) in {"COMPLETE", "PARTIAL"} for row in sectional) else "MISSING", "rows": len(sectional), "detail": "V2 sectional aggregate rows."},
        {"dependency": "Early speed", "status": "READY" if any(clean(row.get("coverage_status")) == "CALCULATED" for row in early) else "MISSING", "rows": len(early), "detail": "V2 early speed rows."},
        {"dependency": "Late speed", "status": "READY" if any(clean(row.get("coverage_status")) == "CALCULATED" for row in late) else "MISSING", "rows": len(late), "detail": "V2 late speed rows."},
        {"dependency": "Performance Intelligence Base", "status": "READY" if base else "MISSING", "rows": len(base), "detail": "Existing base formula output."},
        {"dependency": "Race Entry Projected Performance", "status": "READY" if projected else "MISSING", "rows": len(projected), "detail": "Existing EPI formula dependency; not redesigned here."},
    ]
    readiness = [
        {"input": "lengths_v_standard_v2", "path": "public/data/edgeiq_results_lengths_v_standard_v2.csv", "rows": len(converted), "readiness": "READY" if converted else "MISSING"},
        {"input": "canonical_lengths_v_standard", "path": "public/data/edgeiq_lengths_versus_standard_fact_v1.csv", "rows": len(canonical), "readiness": "READY" if canonical else "MISSING"},
        {"input": "performance_intelligence_base", "path": "public/data/edgeiq_performance_intelligence_base_fact_v1.csv", "rows": len(base), "readiness": "READY" if base else "MISSING"},
        {"input": "race_entry_projected_performance", "path": "public/data/edgeiq_race_entry_projected_performance_fact_v1.csv", "rows": len(projected), "readiness": "READY" if projected else "MISSING"},
    ]
    write_csv(MAP_OUT, deps, ["dependency", "status", "rows", "detail"])
    write_csv(READINESS_OUT, readiness, ["input", "path", "rows", "readiness"])
    if converted and canonical and base and projected:
        decision = "EPI_INPUTS_READY"
    elif converted and canonical and base:
        decision = "EPI_INPUTS_PARTIAL_PROJECTED_PERFORMANCE_MISSING"
    else:
        decision = "EPI_INPUTS_MISSING"
    REPORT.write_text(
        "# EPI Performance Dependency V1\n\n"
        f"EPI readiness: `{decision}`\n\n"
        "The retired Turf-only synthetic blocker is no longer active. Any remaining blocker is an independent EPI formula dependency.\n",
        encoding="utf-8",
    )
    payload = {
        "epi_readiness": decision,
        "lengths_v_standard_rows": len(converted),
        "canonical_lengths_rows": len(canonical),
        "sectional_rows": len(sectional),
        "early_rows": len(early),
        "late_rows": len(late),
        "performance_intelligence_base_rows": len(base),
        "projected_performance_rows": len(projected),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
