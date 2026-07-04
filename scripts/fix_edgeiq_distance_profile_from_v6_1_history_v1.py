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

out_profile = DATA / "edgeiq_distance_profile_rebuilt_from_v6_1_v1.csv"
out_live = DATA / "edgeiq_live_distance_profile_fix_v1.csv"
audit_path = DATA / "edgeiq_distance_profile_fix_v1_audit.csv"
report_path = DATA / "edgeiq_distance_profile_fix_v1_report.txt"

for p in [hist_path, live_path]:
    if not p.exists():
        raise FileNotFoundError(p)

hist = pd.read_csv(hist_path, low_memory=False)
live = pd.read_csv(live_path, low_memory=False)

def clean(v):
    return str(v).strip().upper() if pd.notna(v) else ""

def horse_key(v):
    return "".join(ch for ch in clean(v) if ch.isalnum())

def to_num(v):
    if pd.isna(v):
        return None
    try:
        s = str(v).strip().replace(",", "")
        if not s:
            return None
        return float(s)
    except Exception:
        return None

def dist_bucket(d):
    n = to_num(d)
    if n is None:
        return ""
    return str(int(round(n / 100.0) * 100))

def band(score, starts):
    if starts <= 0:
        return "NO_PROFILE"
    if starts == 1:
        return "LOW_SAMPLE"
    if score >= 80:
        return "ELITE"
    if score >= 65:
        return "STRONG"
    if score >= 50:
        return "POSITIVE"
    if score >= 40:
        return "NEUTRAL"
    return "NEGATIVE"

hist["horse_norm"] = hist["horse"].map(horse_key)
hist["distance_bucket"] = hist["distance"].map(dist_bucket)
hist["rating_num"] = hist["performance_rating_v6_1_research"].map(to_num)
hist["finish_num"] = hist["finish_position"].map(to_num)

usable = hist[
    (hist["horse_norm"] != "") &
    (hist["distance_bucket"] != "") &
    (hist["rating_num"].notna())
].copy()

profile_rows = []
for (hk, db), g in usable.groupby(["horse_norm", "distance_bucket"], dropna=False):
    starts = len(g)
    wins = int((g["finish_num"] == 1).sum())
    places = int((g["finish_num"].fillna(999) <= 3).sum())
    avg_rating = float(g["rating_num"].mean())
    best_rating = float(g["rating_num"].max())
    win_rate = wins / starts if starts else 0
    place_rate = places / starts if starts else 0

    # Rating-led with proven-distance lift. Kept display/profile only.
    score = (
        avg_rating * 0.55 +
        best_rating * 0.20 +
        min(15, starts * 3) +
        win_rate * 12 +
        place_rate * 8
    )
    score = max(0, min(100, score))

    profile_rows.append({
        "horse_key": hk,
        "distance_bucket": db,
        "distance_profile_starts": starts,
        "distance_profile_wins": wins,
        "distance_profile_places": places,
        "distance_profile_avg_rating": round(avg_rating, 2),
        "distance_profile_best_rating": round(best_rating, 2),
        "distance_fit_score_rebuilt": round(score, 1),
        "distance_fit_band_rebuilt": band(score, starts),
        "distance_profile_source": "V6_1_RESEARCH_HISTORY_REBUILD_V1",
    })

profiles = pd.DataFrame(profile_rows)
profiles.to_csv(out_profile, index=False)

profile_map = {
    (r["horse_key"], str(r["distance_bucket"])): r
    for _, r in profiles.iterrows()
}

