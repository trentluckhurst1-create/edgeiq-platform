from pathlib import Path
import pandas as pd
import numpy as np
import re
import json

ROOT = Path(".")
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_results_intelligence_history_v1.csv"
SUMMARY = DATA / "edgeiq_results_intelligence_history_v1_summary.csv"
AUDIT = DATA / "edgeiq_results_intelligence_history_v1_join_audit.csv"
META = DATA / "edgeiq_results_intelligence_history_v1.json"

COUNTRIES = re.compile(r"(NZ|GB|IRE|FR|USA|JPN|AUS)$", re.I)

def clean_text(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def canon_horse(x):
    s = clean_text(x).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def canon_horse_loose(x):
    return COUNTRIES.sub("", canon_horse(x))

def clean_track(x):
    return re.sub(r"[^A-Z0-9]", "", clean_text(x).upper())

def pick_col(df, names):
    lookup = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lookup:
            return lookup[n.lower()]
    return None

def read_csv_if_exists(path):
    if not path.exists():
        print(f"[MISS] {path.name}")
        return pd.DataFrame()
    print(f"[READ] {path.name}")
    return pd.read_csv(path, dtype=str, low_memory=False)

def add_keys(df, horse_cols=("horse_key", "horse_canon", "horse", "horseName", "runner", "runner_name")):
    if df.empty:
        return df

    date_col = pick_col(df, ["race_date", "meeting_date", "date", "raceDate"])
    track_col = pick_col(df, ["track", "meeting", "meeting_name"])
    race_col = pick_col(df, ["race_no", "raceNo", "race_number", "race"])
    horse_col = None

    for c in horse_cols:
        horse_col = pick_col(df, [c])
        if horse_col:
            break

    df = df.copy()
    df["_race_date_key"] = df[date_col].map(clean_text) if date_col else ""
    df["_track_key"] = df[track_col].map(clean_track) if track_col else ""
    df["_race_no_key"] = df[race_col].map(clean_text) if race_col else ""
    df["_horse_key_strict"] = df[horse_col].map(canon_horse) if horse_col else ""
    df["_horse_key_loose"] = df[horse_col].map(canon_horse_loose) if horse_col else ""
    df["_runner_key_strict"] = df["_race_date_key"] + "|" + df["_track_key"] + "|" + df["_race_no_key"] + "|" + df["_horse_key_strict"]
    df["_runner_key_loose"] = df["_race_date_key"] + "|" + df["_track_key"] + "|" + df["_race_no_key"] + "|" + df["_horse_key_loose"]
    df["_race_key"] = df["_race_date_key"] + "|" + df["_track_key"] + "|" + df["_race_no_key"]
    return df

def num(s):
    return pd.to_numeric(s, errors="coerce")

def keep_cols(df, wanted):
    existing = [c for c in wanted if c in df.columns]
    keys = [c for c in ["_runner_key_strict", "_runner_key_loose", "_race_key", "_horse_key_strict", "_horse_key_loose"] if c in df.columns]
    return df[keys + existing].copy()

def dedupe(df, key):
    if df.empty or key not in df.columns:
        return df
    return df[df[key].astype(str).str.len() > 0].drop_duplicates(key, keep="last")

def merge_runner(base, side, prefix, cols):
    if side.empty:
        base[f"{prefix}_matched"] = False
        return base

    side = keep_cols(side, cols)
    strict = dedupe(side, "_runner_key_strict")
    loose = dedupe(side, "_runner_key_loose")

    rename = {c: f"{prefix}_{c}" for c in side.columns if not c.startswith("_")}
    strict = strict.rename(columns=rename)
    loose = loose.rename(columns=rename)

    out = base.merge(strict.drop(columns=["_runner_key_loose"], errors="ignore"), on="_runner_key_strict", how="left")
    matched = out[[c for c in out.columns if c.startswith(prefix + "_")]].notna().any(axis=1)

    missing = ~matched
    if missing.any() and not loose.empty:
        loose_payload = loose.drop(columns=["_runner_key_strict"], errors="ignore")
        fallback = base.loc[missing, ["_runner_key_loose"]].merge(loose_payload, on="_runner_key_loose", how="left")
        for c in fallback.columns:
            if c.startswith(prefix + "_") and c in out.columns:
                out.loc[missing, c] = out.loc[missing, c].fillna(fallback[c].values)

    out[f"{prefix}_matched"] = out[[c for c in out.columns if c.startswith(prefix + "_")]].notna().any(axis=1)
    return out

def merge_race(base, side, prefix, cols):
    if side.empty:
        base[f"{prefix}_matched"] = False
        return base

    side = keep_cols(side, cols)
    side = dedupe(side, "_race_key")
    rename = {c: f"{prefix}_{c}" for c in side.columns if not c.startswith("_")}
    side = side.rename(columns=rename)

    out = base.merge(side.drop(columns=["_runner_key_strict", "_runner_key_loose", "_horse_key_strict", "_horse_key_loose"], errors="ignore"), on="_race_key", how="left")
    out[f"{prefix}_matched"] = out[[c for c in out.columns if c.startswith(prefix + "_")]].notna().any(axis=1)
    return out

# ---------- LOAD RESULTS ----------
results_path = DATA / "edgeiq_racingcom_results_warehouse_full_v1.csv"
if not results_path.exists():
    results_path = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"

results = read_csv_if_exists(results_path)
results = add_keys(results, horse_cols=("horse_key", "horse_canon", "horseName", "horse", "runner", "runner_name"))

pos_col = pick_col(results, ["finishPosition", "finish_position", "position", "pos", "result"])
sp_col = pick_col(results, ["sp", "starting_price", "fixed_win", "stab"])

results["finish_position"] = num(results[pos_col]) if pos_col else np.nan
results["market_sp"] = num(results[sp_col]) if sp_col else np.nan
results["won_flag"] = results["finish_position"].eq(1)
results["placed_flag"] = results["finish_position"].between(1, 3, inclusive="both")
results["top4_flag"] = results["finish_position"].between(1, 4, inclusive="both")

# ---------- LOAD MODEL / SIGNAL SOURCES ----------
bet = add_keys(read_csv_if_exists(DATA / "edgeiq_bet_quality_engine_v1_1.csv"))
if bet.empty:
    bet = add_keys(read_csv_if_exists(DATA / "edgeiq_live_bet_quality_v1_1.csv"))

v8 = add_keys(read_csv_if_exists(DATA / "edgeiq_fair_price_v8_interaction_filter_replay_v1.csv"))
if v8.empty:
    v8 = add_keys(read_csv_if_exists(DATA / "edgeiq_fair_price_v8_brc_fallback_replay_v1.csv"))
if v8.empty:
    v8 = add_keys(read_csv_if_exists(DATA / "edgeiq_live_v8_candidate_display_feed_v1.csv"))

fair = add_keys(read_csv_if_exists(DATA / "edgeiq_fair_price_v7_candidate_replay.csv"))
if fair.empty:
    fair = add_keys(read_csv_if_exists(DATA / "edgeiq_fair_price_replay_v1.csv"))

reliability = add_keys(read_csv_if_exists(DATA / "edgeiq_race_reliability_v1.csv"))

sectional_strength = add_keys(read_csv_if_exists(DATA / "edgeiq_sectional_strength_v2.csv"), horse_cols=("horse_key", "horse", "horse_name"))
sectional_ability = add_keys(read_csv_if_exists(DATA / "edgeiq_sectional_ability_engine_v3.csv"), horse_cols=("horse_key", "horse", "horse_name"))

# ---------- MERGE ----------
out = results.copy()

out = merge_runner(out, fair, "fairhist", [
    "fair_price", "edgeiq_price", "rated_price", "live_price", "edge_pct",
    "v3_probability", "probability", "confidence_score", "model_rank"
])

out = merge_runner(out, bet, "betq", [
    "fair_price", "live_price", "edge_pct", "v3_probability", "confidence_score",
    "bet_quality_score_v1_1", "bet_quality_grade_v1_1", "bet_quality_score_band_v1_1",
    "bet_quality_status_v1_1", "bet_quality_overlay_pct_v1_1",
    "bet_quality_fair_price_used_v1_1", "bet_quality_live_price_used_v1_1",
    "v8_candidate_price_display", "v8_delta_display", "brc_match_level_v8"
])

out = merge_runner(out, v8, "v8", [
    "v8_candidate_price_display", "v8_interaction_candidate_price", "v8_delta_display",
    "v8_interaction_price_delta", "brc_match_level_v8", "v8_candidate_badge",
    "v8_candidate_display_status", "fair_price", "edge_pct"
])

out = merge_race(out, reliability, "reliability", [
    "race_reliability_band_v1", "race_reliability_score_v1", "race_strength_band",
    "race_strength_band_live_v2", "field_size", "pace_pressure", "trust_profile"
])

out = merge_runner(out, sectional_strength, "sect_strength", [
    "sectional_strength_score", "sectional_strength_band", "sectional_strength_rank",
    "sectional_profile", "sectional_edge_tier"
])

out = merge_runner(out, sectional_ability, "sect_ability", [
    "sectional_ability_score", "sectional_profile", "early_speed_score",
    "late_power_index", "sectional_weapon_score", "tempo_role", "run_style"
])

# ---------- CANONICAL OUTPUT FIELDS ----------
out["edgeiq_fair_price"] = (
    num(out.get("betq_bet_quality_fair_price_used_v1_1"))
    .fillna(num(out.get("betq_fair_price")))
    .fillna(num(out.get("fairhist_fair_price")))
    .fillna(num(out.get("fairhist_edgeiq_price")))
)

out["edgeiq_live_price"] = (
    num(out.get("betq_bet_quality_live_price_used_v1_1"))
    .fillna(num(out.get("betq_live_price")))
    .fillna(num(out.get("fairhist_live_price")))
)

out["edgeiq_overlay_pct"] = (
    num(out.get("betq_bet_quality_overlay_pct_v1_1"))
    .fillna(num(out.get("betq_edge_pct")))
    .fillna(num(out.get("fairhist_edge_pct")))
)

mask_calc = out["edgeiq_overlay_pct"].isna() & out["edgeiq_fair_price"].gt(0) & out["market_sp"].gt(0)
out.loc[mask_calc, "edgeiq_overlay_pct"] = ((out.loc[mask_calc, "market_sp"] / out.loc[mask_calc, "edgeiq_fair_price"]) - 1) * 100

out["v8_fair_price"] = (
    num(out.get("v8_v8_candidate_price_display"))
    .fillna(num(out.get("v8_v8_interaction_candidate_price")))
    .fillna(num(out.get("betq_v8_candidate_price_display")))
)

out["v8_confidence"] = (
    out.get("v8_brc_match_level_v8", pd.Series("", index=out.index)).fillna("")
    .where(lambda s: s.astype(str).str.len() > 0, out.get("betq_brc_match_level_v8", pd.Series("", index=out.index)).fillna(""))
    .replace({
        "EXACT": "HIGH",
        "TRACK_DISTANCE_RAIL_CONDITION": "MEDIUM",
        "TRACK_DISTANCE_RAIL_CONDITION_WIDE": "LOW",
    })
)

out["bet_quality_score"] = num(out.get("betq_bet_quality_score_v1_1"))
out["bet_quality_grade"] = out.get("betq_bet_quality_grade_v1_1", pd.Series("", index=out.index)).fillna("")
out["bet_quality_band"] = out.get("betq_bet_quality_score_band_v1_1", pd.Series("", index=out.index)).fillna("")

out["profit_sp"] = np.where(
    out["market_sp"].gt(0),
    np.where(out["won_flag"], out["market_sp"] - 1, -1),
    np.nan
)

out["profit_fair"] = np.where(
    out["edgeiq_fair_price"].gt(0),
    np.where(out["won_flag"], out["edgeiq_fair_price"] - 1, -1),
    np.nan
)

def overlay_bucket(x):
    if pd.isna(x): return "NO_OVERLAY"
    if x < 0: return "NEGATIVE"
    if x < 5: return "0_5"
    if x < 10: return "5_10"
    if x < 15: return "10_15"
    if x < 20: return "15_20"
    if x < 30: return "20_30"
    return "30_PLUS"

out["overlay_bucket"] = out["edgeiq_overlay_pct"].map(overlay_bucket)

# ---------- WRITE ----------
out.to_csv(OUT, index=False)

summary_rows = [
    ("source_results_file", results_path.name),
    ("rows", len(out)),
    ("races", out["_race_key"].nunique()),
    ("max_race_date", out["_race_date_key"].max()),
    ("edgeiq_fair_price_matched", int(out["edgeiq_fair_price"].notna().sum())),
    ("bet_quality_matched", int(out["betq_matched"].sum()) if "betq_matched" in out else 0),
    ("v8_matched", int(out["v8_matched"].sum()) if "v8_matched" in out else 0),
    ("race_reliability_matched", int(out["reliability_matched"].sum()) if "reliability_matched" in out else 0),
    ("sectional_strength_matched", int(out["sect_strength_matched"].sum()) if "sect_strength_matched" in out else 0),
    ("sectional_ability_matched", int(out["sect_ability_matched"].sum()) if "sect_ability_matched" in out else 0),
]
pd.DataFrame(summary_rows, columns=["metric", "value"]).to_csv(SUMMARY, index=False)

audit = pd.DataFrame([
    {"join": "results -> fair history", "matched_rows": int(out.get("fairhist_matched", pd.Series(False, index=out.index)).sum()), "total_rows": len(out)},
    {"join": "results -> bet quality", "matched_rows": int(out.get("betq_matched", pd.Series(False, index=out.index)).sum()), "total_rows": len(out)},
    {"join": "results -> v8", "matched_rows": int(out.get("v8_matched", pd.Series(False, index=out.index)).sum()), "total_rows": len(out)},
    {"join": "results -> race reliability", "matched_rows": int(out.get("reliability_matched", pd.Series(False, index=out.index)).sum()), "total_rows": len(out)},
    {"join": "results -> sectional strength", "matched_rows": int(out.get("sect_strength_matched", pd.Series(False, index=out.index)).sum()), "total_rows": len(out)},
    {"join": "results -> sectional ability", "matched_rows": int(out.get("sect_ability_matched", pd.Series(False, index=out.index)).sum()), "total_rows": len(out)},
])
audit["match_pct"] = (audit["matched_rows"] / audit["total_rows"] * 100).round(2)
audit.to_csv(AUDIT, index=False)

META.write_text(json.dumps({
    "status": "COMPLETE",
    "output": str(OUT),
    "summary": str(SUMMARY),
    "audit": str(AUDIT),
    "rows": int(len(out)),
    "races": int(out["_race_key"].nunique()),
}, indent=2), encoding="utf-8")

print("[RESULTS_INTELLIGENCE_HISTORY_V1] COMPLETE")
print(f"rows={len(out)}")
print(f"races={out['_race_key'].nunique()}")
print(f"wrote={OUT}")
print(f"summary={SUMMARY}")
print(f"audit={AUDIT}")
