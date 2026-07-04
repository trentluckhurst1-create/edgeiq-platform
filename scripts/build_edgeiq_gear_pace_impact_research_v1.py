from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import re

DATA = Path("public/data")
HIST = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
RUNSTYLE = DATA / "edgeiq_historical_run_style_v1.csv"
OUT = DATA / "edgeiq_gear_pace_impact_research_v1.csv"
SUMMARY = DATA / "edgeiq_gear_pace_impact_research_v1_summary.csv"
REPORT = DATA / "edgeiq_gear_pace_impact_research_v1_report.txt"

def clean(v): return "" if pd.isna(v) else str(v).strip()
def nt(v): return re.sub(r"\s+", " ", clean(v).upper()).strip()
def nr(v):
    s=clean(v).upper().replace("R", "")
    try: return str(int(float(s)))
    except Exception: return s
def nh(v): return re.sub(r"[^A-Z0-9]+", "", clean(v).upper())
def num(s): return pd.to_numeric(s, errors="coerce")
def parse_date_series(s):
    raw = s.astype(str).str.strip()
    parsed = pd.to_datetime(raw, errors="coerce")
    mask = parsed.isna()
    if mask.any():
        parsed2 = pd.to_datetime(raw[mask], format="%d%b%y", errors="coerce")
        parsed.loc[mask] = parsed2
    return parsed.dt.strftime("%Y-%m-%d").fillna(raw)
def split_gear(v):
    s=clean(v)
    if not s: return []
    return [x.strip().upper() for x in re.split(r",|;|\|", s) if x.strip()]
def family(item):
    t=item.upper()
    if "BLINKER" in t and ("FIRST TIME" in t or "AGAIN" in t or "ON" in t): return "BLINKERS_ON_OR_FIRST_TIME"
    if "BLINKER" in t and "OFF" in t: return "BLINKERS_OFF"
    if "TONGUE TIE" in t and "OFF" not in t: return "TONGUE_TIE_ON"
    if "WINKER" in t and "OFF" in t: return "WINKERS_OFF"
    if "WINKER" in t and "OFF" not in t: return "WINKERS_ON"
    if "EAR MUFF" in t: return "EAR_MUFFS"
    if "GELD" in t: return "GELDED"
    if "LUGGING BIT" in t: return "LUGGING_BIT"
    if "NOSE BAND" in t or "NOSEBAND" in t: return "NOSE_BAND"
    return "OTHER_GEAR"
def research_verdict(delta, higher_good=True, threshold=2.0):
    if pd.isna(delta): return "INSUFFICIENT_DATA"
    good = delta >= threshold if higher_good else delta <= -threshold
    bad = delta <= -threshold if higher_good else delta >= threshold
    if good: return "POSITIVE_RESEARCH_SIGNAL"
    if bad: return "NEGATIVE_RESEARCH_SIGNAL"
    return "NEUTRAL_RESEARCH_SIGNAL"

hist = pd.read_csv(HIST, dtype=str, keep_default_na=False, low_memory=False)
hist["_horse_key"] = hist["horse"].map(nh)
hist["_race_no"] = hist["race_no"].map(nr)
hist["_pace_join_key"] = hist["race_date"].astype(str) + "|" + hist["_horse_key"]
hist["finish_num"] = num(hist.get("finish_num", hist.get("finish", "")))
hist["margin_num"] = num(hist.get("margin", ""))
hist["sp_num"] = num(hist.get("starting_price_decimal", hist.get("starting_price", "")))
hist["won_flag"] = hist["finish_num"].eq(1)
hist["placed_flag"] = hist["finish_num"].le(3)
gear_rows = hist[hist["gear_changes"].astype(str).str.strip().ne("")].copy()
gear_rows["gear_item_list"] = gear_rows["gear_changes"].map(split_gear)
exploded = gear_rows.explode("gear_item_list").copy()
exploded = exploded[exploded["gear_item_list"].astype(str).str.strip().ne("")]
exploded["gear_family"] = exploded["gear_item_list"].map(family)

