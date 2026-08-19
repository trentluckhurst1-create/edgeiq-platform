import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
import difflib
import math

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

form_path = DATA / "edgeiq_form_enrichment_feed_v1.csv"
hist_path = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
live_path = DATA / "edgeiq_live_runner_board_governed_v1.csv"

out = DATA / "edgeiq_form_no_history_trace_v1.csv"
summary_out = DATA / "edgeiq_form_no_history_trace_v1_summary.csv"
report_out = DATA / "edgeiq_form_no_history_trace_v1_report.txt"

def clean(v):
    return str(v).strip().upper() if pd.notna(v) else ""

def key(v):
    return "".join(ch for ch in clean(v) if ch.isalnum())

def num(v):
    if pd.isna(v):
        return None
    try:
        s = str(v).strip().replace(",", "")
        if not s or s.lower() == "nan":
            return None
        x = float(s)
        if math.isnan(x):
            return None
        return x
    except Exception:
        return None

form = pd.read_csv(form_path, low_memory=False)
hist = pd.read_csv(hist_path, low_memory=False)
live = pd.read_csv(live_path, low_memory=False)

hist["hist_key"] = hist["horse"].map(key)
hist["rating_num"] = hist["performance_rating_v6_1_research"].map(num)

hist_names = sorted(set(clean(x) for x in hist["horse"].dropna()))
hist_keys = set(hist["hist_key"])

hist_by_key_count = hist.groupby("hist_key").size().to_dict()
hist_by_key_rated_count = hist[hist["rating_num"].notna()].groupby("hist_key").size().to_dict()

no_hist = form[form["form_truth_status"].astype(str).str.upper().eq("NO_HISTORY")].copy()

rows = []

for _, r in no_hist.iterrows():
    hname = clean(r.get("horse", ""))
    hk = key(r.get("horse_key", "")) or key(hname)

    exact_key_rows = hist_by_key_count.get(hk, 0)
    exact_key_rated_rows = hist_by_key_rated_count.get(hk, 0)

    close = difflib.get_close_matches(hname, hist_names, n=5, cutoff=0.82)
    close_rows = []
    for c in close:
        ck = key(c)
        close_rows.append(f"{c}:{hist_by_key_count.get(ck,0)}")

    if exact_key_rated_rows > 0:
        status = "HISTORY_EXISTS_HORSE_KEY_FAILURE"
    elif exact_key_rows > 0 and exact_key_rated_rows == 0:
        status = "HISTORY_EXISTS_NO_RATING"
    elif close_rows:
        status = "HISTORY_EXISTS_NAME_VARIATION_POSSIBLE"
    else:
        status = "TRUE_NO_HISTORY_OR_WAREHOUSE_GAP"

    rows.append({
        "race_date": r.get("race_date", ""),
        "track": r.get("track", ""),
        "race_no": r.get("race_no", ""),
        "horse": r.get("horse", ""),
        "horse_key": hk,
        "classification": status,
        "exact_key_rows": exact_key_rows,
        "exact_key_rated_rows": exact_key_rated_rows,
        "close_history_matches": " | ".join(close_rows),
    })

trace = pd.DataFrame(rows)
trace.to_csv(out, index=False)

summary = (
    trace.groupby("classification")
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)

total = pd.DataFrame([{
    "classification": "TOTAL_NO_HISTORY_REVIEWED",
    "count": len(trace)
}])

summary = pd.concat([total, summary], ignore_index=True)
summary.to_csv(summary_out, index=False)

with open(report_out, "w", encoding="utf-8") as f:
    f.write("[EDGEIQ_FORM_NO_HISTORY_TRACE_V1]\n")
    f.write(f"built_at={datetime.now(timezone.utc).isoformat()}\n")
    f.write(f"no_history_reviewed={len(trace)}\n\n")
    f.write(summary.to_string(index=False))
    f.write("\n\npricing_maths_changed=NO\nv6_1_changed=NO\nv7_2g2_changed=NO\n")

print("[EDGEIQ_FORM_NO_HISTORY_TRACE_V1] COMPLETE")
print(summary.to_string(index=False))
print(out)
print(report_out)
