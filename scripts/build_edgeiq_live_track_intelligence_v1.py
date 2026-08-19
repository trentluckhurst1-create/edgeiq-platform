from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TRACK_DNA = DATA / "edgeiq_track_dna_v1.csv"
LIVE_STYLE = DATA / "edgeiq_live_runner_style_v1.csv"
LIVE_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"

OUT = DATA / "edgeiq_live_track_intelligence_v1.csv"
SUMMARY = DATA / "edgeiq_live_track_intelligence_v1_summary.csv"
UNMATCHED = DATA / "edgeiq_live_track_intelligence_v1_unmatched.csv"

TRACK_CODE_MAP = {
    "SEYMOUR": "SEYM",
    "BAIRNSDALE": "BDLE",
    "SALE": "SALE",
    "BENDIGO": "BDGO",
    "FLEMINGTON": "FLEM",
    "CAULFIELD": "CAUL",
    "CAULFIELD HEATH": "CAUH",
    "MOONEE VALLEY": "M V",
    "SANDOWN": "SANH",
    "SANDOWN HILLSIDE": "SANH",
    "SANDOWN LAKESIDE": "SANL",
    "PAKENHAM": "PAKM",
    "PAKENHAM SYNTHETIC": "PAKS",
    "CRANBOURNE": "CRAN",
    "BALLARAT": "BRAT",
    "BALLARAT SYNTHETIC": "BRTS",
    "GEELONG": "GEEL",
    "WARRNAMBOOL": "WNBL",
    "MORNINGTON": "MORN",
    "WANGARATTA": "WANG",
    "WODONGA": "WOD",
    "KILMORE": "KILM",
    "KYNETON": "KYNE",
    "CASTERTON": "CAST",
    "COLAC": "COLR",
    "HAMILTON": "HTON",
    "ARARAT": "ARAT",
    "TERANG": "TER",
    "SWAN HILL": "SW H",
    "ECHUCA": "ECHA",
    "BENALLA": "BLLA",
    "MILDURA": "MILD",
    "MOE": "MOE",
    "STAWELL": "STAW",
    "HORSHAM": "HSHM",
    "AVOCA": "AVOC",
    "WERRIBEE": "WERR",
    "DONALD": "DON",
}

def canon_text(x):
    if pd.isna(x):
        return ""
    return re.sub(r"[^A-Z0-9]+", " ", str(x).upper()).strip()

def canon_horse(x):
    if pd.isna(x):
        return ""
    s = str(x).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[^A-Z0-9]+", "", s)

def track_code(x):
    s = canon_text(x)
    return TRACK_CODE_MAP.get(s, s)

def race_no(x):
    try:
        return str(int(float(str(x).replace("R", "").replace("Race", "").strip())))
    except Exception:
        return str(x).strip()

def distance_bucket(x):
    n = pd.to_numeric(x, errors="coerce")
    if pd.isna(n): return ""
    n = int(n)
    if n < 800: return "UNDER_800"
    if n < 1000: return "800-999"
    if n < 1200: return "1000-1199"
    if n < 1400: return "1200-1399"
    if n < 1600: return "1400-1599"
    if n < 1800: return "1600-1799"
    if n < 2000: return "1800-1999"
    if n < 2200: return "2000-2199"
    if n < 2400: return "2200-2399"
    if n < 2800: return "2400-2799"
    return "2800+"

def season(x):
    d = pd.to_datetime(x, errors="coerce")
    if pd.isna(d): return ""
    if d.month in [12,1,2]: return "SUMMER"
    if d.month in [3,4,5]: return "AUTUMN"
    if d.month in [6,7,8]: return "WINTER"
    return "SPRING"

def condition_group(x):
    s = canon_text(x)
    if "HEAVY" in s: return "HEAVY"
    if "SOFT" in s: return "SOFT"
    if "GOOD" in s: return "GOOD"
    if "FIRM" in s: return "FIRM"
    if "SYNTH" in s or "POLY" in s: return "SYNTHETIC"
    return ""

def barrier_lane(barrier, field_size):
    b = pd.to_numeric(barrier, errors="coerce")
    fs = pd.to_numeric(field_size, errors="coerce")
    if pd.isna(b) or pd.isna(fs) or fs <= 0:
        return ""
    pct = b / fs
    if pct <= 0.33: return "INSIDE"
    if pct <= 0.67: return "MIDDLE"
    return "OUTSIDE"

def clean_style(x):
    s = canon_text(x).replace(" ", "_")
    return s if s in ["LEADER","ON_PACE","MIDFIELD","BACKMARKER"] else ""

def clean_lane(x):
    s = canon_text(x)
    return s if s in ["INSIDE","MIDDLE","OUTSIDE"] else ""

