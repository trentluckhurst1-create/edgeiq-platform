from pathlib import Path
import pandas as pd
import re
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

PRED = DATA / "edgeiq_comprehensive_predictive_model_research_v1.csv"
MARKET = DATA / "edgeiq_timestamp_safe_market_snapshot_spine_v1.csv"

OUT = DATA / "edgeiq_market_predictive_overlap_diagnosis_v1.csv"
SUMMARY = DATA / "edgeiq_market_predictive_overlap_diagnosis_v1_summary.txt"

def norm_text(x):
    if pd.isna(x):
        return ""
    s = str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def norm_date(x):
    if pd.isna(x):
        return ""
    try:
        return str(pd.to_datetime(x, errors="coerce").date())
    except Exception:
        return ""

def pick_col(df, names):
    lower = {str(c).lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None

pred = pd.read_csv(PRED, low_memory=False)
market = pd.read_csv(MARKET, low_memory=False)

pred_cols = {
    "race_date": pick_col(pred, ["race_date", "target_race_date", "date"]),
    "track": pick_col(pred, ["track", "target_track", "venue"]),
    "race_no": pick_col(pred, ["race_no", "race_number", "target_race_no"]),
    "horse": pick_col(pred, ["horse", "runner", "runner_name", "horse_name"]),
}

market_cols = {
    "race_date": pick_col(market, ["race_date", "target_race_date", "date", "meeting_date"]),
    "track": pick_col(market, ["track", "target_track", "venue"]),
    "race_no": pick_col(market, ["race_no", "race_number", "target_race_no"]),
    "horse": pick_col(market, ["horse", "runner", "runner_name", "horse_name"]),
}

def prep(df, cols, label):
    out = pd.DataFrame()
    out["source"] = label
    out["race_date_raw"] = df[cols["race_date"]] if cols["race_date"] else ""
    out["track_raw"] = df[cols["track"]] if cols["track"] else ""
    out["race_no_raw"] = df[cols["race_no"]] if cols["race_no"] else ""
    out["horse_raw"] = df[cols["horse"]] if cols["horse"] else ""

    out["race_date_key"] = out["race_date_raw"].map(norm_date)
    out["track_key"] = out["track_raw"].map(norm_text)
    out["race_no_key"] = out["race_no_raw"].astype(str).str.extract(r"(\d+)", expand=False).fillna("")
    out["horse_key"] = out["horse_raw"].map(norm_text)

    out["race_key_date_track_race"] = out["race_date_key"] + "|" + out["track_key"] + "|" + out["race_no_key"]
    out["race_key_date_track"] = out["race_date_key"] + "|" + out["track_key"]
    out["runner_key_full"] = out["race_key_date_track_race"] + "|" + out["horse_key"]
    out["runner_key_no_race_no"] = out["race_date_key"] + "|" + out["track_key"] + "|" + out["horse_key"]
    return out

p = prep(pred, pred_cols, "predictive")
m = prep(market, market_cols, "market")

pred_races_full = set(p["race_key_date_track_race"].dropna())
market_races_full = set(m["race_key_date_track_race"].dropna())
pred_races_no_race = set(p["race_key_date_track"].dropna())
market_races_no_race = set(m["race_key_date_track"].dropna())

pred_runner_full = set(p["runner_key_full"].dropna())
market_runner_full = set(m["runner_key_full"].dropna())
pred_runner_no_race = set(p["runner_key_no_race_no"].dropna())
market_runner_no_race = set(m["runner_key_no_race_no"].dropna())

rows = []

checks = [
    ("race_full_date_track_race_no", len(pred_races_full), len(market_races_full), len(pred_races_full & market_races_full)),
    ("race_loose_date_track", len(pred_races_no_race), len(market_races_no_race), len(pred_races_no_race & market_races_no_race)),
    ("runner_full_date_track_race_no_horse", len(pred_runner_full), len(market_runner_full), len(pred_runner_full & market_runner_full)),
    ("runner_loose_date_track_horse", len(pred_runner_no_race), len(market_runner_no_race), len(pred_runner_no_race & market_runner_no_race)),
]

for name, pred_n, market_n, overlap_n in checks:
    rows.append({
        "check": name,
        "predictive_unique": pred_n,
        "market_unique": market_n,
        "overlap_unique": overlap_n,
        "market_overlap_pct": round((overlap_n / market_n) * 100, 2) if market_n else 0,
        "predictive_overlap_pct": round((overlap_n / pred_n) * 100, 2) if pred_n else 0,
    })

diagnosis = pd.DataFrame(rows)
diagnosis.to_csv(OUT, index=False)

pred_dates = sorted([x for x in p["race_date_key"].dropna().unique() if x])
market_dates = sorted([x for x in m["race_date_key"].dropna().unique() if x])
date_overlap = sorted(set(pred_dates) & set(market_dates))

pred_tracks = sorted([x for x in p["track_key"].dropna().unique() if x])
market_tracks = sorted([x for x in m["track_key"].dropna().unique() if x])
track_overlap = sorted(set(pred_tracks) & set(market_tracks))

lines = []
lines.append("EDGEIQ_MARKET_PREDICTIVE_OVERLAP_DIAGNOSIS_V1")
lines.append(f"built_at={datetime.now(timezone.utc).isoformat()}")
lines.append("")
lines.append("COLUMN MAP")
lines.append(f"predictive={pred_cols}")
lines.append(f"market={market_cols}")
lines.append("")
lines.append("OVERLAP CHECKS")
for _, r in diagnosis.iterrows():
    lines.append(f"{r['check']}: pred={r['predictive_unique']} market={r['market_unique']} overlap={r['overlap_unique']} market_overlap_pct={r['market_overlap_pct']}")
lines.append("")
lines.append(f"predictive_date_range={pred_dates[:1]} to {pred_dates[-1:]}")
lines.append(f"market_date_range={market_dates[:1]} to {market_dates[-1:]}")
lines.append(f"date_overlap_count={len(date_overlap)}")
lines.append(f"date_overlap_sample={date_overlap[:20]}")
lines.append("")
lines.append(f"predictive_track_count={len(pred_tracks)}")
lines.append(f"market_track_count={len(market_tracks)}")
lines.append(f"track_overlap_count={len(track_overlap)}")
lines.append(f"track_overlap_sample={track_overlap[:40]}")
lines.append("")
lines.append("MARKET TRACKS NOT IN PREDICTIVE SAMPLE")
lines.extend(sorted(set(market_tracks) - set(pred_tracks))[:80])
lines.append("")
lines.append("PREDICTIVE TRACKS NOT IN MARKET SAMPLE")
lines.extend(sorted(set(pred_tracks) - set(market_tracks))[:80])

SUMMARY.write_text("\n".join(lines), encoding="utf-8")

print("[EDGEIQ_MARKET_PREDICTIVE_OVERLAP_DIAGNOSIS_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(diagnosis.to_string(index=False))
