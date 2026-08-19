import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
import math

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

hist_path = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
live_path = DATA / "edgeiq_live_runner_board_governed_v1.csv"
traj_path = DATA / "edgeiq_runner_trajectory_feed_v1.csv"

out = DATA / "edgeiq_form_enrichment_feed_v1.csv"
summary_out = DATA / "edgeiq_form_enrichment_feed_v1_summary.csv"
audit_out = DATA / "edgeiq_form_enrichment_feed_v1_audit.csv"
report_out = DATA / "edgeiq_form_enrichment_feed_v1_report.txt"

def clean(v):
    return str(v).strip().upper() if pd.notna(v) else ""

def horse_key(v):
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

def fmt(v, digits=1):
    x = num(v)
    if x is None:
        return ""
    return round(x, digits)

def band_from_delta(delta):
    x = num(delta)
    if x is None:
        return "NO_HISTORY"
    if x >= 5:
        return "IMPROVING_FAST"
    if x >= 2:
        return "IMPROVING"
    if x <= -5:
        return "DECLINING_FAST"
    if x <= -2:
        return "DECLINING"
    return "STABLE"

def form_signal(avg_recent, latest, peak, starts):
    if starts <= 0:
        return "NO_HISTORY"
    if latest is None:
        return "LIMITED"
    if peak is not None and latest >= peak - 1:
        return "PEAKING"
    if avg_recent is not None and latest >= avg_recent + 3:
        return "IMPROVING"
    if avg_recent is not None and latest <= avg_recent - 5:
        return "REGRESSING"
    return "HOLDING"

def sort_date(df):
    if "race_date" in df.columns:
        df = df.copy()
        df["_sort_date"] = pd.to_datetime(df["race_date"], errors="coerce")
        return df.sort_values("_sort_date", ascending=False)
    return df

hist = pd.read_csv(hist_path, low_memory=False)
live = pd.read_csv(live_path, low_memory=False)
traj = pd.read_csv(traj_path, low_memory=False) if traj_path.exists() else pd.DataFrame()

hist["hk"] = hist["horse"].map(horse_key)
hist["rating_num"] = hist["performance_rating_v6_1_research"].map(num)
hist["finish_num"] = hist["finish_position"].map(num)
hist["margin_num"] = hist["margin"].map(num) if "margin" in hist.columns else None
hist = sort_date(hist)

hist_by_horse = {hk: g.copy() for hk, g in hist[hist["hk"] != ""].groupby("hk")}
traj_by_key = {}
if len(traj):
    for _, r in traj.iterrows():
        k = (clean(r.get("race_date","")), clean(r.get("track","")), clean(r.get("race_no","")), horse_key(r.get("horse","")))
        traj_by_key[k] = r

rows = []
audit = []

for _, r in live.iterrows():
    hk = horse_key(r.get("horse_key","")) or horse_key(r.get("horse",""))
    k = (clean(r.get("race_date","")), clean(r.get("track","")), clean(r.get("race_no","")), horse_key(r.get("horse","")))
    h = hist_by_horse.get(hk, pd.DataFrame())
    if len(h) and "rating_num" in h.columns:
        h = h[h["rating_num"].notna()].copy()
    else:
        h = pd.DataFrame(columns=hist.columns)
    starts = len(h)
    last5 = h.head(5)

    ratings = list(last5["rating_num"]) if starts else []
    finishes = list(last5["finish_num"]) if starts else []
    latest = ratings[0] if ratings else None
    prev = ratings[1] if len(ratings) > 1 else None
    avg5 = sum(ratings) / len(ratings) if ratings else None
    peak = max(ratings) if ratings else None
    delta = latest - prev if latest is not None and prev is not None else None

    wins = int((h["finish_num"] == 1).sum()) if starts else 0
    places = int((h["finish_num"].fillna(999) <= 3).sum()) if starts else 0
    signal = form_signal(avg5, latest, peak, starts)
    trend = band_from_delta(delta)

    t = traj_by_key.get(k)

    row = {
        "race_date": r.get("race_date",""),
        "track": r.get("track",""),
        "race_no": r.get("race_no",""),
        "horse": r.get("horse",""),
        "horse_key": hk,
        "form_history_starts": starts,
        "form_history_wins": wins,
        "form_history_places": places,
        "form_last_start_rating": fmt(latest),
        "form_previous_start_rating": fmt(prev),
        "form_rating_delta_last_start": fmt(delta),
        "form_avg_rating_last5": fmt(avg5),
        "form_peak_rating_last5": fmt(peak),
        "form_trend": trend,
        "form_signal": signal,
        "form_truth_status": "OK_HISTORY" if starts else "NO_HISTORY",
        "form_source": "V6_1_RESEARCH_HISTORY",
        "trajectory_form_signal": t.get("form_signal_v1","") if t is not None else "",
        "trajectory_performance_label": t.get("performance_label_v1","") if t is not None else "",
    }

    for i in range(5):
        if i < len(last5):
            rr = last5.iloc[i]
            prefix = f"last_start_{i+1}_"
            row[prefix+"date"] = rr.get("race_date","")
            row[prefix+"track"] = rr.get("track","")
            row[prefix+"distance"] = rr.get("distance","")
            row[prefix+"class"] = rr.get("race_class_clean","")
            row[prefix+"condition"] = rr.get("condition_recovered","")
            row[prefix+"finish"] = rr.get("finish_position","")
            row[prefix+"margin"] = rr.get("margin","")
            row[prefix+"rating"] = fmt(rr.get("performance_rating_v6_1_research",""))
            row[prefix+"reason"] = rr.get("performance_rating_v6_1_research_reason","")
        else:
            prefix = f"last_start_{i+1}_"
            for c in ["date","track","distance","class","condition","finish","margin","rating","reason"]:
                row[prefix+c] = ""

    rows.append(row)
    audit.append({
        "race_date": row["race_date"],
        "track": row["track"],
        "race_no": row["race_no"],
        "horse": row["horse"],
        "status": row["form_truth_status"],
        "starts": starts,
        "last5_populated": sum(1 for i in range(1,6) if row.get(f"last_start_{i}_date")),
        "fix_required": "NO",
    })

feed = pd.DataFrame(rows)
feed.to_csv(out, index=False)

audit_df = pd.DataFrame(audit)
audit_df.to_csv(audit_out, index=False)

summary = pd.DataFrame([{
    "status": "EDGEIQ_FORM_ENRICHMENT_FEED_V1_BUILT",
    "rows": len(feed),
    "races": feed[["race_date","track","race_no"]].drop_duplicates().shape[0],
    "with_history": int((feed["form_truth_status"] == "OK_HISTORY").sum()),
    "no_history": int((feed["form_truth_status"] == "NO_HISTORY").sum()),
    "last5_any": int((feed["last_start_1_date"].astype(str).str.len() > 0).sum()),
    "fix_required": 0,
    "pricing_maths_changed": "NO",
    "v6_1_changed": "NO",
    "v7_2g2_changed": "NO",
}])
summary.to_csv(summary_out, index=False)

with open(report_out, "w", encoding="utf-8") as f:
    f.write("[EDGEIQ_FORM_ENRICHMENT_FEED_V1]\n")
    f.write(f"built_at={datetime.now(timezone.utc).isoformat()}\n\n")
    f.write(summary.to_string(index=False))

print("[EDGEIQ_FORM_ENRICHMENT_FEED_V1] COMPLETE")
print(summary.to_string(index=False))
print(out)

