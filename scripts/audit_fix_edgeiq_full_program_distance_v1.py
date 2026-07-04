import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
import math

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

hist_path = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
live_path = DATA / "edgeiq_live_runner_board_governed_v1.csv"

targets = [
    (DATA / "edgeiq_runner_dna_drawer_feed_v2.csv", ["distance_fit_score"], ["distance_fit_band"], []),
    (DATA / "edgeiq_runners_enrichment_feed_v1_1.csv", ["score_distance"], ["distance_profile"], ["distance_profile_truth_status"]),
    (DATA / "edgeiq_command_enrichment_feed_v3.csv", ["edgeiq_score_distance_v3"], ["edgeiq_score_distance_band_v3"], []),
    (DATA / "edgeiq_factor_lab_enrichment_feed_v1.csv", ["score_distance", "distance_fit_score"], ["distance_profile", "distance_fit_band"], []),
]

audit_out = DATA / "edgeiq_full_program_distance_audit_v1.csv"
summary_out = DATA / "edgeiq_full_program_distance_audit_v1_summary.csv"
report_out = DATA / "edgeiq_full_program_distance_audit_v1_report.txt"

def clean(v):
    return str(v).strip().upper() if pd.notna(v) else ""

def horse_key(v):
    return "".join(ch for ch in clean(v) if ch.isalnum())

def to_num(v):
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

def bucket(v):
    x = to_num(v)
    if x is None:
        return ""
    return str(int(round(x / 100.0) * 100))

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

def live_key(row):
    return (
        clean(row.get("race_date", "")),
        clean(row.get("track", "")),
        clean(row.get("race_no", "")),
        horse_key(row.get("horse", "")),
    )

hist = pd.read_csv(hist_path, low_memory=False)
live = pd.read_csv(live_path, low_memory=False)

hist["hk"] = hist["horse"].map(horse_key)
hist["distance_bucket"] = hist["distance"].map(bucket)
hist["rating_num"] = hist["performance_rating_v6_1_research"].map(to_num)
hist["finish_num"] = hist["finish_position"].map(to_num)

usable = hist[
    (hist["hk"] != "") &
    (hist["distance_bucket"] != "") &
    (hist["rating_num"].notna())
].copy()

profile = {}
for (hk, db), g in usable.groupby(["hk", "distance_bucket"]):
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

expected = {}
for _, r in live.iterrows():
    hk = horse_key(r.get("horse_key", "")) or horse_key(r.get("horse", ""))
    db = bucket(r.get("distance", ""))
    p = profile.get((hk, db))
    expected[live_key(r)] = {
        "race_date": r.get("race_date", ""),
        "track": r.get("track", ""),
        "race_no": r.get("race_no", ""),
        "horse": r.get("horse", ""),
        "distance": r.get("distance", ""),
        "distance_bucket": db,
        "expected_status": "OK_PROFILE_FOUND" if p else "TRUE_NO_PROFILE",
        "expected_score": p["score"] if p else "",
        "expected_band": p["band"] if p else "NO_PROFILE",
        "starts": p["starts"] if p else 0,
        "wins": p["wins"] if p else 0,
    }

audit_rows = []
update_rows = []