pace_source = "NONE"
pace_cols = []
unsafe_pace_keys = 0
if RUNSTYLE.exists():
    rs = pd.read_csv(RUNSTYLE, dtype=str, keep_default_na=False, low_memory=False)
    rs["_horse_key"] = rs.get("horse_key", rs.get("horse", "")).map(nh)
    rs["_race_no"] = rs["race_no"].map(nr)
    rs["_parsed_race_date"] = parse_date_series(rs["race_date"])
    rs["_pace_join_key"] = rs["_parsed_race_date"].astype(str) + "|" + rs["_horse_key"]
    keep = ["_pace_join_key", "pos800", "pos400", "raw_in_run", "speed_figure", "gain_800_400", "run_style_v1", "movement_profile_v1", "run_style_confidence_v1"]
    keep = [c for c in keep if c in rs.columns]
    counts = rs["_pace_join_key"].value_counts()
    safe_keys = set(counts[counts == 1].index)
    unsafe_pace_keys = int((counts > 1).sum())
    rs = rs[rs["_pace_join_key"].isin(safe_keys)][keep].drop_duplicates("_pace_join_key")
    exploded = exploded.merge(rs, on="_pace_join_key", how="left")
    pace_source = RUNSTYLE.name + ":DATE_HORSE_UNIQUE"
    pace_cols = [c for c in keep if c != "_pace_join_key"]

for c in ["pos800", "pos400", "speed_figure", "gain_800_400"]:
    if c in exploded.columns:
        exploded[c + "_num"] = num(exploded[c])

pace_matched_total = int(exploded["pos800"].notna().sum()) if "pos800" in exploded.columns else 0
base_pos800 = exploded["pos800_num"].mean() if "pos800_num" in exploded else np.nan
base_pos400 = exploded["pos400_num"].mean() if "pos400_num" in exploded else np.nan
base_gain = exploded["gain_800_400_num"].mean() if "gain_800_400_num" in exploded else np.nan
base_win = exploded["won_flag"].mean() * 100 if len(exploded) else np.nan

rows=[]
for fam, g in exploded.groupby("gear_family"):
    observations = len(g)
    pace_matched = int(g["pos800"].notna().sum()) if "pos800" in g.columns else 0
    pos800 = g["pos800_num"].mean() if "pos800_num" in g else np.nan
    pos400 = g["pos400_num"].mean() if "pos400_num" in g else np.nan
    gain = g["gain_800_400_num"].mean() if "gain_800_400_num" in g else np.nan
    win_pct = g["won_flag"].mean() * 100 if observations else np.nan
    place_pct = g["placed_flag"].mean() * 100 if observations else np.nan
    style_mode = g["run_style_v1"].mode().iloc[0] if "run_style_v1" in g.columns and not g["run_style_v1"].dropna().mode().empty else ""
    early_delta = base_pos800 - pos800 if not pd.isna(pos800) and not pd.isna(base_pos800) else np.nan
    late_delta = gain - base_gain if not pd.isna(gain) and not pd.isna(base_gain) else np.nan
    win_delta = win_pct - base_win if not pd.isna(win_pct) and not pd.isna(base_win) else np.nan
    rows.append({
        "gear_family": fam,
        "observations": observations,
        "pace_matched_rows": pace_matched,
        "pace_match_pct": round(pace_matched/observations*100, 2) if observations else 0,
        "avg_pos800": round(pos800, 3) if not pd.isna(pos800) else "",
        "avg_pos400": round(pos400, 3) if not pd.isna(pos400) else "",
        "avg_gain_800_400": round(gain, 3) if not pd.isna(gain) else "",
        "win_pct": round(win_pct, 2) if not pd.isna(win_pct) else "",
        "place_pct": round(place_pct, 2) if not pd.isna(place_pct) else "",
        "dominant_run_style": style_mode,
        "early_position_delta_vs_gear_baseline": round(early_delta, 3) if not pd.isna(early_delta) else "",
        "late_gain_delta_vs_gear_baseline": round(late_delta, 3) if not pd.isna(late_delta) else "",
        "win_pct_delta_vs_gear_baseline": round(win_delta, 3) if not pd.isna(win_delta) else "",
        "early_speed_verdict": research_verdict(early_delta, True, 0.35),
        "late_finish_verdict": research_verdict(late_delta, True, 0.25),
        "outcome_verdict": research_verdict(win_delta, True, 1.5),
        "research_status": "RESEARCH_ONLY",
    })

