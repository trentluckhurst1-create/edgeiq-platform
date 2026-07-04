import re
import json
import pandas as pd
from pathlib import Path

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

RESULTS_FILE = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"

OUT_CLEAN = DATA / "edgeiq_results_warehouse_sorted_v1.csv"
OUT_RACES = DATA / "edgeiq_results_race_index_v1.csv"
OUT_WINNERS = DATA / "edgeiq_results_winner_origin_v1.csv"
OUT_TRACK_PROFILE = DATA / "edgeiq_results_track_distance_condition_profile_v1.csv"
OUT_BARRIER_PROFILE = DATA / "edgeiq_results_barrier_profile_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_results_sort_profile_summary_v1.csv"
OUT_JSON = DATA / "edgeiq_results_sort_profile_summary_v1.json"

def txt(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def first_col(df, names):
    lower = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None

def num(x):
    s = txt(x)
    s = re.sub(r"[^0-9.\-]", "", s)
    if not s:
        return None
    try:
        return float(s)
    except:
        return None

def canon_track(x):
    return re.sub(r"[^A-Z0-9]", "", txt(x).upper())

def canon_horse(x):
    s = txt(x).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def finish_pos(v):
    s = txt(v).upper()
    if s in ["", "SCR", "SCRATCHED", "LR", "BD", "FF", "DNF", "F"]:
        return None
    m = re.search(r"\d+", s)
    if not m:
        return None
    return int(m.group(0))

def distance_m(v):
    s = txt(v)
    m = re.search(r"(\d{3,4})", s)
    return int(m.group(1)) if m else None

def distance_bucket(v):
    d = distance_m(v)
    if d is None: return "UNKNOWN"
    if d < 800: return "UNDER_800"
    if d < 1000: return "800-999"
    if d < 1200: return "1000-1199"
    if d < 1400: return "1200-1399"
    if d < 1600: return "1400-1599"
    if d < 1800: return "1600-1799"
    if d < 2000: return "1800-1999"
    if d < 2200: return "2000-2199"
    if d < 2400: return "2200-2399"
    if d < 2800: return "2400-2799"
    return "2800+"

def condition_group(v):
    s = txt(v).upper()
    if "HEAVY" in s: return "HEAVY"
    if "SOFT" in s: return "SOFT"
    if "GOOD" in s: return "GOOD"
    if "FAST" in s or "FIRM" in s: return "FAST"
    if "SYNTH" in s: return "SYNTHETIC"
    return "UNKNOWN"

def rail_bucket(v):
    s = txt(v).upper()
    if not s or s in ["-", "—", "UNKNOWN", "NAN"]:
        return "UNKNOWN"
    if "TRUE" in s:
        return "TRUE"
    m = re.search(r"(\d+(?:\.\d+)?)\s*M", s)
    if m:
        x = float(m.group(1))
        if x <= 3: return "OUT_0_3M"
        if x <= 6: return "OUT_3_6M"
        if x <= 9: return "OUT_6_9M"
        return "OUT_9M_PLUS"
    if "OUT" in s:
        return "OUT_UNKNOWN"
    return re.sub(r"[^A-Z0-9]+", "_", s).strip("_")

def lane_group(v):
    n = num(v)
    if n is None:
        return "UNKNOWN"
    b = int(n)
    if b <= 4:
        return "INSIDE"
    if b <= 8:
        return "MIDDLE"
    return "OUTSIDE"

def safe_pct(n, d):
    return round((n / d) * 100, 2) if d else 0.0

def main():
    if not RESULTS_FILE.exists():
        raise FileNotFoundError(RESULTS_FILE)

    df = pd.read_csv(RESULTS_FILE, dtype=str).fillna("")

    c_date = first_col(df, ["meeting_date", "race_date", "date"])
    c_track = first_col(df, ["track", "meeting", "meeting_name"])
    c_race_no = first_col(df, ["race_no", "raceNo", "race_number"])
    c_horse = first_col(df, ["horseName", "horse", "runner", "runner_name"])
    c_finish = first_col(df, ["finishPosition", "finish_position", "position", "pos"])
    c_barrier = first_col(df, ["barrier", "bar"])
    c_distance = first_col(df, ["distance", "race_distance"])
    c_class = first_col(df, ["raceClass", "race_class", "class"])
    c_condition = first_col(df, ["trackCondition", "track_condition", "condition"])
    c_rail = first_col(df, ["rail", "rail_position", "rail_position_raw", "rail_bucket", "rail_position_bucket"])
    c_jockey = first_col(df, ["jockey", "rider"])
    c_trainer = first_col(df, ["trainer"])
    c_weight = first_col(df, ["weight"])
    c_margin = first_col(df, ["margin"])
    c_sp = first_col(df, ["sp", "SP"])
    c_inrun = first_col(df, ["inRun", "in_run"])
    c_time = first_col(df, ["raceTime", "race_time"])
    c_prize = first_col(df, ["prizemoneyEarned", "prizemoney", "prize"])

    required = [c_date, c_track, c_race_no, c_horse, c_finish, c_distance, c_condition]
    if any(x is None for x in required):
        raise RuntimeError(f"Missing required columns. Columns={list(df.columns)}")

    out = pd.DataFrame()
    out["race_date"] = df[c_date].map(txt)
    out["track"] = df[c_track].map(lambda x: txt(x).upper())
    out["track_key"] = df[c_track].map(canon_track)
    out["race_no"] = df[c_race_no].map(txt)
    out["race_key"] = out["race_date"] + "|" + out["track_key"] + "|R" + out["race_no"]
    out["horse"] = df[c_horse].map(txt)
    out["horse_key"] = df[c_horse].map(canon_horse)
    out["finish_position_raw"] = df[c_finish].map(txt)
    out["finish_position"] = df[c_finish].map(finish_pos)
    out["is_scratched"] = out["finish_position_raw"].str.upper().isin(["SCR", "SCRATCHED"])
    out["is_winner"] = out["finish_position"].eq(1)
    out["is_top3"] = out["finish_position"].isin([1,2,3])
    out["barrier"] = df[c_barrier].map(txt) if c_barrier else ""
    out["barrier_num"] = df[c_barrier].map(num) if c_barrier else None
    out["barrier_lane"] = df[c_barrier].map(lane_group) if c_barrier else "UNKNOWN"
    out["distance"] = df[c_distance].map(txt)
    out["distance_m"] = df[c_distance].map(distance_m)
    out["distance_bucket"] = df[c_distance].map(distance_bucket)
    out["race_class"] = df[c_class].map(txt) if c_class else ""
    out["track_condition"] = df[c_condition].map(txt)
    out["condition_group"] = df[c_condition].map(condition_group)
    out["rail_position"] = df[c_rail].map(txt) if c_rail else ""
    out["rail_bucket"] = df[c_rail].map(rail_bucket) if c_rail else "UNKNOWN"
    out["jockey"] = df[c_jockey].map(txt) if c_jockey else ""
    out["trainer"] = df[c_trainer].map(txt) if c_trainer else ""
    out["weight"] = df[c_weight].map(txt) if c_weight else ""
    out["margin"] = df[c_margin].map(txt) if c_margin else ""
    out["sp"] = df[c_sp].map(txt) if c_sp else ""
    out["in_run"] = df[c_inrun].map(txt) if c_inrun else ""
    out["race_time"] = df[c_time].map(txt) if c_time else ""
    out["prizemoney_earned"] = df[c_prize].map(txt) if c_prize else ""

    out = out.sort_values(
        ["race_date", "track", "race_no", "is_scratched", "finish_position", "barrier_num", "horse"],
        na_position="last"
    ).reset_index(drop=True)

    out.to_csv(OUT_CLEAN, index=False)

    valid = out[out["finish_position"].notna()].copy()
    winners = valid[valid["is_winner"]].copy()

    race_rows = []
    for race_key, g in out.groupby("race_key", dropna=False):
        valid_g = g[g["finish_position"].notna()]
        winner_g = valid_g[valid_g["is_winner"]]
        w = winner_g.iloc[0] if len(winner_g) else None

        race_rows.append({
            "race_date": g["race_date"].iloc[0],
            "track": g["track"].iloc[0],
            "track_key": g["track_key"].iloc[0],
            "race_no": g["race_no"].iloc[0],
            "race_key": race_key,
            "distance": g["distance"].iloc[0],
            "distance_m": g["distance_m"].iloc[0],
            "distance_bucket": g["distance_bucket"].iloc[0],
            "race_class": g["race_class"].iloc[0],
            "track_condition": g["track_condition"].iloc[0],
            "condition_group": g["condition_group"].iloc[0],
            "rail_position": g["rail_position"].iloc[0],
            "rail_bucket": g["rail_bucket"].iloc[0],
            "field_size_total": len(g),
            "field_size_valid": len(valid_g),
            "scratched_count": int(g["is_scratched"].sum()),
            "winner": "" if w is None else w["horse"],
            "winner_barrier": "" if w is None else w["barrier"],
            "winner_barrier_lane": "" if w is None else w["barrier_lane"],
            "winner_jockey": "" if w is None else w["jockey"],
            "winner_trainer": "" if w is None else w["trainer"],
            "winner_sp": "" if w is None else w["sp"],
        })

    races = pd.DataFrame(race_rows).sort_values(["race_date", "track", "race_no"])
    races.to_csv(OUT_RACES, index=False)

    winners_out = winners[[
        "race_date", "track", "track_key", "race_no", "race_key", "distance", "distance_m",
        "distance_bucket", "race_class", "track_condition", "condition_group", "rail_position",
        "rail_bucket", "horse", "horse_key", "barrier", "barrier_num", "barrier_lane",
        "jockey", "trainer", "sp", "in_run", "race_time"
    ]].rename(columns={"horse": "winner", "horse_key": "winner_key"})

    winners_out = winners_out.sort_values(["track", "distance_m", "condition_group", "rail_bucket", "race_date", "race_no"])
    winners_out.to_csv(OUT_WINNERS, index=False)

    profile_rows = []
    group_cols = ["track", "track_key", "distance_bucket", "condition_group", "rail_bucket"]

    for keys, g in valid.groupby(group_cols, dropna=False):
        track, track_key, db, cond, rail = keys
        wg = g[g["is_winner"]]
        race_count = g["race_key"].nunique()
        runner_count = len(g)
        winner_count = len(wg)

        row = {
            "track": track,
            "track_key": track_key,
            "distance_bucket": db,
            "condition_group": cond,
            "rail_bucket": rail,
            "sample_races": race_count,
            "sample_runners": runner_count,
            "winner_count": winner_count,
            "inside_winners": int((wg["barrier_lane"] == "INSIDE").sum()),
            "middle_winners": int((wg["barrier_lane"] == "MIDDLE").sum()),
            "outside_winners": int((wg["barrier_lane"] == "OUTSIDE").sum()),
            "unknown_lane_winners": int((wg["barrier_lane"] == "UNKNOWN").sum()),
            "inside_winner_share": safe_pct((wg["barrier_lane"] == "INSIDE").sum(), winner_count),
            "middle_winner_share": safe_pct((wg["barrier_lane"] == "MIDDLE").sum(), winner_count),
            "outside_winner_share": safe_pct((wg["barrier_lane"] == "OUTSIDE").sum(), winner_count),
            "avg_winner_barrier": round(wg["barrier_num"].dropna().mean(), 2) if len(wg["barrier_num"].dropna()) else "",
            "median_winner_barrier": round(wg["barrier_num"].dropna().median(), 2) if len(wg["barrier_num"].dropna()) else "",
        }

        shares = {
            "INSIDE": row["inside_winner_share"],
            "MIDDLE": row["middle_winner_share"],
            "OUTSIDE": row["outside_winner_share"],
        }
        row["dominant_winner_lane"] = max(shares, key=shares.get) if winner_count else "UNKNOWN"

        if race_count >= 100:
            conf = "HIGH"
        elif race_count >= 25:
            conf = "MEDIUM"
        else:
            conf = "LOW"
        row["profile_confidence"] = conf

        profile_rows.append(row)

    profile = pd.DataFrame(profile_rows).sort_values(
        ["track", "distance_bucket", "condition_group", "rail_bucket"]
    )
    profile.to_csv(OUT_TRACK_PROFILE, index=False)

    barrier_rows = []
    for keys, g in valid.groupby(["track", "track_key", "distance_bucket", "condition_group", "rail_bucket", "barrier_lane"], dropna=False):
        track, track_key, db, cond, rail, lane = keys
        wg = g[g["is_winner"]]
        barrier_rows.append({
            "track": track,
            "track_key": track_key,
            "distance_bucket": db,
            "condition_group": cond,
            "rail_bucket": rail,
            "barrier_lane": lane,
            "runners": len(g),
            "winners": len(wg),
            "win_rate": safe_pct(len(wg), len(g)),
        })

    barrier_profile = pd.DataFrame(barrier_rows).sort_values(
        ["track", "distance_bucket", "condition_group", "rail_bucket", "barrier_lane"]
    )
    barrier_profile.to_csv(OUT_BARRIER_PROFILE, index=False)

    summary_rows = [
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "source", "value": RESULTS_FILE.name},
        {"metric": "source_rows", "value": len(df)},
        {"metric": "sorted_rows", "value": len(out)},
        {"metric": "valid_finish_rows", "value": len(valid)},
        {"metric": "winner_rows", "value": len(winners_out)},
        {"metric": "race_rows", "value": len(races)},
        {"metric": "track_profile_rows", "value": len(profile)},
        {"metric": "barrier_profile_rows", "value": len(barrier_profile)},
        {"metric": "min_date", "value": out["race_date"].min()},
        {"metric": "max_date", "value": out["race_date"].max()},
        {"metric": "tracks", "value": out["track"].nunique()},
        {"metric": "rail_known_rows", "value": int((out["rail_bucket"] != "UNKNOWN").sum())},
        {"metric": "rail_unknown_rows", "value": int((out["rail_bucket"] == "UNKNOWN").sum())},
        {"metric": "columns_detected", "value": json.dumps({
            "date": c_date, "track": c_track, "race_no": c_race_no, "horse": c_horse,
            "finish": c_finish, "distance": c_distance, "class": c_class,
            "condition": c_condition, "rail": c_rail, "barrier": c_barrier,
            "jockey": c_jockey, "trainer": c_trainer, "sp": c_sp, "in_run": c_inrun
        })},
    ]

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT_SUMMARY, index=False)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({r["metric"]: r["value"] for r in summary_rows}, f, indent=2)

    print("[RESULTS_SORT_PROFILE_V1] COMPLETE")
    print(f"source_rows={len(df)}")
    print(f"valid_finish_rows={len(valid)}")
    print(f"race_rows={len(races)}")
    print(f"winner_rows={len(winners_out)}")
    print(f"profile_rows={len(profile)}")
    print(f"rail_known_rows={int((out['rail_bucket'] != 'UNKNOWN').sum())}")
    print(f"wrote={OUT_CLEAN}")
    print(f"wrote={OUT_RACES}")
    print(f"wrote={OUT_WINNERS}")
    print(f"wrote={OUT_TRACK_PROFILE}")
    print(f"wrote={OUT_BARRIER_PROFILE}")

if __name__ == "__main__":
    main()
