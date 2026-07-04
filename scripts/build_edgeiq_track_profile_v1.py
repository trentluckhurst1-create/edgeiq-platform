import os
import re
import math
import json
import pandas as pd
from pathlib import Path

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

RESULTS_FILE = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"
SPEED_FILE_CANDIDATES = [
    DATA / "edgeiq_real_speed_map_positions.csv",
    DATA / "edgeiq_live_real_speed_map_positions.csv",
    DATA / "edgeiq_tactical_dna_v1.csv",
]

OUT_FILE = DATA / "edgeiq_track_profile_v1.csv"
SUMMARY_FILE = DATA / "edgeiq_track_profile_v1_summary.csv"
JSON_FILE = DATA / "edgeiq_track_profile_v1.json"

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

def run_style(v):
    s = txt(v).upper().replace("_", " ")
    if "LEADER" in s: return "LEADER"
    if "ON PACE" in s or "ONPACE" in s or "PACE" == s: return "ONPACE"
    if "BACK" in s: return "BACKMARKER"
    if "MID" in s: return "MIDFIELD"
    if "OFF PACE" in s: return "MIDFIELD"
    return "UNKNOWN"

def lane_group(v):
    try:
        b = int(float(txt(v)))
    except:
        return "UNKNOWN"
    if b <= 4: return "INSIDE"
    if b <= 8: return "MIDDLE"
    return "OUTSIDE"

def finish_pos(v):
    s = txt(v).upper()
    if s in ["SCR", "SCRATCHED", "LR", "BD", "FF", "DNF"]:
        return None
    m = re.search(r"\d+", s)
    if not m:
        return None
    return int(m.group(0))

def safe_pct(n, d):
    if d <= 0:
        return 0.0
    return round((n / d) * 100, 2)

def confidence(sample):
    if sample >= 100: return "HIGH"
    if sample >= 25: return "MEDIUM"
    return "LOW"

def label_from_bias(row):
    labels = []
    if row["leader_bias"] >= 8: labels.append("LEADER_FRIENDLY")
    if row["onpace_bias"] >= 8: labels.append("ONPACE_FRIENDLY")
    if row["backmarker_bias"] >= 8: labels.append("BACKMARKER_FRIENDLY")
    if row["inside_bias"] >= 8: labels.append("INSIDE_BIAS")
    if row["outside_bias"] >= 8: labels.append("OUTSIDE_BIAS")
    if not labels:
        return "FAIR"
    return "+".join(labels[:2])