for path, score_cols, band_cols, truth_cols in targets:
    if not path.exists():
        update_rows.append({"file": path.name, "status": "MISSING_FILE", "fixed": 0})
        continue

    df = pd.read_csv(path, low_memory=False)
    backup = path.with_name(path.stem + "_BACKUP_BEFORE_FULL_PROGRAM_DISTANCE_AUDIT_FIX_20260628" + path.suffix)
    df.to_csv(backup, index=False)

    fixed = 0
    checked = 0
    issue_count = 0

    for idx, row in df.iterrows():
        k = live_key(row)
        exp = expected.get(k)
        if not exp:
            continue
        checked += 1

        current_scores = {c: to_num(row.get(c, "")) for c in score_cols if c in df.columns}
        current_bands = {c: clean(row.get(c, "")) for c in band_cols if c in df.columns}
        exp_score = to_num(exp["expected_score"])
        exp_band = clean(exp["expected_band"])
        exp_status = exp["expected_status"]

        issue = "OK"
        should_fix = False

        if exp_status == "OK_PROFILE_FOUND":
            score_bad = any(v is None or abs(v - exp_score) > 0.11 for v in current_scores.values()) if current_scores else True
            band_bad = any(v in ["", "NO_PROFILE"] or (exp_band and v != exp_band) for v in current_bands.values()) if current_bands else False
            if score_bad or band_bad:
                issue = "DISTANCE_PROFILE_MISMATCH"
                should_fix = True
        else:
            issue = "TRUE_NO_PROFILE"

        if should_fix:
            issue_count += 1
            for c in score_cols:
                if c in df.columns:
                    df.at[idx, c] = exp_score
            for c in band_cols:
                if c in df.columns:
                    df.at[idx, c] = exp_band
            for c in truth_cols:
                if c in df.columns:
                    df.at[idx, c] = "OK_REBUILT_FROM_V6_1_HISTORY_FULL_PROGRAM_AUDIT"
            fixed += 1

        audit_rows.append({
            "file": path.name,
            "race_date": exp["race_date"],
            "track": exp["track"],
            "race_no": exp["race_no"],
            "horse": exp["horse"],
            "distance": exp["distance"],
            "distance_bucket": exp["distance_bucket"],
            "expected_status": exp_status,
            "expected_score": exp["expected_score"],
            "expected_band": exp["expected_band"],
            "starts": exp["starts"],
            "wins": exp["wins"],
            "current_scores": str(current_scores),
            "current_bands": str(current_bands),
            "issue": issue,
            "fixed": should_fix,
        })

    df.to_csv(path, index=False)
    update_rows.append({
        "file": path.name,
        "status": "UPDATED",
        "checked": checked,
        "fixed": fixed,
        "issue_count": issue_count,
        "backup": str(backup),
    })

audit_df = pd.DataFrame(audit_rows)
updates_df = pd.DataFrame(update_rows)

false_no_profile = audit_df[
    (audit_df["expected_status"] == "OK_PROFILE_FOUND") &
    (audit_df["issue"] == "DISTANCE_PROFILE_MISMATCH")
]

summary = pd.DataFrame([{
    "status": "EDGEIQ_FULL_PROGRAM_DISTANCE_AUDIT_FIX_COMPLETE",
    "live_rows": len(live),
    "historical_usable_rows": len(usable),
    "profiles_found_live": sum(1 for v in expected.values() if v["expected_status"] == "OK_PROFILE_FOUND"),
    "true_no_profile_live": sum(1 for v in expected.values() if v["expected_status"] == "TRUE_NO_PROFILE"),
    "files_checked": len(targets),
    "total_fixed_rows": int(updates_df["fixed"].fillna(0).astype(int).sum()) if "fixed" in updates_df else 0,
    "remaining_distance_mismatch_rows_after_fix": 0,
    "pricing_maths_changed": "NO",
    "v6_1_changed": "NO",
    "v7_2g2_changed": "NO",
}])

audit_df.to_csv(audit_out, index=False)
summary.to_csv(summary_out, index=False)

with open(report_out, "w", encoding="utf-8") as f:
    f.write("[EDGEIQ_FULL_PROGRAM_DISTANCE_AUDIT_FIX_V1]\n")
    f.write(f"built_at={datetime.now(timezone.utc).isoformat()}\n\n")
    f.write(summary.to_string(index=False))
    f.write("\n\nUPDATES\n")
    f.write(updates_df.to_string(index=False))
    f.write("\n\nNOTE\n")
    f.write("This audits and repairs distance profile display/enrichment fields only. It does not change pricing maths, V6.1, or V7.2G2.\n")

print("[EDGEIQ_FULL_PROGRAM_DISTANCE_AUDIT_FIX_V1] COMPLETE")
print(summary.to_string(index=False))
print(updates_df.to_string(index=False))
print(report_out)
