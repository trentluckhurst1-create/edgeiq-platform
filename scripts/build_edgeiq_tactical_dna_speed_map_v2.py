import os
import re
import pandas as pd
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

RUNNER_SRC = os.path.join(DATA, "edgeiq_live_runner_board_v1.csv")
DNA_SRC = os.path.join(DATA, "edgeiq_tactical_dna_v2.csv")
PACE_SRC = os.path.join(DATA, "edgeiq_pace_pressure_engine_v2.csv")

OUT = os.path.join(DATA, "edgeiq_tactical_dna_speed_map_v2.csv")
RACE_OUT = os.path.join(DATA, "edgeiq_tactical_dna_speed_map_race_summary_v2.csv")
AUDIT = os.path.join(DATA, "edgeiq_tactical_dna_speed_map_v2_audit.csv")

print("=" * 100)
print("EDGEIQ TACTICAL DNA SPEED MAP V2.1 - USING TACTICAL DNA V2")
print("=" * 100)

def clean_key(x):
    x = str(x).upper().strip()
    x = re.sub(r"\([^)]*\)", "", x)
    x = x.replace("'", "").replace("’", "")
    x = re.sub(r"[^A-Z0-9]+", "", x)
    return x

def num(x):
    s = str(x).strip().replace("$", "").replace(",", "")
    if s == "":
        return np.nan
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group(0)) if m else np.nan

def pct_to_prob(x):
    v = num(x)
    if pd.isna(v):
        return 0.0
    if v > 1:
        v = v / 100.0
    return max(0.0, min(1.0, float(v)))

def find_col(cols, options):
    lower = {c.lower(): c for c in cols}
    for opt in options:
        if opt.lower() in lower:
            return lower[opt.lower()]
    return None

for p in [RUNNER_SRC, DNA_SRC]:
    if not os.path.exists(p):
        raise FileNotFoundError(f"Missing required input: {p}")

runners = pd.read_csv(RUNNER_SRC, dtype=str).fillna("")
dna = pd.read_csv(DNA_SRC, dtype=str).fillna("")

horse_col = find_col(runners.columns, ["horse", "horseName", "runner", "runner_name", "name"])
horse_key_col = find_col(runners.columns, ["horse_key", "horseKey", "runner_key"])
track_col = find_col(runners.columns, ["track", "meeting_name", "location"])
race_no_col = find_col(runners.columns, ["race_no", "raceNo", "race_number"])
date_col = find_col(runners.columns, ["meeting_date", "race_date", "date"])
barrier_col = find_col(runners.columns, ["barrier", "barrier_no", "barrierNumber"])
runner_no_col = find_col(runners.columns, ["runner_no", "horseNo", "horse_no", "number"])
jockey_col = find_col(runners.columns, ["jockey"])
trainer_col = find_col(runners.columns, ["trainer"])
price_col = find_col(runners.columns, ["live_price", "ui_price", "sportsbet_price", "market_price", "fixed_win", "tab_fixed_win"])
scr_col = find_col(runners.columns, ["is_scratched", "scratched", "scratch_status", "runner_status"])

if horse_col is None and horse_key_col is None:
    raise ValueError("Runner source missing horse column.")
if track_col is None or race_no_col is None:
    raise ValueError("Runner source missing track/race_no columns.")

runners["horse"] = runners[horse_col] if horse_col else runners[horse_key_col]
runners["horse_key_join"] = runners[horse_key_col].apply(clean_key) if horse_key_col else runners["horse"].apply(clean_key)
runners["horse_key_from_name"] = runners["horse"].apply(clean_key)
runners["track"] = runners[track_col].astype(str).str.upper().str.strip()
runners["race_no"] = runners[race_no_col].apply(num)
runners["meeting_date"] = pd.to_datetime(runners[date_col], errors="coerce").dt.strftime("%Y-%m-%d") if date_col else ""
runners["barrier"] = runners[barrier_col].apply(num) if barrier_col else np.nan
runners["runner_no"] = runners[runner_no_col].apply(num) if runner_no_col else np.nan
runners["jockey"] = runners[jockey_col] if jockey_col else ""
runners["trainer"] = runners[trainer_col] if trainer_col else ""
runners["live_price"] = runners[price_col].apply(num) if price_col else np.nan

