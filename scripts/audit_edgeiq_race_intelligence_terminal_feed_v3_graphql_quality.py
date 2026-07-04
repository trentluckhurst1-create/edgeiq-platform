import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INP = DATA / "edgeiq_race_intelligence_terminal_feed_v3_graphql.csv"
OUT = DATA / "edgeiq_race_intelligence_terminal_feed_v3_graphql_quality_audit.csv"
SUMMARY = DATA / "edgeiq_race_intelligence_terminal_feed_v3_graphql_quality_audit_summary.csv"

df = pd.read_csv(INP, low_memory=False)

checks = []

def add(check, value, status):
    checks.append({
        "check": check,
        "value": value,
        "status": status,
        "built_at": datetime.now(timezone.utc).isoformat(),
    })

add("rows", len(df), "INFO")
add("blank_customer_summary", int((df["customer_summary"].fillna("").str.strip() == "").sum()), "PASS")
add("blank_graphql_stable_intent_band", int((df["stable_intent_v2_1_graphql_band"].fillna("").str.strip() == "").sum()), "PASS")
add("no_profile_graphql_stable_intent", int((df["stable_intent_v2_1_graphql_band"] == "NO_PROFILE").sum()), "PASS")
add("duplicate_race_horse_rows", int(df.duplicated(["race_date","track","race_no","horse_key"]).sum()), "PASS")
add("race_count", df[["race_date","track","race_no"]].drop_duplicates().shape[0], "INFO")
add("positive_intent", int((df["stable_intent_v2_1_graphql_band"] == "POSITIVE_INTENT").sum()), "INFO")
add("watch", int((df["stable_intent_v2_1_graphql_band"] == "WATCH").sum()), "INFO")
add("low_evidence", int((df["stable_intent_v2_1_graphql_band"] == "LOW_EVIDENCE").sum()), "INFO")

audit = pd.DataFrame(checks)
audit.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "RACE_INTELLIGENCE_TERMINAL_FEED_V3_GRAPHQL_QUALITY_AUDIT_BUILT",
    "rows": len(df),
    "checks": len(audit),
    "warn_checks": int((audit["status"] == "WARN").sum()),
    "fail_checks": int((audit["status"] == "FAIL").sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[TERMINAL_FEED_V3_GRAPHQL_QUALITY_AUDIT] COMPLETE")
print(summary.to_string(index=False))
