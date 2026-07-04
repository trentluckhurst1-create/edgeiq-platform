import re
import json
import pandas as pd
from pathlib import Path

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SOURCE = DATA / "edgeiq_racingcom_results_warehouse_full_v1.csv"

OUT_WINNERS = DATA / "edgeiq_winner_origin_warehouse_v1.csv"
OUT_PROFILE = DATA / "edgeiq_winner_origin_track_profile_v1.csv"
OUT_TRACK = DATA / "edgeiq_winner_origin_by_track_v1.csv"
OUT_DISTANCE = DATA / "edgeiq_winner_origin_by_distance_v1.csv"
OUT_CONDITION = DATA / "edgeiq_winner_origin_by_condition_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_winner_origin_warehouse_v1_summary.csv"
OUT_JSON = DATA / "edgeiq_winner_origin_warehouse_v1.json"

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

def finish_pos(x):
    s = txt(x).upper()
    if s in ["", "SCR", "SCRATCHED", "LR", "BD", "FF", "DNF", "F"]:
        return None
    m = re.search(r"\d+", s)
    return int(m.group(0)) if m else None

def distance_m(x):
    m = re.search(r"(\d{3,4})", txt(x))
    return int(m.group(1)) if m else None

def distance_bucket(x):
    d = distance_m(x)
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

def condition_group(x):
    s = txt(x).upper()
    if "HEAVY" in s: return "HEAVY"
    if "SOFT" in s: return "SOFT"
    if "GOOD" in s: return "GOOD"
    if "FAST" in s or "FIRM" in s: return "FAST"
    if "SYNTH" in s: return "SYNTHETIC"
    return "UNKNOWN"

def barrier_lane(x):
    n = num(x)
    if n is None:
        return "UNKNOWN"
    b = int(n)
    if b <= 4: return "INSIDE"
    if b <= 8: return "MIDDLE"
    return "OUTSIDE"

def safe_pct(n, d):
    return round((n / d) * 100, 2) if d else 0.0

def confidence(races):
    if races >= 100: return "HIGH"
    if races >= 25: return "MEDIUM"
    return "LOW"

def dominant_lane(row):
    vals = {
        "INSIDE": row.get("inside_winner_share", 0),
        "MIDDLE": row.get("middle_winner_share", 0),
        "OUTSIDE": row.get("outside_winner_share", 0),
    }
    return max(vals, key=vals.get)

def profile_label(row):
    dom = row.get("dominant_winner_lane", "UNKNOWN")
    share = float(row.get(f"{dom.lower()}_winner_share", 0) or 0)
    if share >= 50:
        return f"{dom}_STRONG_BIAS"
    if share >= 40:
        return f"{dom}_LEAN"
    return "EVEN_SPREAD"

def build_profile(winners, group_cols):
    rows = []

    for keys, g in winners.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)

        d = dict(zip(group_cols, keys))
        races = g["race_key"].nunique()
        winners_n = len(g)

        row = dict(d)
        row["sample_races"] = races
        row["winner_count"] = winners_n

        for lane in ["INSIDE", "MIDDLE", "OUTSIDE", "UNKNOWN"]:
            count = int((g["winner_barrier_lane"] == lane).sum())
            row[f"{lane.lower()}_winners"] = count
            row[f"{lane.lower()}_winner_share"] = safe_pct(count, winners_n)

        b = pd.to_numeric(g["winner_barrier"], errors="coerce").dropna()
        row["avg_winner_barrier"] = round(float(b.mean()), 2) if len(b) else ""
        row["median_winner_barrier"] = round(float(b.median()), 2) if len(b) else ""
        row["min_winner_barrier"] = int(b.min()) if len(b) else ""
        row["max_winner_barrier"] = int(b.max()) if len(b) else ""

        row["dominant_winner_lane"] = dominant_lane(row)
        row["profile_confidence"] = confidence(races)
        row["profile_label"] = profile_label(row)

        rows.append(row)

    return pd.DataFrame(rows)

