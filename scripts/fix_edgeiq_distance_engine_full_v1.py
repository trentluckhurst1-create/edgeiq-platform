import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

hist_path = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
live_path = DATA / "edgeiq_live_runner_board_governed_v1.csv"
dna_path = DATA / "edgeiq_runner_dna_drawer_feed_v2.csv"
runners_path = DATA / "edgeiq_runners_enrichment_feed_v1_1.csv"
command_path = DATA / "edgeiq_command_enrichment_feed_v3.csv"

audit_path = DATA / "edgeiq_distance_false_no_profile_v1.csv"
summary_path = DATA / "edgeiq_distance_false_no_profile_summary_v1.csv"
report_path = DATA / "edgeiq_distance_false_no_profile_report.txt"

def clean(v):
    return str(v).strip().upper() if pd.notna(v) else ""

def horse_key(v):
    return "".join(ch for ch in clean(v) if ch.isalnum())

def n(v):
    if pd.isna(v):
        return None
    try:
        s = str(v).strip().replace(",", "")
        if not s or s.lower() == "nan":
            return None
        x = float(s)
        if pd.isna(x):
            return None
        return x
    except Exception:
        return None

def bucket(v):
    x = n(v)
    return "" if x is None else str(int(round(x / 100.0) * 100))

def band(score, starts):
    if starts <= 0: return "NO_PROFILE"
    if starts == 1: return "LOW_SAMPLE"
    if score >= 80: return "ELITE"
    if score >= 65: return "STRONG"
    if score >= 50: return "POSITIVE"
    if score >= 40: return "NEUTRAL"
    return "NEGATIVE"

hist = pd.read_csv(hist_path, low_memory=False)
live = pd.read_csv(live_path, low_memory=False)

hist["hk"] = hist["horse"].map(horse_key)
hist["db"] = hist["distance"].map(bucket)
hist["rating_num"] = hist["performance_rating_v6_1_research"].map(n)
hist["finish_num"] = hist["finish_position"].map(n)

usable = hist[(hist["hk"] != "") & (hist["db"] != "") & hist["rating_num"].notna()].copy()

profile = {}
for (hk, db), g in usable.groupby(["hk", "db"]):
    starts = len(g)
    wins = int((g["finish_num"] == 1).sum())
    places = int((g["finish_num"].fillna(999) <= 3).sum())
    avg_rating = float(g["rating_num"].mean())
    best_rating = float(g["rating_num"].max())
    score = avg_rating * 0.55 + best_rating * 0.20 + min(15, starts * 3) + (wins / starts) * 12 + (places / starts) * 8
    score = max(0, min(100, score))
    profile[(hk, db)] = {
        "starts": starts,
        "wins": wins,
        "places": places,
        "avg_rating": round(avg_rating, 2),
        "best_rating": round(best_rating, 2),
        "score": round(score, 1),
        "band": band(score, starts),
    }

live_fix = {}
audit = []

for _, r in live.iterrows():
    hk = horse_key(r.get("horse_key", "")) or horse_key(r.get("horse", ""))
    db = bucket(r.get("distance", ""))
    p = profile.get((hk, db))
    status = "TRUE_NO_PROFILE"
    if p:
        status = "OK_PROFILE_FOUND"
        live_fix[(clean(r.get("race_date","")), clean(r.get("track","")), clean(r.get("race_no","")), horse_key(r.get("horse","")))] = p
    audit.append({
        "race_date": r.get("race_date",""),
        "track": r.get("track",""),
        "race_no": r.get("race_no",""),
        "horse": r.get("horse",""),
        "distance": r.get("distance",""),
        "distance_bucket": db,
        "status": status,
        "starts": p["starts"] if p else 0,
        "wins": p["wins"] if p else 0,
        "avg_rating": p["avg_rating"] if p else "",
        "score": p["score"] if p else "",
        "band": p["band"] if p else "NO_PROFILE",
    })

audit_df = pd.DataFrame(audit)
audit_df.to_csv(audit_path, index=False)

updates = []

def apply(path, score_cols, band_cols, truth_cols):
    df = pd.read_csv(path, low_memory=False)
    backup = path.with_name(path.stem + "_BACKUP_BEFORE_DISTANCE_FULL_FIX_20260628" + path.suffix)
    df.to_csv(backup, index=False)

    fixed = 0
    for idx, row in df.iterrows():
        k = (clean(row.get("race_date","")), clean(row.get("track","")), clean(row.get("race_no","")), horse_key(row.get("horse","")))
        p = live_fix.get(k)
        if not p:
            continue

        current_scores = [n(row.get(c, "")) for c in score_cols if c in df.columns]
        current_bands = [clean(row.get(c, "")) for c in band_cols if c in df.columns]

        needs_fix = (
            not current_scores
            or any(v is None or v == 0 for v in current_scores)
            or any(v in ["", "NO_PROFILE"] for v in current_bands)
        )

        if needs_fix:
            for c in score_cols:
                if c in df.columns:
                    df.at[idx, c] = p["score"]
            for c in band_cols:
                if c in df.columns:
                    df.at[idx, c] = p["band"]
            for c in truth_cols:
                if c in df.columns:
                    df.at[idx, c] = "OK_REBUILT_FROM_V6_1_HISTORY_FULL_FIX"
            fixed += 1

    df.to_csv(path, index=False)
    updates.append({"file": path.name, "fixed": fixed, "backup": str(backup)})

apply(dna_path, ["distance_fit_score"], ["distance_fit_band"], [])
apply(runners_path, ["score_distance"], ["distance_profile"], ["distance_profile_truth_status"])
apply(command_path, ["edgeiq_score_distance_v3"], ["edgeiq_score_distance_band_v3"], [])

summary = pd.DataFrame([{
    "status": "EDGEIQ_DISTANCE_ENGINE_FULL_FIX_COMPLETE",
    "live_rows": len(live),
    "profiles_found": int((audit_df["status"] == "OK_PROFILE_FOUND").sum()),
    "true_no_profile": int((audit_df["status"] == "TRUE_NO_PROFILE").sum()),
    "files_updated": len(updates),
    "total_fixed_rows": sum(u["fixed"] for u in updates),
    "pricing_maths_changed": "NO",
    "v6_1_changed": "NO",
    "v7_2g2_changed": "NO",
}])
summary.to_csv(summary_path, index=False)

with open(report_path, "w", encoding="utf-8") as f:
    f.write("[EDGEIQ_DISTANCE_ENGINE_FULL_FIX]\n")
    f.write(f"built_at={datetime.now(timezone.utc).isoformat()}\n")
    f.write(summary.to_string(index=False))
    f.write("\n\nUPDATES\n")
    f.write(pd.DataFrame(updates).to_string(index=False))

print("[EDGEIQ_DISTANCE_ENGINE_FULL_FIX] COMPLETE")
print(summary.to_string(index=False))
print(pd.DataFrame(updates).to_string(index=False))
print(report_path)

