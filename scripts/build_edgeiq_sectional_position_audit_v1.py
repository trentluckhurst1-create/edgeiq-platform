import re
import json
import pandas as pd
from pathlib import Path

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

OUT_SOURCE = DATA / "edgeiq_sectional_position_source_audit_v1.csv"
OUT_COLUMNS = DATA / "edgeiq_sectional_position_column_audit_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_sectional_position_audit_v1_summary.csv"
OUT_JSON = DATA / "edgeiq_sectional_position_audit_v1.json"

SECTIONAL_CANDIDATES = [
    DATA / "edgeiq_rendered_sectionals_warehouse_v2.csv",
    DATA / "edgeiq_sectional_warehouse_v2.csv",
    DATA / "edgeiq_sectionals_warehouse_v2.csv",
    DATA / "edgeiq_sectional_profiles_v2.csv",
    DATA / "edgeiq_tactical_dna_v1.csv",
]

KEYWORDS = [
    "sectional",
    "split",
    "speed",
    "tactical",
    "dna",
    "settling",
    "position",
    "rank",
]

EXCLUDE = [
    "summary",
    "audit",
    "profile_summary",
    "unmatched",
    "failures",
]

POSITION_TERMS = [
    "rank", "position", "pos", "settling", "inrun", "in_run", "800", "600", "400", "200",
    "leader", "onpace", "midfield", "backmarker", "pace", "early"
]

