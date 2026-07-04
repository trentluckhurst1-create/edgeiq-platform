import re
import json
import pandas as pd
from pathlib import Path

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SOURCE = DATA / "edgeiq_master_positional_observations_v1.csv"

OUT = DATA / "edgeiq_historical_run_style_v1.csv"
SUMMARY = DATA / "edgeiq_historical_run_style_v1_summary.csv"
JSON_OUT = DATA / "edgeiq_historical_run_style_v1.json"

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

def canon_track(x):
    return re.sub(r"[^A-Z0-9]", "", txt(x).upper())

def canon_horse(x):
    s = txt(x).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    s = re.sub(r"(NZ|GB|IRE|FR|USA|JPN|AUS)$", "", s)
    return s

def num(x):
    s = txt(x)
    s = re.sub(r"[^0-9.\-]", "", s)
    if not s:
        return None
    try:
        return float(s)
    except:
        return None

def infer_race_no_from_source_file(v):
    s = txt(v)
    m = re.search(r"(?:race|r)[_\-\s]*(\d+)", s, flags=re.I)
    if m:
        return str(int(m.group(1)))
    m = re.search(r"/(\d+)(?:\.csv|$)", s.replace("\\", "/"), flags=re.I)
    if m:
        return str(int(m.group(1)))
    return ""

def classify_run_style(pos800, field_size):
    p = num(pos800)
    f = num(field_size)

    if p is None:
        return "UNKNOWN"

    if f is None or f <= 0:
        if p <= 1:
            return "LEADER"
        if p <= 4:
            return "ON_PACE"
        if p <= 8:
            return "MIDFIELD"
        return "BACKMARKER"

    pct = p / f

    if p <= 1:
        return "LEADER"
    if pct <= 0.25:
        return "ON_PACE"
    if pct <= 0.67:
        return "MIDFIELD"
    return "BACKMARKER"

def classify_movement(pos800, pos400):
    p8 = num(pos800)
    p4 = num(pos400)

    if p8 is None or p4 is None:
        return "UNKNOWN"

    gain = p8 - p4

    if gain >= 3:
        return "BIG_IMPROVER"
    if gain >= 1:
        return "IMPROVER"
    if gain <= -3:
        return "BIG_FADER"
    if gain <= -1:
        return "FADER"
    return "HOLDS_POSITION"

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

