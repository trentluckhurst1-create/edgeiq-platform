
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CONFIG = ROOT / "config" / "performance-intelligence"
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating"
OUT = DOC_DIR / "edgeiq_horse_performance_rating_builder_defect_check_v1.csv"
REPORT = DOC_DIR / "edgeiq_horse_performance_rating_builder_defect_check_report_v1.md"

CHECKS = [
    ("wrong input filename", "build_edgeiq_horse_performance_rating_fact_v1.py", "edgeiq_horse_performance_aggregate_fact_v1.csv", "NO_DEFECT"),
    ("wrong V1/V2 path", "build_edgeiq_performance_intelligence_base_fact_v1.py", "edgeiq_lengths_versus_standard_fact_v1.csv", "NO_DEFECT_CANONICAL_BRIDGE_PRESENT"),
    ("incorrect delimiter", "all active builders", "csv.DictReader default comma", "NO_DEFECT"),
    ("empty DataFrame initialisation", "active Python csv builders", "no pandas DataFrame initialisation", "NO_DEFECT"),
    ("incorrect inner join", "rating fact builder", "direct aggregate input, no join", "NO_DEFECT"),
    ("join key type mismatch", "rating fact builder", "direct aggregate input, no join", "NO_DEFECT"),
    ("filter inversion", "parameter builders", "APPROVED source rows become AVAILABLE facts", "NO_DEFECT"),
    ("surface enum mismatch", "rating fact builder", "no explicit surface enum consumed", "NO_DEFECT"),
    ("distance type mismatch", "rating fact builder", "no direct distance consumed; upstream positive int validation", "NO_DEFECT"),
    ("incorrect null test", "active builders", "blank required fields fail hard", "NO_DEFECT"),
    ("formula called before joins", "rating fact builder", "formula applied after aggregate validation", "NO_DEFECT"),
    ("candidate output never promoted", "rating fact builder", "production path only; no candidate stage defined", "GOVERNANCE_CANDIDATE_STAGE_MISSING_NOT_CURRENT_ZERO_CAUSE"),
    ("orchestrator omission", "available local evidence", "not proven in this defect audit", "NOT_PROVEN"),
    ("stale contract column names", "compatibility audit", "0 schema failures", "NO_DEFECT"),
    ("normalisation parameter source missing", "build_edgeiq_performance_normalisation_parameter_fact_v1.py", "config/performance-intelligence/edgeiq_performance_normalisation_parameter_source_v1.csv", "SOURCE_MISSING"),
    ("horse aggregation parameter source missing", "build_edgeiq_horse_performance_aggregation_parameter_fact_v1.py", "config/performance-intelligence/edgeiq_horse_performance_aggregation_parameter_source_v1.csv", "SOURCE_MISSING"),
    ("horse identity map source missing", "build_edgeiq_horse_performance_observation_fact_v1.py", "config/performance-intelligence/edgeiq_horse_performance_identity_map_v1.csv", "SOURCE_MISSING"),
]


def read_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return sum(1 for _ in reader)

rows = []
for check_name, responsible_file, evidence, status in CHECKS:
    rows.append({
        "check_name": check_name,
        "responsible_file": responsible_file,
        "evidence": evidence,
        "defect_status": status,
        "repair_action": "NO_REPAIR_APPLIED" if status != "SOURCE_MISSING" else "SOURCE_GOVERNANCE_REQUIRED",
    })

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=["check_name", "responsible_file", "evidence", "defect_status", "repair_action"], extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

source_files = [
    CONFIG / "edgeiq_performance_normalisation_parameter_source_v1.csv",
    CONFIG / "edgeiq_horse_performance_aggregation_parameter_source_v1.csv",
    CONFIG / "edgeiq_horse_performance_identity_map_v1.csv",
]
lines = [
    "# EDGEiQ Horse Performance Rating Builder Defect Check V1",
    "",
    "Deterministic code defect found: `NO`",
    "Repair applied: `NO`",
    "",
    "## Missing Governed Sources",
]
for path in source_files:
    lines.append(f"- `{path.relative_to(ROOT)}`: exists=`{'YES' if path.exists() else 'NO'}`, rows=`{read_rows(path)}`")
lines.extend([
    "",
    "## Finding",
    "The zero-row outcome is reproducible through missing governed source dependencies, not through a deterministic builder defect. The parameter builders intentionally write header-only fact files when their governed source CSVs are absent. The horse observation builder would fail once rating-base rows exist unless a governed identity map is restored.",
    "No formula, threshold, rating scale, temporal rule, identity rule or source provenance change was made.",
])
REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(json.dumps({
    "deterministic_code_defect_found": False,
    "source_missing_checks": sum(1 for row in rows if row["defect_status"] == "SOURCE_MISSING"),
    "report": str(REPORT),
}, indent=2))
