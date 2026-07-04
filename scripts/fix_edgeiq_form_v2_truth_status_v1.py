import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

path = DATA / "edgeiq_form_enrichment_feed_v2.csv"
backup = DATA / "edgeiq_form_enrichment_feed_v2_BACKUP_BEFORE_TRUTH_STATUS_FIX_20260628.csv"
audit_out = DATA / "edgeiq_form_v2_truth_status_fix_audit.csv"
summary_out = DATA / "edgeiq_form_v2_truth_status_fix_summary.csv"
report_out = DATA / "edgeiq_form_v2_truth_status_fix_report.txt"

df = pd.read_csv(path, low_memory=False)
df.to_csv(backup, index=False)

audit = []
fixed = 0

for idx, r in df.iterrows():
    truth = str(r.get("form_truth_status", "")).strip().upper()
    source = str(r.get("form_source", "")).strip().upper()
    has_detail = any(str(r.get(c, "")).strip() for c in [
        "last_start_1_date",
        "last_start_1_rating",
        "last_start_1_finish",
        "last_start_1_track",
    ])
    starts = pd.to_numeric(pd.Series([r.get("form_history_starts", "")]), errors="coerce").iloc[0]
    starts = 0 if pd.isna(starts) else starts

    new_truth = truth
    if truth == "BACKFILLED_HISTORY" and not has_detail and starts <= 0:
        new_truth = "BACKFILLED_CONTEXT_ONLY"
        df.at[idx, "form_truth_status"] = new_truth
        fixed += 1

    audit.append({
        "race_date": r.get("race_date",""),
        "track": r.get("track",""),
        "race_no": r.get("race_no",""),
        "horse": r.get("horse",""),
        "before_truth": truth,
        "after_truth": new_truth,
        "form_source": source,
        "has_last_start_detail": "YES" if has_detail else "NO",
        "form_history_starts": starts,
        "fixed": "YES" if new_truth != truth else "NO",
    })

df.to_csv(path, index=False)
audit_df = pd.DataFrame(audit)
audit_df.to_csv(audit_out, index=False)

summary = pd.DataFrame([{
    "status": "EDGEIQ_FORM_V2_TRUTH_STATUS_FIXED",
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
    f.write("[EDGEIQ_FORM_V2_TRUTH_STATUS_FIX]\n")
    f.write(f"built_at={datetime.now(timezone.utc).isoformat()}\n\n")
    f.write(summary.to_string(index=False))
    f.write(f"\n\nbackup={backup}\n")

print("[EDGEIQ_FORM_V2_TRUTH_STATUS_FIX] COMPLETE")
print(summary.to_string(index=False))
