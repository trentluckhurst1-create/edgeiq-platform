from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
OUT = DOCS / "edgeiq_standard_time_recovery_shortage_ledger_v1.csv"
SUMMARY = DOCS / "edgeiq_standard_time_recovery_result_summary_v1.json"
REPORT = DOCS / "edgeiq_standard_time_recovery_result_report_v1.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["benchmark_group_id", "track_name", "official_distance_metres", "eligible_observation_count", "minimum_required_sample", "observation_deficit", "accumulation_status", "blocker"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    obs = read_csv(DATA / "edgeiq_benchmark_observation_fact_v1.csv")
    elig = read_csv(DATA / "edgeiq_benchmark_eligibility_fact_v1.csv")
    accum = read_csv(DATA / "edgeiq_benchmark_accumulation_fact_v1.csv")
    std = read_csv(DATA / "edgeiq_standard_time_fact_v1.csv")
    rows = []
    for row in accum:
        count = int(float(row.get("eligible_observation_count") or 0))
        minimum = int(float(row.get("minimum_required_sample") or 20))
        rows.append({
            "benchmark_group_id": row.get("benchmark_group_id", ""),
            "track_name": row.get("track_name", ""),
            "official_distance_metres": row.get("official_distance_metres", ""),
            "eligible_observation_count": str(count),
            "minimum_required_sample": str(minimum),
            "observation_deficit": str(max(0, minimum - count)),
            "accumulation_status": row.get("accumulation_status", ""),
            "blocker": "INSUFFICIENT_GENUINE_OBSERVATIONS" if count < minimum else "READY",
        })
    groups_meeting = sum(1 for r in rows if r["blocker"] == "READY")
    groups_below = sum(1 for r in rows if r["blocker"] != "READY")
    total_deficit = sum(int(r["observation_deficit"]) for r in rows)
    if len(std) > 0:
        decision = "STANDARD_TIME_RECOVERY_PASS_NONZERO"
    elif groups_below and groups_meeting == 0:
        decision = "STANDARD_TIME_RECOVERY_BLOCKED_INSUFFICIENT_OBSERVATIONS"
    else:
        decision = "STANDARD_TIME_RECOVERY_FAIL_CODE_DEFECT"
    summary = {
        "decision": decision,
        "total_performance_observations": len(obs),
        "benchmark_eligible_observations": sum(1 for r in elig if str(r.get("standard_time_eligible")).lower() == "true"),
        "benchmark_groups": len(accum),
        "groups_meeting_minimum": groups_meeting,
        "groups_below_minimum": groups_below,
        "standard_time_rows": len(std),
        "minimum_required_sample": 20,
        "total_observation_deficit": total_deficit,
        "threshold_changed": "NO",
    }
    write_csv(OUT, rows)
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(f"# Standard Time Recovery Result V1\n\nDecision: `{decision}`\n\nStandard Time rows: `{len(std)}`\nGroups below minimum: `{groups_below}`\nTotal observation deficit: `{total_deficit}`\n\nNo threshold was changed and no synthetic observations were created.\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
