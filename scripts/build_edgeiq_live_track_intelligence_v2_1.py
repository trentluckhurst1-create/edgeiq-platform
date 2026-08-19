import pandas as pd
from pathlib import Path
import re
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TRACK_DNA = DATA / "edgeiq_track_dna_v1.csv"
RUNNER_DNA = DATA / "edgeiq_runner_dna_status_v1.csv"
RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"

OUT = DATA / "edgeiq_live_track_intelligence_v2_1.csv"
SUMMARY = DATA / "edgeiq_live_track_intelligence_v2_1_summary.csv"

def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def canon(x):
    s = re.sub(r"[^A-Z0-9]+", "", clean(x).upper())
    TRACK_KEY_MAP = {
        "BAIRNSDALE": "BDLE",
        "SEYMOUR": "SEYM",
        "SANDOWNHILLSIDE": "SANH",
        "SANDOWNLAKESIDE": "SANL",
        "SANDOWN": "SANH",
        "BALLARAT": "BRAT",
        "MOONEEVALLEY": "MV",
        "MORNINGTON": "MORN",
        "WARRNAMBOOL": "WNBL",
        "WANGARATTA": "WANG",
        "WODONGA": "WOD",
        "CAULFIELD": "CAUL",
        "FLEMINGTON": "FLEM",
        "PAKENHAM": "PAK",
        "CRANBOURNE": "CRAN",
        "BENDIGO": "BEND",
        "GEELONG": "GEEL",
        "KYNETON": "KYNE",
        "CASTERTON": "CAST",
        "HAMILTON": "HAMI",
        "SWANHILL": "SWH",
        "TERANG": "TER",
        "BENALLA": "BENA",
        "ECHUCA": "ECH",
        "MILDURA": "MILD",
        "HORSHAM": "HORS",
        "STAWELL": "STAW",
        "SALE": "SALE",
        "MOE": "MOE",
        "COLAC": "COL",
        "ARARAT": "ARAR",
        "KILMORE": "KILM"
    }
    return TRACK_KEY_MAP.get(s, s)
def num(x):
    try:
        if clean(x) == "":
            return None
        return float(x)
    except Exception:
        return None

def condition_group(x):
    s = clean(x).upper()
    if not s:
        return "UNKNOWN"
    if "HEAVY" in s:
        return "HEAVY"
    if "SOFT" in s:
        return "SOFT"
    if "GOOD" in s:
        return "GOOD"
    if "FIRM" in s:
        return "GOOD"
    if "SYNTH" in s or "POLY" in s or "TAPETA" in s:
        return "SYNTHETIC"
    return "UNKNOWN"

def season_from_date(x):
    s = clean(x)
    try:
        dt = datetime.strptime(s[:10], "%Y-%m-%d")
        m = dt.month
        if m in [12, 1, 2]:
            return "SUMMER"
        if m in [3, 4, 5]:
            return "AUTUMN"
        if m in [6, 7, 8]:
            return "WINTER"
        return "SPRING"
    except Exception:
        return ""

def distance_bucket(distance):
    d = num(distance)
    if d is None:
        return ""
    d = int(d)
    if d < 800:
        return "UNDER_800"
    if d <= 999:
        return "800-999"
    if d <= 1199:
        return "1000-1199"
    if d <= 1399:
        return "1200-1399"
    if d <= 1599:
        return "1400-1599"
    if d <= 1799:
        return "1600-1799"
    if d <= 1999:
        return "1800-1999"
    if d <= 2199:
        return "2000-2199"
    if d <= 2399:
        return "2200-2399"
    if d <= 2799:
        return "2400-2799"
    return "2800+"

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

def key_cols(df):
    df["track_key_join"] = df["track"].map(canon)
    df["race_no_key_join"] = df["race_no"].map(clean)
    if "horse_key" in df.columns:
        df["horse_key_join"] = df["horse_key"].map(canon)
    elif "horse_canon" in df.columns:
        df["horse_key_join"] = df["horse_canon"].map(canon)
    else:
        df["horse_key_join"] = df["horse"].map(canon)
    return df

def align(actual, expected):
    a = clean(actual).upper()
    e = clean(expected).upper()
    if not a:
        return "NO_HISTORICAL_RUNNER_STYLE"
    if not e:
        return "NO_TRACK_DNA"
    return "MATCH" if a == e else "NO_MATCH"

def fit_band(score):
    if score >= 85:
        return "ELITE"
    if score >= 70:
        return "STRONG"
    if score >= 55:
        return "POSITIVE"
    if score >= 35:
        return "NEUTRAL"
    return "POOR"

