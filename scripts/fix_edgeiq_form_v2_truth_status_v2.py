import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

path = DATA / "edgeiq_form_enrichment_feed_v2.csv"
backup = DATA / "edgeiq_form_enrichment_feed_v2_BACKUP_BEFORE_TRUTH_STATUS_FIX_V2_20260628.csv"
summary_out = DATA / "edgeiq_form_v2_truth_status_fix_v2_summary.csv"
report_out = DATA / "edgeiq_form_v2_truth_status_fix_v2_report.txt"

def useful(v):
    if pd.isna(v):
        return False
    s = str(v).strip()
    return bool(s) and s.upper() not in ["NAN", "NONE", "NULL", "--", ""]

def to_num(v):
    if pd.isna(v):
        return 0
    try:
        s = str(v).strip()
        if not s or s.upper() == "NAN":
            return 0
        return float(s)
    except Exception:
        return 0

df = pd.read_csv(path, low_memory=False)
df.to_csv(backup, index=False)

fixed = 0

for idx, r in df.iterrows():
    truth = str(r.get("form_truth_status", "")).strip().upper()
    has_detail = any(useful(r.get(c, "")) for c in [
        "last_start_1_date",
        "last_start_1_rating",
        "last_start_1_finish",
        "last_start_1_track",
    ])
    starts = to_num(r.get("form_history_starts", ""))

    if truth == "BACKFILLED_HISTORY" and not has_detail and starts <= 0:
        df.at[idx, "form_truth_status"] = "BACKFILLED_CONTEXT_ONLY"
        df.at[idx, "form_source"] = "TRAJECTORY_CONTEXT_ONLY"
        fixed += 1

df.to_csv(path, index=False)

summary = pd.DataFrame([{
    "status": "EDGEIQ_FORM_V2_TRUTH_STATUS_FIXED_V2",
    "rows": len(df),
    "ok_history": int((df["form_truth_status"] == "OK_HISTORY").sum()),
    "backfilled_history": int((df["form_truth_status"] == "BACKFILLED_HISTORY").sum()),
    "backfilled_context_only": int((df["form_truth_status"] == "BACKFILLED_CONTEXT_ONLY").sum()),
    "no_history": int((df["form_truth_status"] == "NO_HISTORY").sum()),
    "fixed_rows": fixed,
    "pricing_maths_changed": "NO",
    "v6_1_changed": "NO",
    "v7_2g2_changed": "NO",
}])
summary.to_csv(summary_out, index=False)

with open(report_out, "w", encoding="utf-8") as f:
    f.write("[EDGEIQ_FORM_V2_TRUTH_STATUS_FIX_V2]\n")
    f.write(f"built_at={datetime.now(timezone.utc).isoformat()}\n\n")
    f.write(summary.to_string(index=False))
    f.write(f"\n\nbackup={backup}\n")

print("[EDGEIQ_FORM_V2_TRUTH_STATUS_FIX_V2] COMPLETE")
print(summary.to_string(index=False))
