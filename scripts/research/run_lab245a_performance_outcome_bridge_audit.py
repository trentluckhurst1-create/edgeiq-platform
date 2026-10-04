from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "research" / "profitability_program" / "lab245a"
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = [
    ROOT / "docs/performance-intelligence/warehouse/edgeiq_performance_fact_warehouse_v1.csv",
    ROOT / "public/data/edgeiq_historical_results_warehouse_v2_graphql.csv",
    ROOT / "public/data/edgeiq_recovered_timing_warehouse_v1.csv",
    ROOT / "public/data/edgeiq_performance_intelligence_base_recovered_v1.csv",
    ROOT / "public/data/edgeiq_performance_normalisation_recovered_v1.csv",
    ROOT / "public/data/edgeiq_performance_rating_base_fact_v1.csv",
    ROOT / "public/data/edgeiq_horse_performance_observation_fact_v1.csv",
]
AUDITS = [
    ROOT / "docs/performance-intelligence/restart-v1/timing-warehouse-recovery/final-acceptance/final-acceptance.json",
    ROOT / "public/data/edgeiq_performance_rating_base_fact_v1_audit.json",
    ROOT / "public/data/edgeiq_horse_performance_observation_fact_v1_audit.json",
]

def header(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        try:
            return next(csv.reader(f))
        except StopIteration:
            return []

def rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("rb") as f:
        return max(0, sum(1 for _ in f) - 1)

inventory = []
for p in TARGETS:
    inventory.append({
        "path": str(p.relative_to(ROOT)),
        "exists": p.exists(),
        "bytes": p.stat().st_size if p.exists() else 0,
        "rows": rows(p),
        "columns": header(p),
    })

audit_payloads = {}
for p in AUDITS:
    if p.exists():
        try:
            audit_payloads[str(p.relative_to(ROOT))] = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            audit_payloads[str(p.relative_to(ROOT))] = {"read_error": str(exc)}

recovery = audit_payloads.get(
    "docs/performance-intelligence/restart-v1/timing-warehouse-recovery/final-acceptance/final-acceptance.json", {}
)
expected_large = {
    "timed_rows_after_side_by_side": recovery.get("timed_rows_after_side_by_side"),
    "race_time_delta_rows_recovered": recovery.get("race_time_delta_rows_recovered"),
    "lengths_v_standard_rows_recovered": recovery.get("lengths_v_standard_rows_recovered"),
    "performance_base_rows_recovered": recovery.get("performance_base_rows_recovered"),
}

required_missing = [
    x["path"] for x in inventory
    if x["path"] in {
        "docs/performance-intelligence/warehouse/edgeiq_performance_fact_warehouse_v1.csv",
        "public/data/edgeiq_historical_results_warehouse_v2_graphql.csv",
        "public/data/edgeiq_recovered_timing_warehouse_v1.csv",
        "public/data/edgeiq_performance_intelligence_base_recovered_v1.csv",
    } and not x["exists"]
]

current_rating = next(x for x in inventory if x["path"] == "public/data/edgeiq_performance_rating_base_fact_v1.csv")
current_obs = next(x for x in inventory if x["path"] == "public/data/edgeiq_horse_performance_observation_fact_v1.csv")

status = "BLOCKED_MISSING_HISTORICAL_PHYSICAL_DATA" if required_missing else "READY_FOR_RUNNER_BRIDGE"
payload = {
    "lab": "LAB245A",
    "objective": "Audit GitHub-accessible physical outcome data before building race-T performance bridge",
    "production_modified": False,
    "market_used": False,
    "final_sp_used": False,
    "profitability_testing": False,
    "pseudo_holdout_opened": False,
    "inventory": inventory,
    "recovery_acceptance_counts": expected_large,
    "current_canonical_rating_rows": current_rating["rows"],
    "current_horse_observation_rows": current_obs["rows"],
    "required_missing": required_missing,
    "status": status,
    "next_action": (
        "BRIDGE_MISSING_GOVERNED_HISTORICAL_DATA_TO_GITHUB_ACTIONS"
        if required_missing else
        "BUILD_EXACT_RUNNER_TO_RACE_T_PERFORMANCE_JOIN"
    ),
}
(OUT / "LAB245A_AUDIT.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

print("=" * 112)
print("LAB245A - GITHUB PERFORMANCE OUTCOME BRIDGE AUDIT")
print("=" * 112)
print("MODEL_SELECTION=NO")
print("PROFITABILITY_TESTING=NO")
print("FINAL_SP_USED=NO")
print("MARKET_USED=NO")
print("PSEUDO_HOLDOUT_2025_2026_OPENED=NO")
print("PRODUCTION_MODIFIED=NO")
print()
for x in inventory:
    print(f"{x['path']} | EXISTS={x['exists']} | ROWS={x['rows']} | BYTES={x['bytes']}")
print()
print("RECOVERY_ACCEPTANCE_COUNTS=" + json.dumps(expected_large, sort_keys=True))
print("REQUIRED_MISSING=" + json.dumps(required_missing))
print("STATUS=" + status)
print("NEXT_ACTION=" + payload["next_action"])
print("LAB245A=PASS")
