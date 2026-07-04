import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
import re, math

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

live_path = DATA / "edgeiq_live_runner_board_governed_v1.csv"
hist_path = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
traj_path = DATA / "edgeiq_runner_trajectory_feed_v1.csv"
runner_form_path = DATA / "edgeiq_runner_form_engine_current.csv"
runners_path = DATA / "edgeiq_runners_enrichment_feed_v1_1.csv"

out = DATA / "edgeiq_form_enrichment_feed_v2.csv"
audit_out = DATA / "edgeiq_form_enrichment_feed_v2_audit.csv"
summary_out = DATA / "edgeiq_form_enrichment_feed_v2_summary.csv"
report_out = DATA / "edgeiq_form_enrichment_feed_v2_report.txt"

def clean(v):
    return str(v).strip().upper() if pd.notna(v) else ""

def strip_suffixes(s):
    s = clean(s)
    s = re.sub(r"\s*\((NZ|GB|IRE|USA|FR|JPN|SAF|GER|CAN|ARG|BRZ|CHI|HK|AUS)\)\s*$", "", s)
    s = re.sub(r"\s*\([0-9]+E\)\s*$", "", s)
    return s.strip()

def hkey(v):
    return "".join(ch for ch in strip_suffixes(v) if ch.isalnum())

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

def fmt(v, d=1):
    x = num(v)
    return "" if x is None else round(x, d)

def trend(delta):
    x = num(delta)
    if x is None: return "BACKFILLED"
    if x >= 5: return "IMPROVING_FAST"
    if x >= 2: return "IMPROVING"
    if x <= -5: return "DECLINING_FAST"
    if x <= -2: return "DECLINING"
    return "STABLE"

def signal(avg, latest, peak, starts, fallback=""):
    fb = clean(fallback)
    if fb and fb not in ["", "NO_HISTORY", "NAN"]:
        return fb.replace("_", " ")
    if starts <= 0: return "NO_HISTORY"
    if latest is None: return "LIMITED"
    if peak is not None and latest >= peak - 1: return "PEAKING"
    if avg is not None and latest >= avg + 3: return "IMPROVING"
    if avg is not None and latest <= avg - 5: return "REGRESSING"
    return "HOLDING"

def live_key(row):
    return (clean(row.get("race_date","")), clean(row.get("track","")), clean(row.get("race_no","")), hkey(row.get("horse","")))

live = pd.read_csv(live_path, low_memory=False)

# Primary V6.1 historical source
hist = pd.read_csv(hist_path, low_memory=False)
hist["hk"] = hist["horse"].map(hkey)
hist["rating_num"] = hist["performance_rating_v6_1_research"].map(num)
hist["finish_num"] = hist["finish_position"].map(num)
hist["_sort_date"] = pd.to_datetime(hist["race_date"], errors="coerce")
hist = hist.sort_values("_sort_date", ascending=False)
hist_by_horse = {hk:g.copy() for hk,g in hist[(hist["hk"]!="") & hist["rating_num"].notna()].groupby("hk")}

# Backfill sources
traj = pd.read_csv(traj_path, low_memory=False) if traj_path.exists() else pd.DataFrame()
runner_form = pd.read_csv(runner_form_path, low_memory=False) if runner_form_path.exists() else pd.DataFrame()
runners = pd.read_csv(runners_path, low_memory=False) if runners_path.exists() else pd.DataFrame()

traj_by_key = {live_key(r): r for _,r in traj.iterrows()} if len(traj) else {}
runner_form_by_key = {live_key(r): r for _,r in runner_form.iterrows()} if len(runner_form) and "horse" in runner_form.columns else {}
runners_by_key = {live_key(r): r for _,r in runners.iterrows()} if len(runners) else {}

rows = []
audit = []