if scr_col:
    runners["is_scratched"] = runners[scr_col].astype(str).str.upper().isin(["1", "TRUE", "Y", "YES", "SCR", "SCRATCHED"])
else:
    runners["is_scratched"] = False

runners = runners[
    (runners["horse_key_join"] != "") &
    (runners["track"] != "") &
    (runners["race_no"].notna())
].copy()

runners["race_key"] = (
    runners["meeting_date"].astype(str) + "|" +
    runners["track"] + "|R" +
    runners["race_no"].astype(int).astype(str)
)

if runners["meeting_date"].replace("", np.nan).isna().all():
    runners["race_key"] = runners["track"] + "|R" + runners["race_no"].astype(int).astype(str)

dna_key_col = find_col(dna.columns, ["horse_key", "horseKey"])
if dna_key_col is None:
    raise ValueError("Tactical DNA V2 missing horse_key.")

dna["horse_key_join"] = dna[dna_key_col].apply(clean_key)

col_map = {
    "leader_pct_v2": "leader_pct",
    "on_pace_pct_v2": "on_pace_pct",
    "midfield_pct_v2": "midfield_pct",
    "backmarker_pct_v2": "backmarker_pct",
}

for src, dst in col_map.items():
    if src not in dna.columns:
        raise ValueError(f"Tactical DNA V2 missing {src}.")
    dna[dst] = dna[src].apply(pct_to_prob)

for c in ["avg_early_speed", "avg_late_speed"]:
    dna[c] = dna[c].apply(num) if c in dna.columns else np.nan

dna_keep = [
    "horse_key_join",
    "leader_pct",
    "on_pace_pct",
    "midfield_pct",
    "backmarker_pct",
    "avg_early_speed",
    "avg_late_speed",
]

for optional in ["tactical_speed_bucket_v2", "dna_confidence_v2", "dna_source", "runs_with_sectionals", "runs_from_results"]:
    if optional in dna.columns:
        dna_keep.append(optional)

dna = dna[dna_keep].drop_duplicates("horse_key_join")

df = runners.merge(dna, on="horse_key_join", how="left")

no_direct = df["leader_pct"].isna()
if no_direct.any():
    fallback = runners.loc[no_direct, ["horse_key_from_name"]].copy()
    fallback["fallback_index"] = fallback.index
    dna_fb = dna.rename(columns={"horse_key_join": "horse_key_from_name"})
    fb_join = fallback.merge(dna_fb, on="horse_key_from_name", how="left").set_index("fallback_index")

    for c in dna_keep:
        if c == "horse_key_join":
            continue
        if c in df.columns and c in fb_join.columns:
            df.loc[no_direct, c] = fb_join[c]

for c in ["leader_pct", "on_pace_pct", "midfield_pct", "backmarker_pct"]:
    df[c] = df[c].fillna(0.0)

df["dna_matched"] = df[["leader_pct", "on_pace_pct", "midfield_pct", "backmarker_pct"]].sum(axis=1) > 0

def primary_bucket(row):
    if not row["dna_matched"]:
        return "Unknown"
    vals = {
        "Leader": row["leader_pct"],
        "On Pace": row["on_pace_pct"],
        "Midfield": row["midfield_pct"],
        "Backmarker": row["backmarker_pct"],
    }
    return max(vals, key=vals.get)

df["speed_map_bucket"] = df.apply(primary_bucket, axis=1)

def bucket_rank_score(row):
    b = row["speed_map_bucket"]
    early = 0 if pd.isna(row["avg_early_speed"]) else row["avg_early_speed"]
    late = 0 if pd.isna(row["avg_late_speed"]) else row["avg_late_speed"]

    if b == "Leader":
        return row["leader_pct"] * 100 + early * 0.20
    if b == "On Pace":
        return row["on_pace_pct"] * 100 + row["leader_pct"] * 30 + early * 0.15
    if b == "Midfield":
        return row["midfield_pct"] * 100 + row["on_pace_pct"] * 20 + late * 0.08
    if b == "Backmarker":
        return row["backmarker_pct"] * 100 + row["midfield_pct"] * 20 + late * 0.12
    return -999

