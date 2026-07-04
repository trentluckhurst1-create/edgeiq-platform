import re
import json
import pandas as pd
from pathlib import Path

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

OUT_SOURCE = DATA / "edgeiq_results_warehouse_source_audit_v1.csv"
OUT_COLUMNS = DATA / "edgeiq_results_warehouse_column_audit_v1.csv"
OUT_DATE = DATA / "edgeiq_results_warehouse_date_coverage_v1.csv"
OUT_TRACK = DATA / "edgeiq_results_warehouse_track_coverage_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_results_warehouse_audit_summary_v1.csv"
OUT_JSON = DATA / "edgeiq_results_warehouse_audit_summary_v1.json"

RESULT_FILE_PATTERNS = [
    "results",
    "result",
]

EXCLUDE_NAME_PARTS = [
    "summary",
    "audit_summary",
    "source_audit",
    "column_audit",
    "date_coverage",
    "track_coverage",
    "profile",
    "winner_origin",
    "barrier_profile",
    "sort_profile",
    "review",
    "diagnostic",
    "failures",
    "unmatched",
    "roi",
    "model_results",
    "bet_results",
]

DATE_NAMES = [
    "meeting_date", "race_date", "date", "event_date", "raceDate", "meetingDate"
]

TRACK_NAMES = [
    "track", "meeting", "meeting_name", "venue", "track_name"
]

RACE_NO_NAMES = [
    "race_no", "raceNo", "race_number", "race", "raceNumber"
]

HORSE_NAMES = [
    "horse", "horseName", "runner", "runner_name", "selection", "name"
]

FINISH_NAMES = [
    "finishPosition", "finish_position", "position", "pos", "finish", "placing", "result"
]

BARRIER_NAMES = [
    "barrier", "bar", "gate", "draw", "barrierNumber"
]

DISTANCE_NAMES = [
    "distance", "race_distance", "dist", "raceDistance"
]

CONDITION_NAMES = [
    "trackCondition", "track_condition", "condition", "going", "surface"
]

RAIL_NAMES = [
    "rail", "rail_position", "railPosition", "rail_position_raw", "rail_bucket", "rail_true", "rail_out"
]

STYLE_NAMES = [
    "settling_band", "speed_map_bucket", "run_style", "pace_profile", "leader", "onpace",
    "midfield", "backmarker", "tactical_dna_style", "speed_map_band"
]