out = pd.DataFrame(rows).sort_values(["observations"], ascending=False)
out.to_csv(OUT, index=False)
summary_rows = [
    {"metric": "status", "value": "EDGEIQ_GEAR_PACE_IMPACT_RESEARCH_V1_BUILT"},
    {"metric": "historical_rows", "value": len(hist)},
    {"metric": "historical_rows_with_gear", "value": len(gear_rows)},
    {"metric": "gear_observation_rows", "value": len(exploded)},
    {"metric": "pace_source", "value": pace_source},
    {"metric": "pace_columns_used", "value": "|".join(pace_cols)},
    {"metric": "pace_matched_rows", "value": pace_matched_total},
    {"metric": "pace_match_pct", "value": round(pace_matched_total/len(exploded)*100, 2) if len(exploded) else 0},
    {"metric": "unsafe_pace_duplicate_keys_rejected", "value": unsafe_pace_keys},
    {"metric": "families_tested", "value": len(out)},
    {"metric": "base_avg_pos800", "value": round(base_pos800, 3) if not pd.isna(base_pos800) else ""},
    {"metric": "base_avg_pos400", "value": round(base_pos400, 3) if not pd.isna(base_pos400) else ""},
    {"metric": "base_avg_gain_800_400", "value": round(base_gain, 3) if not pd.isna(base_gain) else ""},
    {"metric": "base_win_pct", "value": round(base_win, 2) if not pd.isna(base_win) else ""},
    {"metric": "production_changed", "value": "NO"},
    {"metric": "pricing_changed", "value": "NO"},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
]
pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)
def line_for(fam, question):
    r = out[out["gear_family"] == fam]
    if r.empty:
        return f"- {question}: insufficient observations."
    rr = r.iloc[0]
    return f"- {question}: {rr['observations']} observations, pace match {rr['pace_match_pct']}%, early={rr['early_speed_verdict']}, late={rr['late_finish_verdict']}, outcome={rr['outcome_verdict']}."
REPORT.write_text("\n".join([
    "EDGEIQ_GEAR_PACE_IMPACT_RESEARCH_V1",
    "====================================",
    f"Historical rows: {len(hist)}",
    f"Rows with gear: {len(gear_rows)}",
    f"Gear observation rows: {len(exploded)}",
    f"Pace source: {pace_source}",
    f"Pace matched rows: {pace_matched_total} ({round(pace_matched_total/len(exploded)*100, 2) if len(exploded) else 0}%)",
    f"Unsafe duplicate pace keys rejected: {unsafe_pace_keys}",
    f"Pace columns used: {'|'.join(pace_cols)}",
    "",
    "Research questions:",
    line_for("BLINKERS_ON_OR_FIRST_TIME", "Blinkers On / Blinkers FIRST TIME early speed or settling impact"),
    line_for("TONGUE_TIE_ON", "Tongue Tie On finish/late impact"),
    line_for("WINKERS_OFF", "Winkers Off negative/positive"),
    line_for("EAR_MUFFS", "Ear Muffs debutant impact"),
    line_for("GELDED", "Gelded first-up/second-up impact"),
    "",
    "Caveat: this is correlation research using historical gear observations joined to historical run-style positions. It is not a production model and makes no causal claim.",
    "Production changed: NO",
    "Pricing changed: NO",
]) + "\n", encoding="utf-8")
print("GEAR_PACE_IMPACT_RESEARCH_COMPLETE", len(out), pace_source, pace_matched_total)