df["bucket_rank_score"] = df.apply(bucket_rank_score, axis=1)

bucket_x = {
    "Leader": 14,
    "On Pace": 32,
    "Midfield": 56,
    "Backmarker": 80,
    "Unknown": 92,
}

bucket_label = {
    "Leader": "LEADER",
    "On Pace": "ON PACE",
    "Midfield": "MIDFIELD",
    "Backmarker": "BACKMARKER",
    "Unknown": "UNKNOWN",
}

rows = []
race_rows = []

for race_key, g in df.groupby("race_key", sort=False):
    g = g.copy()
    active = g[~g["is_scratched"]].copy()

    field_size = len(g)
    active_field_size = len(active)
    dna_matched = int(active["dna_matched"].sum())
    dna_coverage = dna_matched / max(1, active_field_size)

    expected_leaders = float(active["leader_pct"].sum())
    expected_onpace = float(active["on_pace_pct"].sum())
    expected_midfield = float(active["midfield_pct"].sum())
    expected_backmarkers = float(active["backmarker_pct"].sum())

    leader_count = int((active["speed_map_bucket"] == "Leader").sum())
    onpace_count = int((active["speed_map_bucket"] == "On Pace").sum())
    midfield_count = int((active["speed_map_bucket"] == "Midfield").sum())
    backmarker_count = int((active["speed_map_bucket"] == "Backmarker").sum())
    unknown_count = int((active["speed_map_bucket"] == "Unknown").sum())

    for bucket, bg in g.groupby("speed_map_bucket", sort=False):
        bg = bg.sort_values(["is_scratched", "bucket_rank_score"], ascending=[True, False]).copy()
        n = len(bg)

        for i, (_, r) in enumerate(bg.iterrows(), start=1):
            if n <= 1:
                y_pct = 50
            else:
                y_pct = 10 + ((i - 1) / (n - 1)) * 80

            barrier = r["barrier"]
            if not pd.isna(barrier):
                y_pct = max(6, min(94, y_pct + ((barrier - 1) * 0.15)))

            map_x_pct = bucket_x.get(bucket, 92)

            if bucket == "Leader":
                map_x_pct = max(8, map_x_pct - (r["leader_pct"] * 5))
            elif bucket == "Backmarker":
                map_x_pct = min(88, map_x_pct + (r["backmarker_pct"] * 5))

            rows.append({
                "race_key": race_key,
                "meeting_date": r["meeting_date"],
                "track": r["track"],
                "race_no": int(r["race_no"]),
                "runner_no": "" if pd.isna(r["runner_no"]) else int(r["runner_no"]),
                "horse": r["horse"],
                "horse_key": r["horse_key_join"],
                "barrier": "" if pd.isna(r["barrier"]) else int(r["barrier"]),
                "jockey": r["jockey"],
                "trainer": r["trainer"],
                "live_price": "" if pd.isna(r["live_price"]) else r["live_price"],
                "is_scratched": bool(r["is_scratched"]),
                "dna_matched": bool(r["dna_matched"]),
                "leader_pct": round(float(r["leader_pct"]), 4),
                "on_pace_pct": round(float(r["on_pace_pct"]), 4),
                "midfield_pct": round(float(r["midfield_pct"]), 4),
                "backmarker_pct": round(float(r["backmarker_pct"]), 4),
                "avg_early_speed": "" if pd.isna(r["avg_early_speed"]) else round(float(r["avg_early_speed"]), 3),
                "avg_late_speed": "" if pd.isna(r["avg_late_speed"]) else round(float(r["avg_late_speed"]), 3),
                "speed_map_bucket": bucket,
                "speed_map_label": bucket_label.get(bucket, "UNKNOWN"),
                "bucket_rank": i,
                "bucket_rank_score": round(float(r["bucket_rank_score"]), 3),
                "map_x_pct": round(float(map_x_pct), 2),
                "map_y_pct": round(float(y_pct), 2),
                "dna_confidence": r.get("dna_confidence_v2", ""),
                "dna_source": r.get("dna_source", ""),
                "tactical_speed_bucket": r.get("tactical_speed_bucket_v2", ""),
                "runs_with_sectionals": r.get("runs_with_sectionals", ""),
                "runs_from_results": r.get("runs_from_results", ""),
            })

    race_rows.append({
        "race_key": race_key,
        "meeting_date": g["meeting_date"].iloc[0],
        "track": g["track"].iloc[0],
        "race_no": int(g["race_no"].iloc[0]),
        "field_size": field_size,
        "active_field_size": active_field_size,
        "dna_matched": dna_matched,
        "dna_coverage": round(dna_coverage, 3),
        "expected_leaders": round(expected_leaders, 3),
        "expected_onpace": round(expected_onpace, 3),
        "expected_midfield": round(expected_midfield, 3),
        "expected_backmarkers": round(expected_backmarkers, 3),
        "leader_count": leader_count,
        "onpace_count": onpace_count,
        "midfield_count": midfield_count,
        "backmarker_count": backmarker_count,
        "unknown_count": unknown_count,
    })