def pick_dna(r, dna):
    checks = [
        ("TRACK_DISTANCE_CONDITION_SEASON",
         (dna.track_key == r.track_key) &
         (dna.distance_bucket == r.distance_bucket) &
         (dna.condition_group == r.condition_group) &
         (dna.season == r.season) &
         (dna.profile_level == "TRACK_DISTANCE_CONDITION_SEASON")),
        ("TRACK_DISTANCE_SEASON",
         (dna.track_key == r.track_key) &
         (dna.distance_bucket == r.distance_bucket) &
         (dna.season == r.season) &
         (dna.profile_level == "TRACK_DISTANCE_SEASON")),
        ("TRACK_DISTANCE_CONDITION",
         (dna.track_key == r.track_key) &
         (dna.distance_bucket == r.distance_bucket) &
         (dna.condition_group == r.condition_group) &
         (dna.profile_level == "TRACK_DISTANCE_CONDITION")),
        ("TRACK_DISTANCE",
         (dna.track_key == r.track_key) &
         (dna.distance_bucket == r.distance_bucket) &
         (dna.profile_level == "TRACK_DISTANCE")),
    ]

    for level, mask in checks:
        m = dna.loc[mask].copy()
        if len(m):
            m["_sample"] = pd.to_numeric(m["sample_winners"], errors="coerce").fillna(0)
            m["_conf"] = m["profile_confidence"].map({"HIGH":3,"MEDIUM":2,"LOW":1}).fillna(0)
            m = m.sort_values(["_conf","_sample"], ascending=False)
            d = m.iloc[0].to_dict()
            d["_level_used"] = level
            return d
    return None

def score_fit(style_align, barrier_align, dna_conf, runner_conf):
    score = 50
    score += 25 if style_align == "MATCH" else -12 if style_align == "MISMATCH" else 0
    score += 15 if barrier_align == "MATCH" else -8 if barrier_align == "MISMATCH" else 0
    score += 5 if dna_conf == "HIGH" else -3 if dna_conf == "LOW" else 0
    score += 5 if runner_conf == "HIGH" else -8 if runner_conf == "VERY_LOW" else -4 if runner_conf == "LOW" else 0
    return max(0, min(100, round(score, 1)))

def band(x):
    if x >= 80: return "ELITE"
    if x >= 68: return "STRONG"
    if x >= 55: return "POSITIVE"
    if x >= 45: return "NEUTRAL"
    if x >= 32: return "NEGATIVE"
    return "POOR"