def main():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    df = pd.read_csv(SOURCE, dtype=str).fillna("")

    c_date = first_col(df, ["meeting_date", "race_date", "date"])
    c_track = first_col(df, ["track", "meeting", "meeting_name"])
    c_race_no = first_col(df, ["race_no", "raceNo", "race_number"])
    c_horse = first_col(df, ["horseName", "horse", "runner", "runner_name"])
    c_finish = first_col(df, ["finishPosition", "finish_position", "position", "pos"])
    c_barrier = first_col(df, ["barrier", "bar", "gate", "draw"])
    c_distance = first_col(df, ["distance", "race_distance", "raceDistance"])
    c_class = first_col(df, ["raceClass", "race_class", "class"])
    c_condition = first_col(df, ["trackCondition", "track_condition", "condition", "going"])
    c_jockey = first_col(df, ["jockey", "rider"])
    c_trainer = first_col(df, ["trainer"])
    c_sp = first_col(df, ["sp", "SP"])
    c_margin = first_col(df, ["margin"])
    c_inrun = first_col(df, ["inRun", "in_run"])
    c_time = first_col(df, ["raceTime", "race_time"])
    c_weight = first_col(df, ["weight"])

    required = [c_date, c_track, c_race_no, c_horse, c_finish, c_barrier, c_distance, c_condition]
    if any(c is None for c in required):
        raise RuntimeError({
            "missing_required": {
                "date": c_date,
                "track": c_track,
                "race_no": c_race_no,
                "horse": c_horse,
                "finish": c_finish,
                "barrier": c_barrier,
                "distance": c_distance,
                "condition": c_condition,
            },
            "columns": list(df.columns),
        })

    work = pd.DataFrame()
    work["race_date"] = df[c_date].map(txt)
    work["track"] = df[c_track].map(lambda x: txt(x).upper())
    work["track_key"] = df[c_track].map(canon_track)
    work["race_no"] = df[c_race_no].map(txt)
    work["race_key"] = work["race_date"] + "|" + work["track_key"] + "|R" + work["race_no"]
    work["horse"] = df[c_horse].map(txt)
    work["horse_key"] = df[c_horse].map(canon_horse)
    work["finish_position"] = df[c_finish].map(finish_pos)
    work["barrier"] = df[c_barrier].map(num)
    work["barrier_raw"] = df[c_barrier].map(txt)
    work["distance"] = df[c_distance].map(txt)
    work["distance_m"] = df[c_distance].map(distance_m)
    work["distance_bucket"] = df[c_distance].map(distance_bucket)
    work["race_class"] = df[c_class].map(txt) if c_class else ""
    work["track_condition"] = df[c_condition].map(txt)
    work["condition_group"] = df[c_condition].map(condition_group)
    work["jockey"] = df[c_jockey].map(txt) if c_jockey else ""
    work["trainer"] = df[c_trainer].map(txt) if c_trainer else ""
    work["sp"] = df[c_sp].map(txt) if c_sp else ""
    work["margin"] = df[c_margin].map(txt) if c_margin else ""
    work["in_run"] = df[c_inrun].map(txt) if c_inrun else ""
    work["race_time"] = df[c_time].map(txt) if c_time else ""
    work["weight"] = df[c_weight].map(txt) if c_weight else ""

    valid = work[work["finish_position"].notna()].copy()
    winners = valid[valid["finish_position"].eq(1)].copy()

    winners["winner"] = winners["horse"]
    winners["winner_key"] = winners["horse_key"]
    winners["winner_barrier"] = winners["barrier"]
    winners["winner_barrier_lane"] = winners["barrier"].map(barrier_lane)

    winners = winners[[
        "race_date",
        "track",
        "track_key",
        "race_no",
        "race_key",
        "distance",
        "distance_m",
        "distance_bucket",
        "race_class",
        "track_condition",
        "condition_group",
        "winner",
        "winner_key",
        "winner_barrier",
        "winner_barrier_lane",
        "jockey",
        "trainer",
        "sp",
        "margin",
        "in_run",
        "race_time",
        "weight",
    ]].sort_values(["track", "distance_m", "condition_group", "race_date", "race_no"])

    winners.to_csv(OUT_WINNERS, index=False)

    profile = build_profile(winners, ["track", "track_key", "distance_bucket", "condition_group"])
    profile = profile.sort_values(["track", "distance_bucket", "condition_group"])
    profile.to_csv(OUT_PROFILE, index=False)

    by_track = build_profile(winners, ["track", "track_key"])
    by_track = by_track.sort_values(["track"])
    by_track.to_csv(OUT_TRACK, index=False)

    by_distance = build_profile(winners, ["distance_bucket"])
    by_distance = by_distance.sort_values(["distance_bucket"])
    by_distance.to_csv(OUT_DISTANCE, index=False)

    by_condition = build_profile(winners, ["condition_group"])
    by_condition = by_condition.sort_values(["condition_group"])
    by_condition.to_csv(OUT_CONDITION, index=False)

    summary_rows = [
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "source", "value": SOURCE.name},
        {"metric": "source_rows", "value": len(df)},
        {"metric": "valid_finish_rows", "value": len(valid)},
        {"metric": "winner_rows", "value": len(winners)},
        {"metric": "unique_races", "value": valid["race_key"].nunique()},
        {"metric": "unique_winner_races", "value": winners["race_key"].nunique()},
        {"metric": "tracks", "value": winners["track"].nunique()},
        {"metric": "min_date", "value": winners["race_date"].min()},
        {"metric": "max_date", "value": winners["race_date"].max()},
        {"metric": "track_distance_condition_profiles", "value": len(profile)},
        {"metric": "track_profiles", "value": len(by_track)},
        {"metric": "distance_profiles", "value": len(by_distance)},
        {"metric": "condition_profiles", "value": len(by_condition)},
        {"metric": "high_confidence_track_distance_condition_profiles", "value": int((profile["profile_confidence"] == "HIGH").sum())},
        {"metric": "medium_confidence_track_distance_condition_profiles", "value": int((profile["profile_confidence"] == "MEDIUM").sum())},
        {"metric": "low_confidence_track_distance_condition_profiles", "value": int((profile["profile_confidence"] == "LOW").sum())},
        {"metric": "outputs", "value": json.dumps([
            OUT_WINNERS.name,
            OUT_PROFILE.name,
            OUT_TRACK.name,
            OUT_DISTANCE.name,
            OUT_CONDITION.name,
        ])},
    ]

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT_SUMMARY, index=False)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({r["metric"]: r["value"] for r in summary_rows}, f, indent=2)

    print("[WINNER_ORIGIN_WAREHOUSE_V1] COMPLETE")
    print(f"source_rows={len(df)}")
    print(f"valid_finish_rows={len(valid)}")
    print(f"winner_rows={len(winners)}")
    print(f"profiles={len(profile)}")
    print(f"tracks={winners['track'].nunique()}")
    print(f"date_range={winners['race_date'].min()} to {winners['race_date'].max()}")
    print(f"wrote={OUT_WINNERS}")
    print(f"wrote={OUT_PROFILE}")

if __name__ == "__main__":
    main()