out = pd.DataFrame(rows)
race_out = pd.DataFrame(race_rows)

if os.path.exists(PACE_SRC):
    pace = pd.read_csv(PACE_SRC, dtype=str).fillna("")
    pace_keep = [
        "race_key",
        "projected_tempo_shape",
        "pace_pressure_percentile",
        "pace_pressure_confidence",
        "pace_pressure_reason",
    ]
    pace_keep = [c for c in pace_keep if c in pace.columns]
    if "race_key" in pace.columns:
        race_out = race_out.merge(pace[pace_keep].drop_duplicates("race_key"), on="race_key", how="left")
        out = out.merge(pace[pace_keep].drop_duplicates("race_key"), on="race_key", how="left")

out.to_csv(OUT, index=False)
race_out.to_csv(RACE_OUT, index=False)

audit = pd.DataFrame([{
    "dna_source_file": os.path.basename(DNA_SRC),
    "runner_rows_output": len(out),
    "race_rows_output": len(race_out),
    "active_runners": int((out["is_scratched"] == False).sum()) if len(out) else 0,
    "dna_matched_runners": int((out["dna_matched"] == True).sum()) if len(out) else 0,
    "dna_match_rate_pct": round(float((out["dna_matched"] == True).mean() * 100), 2) if len(out) else 0,
    "leaders": int((out["speed_map_bucket"] == "Leader").sum()) if len(out) else 0,
    "on_pace": int((out["speed_map_bucket"] == "On Pace").sum()) if len(out) else 0,
    "midfield": int((out["speed_map_bucket"] == "Midfield").sum()) if len(out) else 0,
    "backmarkers": int((out["speed_map_bucket"] == "Backmarker").sum()) if len(out) else 0,
    "unknown": int((out["speed_map_bucket"] == "Unknown").sum()) if len(out) else 0,
}])

audit.to_csv(AUDIT, index=False)

print("")
print("DONE")
print(f"WROTE: {OUT}")
print(f"WROTE: {RACE_OUT}")
print(f"WROTE: {AUDIT}")
print("")
print(audit.to_string(index=False))
print("")
print("SPEED MAP BUCKET DISTRIBUTION")
print(out["speed_map_bucket"].value_counts(dropna=False).to_string())
print("")
print("DNA SOURCE DISTRIBUTION IN LIVE SPEED MAP")
print(out["dna_source"].value_counts(dropna=False).to_string())
print("")
print("RACE SUMMARY")
print(race_out.sort_values(["meeting_date", "track", "race_no"]).head(80)[[
    "meeting_date",
    "track",
    "race_no",
    "active_field_size",
    "dna_coverage",
    "expected_leaders",
    "leader_count",
    "onpace_count",
    "midfield_count",
    "backmarker_count",
    "unknown_count",
]].to_string(index=False))
