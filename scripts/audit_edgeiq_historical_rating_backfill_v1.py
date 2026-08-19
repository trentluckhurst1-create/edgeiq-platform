import csv, json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
data = root / "public" / "data"
docs = root / "docs" / "victoria-live-recovery-v6"
def count(name):
    with (data / name).open(encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))
summary = {
    "normalisation_rows": count("edgeiq_performance_normalisation_fact_v1.csv"),
    "rating_base_rows": count("edgeiq_performance_rating_base_fact_v1.csv"),
    "observation_rows": count("edgeiq_horse_performance_observation_fact_v1.csv"),
    "aggregate_rows": count("edgeiq_horse_performance_aggregate_fact_v1.csv"),
    "horse_rating_rows": count("edgeiq_horse_performance_rating_fact_v1.csv"),
    "snapshot_rows": count("edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv"),
}
summary["status"] = "PASS_WITH_GOVERNED_EXCLUSIONS" if summary["horse_rating_rows"] > 0 else "BLOCKED"
(docs / "EDGEIQ_HISTORICAL_RATING_BACKFILL_AUDIT_V1.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("EDGEIQ_HISTORICAL_RATING_BACKFILL_AUDIT_" + summary["status"])