def main():
    if not RESULTS_FILE.exists():
        raise FileNotFoundError(f"Missing {RESULTS_FILE}")

    speed_file = next((p for p in SPEED_FILE_CANDIDATES if p.exists()), None)
    if speed_file is None:
        raise FileNotFoundError("No speed map / tactical DNA source found.")

    res = pd.read_csv(RESULTS_FILE, dtype=str).fillna("")
    spd = pd.read_csv(speed_file, dtype=str).fillna("")

    res_track = first_col(res, ["track", "meeting", "meeting_name"])
    res_race_no = first_col(res, ["race_no", "raceNo", "race_number"])
    res_date = first_col(res, ["meeting_date", "race_date", "date"])
    res_horse = first_col(res, ["horseName", "horse", "runner", "runner_name"])
    res_finish = first_col(res, ["finishPosition", "finish_position", "position", "pos"])
    res_distance = first_col(res, ["distance", "race_distance"])
    res_condition = first_col(res, ["trackCondition", "track_condition", "condition"])
    res_barrier = first_col(res, ["barrier", "bar"])

    spd_track = first_col(spd, ["track", "meeting", "meeting_name"])
    spd_race_no = first_col(spd, ["race_no", "raceNo", "race_number"])
    spd_date = first_col(spd, ["race_date", "meeting_date", "date"])
    spd_horse = first_col(spd, ["horse", "horseName", "runner", "runner_name", "horse_canon"])
    spd_style = first_col(spd, ["settling_band", "speed_map_bucket", "run_style", "pace_profile", "tactical_dna_style"])
    spd_barrier = first_col(spd, ["barrier", "bar", "barrier_bucket_v8"])

    required = [res_track, res_race_no, res_horse, res_finish, res_distance, res_condition]
    if any(c is None for c in required):
        raise RuntimeError(f"Results file missing required columns. Columns={list(res.columns)}")

    if any(c is None for c in [spd_track, spd_race_no, spd_horse, spd_style]):
        raise RuntimeError(f"Speed file missing required columns. source={speed_file.name} columns={list(spd.columns)}")

    res["_track_key"] = res[res_track].map(canon_track)
    res["_race_no"] = res[res_race_no].map(txt)
    res["_horse_key"] = res[res_horse].map(canon_horse)
    res["_race_date"] = res[res_date].map(txt) if res_date else ""
    res["_finish_pos"] = res[res_finish].map(finish_pos)
    res["_is_win"] = res["_finish_pos"].eq(1)
    res["_is_top3"] = res["_finish_pos"].isin([1,2,3])
    res["_distance_bucket"] = res[res_distance].map(distance_bucket)
    res["_condition_group"] = res[res_condition].map(condition_group)
    res["_lane_group_res"] = res[res_barrier].map(lane_group) if res_barrier else "UNKNOWN"

    spd["_track_key"] = spd[spd_track].map(canon_track)
    spd["_race_no"] = spd[spd_race_no].map(txt)
    spd["_horse_key"] = spd[spd_horse].map(canon_horse)
    spd["_race_date"] = spd[spd_date].map(txt) if spd_date else ""
    spd["_run_style"] = spd[spd_style].map(run_style)
    spd["_lane_group_spd"] = spd[spd_barrier].map(lane_group) if spd_barrier else "UNKNOWN"

    join_cols = ["_track_key", "_race_no", "_horse_key"]
    if res_date and spd_date:
        join_cols = ["_race_date"] + join_cols

    merged = res.merge(
        spd[join_cols + ["_run_style", "_lane_group_spd"]].drop_duplicates(join_cols),
        on=join_cols,
        how="left"
    )

    merged["_lane_group"] = merged["_lane_group_spd"]
    merged.loc[merged["_lane_group"].eq("UNKNOWN") | merged["_lane_group"].eq(""), "_lane_group"] = merged["_lane_group_res"]

    valid = merged[
        merged["_finish_pos"].notna() &
        merged["_distance_bucket"].ne("UNKNOWN") &
        merged["_condition_group"].ne("UNKNOWN")
    ].copy()

    base_win = valid["_is_win"].mean() * 100 if len(valid) else 0
    base_top3 = valid["_is_top3"].mean() * 100 if len(valid) else 0

    out_rows = []

    group_cols = ["_track_key", res_track, "_distance_bucket", "_condition_group"]

    for keys, g in valid.groupby(group_cols, dropna=False):
        track_key, track_name, dist_bucket, cond = keys
        sample = len(g)
        if sample < 5:
            continue

        style_stats = {}
        for style in ["LEADER", "ONPACE", "MIDFIELD", "BACKMARKER"]:
            sg = g[g["_run_style"].eq(style)]
            style_stats[style] = {
                "runners": len(sg),
                "win_pct": safe_pct(sg["_is_win"].sum(), len(sg)),
                "top3_pct": safe_pct(sg["_is_top3"].sum(), len(sg)),
                "bias": round(safe_pct(sg["_is_win"].sum(), len(sg)) - base_win, 2) if len(sg) else 0.0,
            }

        lane_stats = {}
        for lane in ["INSIDE", "MIDDLE", "OUTSIDE"]:
            lg = g[g["_lane_group"].eq(lane)]
            lane_stats[lane] = {
                "runners": len(lg),
                "win_pct": safe_pct(lg["_is_win"].sum(), len(lg)),
                "top3_pct": safe_pct(lg["_is_top3"].sum(), len(lg)),
                "bias": round(safe_pct(lg["_is_win"].sum(), len(lg)) - base_win, 2) if len(lg) else 0.0,
            }

        row = {
            "track": txt(track_name).upper(),
            "track_key": track_key,
            "distance_bucket": dist_bucket,
            "condition_group": cond,
            "sample_size": sample,
            "baseline_win_pct": round(base_win, 2),
            "baseline_top3_pct": round(base_top3, 2),

            "leader_runners": style_stats["LEADER"]["runners"],
            "leader_win_pct": style_stats["LEADER"]["win_pct"],
            "leader_top3_pct": style_stats["LEADER"]["top3_pct"],
            "leader_bias": style_stats["LEADER"]["bias"],

            "onpace_runners": style_stats["ONPACE"]["runners"],
            "onpace_win_pct": style_stats["ONPACE"]["win_pct"],
            "onpace_top3_pct": style_stats["ONPACE"]["top3_pct"],
            "onpace_bias": style_stats["ONPACE"]["bias"],

            "midfield_runners": style_stats["MIDFIELD"]["runners"],
            "midfield_win_pct": style_stats["MIDFIELD"]["win_pct"],
            "midfield_top3_pct": style_stats["MIDFIELD"]["top3_pct"],
            "midfield_bias": style_stats["MIDFIELD"]["bias"],

            "backmarker_runners": style_stats["BACKMARKER"]["runners"],
            "backmarker_win_pct": style_stats["BACKMARKER"]["win_pct"],
            "backmarker_top3_pct": style_stats["BACKMARKER"]["top3_pct"],
            "backmarker_bias": style_stats["BACKMARKER"]["bias"],

            "inside_runners": lane_stats["INSIDE"]["runners"],
            "inside_win_pct": lane_stats["INSIDE"]["win_pct"],
            "inside_top3_pct": lane_stats["INSIDE"]["top3_pct"],
            "inside_bias": lane_stats["INSIDE"]["bias"],

            "middle_runners": lane_stats["MIDDLE"]["runners"],
            "middle_win_pct": lane_stats["MIDDLE"]["win_pct"],
            "middle_top3_pct": lane_stats["MIDDLE"]["top3_pct"],
            "middle_bias": lane_stats["MIDDLE"]["bias"],

            "outside_runners": lane_stats["OUTSIDE"]["runners"],
            "outside_win_pct": lane_stats["OUTSIDE"]["win_pct"],
            "outside_top3_pct": lane_stats["OUTSIDE"]["top3_pct"],
            "outside_bias": lane_stats["OUTSIDE"]["bias"],

            "track_profile_confidence": confidence(sample),
        }
        row["track_profile_label"] = label_from_bias(row)
        out_rows.append(row)

    out = pd.DataFrame(out_rows)

    if out.empty:
        out = pd.DataFrame([{
            "track": "",
            "track_key": "",
            "distance_bucket": "",
            "condition_group": "",
            "sample_size": 0,
            "track_profile_confidence": "LOW",
            "track_profile_label": "NO_PROFILE"
        }])

    out = out.sort_values(["track", "distance_bucket", "condition_group"]).reset_index(drop=True)
    out.to_csv(OUT_FILE, index=False)

    summary = pd.DataFrame([
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "results_file", "value": RESULTS_FILE.name},
        {"metric": "speed_file", "value": speed_file.name},
        {"metric": "results_rows", "value": len(res)},
        {"metric": "speed_rows", "value": len(spd)},
        {"metric": "merged_rows", "value": len(merged)},
        {"metric": "matched_run_style_rows", "value": int(merged["_run_style"].ne("").sum())},
        {"metric": "valid_rows", "value": len(valid)},
        {"metric": "profile_rows", "value": len(out)},
        {"metric": "high_confidence_profiles", "value": int(out["track_profile_confidence"].eq("HIGH").sum()) if "track_profile_confidence" in out.columns else 0},
        {"metric": "medium_confidence_profiles", "value": int(out["track_profile_confidence"].eq("MEDIUM").sum()) if "track_profile_confidence" in out.columns else 0},
        {"metric": "low_confidence_profiles", "value": int(out["track_profile_confidence"].eq("LOW").sum()) if "track_profile_confidence" in out.columns else 0},
    ])
    summary.to_csv(SUMMARY_FILE, index=False)

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump({r["metric"]: r["value"] for _, r in summary.iterrows()}, f, indent=2)

    print("[TRACK_PROFILE_V1] COMPLETE")
    print(f"results_rows={len(res)}")
    print(f"speed_rows={len(spd)}")
    print(f"valid_rows={len(valid)}")
    print(f"profile_rows={len(out)}")
    print(f"wrote={OUT_FILE}")

if __name__ == "__main__":
    main()