def main():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    df = pd.read_csv(SOURCE, dtype=str).fillna("")

    c_date = first_col(df, ["race_date", "meeting_date", "date", "run_date"])
    c_track = first_col(df, ["track", "meeting", "meeting_name"])
    c_race_no = first_col(df, ["race_no", "raceNo", "race_number"])
    c_source_file = first_col(df, ["source_file"])
    c_horse = first_col(df, ["horse", "horseName", "horse_name", "runner", "runner_name"])
    c_pos800 = first_col(df, ["pos800", "avg_800m_position", "position_800", "pos_800"])
    c_pos400 = first_col(df, ["pos400", "avg_400m_position", "position_400", "pos_400"])
    c_raw = first_col(df, ["raw_in_run", "in_run", "inRun"])
    c_finish = first_col(df, ["finish_pos", "finish_position", "finishPosition"])
    c_speed = first_col(df, ["speed_figure", "avg_speed_figure"])
    c_gain = first_col(df, ["gain_800_400", "avg_800_to_400_gain"])
    c_barrier = first_col(df, ["barrier", "bar"])
    c_distance = first_col(df, ["distance", "race_distance"])
    c_condition = first_col(df, ["track_condition", "trackCondition", "condition"])
    c_field = first_col(df, ["field_size", "runners", "field_size_valid"])

    required = [c_date, c_track, c_horse, c_pos800]
    if any(c is None for c in required):
        raise RuntimeError({
            "missing_required": {
                "date": c_date,
                "track": c_track,
                "race_no": c_race_no,
                "source_file": c_source_file,
                "horse": c_horse,
                "pos800": c_pos800,
            },
            "columns": list(df.columns),
        })

    out = pd.DataFrame()
    out["race_date"] = df[c_date].map(txt)
    out["track"] = df[c_track].map(lambda x: txt(x).upper())
    out["track_key"] = df[c_track].map(canon_track)

    if c_race_no:
        out["race_no"] = df[c_race_no].map(txt)
        out["race_no_source"] = "COLUMN"
    elif c_source_file:
        out["race_no"] = df[c_source_file].map(infer_race_no_from_source_file)
        out["race_no_source"] = "SOURCE_FILE_INFERRED"
    else:
        out["race_no"] = ""
        out["race_no_source"] = "MISSING"

    out["race_key"] = out["race_date"] + "|" + out["track_key"] + "|R" + out["race_no"]
    out["horse"] = df[c_horse].map(txt)
    out["horse_key"] = df[c_horse].map(canon_horse)

    out["pos800"] = df[c_pos800].map(num)
    out["pos400"] = df[c_pos400].map(num) if c_pos400 else None
    out["raw_in_run"] = df[c_raw].map(txt) if c_raw else ""
    out["finish_pos"] = df[c_finish].map(num) if c_finish else None
    out["speed_figure"] = df[c_speed].map(num) if c_speed else None
    out["gain_800_400"] = df[c_gain].map(num) if c_gain else None
    out["barrier"] = df[c_barrier].map(num) if c_barrier else None
    out["distance"] = df[c_distance].map(txt) if c_distance else ""
    out["distance_bucket"] = out["distance"].map(distance_bucket)
    out["track_condition"] = df[c_condition].map(txt) if c_condition else ""
    out["condition_group"] = out["track_condition"].map(condition_group)

    if c_field:
      out["field_size"] = df[c_field].map(num)
    else:
      out["field_size"] = out.groupby("race_key")["horse_key"].transform("count")

    out["run_style_v1"] = out.apply(lambda r: classify_run_style(r["pos800"], r["field_size"]), axis=1)
    out["movement_profile_v1"] = out.apply(lambda r: classify_movement(r["pos800"], r["pos400"]), axis=1)

    out["run_style_confidence_v1"] = "LOW"
    out.loc[out["pos800"].notna() & out["field_size"].notna() & out["race_no"].ne(""), "run_style_confidence_v1"] = "HIGH"
    out.loc[out["pos800"].notna() & out["field_size"].notna() & out["race_no"].eq(""), "run_style_confidence_v1"] = "MEDIUM"

    out = out.sort_values(["race_date", "track", "race_no", "pos800", "horse"]).reset_index(drop=True)
    out.to_csv(OUT, index=False)

    summary_rows = [
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "source", "value": SOURCE.name},
        {"metric": "source_rows", "value": len(df)},
        {"metric": "output_rows", "value": len(out)},
        {"metric": "unique_races", "value": out["race_key"].nunique()},
        {"metric": "unique_horses", "value": out["horse_key"].nunique()},
        {"metric": "race_no_nonblank_rows", "value": int(out["race_no"].astype(str).str.strip().ne("").sum())},
        {"metric": "race_no_source", "value": out["race_no_source"].mode().iloc[0] if len(out) else ""},
        {"metric": "pos800_known_rows", "value": int(out["pos800"].notna().sum())},
        {"metric": "pos400_known_rows", "value": int(out["pos400"].notna().sum())},
        {"metric": "leader_rows", "value": int((out["run_style_v1"] == "LEADER").sum())},
        {"metric": "onpace_rows", "value": int((out["run_style_v1"] == "ON_PACE").sum())},
        {"metric": "midfield_rows", "value": int((out["run_style_v1"] == "MIDFIELD").sum())},
        {"metric": "backmarker_rows", "value": int((out["run_style_v1"] == "BACKMARKER").sum())},
        {"metric": "unknown_rows", "value": int((out["run_style_v1"] == "UNKNOWN").sum())},
        {"metric": "high_confidence_rows", "value": int((out["run_style_confidence_v1"] == "HIGH").sum())},
        {"metric": "medium_confidence_rows", "value": int((out["run_style_confidence_v1"] == "MEDIUM").sum())},
        {"metric": "min_date", "value": out["race_date"].min()},
        {"metric": "max_date", "value": out["race_date"].max()},
        {"metric": "output", "value": OUT.name},
    ]

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(SUMMARY, index=False)

    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump({r["metric"]: r["value"] for r in summary_rows}, f, indent=2)

    print("[HISTORICAL_RUN_STYLE_V1] COMPLETE")
    print(f"source_rows={len(df)}")
    print(f"output_rows={len(out)}")
    print(f"unique_races={out['race_key'].nunique()}")
    print(f"race_no_nonblank_rows={int(out['race_no'].astype(str).str.strip().ne('').sum())}")
    print(f"pos800_known_rows={int(out['pos800'].notna().sum())}")
    print(f"wrote={OUT}")

if __name__ == "__main__":
    main()