def txt(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def canon_col(c):
    return re.sub(r"[^a-z0-9]", "", str(c).lower())

def first_col(cols, names):
    cmap = {canon_col(c): c for c in cols}
    for n in names:
        k = canon_col(n)
        if k in cmap:
            return cmap[k]
    return ""

def looks_like_sectional_file(p):
    n = p.name.lower()
    if not n.endswith(".csv"):
        return False
    if any(x in n for x in EXCLUDE):
        return False
    return any(k in n for k in KEYWORDS)

def main():
    files = []

    for p in SECTIONAL_CANDIDATES:
        if p.exists():
            files.append(p)

    for p in DATA.rglob("*.csv"):
        if looks_like_sectional_file(p) and p not in files:
            files.append(p)

    files = sorted(set(files))

    source_rows = []
    column_rows = []

    for p in files:
        rel = str(p.relative_to(ROOT))
        try:
            df = pd.read_csv(p, dtype=str).fillna("")
        except Exception as e:
            source_rows.append({
                "source_file": rel,
                "status": "READ_FAILED",
                "error": str(e),
                "rows": 0,
            })
            continue

        cols = list(df.columns)
        rows = len(df)

        c_date = first_col(cols, ["race_date", "meeting_date", "date"])
        c_track = first_col(cols, ["track", "meeting", "meeting_name"])
        c_race_no = first_col(cols, ["race_no", "raceNo", "race_number", "race"])
        c_horse = first_col(cols, ["horse", "horseName", "runner", "runner_name", "horse_name"])
        c_style = first_col(cols, ["settling_band", "speed_map_bucket", "run_style", "pace_profile", "tactical_dna_style"])
        c_early = first_col(cols, ["early_speed", "avg_early_speed", "early_speed_band", "early_rank", "rank_800", "pos_800", "position_800"])
        c_late = first_col(cols, ["late_speed", "avg_late_speed", "late_speed_band", "late_rank", "rank_200", "pos_200", "position_200"])

        unique_races = 0
        if c_date and c_track and c_race_no:
            unique_races = int((df[c_date].astype(str) + "|" + df[c_track].astype(str) + "|" + df[c_race_no].astype(str)).nunique())
        elif c_track and c_race_no:
            unique_races = int((df[c_track].astype(str) + "|" + df[c_race_no].astype(str)).nunique())

        unique_horses = int(df[c_horse].astype(str).str.upper().str.strip().replace("", pd.NA).dropna().nunique()) if c_horse else 0

        position_cols = []
        rank_cols = []
        split_cols = []
        speed_cols = []
        style_cols = []

        for c in cols:
            cl = c.lower()
            if any(t in cl for t in POSITION_TERMS):
                position_cols.append(c)
            if "rank" in cl:
                rank_cols.append(c)
            if any(t in cl for t in ["800", "600", "400", "200", "split"]):
                split_cols.append(c)
            if "speed" in cl:
                speed_cols.append(c)
            if any(t in cl for t in ["settling", "leader", "onpace", "midfield", "backmarker", "run_style", "pace_profile", "speed_map_bucket"]):
                style_cols.append(c)

        source_rows.append({
            "source_file": rel,
            "status": "LOADED",
            "rows": rows,
            "columns": len(cols),
            "unique_races": unique_races,
            "unique_horses": unique_horses,
            "date_col": c_date,
            "track_col": c_track,
            "race_no_col": c_race_no,
            "horse_col": c_horse,
            "style_col": c_style,
            "early_col": c_early,
            "late_col": c_late,
            "position_like_cols": len(position_cols),
            "rank_cols": len(rank_cols),
            "split_cols": len(split_cols),
            "speed_cols": len(speed_cols),
            "style_cols": len(style_cols),
            "position_col_names": " | ".join(position_cols[:40]),
            "rank_col_names": " | ".join(rank_cols[:40]),
            "split_col_names": " | ".join(split_cols[:40]),
            "speed_col_names": " | ".join(speed_cols[:40]),
            "style_col_names": " | ".join(style_cols[:40]),
        })

        for c in cols:
            cl = c.lower()
            tags = []
            if any(t in cl for t in ["race_date", "meeting_date", "date"]): tags.append("DATE")
            if any(t in cl for t in ["track", "meeting"]): tags.append("TRACK")
            if any(t in cl for t in ["race_no", "race_number"]): tags.append("RACE_NO")
            if any(t in cl for t in ["horse", "runner"]): tags.append("HORSE")
            if "rank" in cl: tags.append("RANK")
            if any(t in cl for t in ["position", "pos", "settling", "inrun", "in_run"]): tags.append("POSITION")
            if any(t in cl for t in ["800", "600", "400", "200", "split"]): tags.append("SPLIT")
            if "speed" in cl: tags.append("SPEED")
            if any(t in cl for t in ["leader", "onpace", "midfield", "backmarker", "pace_profile", "run_style", "speed_map_bucket"]): tags.append("STYLE")

            nonblank = int(df[c].astype(str).str.strip().ne("").sum())
            sample = " | ".join(df[c].astype(str).str.strip().replace("", pd.NA).dropna().head(8).tolist())

            column_rows.append({
                "source_file": rel,
                "column": c,
                "tag": ",".join(tags),
                "nonblank_rows": nonblank,
                "rows": rows,
                "coverage_pct": round((nonblank / rows) * 100, 2) if rows else 0,
                "sample_values": sample[:400],
            })

    source = pd.DataFrame(source_rows)
    columns = pd.DataFrame(column_rows)

    if len(source):
        source = source.sort_values(
            ["unique_races", "rows", "position_like_cols", "style_cols"],
            ascending=[False, False, False, False]
        )

    if len(columns):
        columns = columns.sort_values(["source_file", "tag", "coverage_pct"], ascending=[True, True, False])

    source.to_csv(OUT_SOURCE, index=False)
    columns.to_csv(OUT_COLUMNS, index=False)

    best = source.iloc[0].to_dict() if len(source) else {}
    best_style = source.sort_values(["style_cols", "unique_races", "rows"], ascending=[False, False, False]).iloc[0].to_dict() if len(source) else {}
    best_rank = source.sort_values(["rank_cols", "unique_races", "rows"], ascending=[False, False, False]).iloc[0].to_dict() if len(source) else {}
    best_split = source.sort_values(["split_cols", "unique_races", "rows"], ascending=[False, False, False]).iloc[0].to_dict() if len(source) else {}

    summary_rows = [
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "files_audited", "value": len(source)},
        {"metric": "best_overall_source", "value": best.get("source_file", "")},
        {"metric": "best_overall_rows", "value": best.get("rows", "")},
        {"metric": "best_overall_unique_races", "value": best.get("unique_races", "")},
        {"metric": "best_style_source", "value": best_style.get("source_file", "")},
        {"metric": "best_style_cols", "value": best_style.get("style_col_names", "")},
        {"metric": "best_rank_source", "value": best_rank.get("source_file", "")},
        {"metric": "best_rank_cols", "value": best_rank.get("rank_col_names", "")},
        {"metric": "best_split_source", "value": best_split.get("source_file", "")},
        {"metric": "best_split_cols", "value": best_split.get("split_col_names", "")},
        {"metric": "output_source_audit", "value": OUT_SOURCE.name},
        {"metric": "output_column_audit", "value": OUT_COLUMNS.name},
    ]

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT_SUMMARY, index=False)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({r["metric"]: r["value"] for r in summary_rows}, f, indent=2)

    print("[SECTIONAL_POSITION_AUDIT_V1] COMPLETE")
    print(f"files_audited={len(source)}")
    print(f"best_overall_source={best.get('source_file', '')}")
    print(f"best_style_source={best_style.get('source_file', '')}")
    print(f"best_rank_source={best_rank.get('source_file', '')}")
    print(f"best_split_source={best_split.get('source_file', '')}")
    print(f"wrote={OUT_SOURCE}")
    print(f"wrote={OUT_COLUMNS}")

if __name__ == "__main__":
    main()
