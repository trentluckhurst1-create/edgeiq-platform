from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# Resolve the checked-out repository on every platform. The previous hard-coded
# Windows workstation path made the GitHub Pages current-intelligence job run
# scripts against a path that cannot exist on ubuntu-latest.
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard"
MANIFEST_JSON = DOCS / "edgeiq_performance_intelligence_production_v2_manifest.json"
MANIFEST_CSV = DOCS / "edgeiq_performance_intelligence_production_v2_manifest.csv"
REPORT = DOCS / "edgeiq_performance_intelligence_production_v2_report.md"

STAGES = [
    ("elapsed_time_observations", "scripts/build_edgeiq_results_elapsed_time_observations_v1.py", "REQUIRED"),
    ("standard_time_facts", "scripts/build_edgeiq_standard_time_performance_facts_from_results_v1.py", "REQUIRED"),
    ("benchmark_eligibility", "scripts/build_edgeiq_results_standard_time_eligibility_v1.py", "REQUIRED"),
    ("standard_times", "scripts/build_edgeiq_results_standard_times_v1.py", "REQUIRED"),
    ("surface_registry", "scripts/build_edgeiq_canonical_surface_registry_v1.py", "REQUIRED"),
    ("surface_registry_audit", "scripts/audit_edgeiq_canonical_surface_registry_v1.py", "REQUIRED"),
    ("length_conversion_provider_tests", "scripts/test_edgeiq_length_conversion_method_v1.py", "REQUIRED"),
    ("lengths_v_standard_v2", "scripts/build_edgeiq_results_lengths_v_standard_v2.py", "REQUIRED"),
    ("lengths_v_standard_v2_audit", "scripts/audit_edgeiq_results_lengths_v_standard_v2.py", "REQUIRED"),
    ("runner_sectional_v2", "scripts/build_edgeiq_runner_sectional_performance_v2.py", "REQUIRED"),
    ("early_late_speed_v2", "scripts/build_edgeiq_results_early_late_speed_v2.py", "REQUIRED"),
    ("canonical_lvs_fact", "scripts/build_edgeiq_lengths_versus_standard_fact_from_results_v2.py", "REQUIRED"),
    ("performance_intelligence_base", "scripts/build_edgeiq_performance_intelligence_base_fact_v1.py", "REQUIRED"),
    ("epi_dependency", "scripts/audit_edgeiq_epi_performance_dependency_v1.py", "REQUIRED"),
]


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = ["stage", "script", "requirement", "status", "return_code", "detail"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: clean(row.get(field, "")) for field in fields})


def run_stage(script: str) -> tuple[str, int, str]:
    proc = subprocess.run([sys.executable, "-u", str(ROOT / script)], cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
    return ("PASS" if proc.returncode == 0 else "FAIL"), proc.returncode, proc.stdout[-2500:]


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    network_mode = os.environ.get("EDGEIQ_NETWORK_MODE", "OFFLINE").upper()
    rows: list[dict[str, object]] = []
    stopped = False
    for stage, script, requirement in STAGES:
        if stopped:
            rows.append({"stage": stage, "script": script, "requirement": requirement, "status": "SKIPPED", "return_code": "", "detail": "Skipped after failed required stage."})
            continue
        status, code, detail = run_stage(script)
        rows.append({"stage": stage, "script": script, "requirement": requirement, "status": status, "return_code": code, "detail": detail.replace("\r", " ").replace("\n", " ")})
        if status != "PASS":
            stopped = True
    candidate = ROOT / "public" / "data" / "edgeiq_results_lengths_v_standard_v2_CANDIDATE.csv"
    first_hash = hashlib.sha256(candidate.read_bytes()).hexdigest() if candidate.exists() else ""
    status, code, detail = run_stage("scripts/build_edgeiq_results_lengths_v_standard_v2.py") if not stopped else ("SKIPPED", 0, "")
    rows.append({"stage": "deterministic_rerun_lengths_v2", "script": "scripts/build_edgeiq_results_lengths_v_standard_v2.py", "requirement": "VALIDATION", "status": status, "return_code": code, "detail": detail.replace("\r", " ").replace("\n", " ")})
    second_hash = hashlib.sha256(candidate.read_bytes()).hexdigest() if candidate.exists() else ""
    rows.append({"stage": "candidate_hash_comparison", "script": "", "requirement": "VALIDATION", "status": "PASS" if first_hash and first_hash == second_hash else "FAIL", "return_code": "", "detail": f"first={first_hash}; second={second_hash}"})
    decision = "PERFORMANCE_INTELLIGENCE_PRODUCTION_V2_SYNTHETIC_CHAIN_PASS" if not stopped and first_hash == second_hash else "PERFORMANCE_INTELLIGENCE_PRODUCTION_V2_REVIEW_REQUIRED"
    payload = {
        "built_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "network_mode": network_mode,
        "decision": decision,
        "stages": rows,
        "candidate_paths_active": "NO",
        "production_outputs_overwritten": "PERFORMANCE_INTELLIGENCE_ONLY",
        "deterministic_hash_match": "YES" if first_hash and first_hash == second_hash else "NO",
    }
    MANIFEST_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    write_csv(MANIFEST_CSV, rows)
    REPORT.write_text("# Performance Intelligence Production V2 Orchestration\n\n" + f"Decision: `{decision}`\n\n" + "The retired Turf-only synthetic blocker is removed. Australian Synthetic V2 conversion, LVS, sectional, early/late, and canonical performance-base stages are included.\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "stages": len(rows)}, indent=2))
    return 0 if decision.endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
