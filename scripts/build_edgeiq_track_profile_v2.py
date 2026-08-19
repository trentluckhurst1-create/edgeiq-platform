import re
import json
import pandas as pd
from pathlib import Path

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

RESULTS_FILE = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"

SIDE_CAR_CANDIDATES = [
    DATA / "edgeiq_real_speed_map_positions.csv",
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "edgeiq_live_v8_candidate_display_feed_v1.csv",
    DATA / "edgeiq_live_race_reliability_v1_feed.csv",
    DATA / "edgeiq_race_intelligence_cards_v1.csv",
]

OUT_FILE = DATA / "edgeiq_track_profile_v2.csv"
SUMMARY_FILE = DATA / "edgeiq_track_profile_v2_summary.csv"
WINNER_ORIGIN_FILE = DATA / "edgeiq_track_profile_winner_origin_v2.csv"
AUDIT_FILE = DATA / "edgeiq_track_profile_v2_join_audit.csv"
JSON_FILE = DATA / "edgeiq_track_profile_v2.json"

def txt(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def canon_track(x):
    return re.sub(r"[^A-Z0-9]", "", txt(x).upper())

def canon_horse(x):
    s = txt(x).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    s = re.sub(r"(NZ|GB|IRE|FR|USA|JPN|AUS)$", "", s)
    return s

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

def finish_pos(v):
    s = txt(v).upper()
    if s in ["SCR", "SCRATCHED", "LR", "BD", "FF", "DNF", ""]:
        return None
    m = re.search(r"\d+", s)
    if not m:
        return None
    return int(m.group(0))

def distance_bucket(v):
    s = txt(v)
    m = re.search(r"(\d{3,4})", s)
    if not m:
        return "UNKNOWN"
    d = int(m.group(1))
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
    if not s or s in ["-", "—", "NAN", "NONE", "UNKNOWN"]:
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
    return s.replace(" ", "_")

def run_style(v):
    s = txt(v).upper().replace("_", " ")
    if not s:
        return "UNKNOWN"
    if "LEADER" in s:
        return "LEADER"
    if "ON PACE" in s or "ONPACE" in s:
        return "ONPACE"
    if "OFF PACE" in s:
        return "MIDFIELD"
    if "MID" in s:
        return "MIDFIELD"
    if "BACK" in s:
        return "BACKMARKER"
    if s in ["PACE", "PROMINENT"]:
        return "ONPACE"
    return "UNKNOWN"

def lane_group_from_barrier(v):
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
    if d <= 0:
        return 0.0
    return round((n / d) * 100, 2)

def confidence(sample):
    if sample >= 100:
        return "HIGH"
    if sample >= 25:
        return "MEDIUM"
    return "LOW"

def label_from_row(row):
    candidates = [
        ("LEADER_FRIENDLY", row.get("leader_win_bias", 0)),
        ("ONPACE_FRIENDLY", row.get("onpace_win_bias", 0)),
        ("MIDFIELD_FRIENDLY", row.get("midfield_win_bias", 0)),
        ("BACKMARKER_FRIENDLY", row.get("backmarker_win_bias", 0)),
        ("INSIDE_BIAS", row.get("inside_win_bias", 0)),
        ("MIDDLE_BIAS", row.get("middle_win_bias", 0)),
        ("OUTSIDE_BIAS", row.get("outside_win_bias", 0)),
    ]
    strong = [name for name, val in candidates if val >= 8]
    if strong:
        return "+".join(strong[:2])
    negative = [name.replace("_FRIENDLY", "_PENALTY").replace("_BIAS", "_PENALTY") for name, val in candidates if val <= -8]
    if negative:
        return negative[0]
    return "FAIR"

def prep_common(df, source_name):
    out = df.copy()

    c_track = first_col(out, ["track", "meeting", "meeting_name", "join_track"])
    c_race_no = first_col(out, ["race_no", "raceNo", "race_number", "join_race_no"])
    c_date = first_col(out, ["race_date", "meeting_date", "date"])
    c_horse = first_col(out, ["horse", "horseName", "runner", "runner_name", "horse_canon", "join_horse"])
    c_rail = first_col(out, [
        "rail", "rail_position", "rail_position_raw", "rail_position_v1",
        "rail_bucket", "rail_bucket_v8", "rail_bucket_live", "rail_position_bucket"
    ])
    c_style = first_col(out, [
        "settling_band", "speed_map_bucket", "run_style", "pace_profile",
        "tactical_dna_style", "speed_map_band", "projected_settling_band"
    ])
    c_barrier = first_col(out, ["barrier", "bar", "barrier_bucket_v8"])

    if c_track: out["_track_key"] = out[c_track].map(canon_track)
    else: out["_track_key"] = ""

    if c_race_no: out["_race_no"] = out[c_race_no].map(txt)
    else: out["_race_no"] = ""

    if c_date: out["_race_date"] = out[c_date].map(txt)
    else: out["_race_date"] = ""

    if c_horse: out["_horse_key"] = out[c_horse].map(canon_horse)
    else: out["_horse_key"] = ""

    if c_rail: out["_rail_bucket"] = out[c_rail].map(rail_bucket)
    else: out["_rail_bucket"] = "UNKNOWN"

    if c_style: out["_run_style"] = out[c_style].map(run_style)
    else: out["_run_style"] = "UNKNOWN"

    if c_barrier: out["_lane_group"] = out[c_barrier].map(lane_group_from_barrier)
    else: out["_lane_group"] = "UNKNOWN"

    out["_source_name"] = source_name

    return out, {
        "source": source_name,
        "rows": len(out),
        "track_col": c_track or "",
        "race_no_col": c_race_no or "",
        "date_col": c_date or "",
        "horse_col": c_horse or "",
        "rail_col": c_rail or "",
        "style_col": c_style or "",
        "barrier_col": c_barrier or "",
        "rail_known_rows": int((out["_rail_bucket"] != "UNKNOWN").sum()),
        "style_known_rows": int((out["_run_style"] != "UNKNOWN").sum()),
        "lane_known_rows": int((out["_lane_group"] != "UNKNOWN").sum()),
    }

def main():
    if not RESULTS_FILE.exists():
        raise FileNotFoundError(RESULTS_FILE)

    res = pd.read_csv(RESULTS_FILE, dtype=str).fillna("")
    res_raw_cols = list(res.columns)

    res_track = first_col(res, ["track", "meeting", "meeting_name"])
    res_race_no = first_col(res, ["race_no", "raceNo", "race_number"])
    res_date = first_col(res, ["meeting_date", "race_date", "date"])
    res_horse = first_col(res, ["horseName", "horse", "runner", "runner_name"])
    res_finish = first_col(res, ["finishPosition", "finish_position", "position", "pos"])
    res_distance = first_col(res, ["distance", "race_distance"])
    res_condition = first_col(res, ["trackCondition", "track_condition", "condition"])
    res_barrier = first_col(res, ["barrier", "bar"])
    res_rail = first_col(res, ["rail", "rail_position", "rail_position_raw", "rail_bucket", "rail_position_bucket"])

    required = [res_track, res_race_no, res_horse, res_finish, res_distance, res_condition]
    if any(c is None for c in required):
        raise RuntimeError(f"Missing required results columns. columns={res_raw_cols}")

    res["_track_key"] = res[res_track].map(canon_track)
    res["_track_name"] = res[res_track].map(lambda x: txt(x).upper())
    res["_race_no"] = res[res_race_no].map(txt)
    res["_race_date"] = res[res_date].map(txt) if res_date else ""
    res["_horse_key"] = res[res_horse].map(canon_horse)
    res["_finish_pos"] = res[res_finish].map(finish_pos)
    res["_is_win"] = res["_finish_pos"].eq(1)
    res["_is_top3"] = res["_finish_pos"].isin([1,2,3])
    res["_distance_bucket"] = res[res_distance].map(distance_bucket)
    res["_condition_group"] = res[res_condition].map(condition_group)
    res["_lane_group_result"] = res[res_barrier].map(lane_group_from_barrier) if res_barrier else "UNKNOWN"
    res["_rail_bucket_result"] = res[res_rail].map(rail_bucket) if res_rail else "UNKNOWN"

    sidecars = []
    audits = []

    for p in SIDE_CAR_CANDIDATES:
        if not p.exists():
            audits.append({"source": p.name, "rows": 0, "status": "MISSING"})
            continue
        df = pd.read_csv(p, dtype=str).fillna("")
        prepped, audit = prep_common(df, p.name)
        audit["status"] = "LOADED"
        audits.append(audit)
        sidecars.append(prepped)

    if sidecars:
        side = pd.concat(sidecars, ignore_index=True)
    else:
        side = pd.DataFrame(columns=["_track_key", "_race_no", "_race_date", "_horse_key", "_rail_bucket", "_run_style", "_lane_group", "_source_name"])

    runner_side = side[
        side["_track_key"].ne("") &
        side["_race_no"].ne("") &
        side["_horse_key"].ne("")
    ].copy()

    race_side = side[
        side["_track_key"].ne("") &
        side["_race_no"].ne("")
    ].copy()

    runner_side = runner_side.sort_values(
        by=["_run_style", "_lane_group", "_rail_bucket"],
        key=lambda col: col.ne("UNKNOWN").astype(int),
        ascending=False
    ).drop_duplicates(["_race_date", "_track_key", "_race_no", "_horse_key"], keep="first")

    race_side = race_side.sort_values(
        by=["_rail_bucket"],
        key=lambda col: col.ne("UNKNOWN").astype(int),
        ascending=False
    ).drop_duplicates(["_race_date", "_track_key", "_race_no"], keep="first")

    join_cols_runner = ["_race_date", "_track_key", "_race_no", "_horse_key"] if res_date else ["_track_key", "_race_no", "_horse_key"]
    join_cols_race = ["_race_date", "_track_key", "_race_no"] if res_date else ["_track_key", "_race_no"]

    merged = res.merge(
        runner_side[join_cols_runner + ["_run_style", "_lane_group", "_rail_bucket", "_source_name"]],
        on=join_cols_runner,
        how="left"
    )

    merged = merged.merge(
        race_side[join_cols_race + ["_rail_bucket"]].rename(columns={"_rail_bucket": "_rail_bucket_race_side"}),
        on=join_cols_race,
        how="left"
    )

    merged["_run_style"] = merged["_run_style"].fillna("UNKNOWN")
    merged["_lane_group"] = merged["_lane_group"].fillna("UNKNOWN")
    merged["_rail_bucket"] = merged["_rail_bucket"].fillna("UNKNOWN")
    merged["_rail_bucket_race_side"] = merged["_rail_bucket_race_side"].fillna("UNKNOWN")

    merged.loc[merged["_lane_group"].eq("UNKNOWN"), "_lane_group"] = merged["_lane_group_result"]
    merged["_rail_final"] = merged["_rail_bucket_result"]
    merged.loc[merged["_rail_final"].eq("UNKNOWN"), "_rail_final"] = merged["_rail_bucket"]
    merged.loc[merged["_rail_final"].eq("UNKNOWN"), "_rail_final"] = merged["_rail_bucket_race_side"]
    merged.loc[merged["_rail_final"].eq(""), "_rail_final"] = "UNKNOWN"

    valid = merged[
        merged["_finish_pos"].notna() &
        merged["_distance_bucket"].ne("UNKNOWN") &
        merged["_condition_group"].ne("UNKNOWN")
    ].copy()

    profile_rows = []
    winner_rows = []

    group_sets = [
        ("TRACK_DISTANCE_CONDITION_RAIL", ["_track_key", "_track_name", "_distance_bucket", "_condition_group", "_rail_final"]),
        ("TRACK_DISTANCE_CONDITION_ANY_RAIL", ["_track_key", "_track_name", "_distance_bucket", "_condition_group"]),
    ]

    for profile_level, group_cols in group_sets:
        for keys, g in valid.groupby(group_cols, dropna=False):
            if profile_level == "TRACK_DISTANCE_CONDITION_RAIL":
                track_key, track_name, dist_bucket, cond, rail = keys
            else:
                track_key, track_name, dist_bucket, cond = keys
                rail = "ANY"

            sample = len(g)
            if sample < 5:
                continue

            races = g[["_race_date", "_track_key", "_race_no"]].drop_duplicates().shape[0]
            winners = g[g["_is_win"]].copy()
            winner_count = len(winners)
            field_win_rate = safe_pct(winner_count, sample)

            row = {
                "profile_level": profile_level,
                "track": track_name,
                "track_key": track_key,
                "distance_bucket": dist_bucket,
                "condition_group": cond,
                "rail_bucket": rail,
                "sample_runners": sample,
                "sample_races": races,
                "winner_count": winner_count,
                "field_win_rate": field_win_rate,
                "track_profile_confidence": confidence(races),
            }

            for style in ["LEADER", "ONPACE", "MIDFIELD", "BACKMARKER", "UNKNOWN"]:
                all_s = g[g["_run_style"].eq(style)]
                win_s = winners[winners["_run_style"].eq(style)]
                row[f"{style.lower()}_runners"] = len(all_s)
                row[f"{style.lower()}_winners"] = len(win_s)
                row[f"{style.lower()}_winner_share"] = safe_pct(len(win_s), winner_count)
                row[f"{style.lower()}_runner_share"] = safe_pct(len(all_s), sample)
                row[f"{style.lower()}_win_rate"] = safe_pct(len(win_s), len(all_s))
                row[f"{style.lower()}_win_bias"] = round(row[f"{style.lower()}_win_rate"] - field_win_rate, 2)

            for lane in ["INSIDE", "MIDDLE", "OUTSIDE", "UNKNOWN"]:
                all_l = g[g["_lane_group"].eq(lane)]
                win_l = winners[winners["_lane_group"].eq(lane)]
                row[f"{lane.lower()}_runners"] = len(all_l)
                row[f"{lane.lower()}_winners"] = len(win_l)
                row[f"{lane.lower()}_winner_share"] = safe_pct(len(win_l), winner_count)
                row[f"{lane.lower()}_runner_share"] = safe_pct(len(all_l), sample)
                row[f"{lane.lower()}_win_rate"] = safe_pct(len(win_l), len(all_l))
                row[f"{lane.lower()}_win_bias"] = round(row[f"{lane.lower()}_win_rate"] - field_win_rate, 2)

            row["dominant_winner_run_style"] = max(
                ["LEADER", "ONPACE", "MIDFIELD", "BACKMARKER", "UNKNOWN"],
                key=lambda s: row[f"{s.lower()}_winner_share"]
            )

            row["dominant_winner_lane"] = max(
                ["INSIDE", "MIDDLE", "OUTSIDE", "UNKNOWN"],
                key=lambda s: row[f"{s.lower()}_winner_share"]
            )

            row["track_profile_label"] = label_from_row(row)

            profile_rows.append(row)

            for _, w in winners.iterrows():
                winner_rows.append({
                    "profile_level": profile_level,
                    "track": track_name,
                    "track_key": track_key,
                    "distance_bucket": dist_bucket,
                    "condition_group": cond,
                    "rail_bucket": rail,
                    "race_date": w["_race_date"],
                    "race_no": w["_race_no"],
                    "winner": txt(w[res_horse]),
                    "winner_run_style": w["_run_style"],
                    "winner_lane": w["_lane_group"],
                    "barrier": txt(w[res_barrier]) if res_barrier else "",
                    "finish_position": int(w["_finish_pos"]),
                })

    out = pd.DataFrame(profile_rows)
    winners_out = pd.DataFrame(winner_rows)

    if out.empty:
        out = pd.DataFrame([{
            "profile_level": "NONE",
            "track": "",
            "track_key": "",
            "distance_bucket": "",
            "condition_group": "",
            "rail_bucket": "",
            "sample_runners": 0,
            "sample_races": 0,
            "winner_count": 0,
            "track_profile_confidence": "LOW",
            "track_profile_label": "NO_PROFILE",
        }])

    out = out.sort_values(["track", "distance_bucket", "condition_group", "rail_bucket", "profile_level"]).reset_index(drop=True)
    out.to_csv(OUT_FILE, index=False)

    if winners_out.empty:
        winners_out = pd.DataFrame(columns=[
            "profile_level", "track", "track_key", "distance_bucket", "condition_group", "rail_bucket",
            "race_date", "race_no", "winner", "winner_run_style", "winner_lane", "barrier", "finish_position"
        ])
    winners_out.to_csv(WINNER_ORIGIN_FILE, index=False)

    audit_df = pd.DataFrame(audits)
    audit_df.to_csv(AUDIT_FILE, index=False)

    summary_rows = [
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "results_file", "value": RESULTS_FILE.name},
        {"metric": "results_rows", "value": len(res)},
        {"metric": "valid_rows", "value": len(valid)},
        {"metric": "profile_rows", "value": len(out)},
        {"metric": "winner_origin_rows", "value": len(winners_out)},
        {"metric": "rail_known_rows", "value": int(valid["_rail_final"].ne("UNKNOWN").sum())},
        {"metric": "run_style_known_rows", "value": int(valid["_run_style"].ne("UNKNOWN").sum())},
        {"metric": "lane_known_rows", "value": int(valid["_lane_group"].ne("UNKNOWN").sum())},
        {"metric": "profiles_exact_rail", "value": int(out["profile_level"].eq("TRACK_DISTANCE_CONDITION_RAIL").sum()) if "profile_level" in out.columns else 0},
        {"metric": "profiles_any_rail", "value": int(out["profile_level"].eq("TRACK_DISTANCE_CONDITION_ANY_RAIL").sum()) if "profile_level" in out.columns else 0},
        {"metric": "high_confidence_profiles", "value": int(out["track_profile_confidence"].eq("HIGH").sum()) if "track_profile_confidence" in out.columns else 0},
        {"metric": "medium_confidence_profiles", "value": int(out["track_profile_confidence"].eq("MEDIUM").sum()) if "track_profile_confidence" in out.columns else 0},
        {"metric": "low_confidence_profiles", "value": int(out["track_profile_confidence"].eq("LOW").sum()) if "track_profile_confidence" in out.columns else 0},
    ]

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(SUMMARY_FILE, index=False)

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump({r["metric"]: r["value"] for r in summary_rows}, f, indent=2)

    print("[TRACK_PROFILE_V2] COMPLETE")
    print(f"results_rows={len(res)}")
    print(f"valid_rows={len(valid)}")
    print(f"profile_rows={len(out)}")
    print(f"winner_origin_rows={len(winners_out)}")
    print(f"rail_known_rows={int(valid['_rail_final'].ne('UNKNOWN').sum())}")
    print(f"run_style_known_rows={int(valid['_run_style'].ne('UNKNOWN').sum())}")
    print(f"wrote={OUT_FILE}")
    print(f"wrote={WINNER_ORIGIN_FILE}")
    print(f"wrote={AUDIT_FILE}")

if __name__ == "__main__":
    main()
