import re
import json
import pandas as pd
from pathlib import Path

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SOURCE = DATA / "edgeiq_master_positional_observations_v1.csv"

OUT_RUNNER = DATA / "edgeiq_track_intelligence_runner_profile_v2.csv"
OUT_TRACK_DISTANCE = DATA / "edgeiq_track_intelligence_profile_v2.csv"
OUT_TRACK_DISTANCE_CONDITION = DATA / "edgeiq_track_intelligence_profile_by_condition_v2.csv"
OUT_TRACK = DATA / "edgeiq_track_intelligence_by_track_v2.csv"
OUT_DISTANCE = DATA / "edgeiq_track_intelligence_by_distance_v2.csv"
OUT_SUMMARY = DATA / "edgeiq_track_intelligence_profile_v2_summary.csv"
OUT_JSON = DATA / "edgeiq_track_intelligence_profile_v2.json"

def txt(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

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
    s = re.sub(r"(NZ|GB|IRE|FR|USA|JPN|AUS)$", "", s)
    return s

def first_col(df, names):
    lower = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None

def distance_bucket(v):
    d = num(v)
    if d is None:
        m = re.search(r"(\d{3,4})", txt(v))
        d = float(m.group(1)) if m else None
    if d is None:
        return "UNKNOWN"
    d = int(d)
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

def barrier_lane(barrier, field_size):
    b = num(barrier)
    f = num(field_size)
    if b is None:
        return "UNKNOWN"

    if f is not None and f > 0:
        pct = b / f
        if pct <= 0.33:
            return "INSIDE"
        if pct <= 0.67:
            return "MIDDLE"
        return "OUTSIDE"

    if b <= 4:
        return "INSIDE"
    if b <= 8:
        return "MIDDLE"
    return "OUTSIDE"

def run_style(pos800, field_size):
    p = num(pos800)
    f = num(field_size)
    if p is None:
        return "UNKNOWN"

    if f is not None and f > 0:
        pct = p / f
        if p <= 1:
            return "LEADER"
        if pct <= 0.25:
            return "ON_PACE"
        if pct <= 0.67:
            return "MIDFIELD"
        return "BACKMARKER"

    if p <= 1:
        return "LEADER"
    if p <= 4:
        return "ON_PACE"
    if p <= 8:
        return "MIDFIELD"
    return "BACKMARKER"

def movement_profile(gain):
    g = num(gain)
    if g is None:
        return "UNKNOWN"
    if g >= 3:
        return "BIG_IMPROVER"
    if g >= 1:
        return "IMPROVER"
    if g <= -3:
        return "BIG_FADER"
    if g <= -1:
        return "FADER"
    return "HOLDS_POSITION"

def valid_finish(v):
    x = num(v)
    if x is None:
        return None
    if 1 <= x <= 24:
        return x
    return None

def safe_pct(n, d):
    return round((n / d) * 100, 2) if d else 0.0

def confidence(n):
    if n >= 100:
        return "HIGH"
    if n >= 25:
        return "MEDIUM"
    return "LOW"

def dominant(row, keys):
    vals = {k: float(row.get(k, 0) or 0) for k in keys}
    return max(vals, key=vals.get) if vals else "UNKNOWN"

def label_from_row(row):
    style = row.get("dominant_run_style", "UNKNOWN")
    lane = row.get("dominant_barrier_lane", "UNKNOWN")
    move = row.get("dominant_movement_profile", "UNKNOWN")

    style_share = float(row.get(f"{style.lower()}_winner_share", 0) or 0) if style != "UNKNOWN" else 0
    lane_share = float(row.get(f"{lane.lower()}_winner_share", 0) or 0) if lane != "UNKNOWN" else 0

    labels = []
    if style_share >= 40:
        labels.append(f"{style}_STYLE")
    if lane_share >= 45:
        labels.append(f"{lane}_BARRIER")
    if move in ["IMPROVER", "BIG_IMPROVER"] and float(row.get("improver_winner_share", 0) or 0) >= 35:
        labels.append("IMPROVER_FINISH")
    if move in ["HOLDS_POSITION"] and float(row.get("holds_position_winner_share", 0) or 0) >= 45:
        labels.append("HOLDS_POSITION")

    if not labels:
        return "FAIR_PROFILE"
    return "+".join(labels[:3])

def build_profile(df, group_cols, profile_level):
    rows = []

    for keys, g in df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = dict(zip(group_cols, keys))

        winners = g[g["is_winner"]].copy()
        sample_runs = len(g)
        sample_winners = len(winners)

        row["profile_level"] = profile_level
        row["sample_runs"] = sample_runs
        row["sample_winners"] = sample_winners
        row["winner_rate"] = safe_pct(sample_winners, sample_runs)

        for s in ["LEADER", "ON_PACE", "MIDFIELD", "BACKMARKER", "UNKNOWN"]:
            all_count = int((g["run_style_v2"] == s).sum())
            win_count = int((winners["run_style_v2"] == s).sum())
            key = s.lower()
            row[f"{key}_runs"] = all_count
            row[f"{key}_winners"] = win_count
            row[f"{key}_runner_share"] = safe_pct(all_count, sample_runs)
            row[f"{key}_winner_share"] = safe_pct(win_count, sample_winners)
            row[f"{key}_win_rate"] = safe_pct(win_count, all_count)

        for l in ["INSIDE", "MIDDLE", "OUTSIDE", "UNKNOWN"]:
            all_count = int((g["barrier_lane_v2"] == l).sum())
            win_count = int((winners["barrier_lane_v2"] == l).sum())
            key = l.lower()
            row[f"{key}_runs"] = all_count
            row[f"{key}_winners"] = win_count
            row[f"{key}_runner_share"] = safe_pct(all_count, sample_runs)
            row[f"{key}_winner_share"] = safe_pct(win_count, sample_winners)
            row[f"{key}_win_rate"] = safe_pct(win_count, all_count)

        move_groups = {
            "BIG_IMPROVER": "big_improver",
            "IMPROVER": "improver",
            "HOLDS_POSITION": "holds_position",
            "FADER": "fader",
            "BIG_FADER": "big_fader",
            "UNKNOWN": "unknown_movement",
        }

        for m, key in move_groups.items():
            all_count = int((g["movement_profile_v2"] == m).sum())
            win_count = int((winners["movement_profile_v2"] == m).sum())
            row[f"{key}_runs"] = all_count
            row[f"{key}_winners"] = win_count
            row[f"{key}_runner_share"] = safe_pct(all_count, sample_runs)
            row[f"{key}_winner_share"] = safe_pct(win_count, sample_winners)
            row[f"{key}_win_rate"] = safe_pct(win_count, all_count)

        row["dominant_run_style"] = dominant(row, [
            "leader_winner_share",
            "on_pace_winner_share",
            "midfield_winner_share",
            "backmarker_winner_share",
        ]).replace("_winner_share", "").upper()

        row["dominant_barrier_lane"] = dominant(row, [
            "inside_winner_share",
            "middle_winner_share",
            "outside_winner_share",
        ]).replace("_winner_share", "").upper()

        dom_move_key = dominant(row, [
            "big_improver_winner_share",
            "improver_winner_share",
            "holds_position_winner_share",
            "fader_winner_share",
            "big_fader_winner_share",
        ])
        row["dominant_movement_profile"] = dom_move_key.replace("_winner_share", "").upper()

        b = pd.to_numeric(winners["barrier"], errors="coerce").dropna()
        p8 = pd.to_numeric(winners["pos800"], errors="coerce").dropna()
        p4 = pd.to_numeric(winners["pos400"], errors="coerce").dropna()

        row["avg_winner_barrier"] = round(float(b.mean()), 2) if len(b) else ""
        row["median_winner_barrier"] = round(float(b.median()), 2) if len(b) else ""
        row["avg_winner_pos800"] = round(float(p8.mean()), 2) if len(p8) else ""
        row["median_winner_pos800"] = round(float(p8.median()), 2) if len(p8) else ""
        row["avg_winner_pos400"] = round(float(p4.mean()), 2) if len(p4) else ""
        row["median_winner_pos400"] = round(float(p4.median()), 2) if len(p4) else ""

        row["profile_confidence"] = confidence(sample_winners)
        row["track_intelligence_label_v2"] = label_from_row(row)

        rows.append(row)

    return pd.DataFrame(rows)

def main():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    df = pd.read_csv(SOURCE, dtype=str).fillna("")

    c_horse = first_col(df, ["horse", "horseName", "horse_name", "runner", "runner_name"])
    c_date = first_col(df, ["run_date", "race_date", "meeting_date", "date"])
    c_track = first_col(df, ["track", "meeting", "meeting_name"])
    c_distance = first_col(df, ["distance", "race_distance"])
    c_barrier = first_col(df, ["barrier", "bar"])
    c_field = first_col(df, ["field_size", "runners", "field_size_valid"])
    c_finish = first_col(df, ["finish_pos", "finish_position", "finishPosition"])
    c_pos800 = first_col(df, ["pos800", "avg_800m_position", "position_800", "pos_800"])
    c_pos400 = first_col(df, ["pos400", "avg_400m_position", "position_400", "pos_400"])
    c_gain = first_col(df, ["gain_800_400", "avg_800_to_400_gain"])
    c_raw = first_col(df, ["raw_in_run", "in_run", "inRun"])
    c_speed = first_col(df, ["speed_figure", "avg_speed_figure"])
    c_sectional = first_col(df, ["sectional_figure"])
    c_last600 = first_col(df, ["last600", "last_600"])

    required = [c_horse, c_date, c_track, c_distance, c_barrier, c_field, c_finish, c_pos800, c_pos400]
    if any(c is None for c in required):
        raise RuntimeError({
            "missing": {
                "horse": c_horse,
                "date": c_date,
                "track": c_track,
                "distance": c_distance,
                "barrier": c_barrier,
                "field": c_field,
                "finish": c_finish,
                "pos800": c_pos800,
                "pos400": c_pos400,
            },
            "columns": list(df.columns),
        })

    out = pd.DataFrame()
    out["race_date"] = df[c_date].map(txt)
    out["track"] = df[c_track].map(lambda x: txt(x).upper())
    out["track_key"] = df[c_track].map(canon_track)
    out["horse"] = df[c_horse].map(txt)
    out["horse_key"] = df[c_horse].map(canon_horse)
    out["distance"] = df[c_distance].map(num)
    out["distance_bucket"] = out["distance"].map(distance_bucket)
    out["barrier"] = df[c_barrier].map(num)
    out["field_size"] = df[c_field].map(num)
    out["finish_pos_raw"] = df[c_finish].map(txt)
    out["finish_pos"] = df[c_finish].map(valid_finish)
    out["is_winner"] = out["finish_pos"].eq(1)
    out["pos800"] = df[c_pos800].map(num)
    out["pos400"] = df[c_pos400].map(num)
    out["gain_800_400"] = df[c_gain].map(num) if c_gain else (out["pos800"] - out["pos400"])
    out["raw_in_run"] = df[c_raw].map(txt) if c_raw else ""
    out["speed_figure"] = df[c_speed].map(num) if c_speed else None
    out["sectional_figure"] = df[c_sectional].map(num) if c_sectional else None
    out["last600"] = df[c_last600].map(num) if c_last600 else None
    out["condition_group"] = "UNKNOWN"

    out["barrier_lane_v2"] = out.apply(lambda r: barrier_lane(r["barrier"], r["field_size"]), axis=1)
    out["run_style_v2"] = out.apply(lambda r: run_style(r["pos800"], r["field_size"]), axis=1)
    out["movement_profile_v2"] = out["gain_800_400"].map(movement_profile)

    out["profile_ready_v2"] = (
        out["finish_pos"].notna() &
        out["distance_bucket"].ne("UNKNOWN") &
        out["track_key"].ne("") &
        out["pos800"].notna() &
        out["field_size"].notna()
    )

    runner = out.sort_values(["track", "distance", "race_date", "horse"]).reset_index(drop=True)
    runner.to_csv(OUT_RUNNER, index=False)

    ready = runner[runner["profile_ready_v2"]].copy()

    profile_td = build_profile(
        ready,
        ["track", "track_key", "distance_bucket"],
        "TRACK_DISTANCE"
    ).sort_values(["track", "distance_bucket"])

    profile_tdc = build_profile(
        ready,
        ["track", "track_key", "distance_bucket", "condition_group"],
        "TRACK_DISTANCE_CONDITION"
    ).sort_values(["track", "distance_bucket", "condition_group"])

    profile_track = build_profile(
        ready,
        ["track", "track_key"],
        "TRACK"
    ).sort_values(["sample_winners", "track"], ascending=[False, True])

    profile_dist = build_profile(
        ready,
        ["distance_bucket"],
        "DISTANCE"
    ).sort_values(["distance_bucket"])

    profile_td.to_csv(OUT_TRACK_DISTANCE, index=False)
    profile_tdc.to_csv(OUT_TRACK_DISTANCE_CONDITION, index=False)
    profile_track.to_csv(OUT_TRACK, index=False)
    profile_dist.to_csv(OUT_DISTANCE, index=False)

    summary_rows = [
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "source", "value": SOURCE.name},
        {"metric": "source_rows", "value": len(df)},
        {"metric": "runner_rows", "value": len(runner)},
        {"metric": "profile_ready_rows", "value": len(ready)},
        {"metric": "winner_rows", "value": int(runner["is_winner"].sum())},
        {"metric": "profile_ready_winners", "value": int(ready["is_winner"].sum())},
        {"metric": "track_distance_profiles", "value": len(profile_td)},
        {"metric": "track_distance_condition_profiles", "value": len(profile_tdc)},
        {"metric": "track_profiles", "value": len(profile_track)},
        {"metric": "distance_profiles", "value": len(profile_dist)},
        {"metric": "leader_winners", "value": int((ready["is_winner"] & ready["run_style_v2"].eq("LEADER")).sum())},
        {"metric": "onpace_winners", "value": int((ready["is_winner"] & ready["run_style_v2"].eq("ON_PACE")).sum())},
        {"metric": "midfield_winners", "value": int((ready["is_winner"] & ready["run_style_v2"].eq("MIDFIELD")).sum())},
        {"metric": "backmarker_winners", "value": int((ready["is_winner"] & ready["run_style_v2"].eq("BACKMARKER")).sum())},
        {"metric": "inside_winners", "value": int((ready["is_winner"] & ready["barrier_lane_v2"].eq("INSIDE")).sum())},
        {"metric": "middle_winners", "value": int((ready["is_winner"] & ready["barrier_lane_v2"].eq("MIDDLE")).sum())},
        {"metric": "outside_winners", "value": int((ready["is_winner"] & ready["barrier_lane_v2"].eq("OUTSIDE")).sum())},
        {"metric": "high_confidence_track_distance_profiles", "value": int((profile_td["profile_confidence"].eq("HIGH")).sum()) if len(profile_td) else 0},
        {"metric": "medium_confidence_track_distance_profiles", "value": int((profile_td["profile_confidence"].eq("MEDIUM")).sum()) if len(profile_td) else 0},
        {"metric": "low_confidence_track_distance_profiles", "value": int((profile_td["profile_confidence"].eq("LOW")).sum()) if len(profile_td) else 0},
        {"metric": "min_date", "value": runner["race_date"].min()},
        {"metric": "max_date", "value": runner["race_date"].max()},
        {"metric": "outputs", "value": json.dumps([
            OUT_RUNNER.name,
            OUT_TRACK_DISTANCE.name,
            OUT_TRACK_DISTANCE_CONDITION.name,
            OUT_TRACK.name,
            OUT_DISTANCE.name,
        ])},
    ]

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT_SUMMARY, index=False)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({r["metric"]: r["value"] for r in summary_rows}, f, indent=2)

    print("[TRACK_INTELLIGENCE_PROFILE_V2] COMPLETE")
    print(f"source_rows={len(df)}")
    print(f"profile_ready_rows={len(ready)}")
    print(f"winner_rows={int(runner['is_winner'].sum())}")
    print(f"profile_ready_winners={int(ready['is_winner'].sum())}")
    print(f"track_distance_profiles={len(profile_td)}")
    print(f"track_profiles={len(profile_track)}")
    print(f"wrote={OUT_TRACK_DISTANCE}")

if __name__ == "__main__":
    main()