def txt(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def canon_col(c):
    return re.sub(r"[^a-z0-9]", "", str(c).lower())

def find_col(cols, candidates):
    cmap = {canon_col(c): c for c in cols}
    for x in candidates:
        key = canon_col(x)
        if key in cmap:
            return cmap[key]
    return ""

def looks_like_result_file(p):
    n = p.name.lower()
    if not n.endswith(".csv"):
        return False
    if not any(x in n for x in RESULT_FILE_PATTERNS):
        return False
    if any(x in n for x in EXCLUDE_NAME_PARTS):
        return False
    return True

def maybe_date_series(s):
    if s is None:
        return None
    try:
        return pd.to_datetime(s.astype(str).str.strip(), errors="coerce")
    except Exception:
        return None

def main():
    files = sorted([p for p in DATA.rglob("*.csv") if looks_like_result_file(p)])

    source_rows = []
    column_rows = []
    date_rows = []
    track_rows = []

    total_rows = 0
    best_by_valid_runners = None
    best_by_unique_races = None
    best_rail_source = None
    best_style_source = None

    for p in files:
        rel = str(p.relative_to(ROOT))
        try:
            df = pd.read_csv(p, dtype=str, nrows=None).fillna("")
        except Exception as e:
            source_rows.append({
                "source_file": rel,
                "status": "READ_FAILED",
                "error": str(e),
                "rows": 0,
            })
            continue

        rows = len(df)
        total_rows += rows
        cols = list(df.columns)

        c_date = find_col(cols, DATE_NAMES)
        c_track = find_col(cols, TRACK_NAMES)
        c_race = find_col(cols, RACE_NO_NAMES)
        c_horse = find_col(cols, HORSE_NAMES)
        c_finish = find_col(cols, FINISH_NAMES)
        c_barrier = find_col(cols, BARRIER_NAMES)
        c_distance = find_col(cols, DISTANCE_NAMES)
        c_condition = find_col(cols, CONDITION_NAMES)
        c_rail = find_col(cols, RAIL_NAMES)
        c_style = find_col(cols, STYLE_NAMES)

        date_ser = maybe_date_series(df[c_date]) if c_date else None
        min_date = ""
        max_date = ""
        valid_date_rows = 0

        if date_ser is not None:
            valid_date_rows = int(date_ser.notna().sum())
            if valid_date_rows:
                min_date = str(date_ser.min().date())
                max_date = str(date_ser.max().date())

        if c_track:
            track_clean = df[c_track].astype(str).str.upper().str.strip()
            tracks = int(track_clean[track_clean.ne("")].nunique())
        else:
            tracks = 0

        if c_date and c_track and c_race:
            race_key = (
                df[c_date].astype(str).str.strip() + "|" +
                df[c_track].astype(str).str.upper().str.strip() + "|" +
                df[c_race].astype(str).str.strip()
            )
            unique_races = int(race_key[race_key.str.len() > 2].nunique())
        elif c_track and c_race:
            race_key = (
                df[c_track].astype(str).str.upper().str.strip() + "|" +
                df[c_race].astype(str).str.strip()
            )
            unique_races = int(race_key[race_key.str.len() > 2].nunique())
        else:
            unique_races = 0

        if c_horse:
            unique_runners = int(df[c_horse].astype(str).str.upper().str.strip().replace("", pd.NA).dropna().nunique())
        else:
            unique_runners = 0

        if c_finish:
            finish_s = df[c_finish].astype(str).str.upper().str.strip()
            valid_finish_rows = int(finish_s.str.contains(r"\d", regex=True).sum())
            winner_rows = int(finish_s.eq("1").sum() + finish_s.eq("1ST").sum())
            scratched_rows = int(finish_s.isin(["SCR", "SCRATCHED"]).sum())
        else:
            valid_finish_rows = 0
            winner_rows = 0
            scratched_rows = 0

        barrier_known = int(df[c_barrier].astype(str).str.strip().ne("").sum()) if c_barrier else 0
        distance_known = int(df[c_distance].astype(str).str.strip().ne("").sum()) if c_distance else 0
        condition_known = int(df[c_condition].astype(str).str.strip().ne("").sum()) if c_condition else 0
        rail_known = int(df[c_rail].astype(str).str.strip().ne("").sum()) if c_rail else 0
        style_known = int(df[c_style].astype(str).str.strip().ne("").sum()) if c_style else 0

        completeness_score = (
            valid_finish_rows +
            unique_races * 10 +
            barrier_known +
            distance_known +
            condition_known +
            rail_known * 5 +
            style_known * 5
        )

        row = {
            "source_file": rel,
            "status": "LOADED",
            "rows": rows,
            "columns": len(cols),
            "unique_races": unique_races,
            "unique_runners": unique_runners,
            "tracks": tracks,
            "min_date": min_date,
            "max_date": max_date,
            "valid_date_rows": valid_date_rows,
            "valid_finish_rows": valid_finish_rows,
            "winner_rows": winner_rows,
            "scratched_rows": scratched_rows,
            "barrier_known_rows": barrier_known,
            "distance_known_rows": distance_known,
            "condition_known_rows": condition_known,
            "rail_known_rows": rail_known,
            "run_style_known_rows": style_known,
            "date_col": c_date,
            "track_col": c_track,
            "race_no_col": c_race,
            "horse_col": c_horse,
            "finish_col": c_finish,
            "barrier_col": c_barrier,
            "distance_col": c_distance,
            "condition_col": c_condition,
            "rail_col": c_rail,
            "run_style_col": c_style,
            "completeness_score": completeness_score,
        }

        source_rows.append(row)

        for c in cols:
            cl = c.lower()
            tags = []
            if any(x in cl for x in ["rail"]): tags.append("RAIL")
            if any(x in cl for x in ["barrier", "gate", "draw"]): tags.append("BARRIER")
            if any(x in cl for x in ["condition", "going", "surface"]): tags.append("CONDITION")
            if any(x in cl for x in ["distance", "dist"]): tags.append("DISTANCE")
            if any(x in cl for x in ["finish", "position", "placing", "result"]): tags.append("FINISH")
            if any(x in cl for x in ["leader", "onpace", "pace", "midfield", "backmarker", "settling", "speed_map", "run_style"]): tags.append("RUN_STYLE")
            if any(x in cl for x in ["date"]): tags.append("DATE")
            if any(x in cl for x in ["track", "venue", "meeting"]): tags.append("TRACK")

            nonblank = int(df[c].astype(str).str.strip().ne("").sum())
            sample_values = " | ".join(df[c].astype(str).str.strip().replace("", pd.NA).dropna().head(5).tolist())

            column_rows.append({
                "source_file": rel,
                "column": c,
                "tag": ",".join(tags),
                "nonblank_rows": nonblank,
                "rows": rows,
                "coverage_pct": round((nonblank / rows) * 100, 2) if rows else 0,
                "sample_values": sample_values[:300],
            })

        if c_date:
            tmp = pd.DataFrame({
                "date": date_ser,
                "track": df[c_track].astype(str).str.upper().str.strip() if c_track else "",
                "race_no": df[c_race].astype(str).str.strip() if c_race else "",
                "horse": df[c_horse].astype(str).str.upper().str.strip() if c_horse else "",
            })
            tmp = tmp[tmp["date"].notna()].copy()
            if len(tmp):
                tmp["year"] = tmp["date"].dt.year
                for year, gy in tmp.groupby("year"):
                    date_rows.append({
                        "source_file": rel,
                        "year": int(year),
                        "rows": len(gy),
                        "unique_dates": int(gy["date"].dt.date.nunique()),
                        "unique_races": int((gy["date"].dt.strftime("%Y-%m-%d") + "|" + gy["track"] + "|" + gy["race_no"]).nunique()) if c_track and c_race else 0,
                        "unique_runners": int(gy["horse"].replace("", pd.NA).dropna().nunique()) if c_horse else 0,
                        "min_date": str(gy["date"].min().date()),
                        "max_date": str(gy["date"].max().date()),
                    })

        if c_track:
            tmp = pd.DataFrame({
                "track": df[c_track].astype(str).str.upper().str.strip(),
                "date": date_ser if c_date else pd.NaT,
                "race_no": df[c_race].astype(str).str.strip() if c_race else "",
                "horse": df[c_horse].astype(str).str.upper().str.strip() if c_horse else "",
            })
            tmp = tmp[tmp["track"].ne("")]
            for track, gt in tmp.groupby("track"):
                track_rows.append({
                    "source_file": rel,
                    "track": track,
                    "rows": len(gt),
                    "unique_races": int((gt["date"].astype(str) + "|" + gt["track"] + "|" + gt["race_no"]).nunique()) if c_race else 0,
                    "unique_runners": int(gt["horse"].replace("", pd.NA).dropna().nunique()) if c_horse else 0,
                    "min_date": str(gt["date"].min().date()) if c_date and gt["date"].notna().any() else "",
                    "max_date": str(gt["date"].max().date()) if c_date and gt["date"].notna().any() else "",
                })

    source = pd.DataFrame(source_rows)
    columns = pd.DataFrame(column_rows)
    dates = pd.DataFrame(date_rows)
    tracks = pd.DataFrame(track_rows)

    if len(source):
        source = source.sort_values(["completeness_score", "rows"], ascending=[False, False])
    if len(columns):
        columns = columns.sort_values(["source_file", "tag", "coverage_pct"], ascending=[True, True, False])
    if len(dates):
        dates = dates.sort_values(["source_file", "year"])
    if len(tracks):
        tracks = tracks.sort_values(["source_file", "rows"], ascending=[True, False])

    source.to_csv(OUT_SOURCE, index=False)
    columns.to_csv(OUT_COLUMNS, index=False)
    dates.to_csv(OUT_DATE, index=False)
    tracks.to_csv(OUT_TRACK, index=False)

    if len(source):
        best = source.iloc[0].to_dict()
        best_rail = source.sort_values(["rail_known_rows", "unique_races", "rows"], ascending=[False, False, False]).iloc[0].to_dict()
        best_style = source.sort_values(["run_style_known_rows", "unique_races", "rows"], ascending=[False, False, False]).iloc[0].to_dict()
    else:
        best = {}
        best_rail = {}
        best_style = {}

    summary_rows = [
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "files_audited", "value": len(source)},
        {"metric": "total_rows_seen", "value": total_rows},
        {"metric": "best_overall_source", "value": best.get("source_file", "")},
        {"metric": "best_overall_rows", "value": best.get("rows", "")},
        {"metric": "best_overall_unique_races", "value": best.get("unique_races", "")},
        {"metric": "best_overall_min_date", "value": best.get("min_date", "")},
        {"metric": "best_overall_max_date", "value": best.get("max_date", "")},
        {"metric": "best_rail_source", "value": best_rail.get("source_file", "")},
        {"metric": "best_rail_known_rows", "value": best_rail.get("rail_known_rows", "")},
        {"metric": "best_run_style_source", "value": best_style.get("source_file", "")},
        {"metric": "best_run_style_known_rows", "value": best_style.get("run_style_known_rows", "")},
        {"metric": "output_source_audit", "value": OUT_SOURCE.name},
        {"metric": "output_column_audit", "value": OUT_COLUMNS.name},
        {"metric": "output_date_coverage", "value": OUT_DATE.name},
        {"metric": "output_track_coverage", "value": OUT_TRACK.name},
    ]

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT_SUMMARY, index=False)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({r["metric"]: r["value"] for r in summary_rows}, f, indent=2)

    print("[RESULTS_WAREHOUSE_AUDIT_V1] COMPLETE")
    print(f"files_audited={len(source)}")
    print(f"total_rows_seen={total_rows}")
    print(f"best_overall_source={best.get('source_file', '')}")
    print(f"best_rail_source={best_rail.get('source_file', '')}")
    print(f"best_run_style_source={best_style.get('source_file', '')}")
    print(f"wrote={OUT_SOURCE}")
    print(f"wrote={OUT_COLUMNS}")
    print(f"wrote={OUT_DATE}")
    print(f"wrote={OUT_TRACK}")

if __name__ == "__main__":
    main()
