from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
AUDIT = DOCS / "edgeiq_performance_fact_rebuild_from_racingcom_v1.csv"
SUMMARY = DOCS / "edgeiq_performance_fact_rebuild_from_racingcom_summary_v1.json"
REPORT = DOCS / "edgeiq_performance_fact_rebuild_from_racingcom_report_v1.md"


def run(script: str) -> tuple[int, str]:
    result = subprocess.run([sys.executable, "-u", str(ROOT / "scripts" / script)], cwd=str(ROOT), capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()


def count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["stage", "script", "status", "exit_code", "output_rows", "detail"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    stages = [
        ("canonical_speed_v2_1", "build_edgeiq_racingcom_canonical_speed_warehouse_v2_1.py", DATA / "edgeiq_racingcom_canonical_runner_speed_fact_v2_1.csv"),
        ("benchmark_observation", "build_edgeiq_benchmark_observation_fact_v1.py", DATA / "edgeiq_benchmark_observation_fact_v1.csv"),
        ("benchmark_eligibility", "build_edgeiq_benchmark_eligibility_fact_v1.py", DATA / "edgeiq_benchmark_eligibility_fact_v1.csv"),
        ("benchmark_accumulation", "build_edgeiq_benchmark_accumulation_fact_v1.py", DATA / "edgeiq_benchmark_accumulation_fact_v1.csv"),
        ("standard_time", "build_edgeiq_standard_time_engine_v1.py", DATA / "edgeiq_standard_time_fact_v1.csv"),
    ]
    rows = []
    ok = True
    for stage, script, output in stages:
        code, detail = run(script)
        rows.append({"stage": stage, "script": script, "status": "PASS" if code == 0 else "FAIL", "exit_code": str(code), "output_rows": str(count(output)), "detail": detail[-800:]})
        if code != 0:
            ok = False
            break
    summary = {
        "decision": "PERFORMANCE_FACT_REBUILD_PASS" if ok else "PERFORMANCE_FACT_REBUILD_FAIL",
        "canonical_runner_rows": count(DATA / "edgeiq_racingcom_canonical_runner_speed_fact_v2_1.csv"),
        "benchmark_observation_rows": count(DATA / "edgeiq_benchmark_observation_fact_v1.csv"),
        "benchmark_eligible_rows": count(DATA / "edgeiq_benchmark_eligibility_fact_v1.csv"),
        "benchmark_groups": count(DATA / "edgeiq_benchmark_accumulation_fact_v1.csv"),
        "standard_time_rows": count(DATA / "edgeiq_standard_time_fact_v1.csv"),
    }
    write_csv(AUDIT, rows)
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(f"# Performance Fact Rebuild From Racing.com V1\n\nDecision: `{summary['decision']}`\n\nBenchmark observations: `{summary['benchmark_observation_rows']}`\nStandard Time rows: `{summary['standard_time_rows']}`\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