def choose_profile(dna, track_key, dist_bucket, cond, season):
    subset = dna[
        (dna["track_key_join"] == track_key) &
        (dna["distance_bucket"] == dist_bucket)
    ].copy()

    if subset.empty:
        return None

    attempts = [
        ("TRACK_DISTANCE_CONDITION_SEASON", cond, season),
        ("TRACK_DISTANCE_CONDITION", cond, ""),
        ("TRACK_DISTANCE_SEASON", "", season),
        ("TRACK_DISTANCE", "", ""),
    ]

    for level, cnd, sea in attempts:
        q = subset[subset["profile_level"] == level].copy()

        if cnd:
            q = q[q["condition_group"].map(lambda x: clean(x).upper()) == cnd]
        if sea:
            q = q[q["season"].map(lambda x: clean(x).upper()) == sea]

        if not q.empty:
            q["sample_winners_num"] = pd.to_numeric(q["sample_winners"], errors="coerce").fillna(0)
            q = q.sort_values("sample_winners_num", ascending=False)
            return q.iloc[0].to_dict()

    return None

def score_row(r):
    score = 0

    if r["run_style_alignment"] == "MATCH":
        score += 35
    elif r["run_style_alignment"] == "NO_HISTORICAL_RUNNER_STYLE":
        score += 10

    if r["barrier_alignment"] == "MATCH":
        score += 30

    if r["movement_alignment"] == "MATCH":
        score += 20
    elif r["movement_alignment"] == "NO_HISTORICAL_RUNNER_STYLE":
        score += 5

    conf = clean(r.get("track_profile_confidence", "")).upper()
    if conf == "HIGH":
        score += 10
    elif conf == "MEDIUM":
        score += 7
    elif conf == "LOW":
        score += 3

    sample = num(r.get("track_profile_sample_winners", ""))
    if sample is not None:
        if sample >= 30:
            score += 5
        elif sample < 5:
            score -= 5

    return max(0, min(100, int(score)))

def comment(r):
    return (
        f"Track DNA profile used: {r.get('track_profile_level','')}. "
        f"Condition group: {r.get('condition_group','UNKNOWN')}. "
        f"Season: {r.get('season','')}. "
        f"Historical winners at {r.get('track','')} {r.get('distance_bucket','')} most often profile as "
        f"{r.get('historical_run_style','UNKNOWN')}, from {r.get('historical_barrier_lane','UNKNOWN')} lanes, "
        f"with {r.get('historical_movement_profile','UNKNOWN')} movement. "
        f"Run-style alignment: {r.get('run_style_alignment','')}. "
        f"Barrier alignment: {r.get('barrier_alignment','')}. "
        f"Movement alignment: {r.get('movement_alignment','')}. "
        f"Track fit: {r.get('track_fit_band','')}."
    )

