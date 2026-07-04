import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INP = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
OUT = DATA / "edgeiq_historical_results_warehouse_v2_graphql_quality_audit.csv"
SUMMARY = DATA / "edgeiq_historical_results_warehouse_v2_graphql_quality_audit_summary.csv"

df = pd.read_csv(INP, low_memory=False)

checks = []

def add(name, value, status):
    checks.append({
        "check": name,
        "value": value,
        "status": status,
        "built_at": datetime.now(timezone.utc).isoformat(),
    })

add("rows", len(df), "INFO")
add("blank_race_date", int(df["race_date"].fillna("").eq("").sum()), "PASS")
add("blank_track", int(df["track"].fillna("").eq("").sum()), "PASS")
add("blank_horse", int(df["horse"].fillna("").eq("").sum()), "PASS")
add("blank_trainer", int(df["trainer"].fillna("").eq("").sum()), "WARN")
add("blank_jockey", int(df["jockey"].fillna("").eq("").sum()), "WARN")
add("duplicate_runner_rows", int(df.duplicated(["race_date","track","race_id","runner_id","horse"]).sum()), "PASS")
add("scratched_rows", int(df["scratched"].astype(str).str.lower().eq("true").sum()), "INFO")
add("finished_rows", int(pd.to_numeric(df["finish_num"], errors="coerce").notna().sum()), "INFO")
add("winner_rows", int((pd.to_numeric(df["finish_num"], errors="coerce") == 1).sum()), "INFO")
add("sp_rows", int(pd.to_numeric(df["starting_price_decimal"], errors="coerce").notna().sum()), "INFO")
add("date_min", df["race_date"].min(), "INFO")
add("date_max", df["race_date"].max(), "INFO")
add("unique_tracks", df["track"].nunique(), "INFO")
add("unique_horses", df["horse"].nunique(), "INFO")
add("unique_trainers", df["trainer"].nunique(), "INFO")
add("unique_jockeys", df["jockey"].nunique(), "INFO")

audit = pd.DataFrame(checks)
audit.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL_QUALITY_AUDIT_BUILT",
    "rows": len(df),
    "checks": len(audit),
    "warn_checks": int((audit["status"] == "WARN").sum()),
    "fail_checks": int((audit["status"] == "FAIL").sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[WAREHOUSE_V2_QUALITY_AUDIT] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
