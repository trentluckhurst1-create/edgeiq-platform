import pandas as pd
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INFILE = DATA / "edgeiq_live_runner_style_v1.csv"
OUTFILE = DATA / "edgeiq_live_runner_style_v2.csv"
SUMMARY = DATA / "edgeiq_live_runner_style_v2_summary.csv"

def num(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return None
        return float(x)
    except Exception:
        return None

def barrier_lane(barrier, field_size):
    b = num(barrier)
    f = num(field_size)
    if b is None:
        return "UNKNOWN"
    if f is None or f <= 0:
        if b <= 4:
            return "INSIDE"
        if b <= 9:
            return "MIDDLE"
        return "OUTSIDE"
    if b <= max(1, round(f * 0.33)):
        return "INSIDE"
    if b <= max(2, round(f * 0.67)):
        return "MIDDLE"
    return "OUTSIDE"

def distance_bucket_style(distance, lane):
    d = num(distance)
    if d is None:
        return "MIDFIELD"

    if d <= 1100:
        if lane == "INSIDE":
            return "ON_PACE"
        if lane == "MIDDLE":
            return "MIDFIELD"
        return "BACKMARKER"

    if d <= 1400:
        if lane == "INSIDE":
            return "ON_PACE"
        if lane == "MIDDLE":
            return "MIDFIELD"
        return "MIDFIELD"

    if d <= 1800:
        if lane == "INSIDE":
            return "MIDFIELD"
        if lane == "MIDDLE":
            return "MIDFIELD"
        return "BACKMARKER"

    if lane == "INSIDE":
        return "MIDFIELD"
    if lane == "MIDDLE":
        return "MIDFIELD"
    return "BACKMARKER"

def infer_movement(style):
    if style in ["LEADER", "ON_PACE"]:
        return "HOLDS_POSITION"
    if style == "MIDFIELD":
        return "HOLDS_POSITION"
    if style == "BACKMARKER":
        return "IMPROVER"
    return "UNKNOWN"

def make_comment(r):
    if r["runner_style_source_v2"] == "HISTORICAL":
        return r.get("runner_style_comment", "")
    return (
        f"No historical runner style profile found. Inferred as {r['dominant_run_style']} "
        f"from barrier lane {r['runner_barrier_lane_v2']} and distance {r.get('distance','')}. "
        f"This is an inferred profile, not a historical profile."
    )

def main():
    df = pd.read_csv(INFILE, dtype=str).fillna("")

    if "field_size" not in df.columns:
        df["field_size"] = ""

    lanes = []
    sources = []

    for _, r in df.iterrows():
        lanes.append(barrier_lane(r.get("barrier", ""), r.get("field_size", "")))
        if str(r.get("dominant_run_style", "")).strip():
            sources.append("HISTORICAL")
        else:
            sources.append("INFERRED")

    df["runner_barrier_lane_v2"] = lanes
    df["runner_style_source_v2"] = sources

    for idx, r in df.iterrows():
        if df.at[idx, "runner_style_source_v2"] == "INFERRED":
            inferred_style = distance_bucket_style(r.get("distance", ""), r.get("runner_barrier_lane_v2", ""))
            df.at[idx, "dominant_run_style"] = inferred_style
            df.at[idx, "movement_profile"] = infer_movement(inferred_style)
            df.at[idx, "style_confidence"] = "INFERRED"
            df.at[idx, "runner_style_match_status"] = "INFERRED_STYLE"
            df.at[idx, "starts"] = "0"

            for c in [
                "leader_pct","onpace_pct","midfield_pct","backmarker_pct",
                "leader_runs","onpace_runs","midfield_runs","backmarker_runs",
                "avg_pos800","avg_pos400","avg_gain_800_400",
                "improver_pct","fader_pct","holds_position_pct"
            ]:
                if c in df.columns:
                    df.at[idx, c] = ""

    df["runner_style_comment_v2"] = df.apply(make_comment, axis=1)

    df.to_csv(OUTFILE, index=False)

    summary = pd.DataFrame([
        ["status", "COMPLETE"],
        ["input_rows", len(df)],
        ["historical_rows", int((df["runner_style_source_v2"] == "HISTORICAL").sum())],
        ["inferred_rows", int((df["runner_style_source_v2"] == "INFERRED").sum())],
        ["output", str(OUTFILE.name)],
    ], columns=["metric", "value"])

    summary.to_csv(SUMMARY, index=False)

    print("[LIVE_RUNNER_STYLE_V2] COMPLETE")
    print(f"rows={len(df)}")
    print(f"historical={(df['runner_style_source_v2'] == 'HISTORICAL').sum()}")
    print(f"inferred={(df['runner_style_source_v2'] == 'INFERRED').sum()}")
    print(f"wrote={OUTFILE}")

if __name__ == "__main__":
    main()