for _, r in live.iterrows():
    k = live_key(r)
    hk = hkey(r.get("horse_key","")) or hkey(r.get("horse",""))
    h = hist_by_horse.get(hk, pd.DataFrame(columns=hist.columns)).copy()

    source = "V6_1_RESEARCH_HISTORY"
    truth = "OK_HISTORY" if len(h) else "NO_HISTORY"
    starts = len(h)
    wins = int((h["finish_num"] == 1).sum()) if starts else 0
    places = int((h["finish_num"].fillna(999) <= 3).sum()) if starts else 0

    ratings = list(h.head(5)["rating_num"]) if starts else []
    latest = ratings[0] if ratings else None
    prev = ratings[1] if len(ratings) > 1 else None
    avg5 = sum(ratings)/len(ratings) if ratings else None
    peak = max(ratings) if ratings else None
    delta = latest - prev if latest is not None and prev is not None else None

    t = traj_by_key.get(k)
    rf = runner_form_by_key.get(k)
    rn = runners_by_key.get(k)

    # Backfill when V6.1 history missing but trajectory/form/runners sources have evidence.
    if not starts and t is not None:
        source = "TRAJECTORY_BACKFILL"
        truth = "BACKFILLED_HISTORY"
        starts = int(num(t.get("recent_start_count_v1","")) or 0)
        latest = num(t.get("latest_rating_v1","")) or num(t.get("last_start_1_rating_v1",""))
        prev = num(t.get("last_start_2_rating_v1",""))
        vals = [num(t.get(f"last_start_{i}_rating_v1","")) for i in range(1,6)]
        vals = [v for v in vals if v is not None]
        avg5 = sum(vals)/len(vals) if vals else latest
        peak = max(vals) if vals else latest
        delta = num(t.get("rating_delta_last_start_v1",""))
        if delta is None and latest is not None and prev is not None:
            delta = latest - prev

    if truth == "NO_HISTORY" and rf is not None:
        source = "RUNNER_FORM_BACKFILL"
        truth = "BACKFILLED_HISTORY"
        starts = int(num(rf.get("recent_runs_found","")) or num(rf.get("career_starts","")) or 1)
        latest = num(rf.get("rating_1","")) or num(rf.get("last_start_rating",""))
        prev = num(rf.get("rating_2",""))
        vals = [num(rf.get(f"rating_{i}","")) for i in range(1,6)]
        vals = [v for v in vals if v is not None]
        avg5 = sum(vals)/len(vals) if vals else latest
        peak = max(vals) if vals else latest
        delta = latest - prev if latest is not None and prev is not None else None

    if truth == "NO_HISTORY" and rn is not None:
        source = "RUNNERS_ENRICHMENT_BACKFILL"
        truth = "BACKFILLED_PROFILE_ONLY"
        starts = int(num(rn.get("career_starts","")) or 1)
        latest = num(rn.get("projected_rating","")) or num(rn.get("rating_ladder_score",""))
        avg5 = latest
        peak = latest
        delta = None

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
        "form_trend": trend(delta),
        "form_signal": signal(avg5, latest, peak, starts, t.get("form_signal_v1","") if t is not None else ""),
        "form_truth_status": truth,
        "form_source": source,
    }

    # last 5 from V6.1 if available
    for i in range(1,6):
        prefix = f"last_start_{i}_"
        if len(h) >= i:
            rr = h.iloc[i-1]
            row[prefix+"date"] = rr.get("race_date","")
            row[prefix+"track"] = rr.get("track","")
            row[prefix+"distance"] = rr.get("distance","")
            row[prefix+"class"] = rr.get("race_class_clean","")
            row[prefix+"condition"] = rr.get("condition_recovered","")
            row[prefix+"finish"] = rr.get("finish_position","")
            row[prefix+"margin"] = rr.get("margin","")
            row[prefix+"rating"] = fmt(rr.get("performance_rating_v6_1_research",""))
            row[prefix+"sp"] = ""
        elif t is not None:
            row[prefix+"date"] = t.get(f"last_start_{i}_date_v1","")
            row[prefix+"track"] = ""
            row[prefix+"distance"] = ""
            row[prefix+"class"] = ""
            row[prefix+"condition"] = ""
            row[prefix+"finish"] = t.get(f"last_start_{i}_finish_v1","")
            row[prefix+"margin"] = t.get(f"last_start_{i}_margin_v1","")
            row[prefix+"rating"] = t.get(f"last_start_{i}_rating_v1","")
            row[prefix+"sp"] = t.get(f"last_start_{i}_sp_v1","")
        elif rf is not None:
            row[prefix+"date"] = rf.get(f"last_start_{i}_date","")
            row[prefix+"track"] = rf.get(f"last_start_{i}_track","")
            row[prefix+"distance"] = rf.get(f"last_start_{i}_distance","")
            row[prefix+"class"] = rf.get(f"last_start_{i}_class","")
            row[prefix+"condition"] = rf.get(f"last_start_{i}_condition","")
            row[prefix+"finish"] = rf.get(f"last_start_{i}_finish","")
            row[prefix+"margin"] = rf.get(f"last_start_{i}_margin","")
            row[prefix+"rating"] = rf.get(f"rating_{i}","")
            row[prefix+"sp"] = rf.get(f"last_start_{i}_sp","")
        else:
            for c in ["date","track","distance","class","condition","finish","margin","rating","sp"]:
                row[prefix+c] = ""

    rows.append(row)
    audit.append({
        "race_date": row["race_date"],
        "track": row["track"],
        "race_no": row["race_no"],
        "horse": row["horse"],
        "form_truth_status": truth,
        "form_source": source,
        "last_start_1_present": "YES" if str(row.get("last_start_1_date","")).strip() or str(row.get("last_start_1_rating","")).strip() else "NO",
        "fix_required": "NO" if truth != "NO_HISTORY" else "SOURCE_GAP",
    })

feed = pd.DataFrame(rows)
audit_df = pd.DataFrame(audit)

feed.to_csv(out, index=False)
audit_df.to_csv(audit_out, index=False)

summary = pd.DataFrame([{
    "status": "EDGEIQ_FORM_ENRICHMENT_FEED_V2_BUILT",
    "rows": len(feed),
    "races": feed[["race_date","track","race_no"]].drop_duplicates().shape[0],
    "ok_history": int((feed["form_truth_status"]=="OK_HISTORY").sum()),
    "backfilled_history": int((feed["form_truth_status"]=="BACKFILLED_HISTORY").sum()),
    "backfilled_profile_only": int((feed["form_truth_status"]=="BACKFILLED_PROFILE_ONLY").sum()),
    "no_history": int((feed["form_truth_status"]=="NO_HISTORY").sum()),
    "last_start_1_populated": int(((feed["last_start_1_date"].astype(str).str.strip()!="") | (feed["last_start_1_rating"].astype(str).str.strip()!="")).sum()),
    "fix_required": int((audit_df["fix_required"]!="NO").sum()),
    "pricing_maths_changed": "NO",
    "v6_1_changed": "NO",
    "v7_2g2_changed": "NO",
}])
summary.to_csv(summary_out, index=False)

with open(report_out, "w", encoding="utf-8") as f:
    f.write("[EDGEIQ_FORM_ENRICHMENT_FEED_V2]\n")
    f.write(f"built_at={datetime.now(timezone.utc).isoformat()}\n\n")
    f.write(summary.to_string(index=False))

print("[EDGEIQ_FORM_ENRICHMENT_FEED_V2] COMPLETE")
print(summary.to_string(index=False))
print(out)