live_rows = []
for _, r in live.iterrows():
    hk = horse_key(r.get("horse_key", "")) or horse_key(r.get("horse", ""))
    db = dist_bucket(r.get("distance", ""))
    prof = profile_map.get((hk, db))

    if prof is None:
        status = "NO_MATCH"
        live_rows.append({
            "race_date": r.get("race_date", ""),
            "track": r.get("track", ""),
            "race_no": r.get("race_no", ""),
            "horse": r.get("horse", ""),
            "horse_key": hk,
            "distance": r.get("distance", ""),
            "distance_bucket": db,
            "distance_fit_score_rebuilt": "",
            "distance_fit_band_rebuilt": "NO_PROFILE",
            "distance_profile_truth_status_rebuilt": status,
            "distance_profile_source": "",
        })
    else:
        row = prof.to_dict()
        row.update({
            "race_date": r.get("race_date", ""),
            "track": r.get("track", ""),
            "race_no": r.get("race_no", ""),
            "horse": r.get("horse", ""),
            "horse_key": hk,
            "distance": r.get("distance", ""),
            "distance_profile_truth_status_rebuilt": "OK_REBUILT",
        })
        live_rows.append(row)

live_fix = pd.DataFrame(live_rows)
live_fix.to_csv(out_live, index=False)

audit_rows = []

def apply_to_file(path, score_col, band_col, truth_col):
    if not path.exists():
        audit_rows.append({"file": path.name, "status": "MISSING"})
        return
    df = pd.read_csv(path, low_memory=False)
    backup = path.with_name(path.stem + "_BACKUP_BEFORE_DISTANCE_PROFILE_FIX_20260628" + path.suffix)
    df.to_csv(backup, index=False)

    fix_by_key = {
        (clean(r["race_date"]), clean(r["track"]), clean(r["race_no"]), horse_key(r["horse"])): r
        for _, r in live_fix.iterrows()
    }

    fixed = 0
    for idx, row in df.iterrows():
        k = (clean(row.get("race_date", "")), clean(row.get("track", "")), clean(row.get("race_no", "")), horse_key(row.get("horse", "")))
        fix = fix_by_key.get(k)
        if fix is None:
            continue
        new_score = to_num(fix.get("distance_fit_score_rebuilt", ""))
        new_band = clean(fix.get("distance_fit_band_rebuilt", ""))
        status = clean(fix.get("distance_profile_truth_status_rebuilt", ""))
        if new_score is not None and status == "OK_REBUILT":
            old_score = to_num(row.get(score_col, ""))
            old_band = clean(row.get(band_col, ""))
            if old_score in [None, 0.0] or old_band in ["", "NO_PROFILE"]:
                df.at[idx, score_col] = round(new_score, 1)
                if band_col in df.columns:
                    df.at[idx, band_col] = new_band
                if truth_col and truth_col in df.columns:
                    df.at[idx, truth_col] = "OK_REBUILT_FROM_V6_1_HISTORY"
                fixed += 1

    df.to_csv(path, index=False)
    audit_rows.append({"file": path.name, "status": "UPDATED", "fixed": fixed, "backup": str(backup)})

apply_to_file(dna_path, "distance_fit_score", "distance_fit_band", "")
apply_to_file(runners_path, "score_distance", "distance_profile", "distance_profile_truth_status")
apply_to_file(command_path, "edgeiq_score_distance_v3", "edgeiq_score_distance_band_v3", "")

pd.DataFrame(audit_rows).to_csv(audit_path, index=False)

with open(report_path, "w", encoding="utf-8") as f:
    f.write("[EDGEIQ_DISTANCE_PROFILE_FIX_V1]\n")
    f.write(f"built_at={datetime.now(timezone.utc).isoformat()}\n")
    f.write(f"historical_rows={len(hist)}\n")
    f.write(f"usable_rows={len(usable)}\n")
    f.write(f"profile_rows={len(profiles)}\n")
    f.write(f"live_rows={len(live_fix)}\n")
    f.write(f"live_ok_rebuilt={(live_fix['distance_profile_truth_status_rebuilt'] == 'OK_REBUILT').sum()}\n")
    f.write(f"profile_out={out_profile}\n")
    f.write(f"live_out={out_live}\n")
    f.write(f"audit={audit_path}\n")
    f.write("pricing_maths_changed=NO\n")
    f.write("v6_1_changed=NO\n")
    f.write("v7_2g2_changed=NO\n")

print("[EDGEIQ_DISTANCE_PROFILE_FIX_V1] COMPLETE")
print(pd.DataFrame(audit_rows).to_string(index=False))
print(report_path)
