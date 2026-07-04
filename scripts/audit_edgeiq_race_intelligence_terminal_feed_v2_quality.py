import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INP = DATA / "edgeiq_race_intelligence_terminal_feed_v2.csv"
OUT = DATA / "edgeiq_race_intelligence_terminal_feed_v2_quality_audit.csv"
SUMMARY = DATA / "edgeiq_race_intelligence_terminal_feed_v2_quality_audit_summary.csv"

df = pd.read_csv(INP, low_memory=False)

checks = []

def add_check(name, value, status):
    checks.append({
        "check": name,
        "value": value,
        "status": status,
        "built_at": datetime.now(timezone.utc).isoformat(),
    })

add_check("rows", len(df), "INFO")
add_check("blank_customer_summary", int((df["customer_summary"].fillna("").str.strip() == "").sum()), "PASS")
add_check("blank_stable_intent_band", int((df["stable_intent_v1_1_band"].fillna("").str.strip() == "").sum()), "PASS")
add_check("no_profile_stable_intent", int((df["stable_intent_v1_1_band"] == "NO_PROFILE").sum()), "WARN")
add_check("low_evidence_as_watch", int(((df["stable_intent_v1_1_band"] == "WATCH") & (df["stable_intent_v1_1_reason"] == "Low evidence stable-intent profile.")).sum()), "WARN")
add_check("duplicate_race_horse_rows", int(df.duplicated(["race_date","track","race_no","horse_key"]).sum()), "PASS")
add_check("race_count", df[["race_date","track","race_no"]].drop_duplicates().shape[0], "INFO")

band_counts = df.groupby("stable_intent_v1_1_band").size().reset_index(name="count")
for _, r in band_counts.iterrows():
    add_check(f"band_count_{r['stable_intent_v1_1_band']}", int(r["count"]), "INFO")

audit = pd.DataFrame(checks)
audit.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "RACE_INTELLIGENCE_TERMINAL_FEED_V2_QUALITY_AUDIT_BUILT",
    "rows": len(df),
    "checks": len(audit),
    "warn_checks": int((audit["status"] == "WARN").sum()),
    "fail_checks": int((audit["status"] == "FAIL").sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[RACE_INTELLIGENCE_TERMINAL_FEED_V2_QUALITY_AUDIT] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