def main():
    dna = pd.read_csv(TRACK_DNA, dtype=str, low_memory=False)
    board = pd.read_csv(LIVE_BOARD, dtype=str, low_memory=False)
    style = pd.read_csv(LIVE_STYLE, dtype=str, low_memory=False)

    dna.columns = [c.strip() for c in dna.columns]
    board.columns = [c.strip() for c in board.columns]
    style.columns = [c.strip() for c in style.columns]

    board["track_key"] = board["track"].map(track_code)
    board["race_no_key"] = board["race_no"].map(race_no)
    board["horse_key_join"] = board["horse"].map(canon_horse)
    board["distance_bucket"] = board["distance"].map(distance_bucket)
    board["season"] = board["race_date"].map(season)
    board["condition_group"] = board["track_condition"].map(condition_group)
    board["field_size"] = board.groupby(["race_date","track","race_no"])["horse"].transform("count")
    board["runner_barrier_lane"] = [barrier_lane(b, f) for b, f in zip(board["barrier"], board["field_size"])]

    style["horse_key_join"] = style["horse"].map(canon_horse)

    style_cols = [
        "horse_key_join","dominant_run_style","movement_profile","style_confidence",
        "leader_pct","onpace_pct","midfield_pct","backmarker_pct",
        "avg_pos800","avg_pos400","avg_gain_800_400",
        "runner_style_match_status","runner_style_comment"
    ]
    style_cols = [c for c in style_cols if c in style.columns]

    live = board.merge(style[style_cols], on="horse_key_join", how="left")

    dna["track_key"] = dna["track_key"].map(lambda x: str(x).upper().strip())
    dna["distance_bucket"] = dna["distance_bucket"].astype(str).str.strip()
    dna["profile_level"] = dna["profile_level"].astype(str).str.strip()
    dna["season"] = dna["season"].fillna("").map(canon_text)
    dna["condition_group"] = dna["condition_group"].fillna("").map(condition_group)

    rows = []

    for _, r in live.iterrows():
        base = r.to_dict()
        d = pick_dna(r, dna)

        if d is None:
            base.update({
                "track_dna_status": "NO_DNA_MATCH",
                "track_dna_level_used": "",
                "track_dna_dominant_run_style": "",
                "track_dna_dominant_barrier_lane": "",
                "track_dna_dominant_movement_profile": "",
                "track_dna_profile_confidence": "",
                "track_dna_sample_winners": "",
                "run_style_alignment": "UNKNOWN",
                "barrier_alignment": "UNKNOWN",
                "track_fit_score": 0,
                "track_fit_band": "NO_DNA",
                "track_intelligence_comment": "No matching Track DNA profile found for this track and distance setup."
            })
        else:
            runner_style = clean_style(base.get("dominant_run_style", ""))
            dna_style = clean_style(d.get("dominant_run_style", ""))
            runner_lane = clean_lane(base.get("runner_barrier_lane", ""))
            dna_lane = clean_lane(d.get("dominant_barrier_lane", ""))

            style_align = "MATCH" if runner_style and dna_style and runner_style == dna_style else "MISMATCH" if runner_style and dna_style else "UNKNOWN"
            barrier_align = "MATCH" if runner_lane and dna_lane and runner_lane == dna_lane else "MISMATCH" if runner_lane and dna_lane else "UNKNOWN"

            fit = score_fit(
                style_align,
                barrier_align,
                canon_text(d.get("profile_confidence", "")),
                canon_text(base.get("style_confidence", ""))
            )

            base.update({
                "track_dna_status": "MATCHED",
                "track_dna_level_used": d.get("_level_used", ""),
                "track_dna_dominant_run_style": dna_style,
                "track_dna_dominant_barrier_lane": dna_lane,
                "track_dna_dominant_movement_profile": d.get("dominant_movement_profile", ""),
                "track_dna_profile_confidence": d.get("profile_confidence", ""),
                "track_dna_sample_winners": d.get("sample_winners", ""),
                "track_dna_label": d.get("track_dna_label", ""),
                "leader_winner_share": d.get("leader_winner_share", ""),
                "on_pace_winner_share": d.get("on_pace_winner_share", ""),
                "midfield_winner_share": d.get("midfield_winner_share", ""),
                "backmarker_winner_share": d.get("backmarker_winner_share", ""),
                "inside_winner_share": d.get("inside_winner_share", ""),
                "middle_winner_share": d.get("middle_winner_share", ""),
                "outside_winner_share": d.get("outside_winner_share", ""),
                "runner_dominant_run_style": runner_style,
                "run_style_alignment": style_align,
                "barrier_alignment": barrier_align,
                "track_fit_score": fit,
                "track_fit_band": band(fit),
                "track_intelligence_comment": f"Track DNA favours {dna_style} runners from {dna_lane} lanes. This runner profiles as {runner_style or 'UNKNOWN'} from a {runner_lane or 'UNKNOWN'} draw: style {style_align}, barrier {barrier_align}. Track fit: {band(fit)}."
            })

        rows.append(base)

    out = pd.DataFrame(rows)

    preferred = [
        "race_date","track","track_key","race_no","horse_no","horse","barrier","field_size",
        "distance","distance_bucket","track_condition","condition_group","season",
        "dominant_run_style","movement_profile","style_confidence",
        "runner_barrier_lane",
        "track_dna_status","track_dna_level_used",
        "track_dna_dominant_run_style","track_dna_dominant_barrier_lane",
        "track_dna_dominant_movement_profile","track_dna_profile_confidence",
        "track_dna_sample_winners","track_dna_label",
        "run_style_alignment","barrier_alignment",
        "track_fit_score","track_fit_band","track_intelligence_comment",
        "live_price","fair_price","edge_pct","execution_action"
    ]
    cols = [c for c in preferred if c in out.columns] + [c for c in out.columns if c not in preferred]
    out = out[cols]

    out.to_csv(OUT, index=False)
    out[out["track_dna_status"] != "MATCHED"].to_csv(UNMATCHED, index=False)

    summary = []
    summary.append(("status","COMPLETE"))
    summary.append(("input_live_rows",len(live)))
    summary.append(("output_rows",len(out)))
    summary.append(("matched_rows",int((out["track_dna_status"]=="MATCHED").sum())))
    summary.append(("unmatched_rows",int((out["track_dna_status"]!="MATCHED").sum())))
    summary.append(("matched_pct",round(float((out["track_dna_status"]=="MATCHED").mean()*100),2)))

    for k,v in out["track_fit_band"].value_counts(dropna=False).to_dict().items():
        summary.append((f"track_fit_band_{k}",v))

    for k,v in out["track_dna_level_used"].value_counts(dropna=False).to_dict().items():
        summary.append((f"track_dna_level_used_{k}",v))

    pd.DataFrame(summary, columns=["metric","value"]).to_csv(SUMMARY, index=False)

    print("[LIVE_TRACK_INTELLIGENCE_V1] COMPLETE")
    print(f"rows={len(out)}")
    print(f"matched={(out['track_dna_status']=='MATCHED').sum()}")
    print(f"unmatched={(out['track_dna_status']!='MATCHED').sum()}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")
    print(f"unmatched_file={UNMATCHED}")

if __name__ == "__main__":
    main()