def main():
    dna = pd.read_csv(TRACK_DNA, dtype=str).fillna("")
    runner = key_cols(pd.read_csv(RUNNER_DNA, dtype=str).fillna(""))
    board = key_cols(pd.read_csv(RUNNER_BOARD, dtype=str).fillna(""))

    dna["track_key_join"] = dna["track"].map(canon)

    board_keep = [
        "track_key_join","race_no_key_join","horse_key_join",
        "track_condition","rail_position","distance"
    ]
    board_keep = [c for c in board_keep if c in board.columns]

    live = runner.merge(
        board[board_keep].drop_duplicates(["track_key_join","race_no_key_join","horse_key_join"]),
        on=["track_key_join","race_no_key_join","horse_key_join"],
        how="left",
        suffixes=("", "_board")
    )

    live["track_condition"] = live.get("track_condition", "").fillna("")
    live["condition_group"] = live["track_condition"].map(condition_group)

    if "distance_board" in live.columns:
        live["distance"] = live.apply(lambda r: clean(r.get("distance", "")) or clean(r.get("distance_board", "")), axis=1)

    live["distance_bucket"] = live["distance"].map(distance_bucket)
    live["season"] = live["race_date"].map(season_from_date)

    if "field_size" not in live.columns:
        live["field_size"] = ""

    live["runner_barrier_lane"] = live.apply(
        lambda r: barrier_lane(r.get("barrier", ""), r.get("field_size", "")),
        axis=1
    )

    rows = []

    for _, r in live.iterrows():
        profile = choose_profile(
            dna,
            r.get("track_key_join", ""),
            r.get("distance_bucket", ""),
            r.get("condition_group", "UNKNOWN"),
            r.get("season", "")
        )

        out = r.to_dict()

        if profile is None:
            out.update({
                "track_dna_match_status_v2_1": "NO_TRACK_DNA_MATCH",
                "track_profile_level": "",
                "track_profile_sample_winners": "",
                "track_profile_confidence": "",
                "historical_run_style": "",
                "historical_barrier_lane": "",
                "historical_movement_profile": "",
                "run_style_alignment": "NO_TRACK_DNA",
                "barrier_alignment": "NO_TRACK_DNA",
                "movement_alignment": "NO_TRACK_DNA",
                "track_fit_score": 0,
                "track_fit_band": "POOR",
                "track_intelligence_label_v2_1": "",
            })
        else:
            out.update({
                "track_dna_match_status_v2_1": "MATCHED",
                "track_profile_level": profile.get("profile_level", ""),
                "track_profile_sample_winners": profile.get("sample_winners", ""),
                "track_profile_confidence": profile.get("profile_confidence", ""),
                "historical_run_style": profile.get("dominant_run_style", ""),
                "historical_barrier_lane": profile.get("dominant_barrier_lane", ""),
                "historical_movement_profile": profile.get("dominant_movement_profile", ""),
                "leader_winner_share": profile.get("leader_winner_share", ""),
                "on_pace_winner_share": profile.get("on_pace_winner_share", ""),
                "midfield_winner_share": profile.get("midfield_winner_share", ""),
                "backmarker_winner_share": profile.get("backmarker_winner_share", ""),
                "inside_winner_share": profile.get("inside_winner_share", ""),
                "middle_winner_share": profile.get("middle_winner_share", ""),
                "outside_winner_share": profile.get("outside_winner_share", ""),
                "track_intelligence_label_v2_1": profile.get("track_dna_label", ""),
            })

            runner_style = clean(r.get("dominant_run_style", ""))
            runner_move = clean(r.get("movement_profile", ""))

            out["runner_run_style"] = runner_style
            out["runner_movement_profile"] = runner_move
            out["runner_style_confidence"] = clean(r.get("style_confidence", ""))
            out["runner_style_starts"] = clean(r.get("starts", ""))
            out["run_style_alignment"] = align(runner_style, out["historical_run_style"])
            out["barrier_alignment"] = align(out["runner_barrier_lane"], out["historical_barrier_lane"])
            out["movement_alignment"] = align(runner_move, out["historical_movement_profile"])
            out["track_fit_score"] = score_row(out)
            out["track_fit_band"] = fit_band(out["track_fit_score"])

        out["track_intelligence_comment_v2_1"] = comment(out)
        rows.append(out)

    outdf = pd.DataFrame(rows)
    outdf.to_csv(OUT, index=False)

    summary = pd.DataFrame([
        ["status", "COMPLETE"],
        ["rows", len(outdf)],
        ["matched_rows", int((outdf["track_dna_match_status_v2_1"] == "MATCHED").sum())],
        ["condition_groups", "; ".join([f"{k}:{v}" for k,v in outdf["condition_group"].value_counts().to_dict().items()])],
        ["profile_levels_used", "; ".join([f"{k}:{v}" for k,v in outdf["track_profile_level"].value_counts().to_dict().items()])],
        ["elite_rows", int((outdf["track_fit_band"] == "ELITE").sum())],
        ["strong_rows", int((outdf["track_fit_band"] == "STRONG").sum())],
        ["positive_rows", int((outdf["track_fit_band"] == "POSITIVE").sum())],
        ["neutral_rows", int((outdf["track_fit_band"] == "NEUTRAL").sum())],
        ["poor_rows", int((outdf["track_fit_band"] == "POOR").sum())],
        ["output", OUT.name],
    ], columns=["metric", "value"])

    summary.to_csv(SUMMARY, index=False)

    print("[LIVE_TRACK_INTELLIGENCE_V2_1] COMPLETE")
    print(f"rows={len(outdf)}")
    print(f"matched={(outdf['track_dna_match_status_v2_1'] == 'MATCHED').sum()}")
    print("condition_groups=" + "; ".join([f"{k}:{v}" for k,v in outdf["condition_group"].value_counts().to_dict().items()]))
    print("profile_levels_used=" + "; ".join([f"{k}:{v}" for k,v in outdf["track_profile_level"].value_counts().to_dict().items()]))
    print(f"wrote={OUT}")

if __name__ == "__main__":
    main()


