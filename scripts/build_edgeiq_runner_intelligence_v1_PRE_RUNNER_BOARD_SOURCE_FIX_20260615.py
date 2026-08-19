from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_CARD_CANDIDATES = [
    DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
    DATA / "edgeiq_live_terminal_feed_v1.csv",
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "race_card_report.csv",
]

SPEED_PATH = DATA / "edgeiq_projected_settling_engine_v4.csv"
SECTIONAL_PATH = DATA / "edgeiq_live_sectional_intelligence_v1.csv"

OUT_PATH = DATA / "edgeiq_runner_intelligence_v1.csv"
DIAG_PATH = DATA / "edgeiq_runner_intelligence_v1_diagnostics.csv"

def canon(x):
    return re.sub(r"[^A-Z0-9]", "", re.sub(r"\([^)]*\)", "", str(x or "").upper()))

def clean(x):
    if x is None:
        return ""
    s = str(x).strip()
    if s.upper() in {"", "NAN", "NONE", "NULL", "NA", "N/A", "-"}:
        return ""
    return s

def num(x):
    try:
        if x is None or str(x).strip() == "":
            return np.nan
        return float(str(x).replace("$", "").replace(",", "").strip())
    except Exception:
        return np.nan

def read_first_existing(paths):
    for p in paths:
        if p.exists():
            df = pd.read_csv(p, low_memory=False)
            df.columns = [c.strip() for c in df.columns]
            return df, p
    return pd.DataFrame(), None

def read_csv(path):
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    return df

def first_val(row, cols):
    for c in cols:
        if c in row.index:
            v = clean(row.get(c))
            if v:
                return v
    return ""

def price(row, cols):
    for c in cols:
        if c in row.index:
            v = num(row.get(c))
            if not pd.isna(v):
                return v
    return np.nan

print("=" * 100)
print("EDGEIQ RUNNER INTELLIGENCE ENGINE V1 - LIVE SAFE")
print("=" * 100)

card, card_source = read_first_existing(LIVE_CARD_CANDIDATES)
speed = read_csv(SPEED_PATH)
sectional = read_csv(SECTIONAL_PATH)

if card.empty:
    raise SystemExit("NO_CARD_SOURCE_FOUND")

for df in [card, speed, sectional]:
    if not df.empty and "horse_canon" not in df.columns:
        horse_col = "horse"
        if horse_col not in df.columns and "horse_name" in df.columns:
            horse_col = "horse_name"
        if horse_col in df.columns:
            df["horse_canon"] = df[horse_col].apply(canon)

for df in [card, speed, sectional]:
    if not df.empty:
        if "race_no" in df.columns:
            df["race_no"] = df["race_no"].apply(lambda x: str(int(num(x))) if not pd.isna(num(x)) else clean(x))
        if "track" in df.columns:
            df["track"] = df["track"].apply(lambda x: clean(x).upper())

merged = card.copy()

if not speed.empty and {"track", "race_no", "horse_canon"}.issubset(speed.columns):
    keep = [c for c in [
        "track","race_no","horse_canon","projected_spd","settling_band","confidence",
        "archetype","early_speed_rating","leader_pct","backmarker_pct","settling_rank"
    ] if c in speed.columns]
    speed_small = speed[keep].drop_duplicates(["track","race_no","horse_canon"])
    merged = merged.merge(speed_small, on=["track","race_no","horse_canon"], how="left", suffixes=("", "_speed"))

if not sectional.empty and {"track", "race_no", "horse_canon"}.issubset(sectional.columns):
    keep = [c for c in [
        "track","race_no","horse_canon","sectional_profile_found","runs_with_sectionals",
        "profile_depth_status","sectional_archetype","avg_early_speed","avg_mid_speed",
        "avg_late_speed","avg_peak_speed","avg_speed","avg_late_vs_early_delta",
        "avg_split_consistency_score","sectional_intelligence_status"
    ] if c in sectional.columns]
    sec_small = sectional[keep].drop_duplicates(["track","race_no","horse_canon"])
    merged = merged.merge(sec_small, on=["track","race_no","horse_canon"], how="left", suffixes=("", "_sec"))

rows = []

for _, r in merged.iterrows():
    horse = first_val(r, ["horse", "horse_name", "runner"])
    track = clean(r.get("track")).upper()
    race_no = clean(r.get("race_no"))

    projected_spd = num(r.get("projected_spd"))
    settling_band = first_val(r, ["settling_band"])
    dna_confidence = first_val(r, ["confidence", "dna_confidence"])
    archetype = first_val(r, ["archetype", "sectional_archetype"])

    avg_early = num(r.get("avg_early_speed"))
    avg_late = num(r.get("avg_late_speed"))
    avg_peak = num(r.get("avg_peak_speed"))
    avg_speed = num(r.get("avg_speed"))
    early_speed = num(r.get("early_speed_rating"))
    leader_pct = num(r.get("leader_pct"))
    backmarker_pct = num(r.get("backmarker_pct"))

    if pd.isna(projected_spd):
        base = 6.5
        if not pd.isna(avg_early):
            base -= (avg_early - 50) / 18
        elif not pd.isna(avg_speed):
            base -= (avg_speed - 50) / 22
        barrier = num(r.get("barrier"))
        field_size = num(r.get("field_size"))
        if pd.isna(field_size):
            field_size = 12
        if not pd.isna(barrier):
            base += ((barrier / max(field_size, 1)) - 0.5) * 1.2
        projected_spd = round(max(1, min(float(field_size), base)), 1)

    if not settling_band:
        if projected_spd <= 2:
            settling_band = "LEADER"
        elif projected_spd <= 5:
            settling_band = "ON PACE"
        elif projected_spd <= 9:
            settling_band = "MIDFIELD"
        else:
            settling_band = "BACKMARKER"

    if not dna_confidence:
        if clean(r.get("sectional_profile_found")).upper() == "TRUE":
            dna_confidence = "MEDIUM"
        else:
            dna_confidence = "NO DNA"

    if not archetype:
        if settling_band in ["LEADER", "ON PACE"]:
            archetype = "NATURAL LEADER"
        elif settling_band == "BACKMARKER":
            archetype = "BACKMARKER / CLOSER"
        else:
            archetype = "TACTICALLY FLEXIBLE"

    rated_price = price(r, ["rated_price", "fair_price", "ui_fair_price", "edgeiq_price"])
    live_price = price(r, ["live_price", "ui_price", "sportsbet_price", "market_price", "fixed_win"])

    edge_pct = np.nan
    if not pd.isna(live_price) and not pd.isna(rated_price) and rated_price > 0:
        edge_pct = round(((live_price / rated_price) - 1) * 100, 1)

    late_power = np.nan
    if not pd.isna(avg_late):
        late_power = round(max(0, min(100, avg_late)), 0)
    elif not pd.isna(projected_spd):
        late_power = round(max(0, min(100, projected_spd * 7.5)), 0)

    sectional_weapon = np.nan
    if not pd.isna(avg_peak) and not pd.isna(avg_late):
        sectional_weapon = round(max(0, min(100, (avg_peak * 0.6) + (avg_late * 0.4))), 0)
    elif not pd.isna(avg_peak):
        sectional_weapon = round(max(0, min(100, avg_peak)), 0)

    tactical_score = 50
    if not pd.isna(early_speed):
        tactical_score += (early_speed - 50) * 0.35
    if settling_band == "ON PACE":
        tactical_score += 8
    if settling_band == "LEADER":
        tactical_score += 6
    if settling_band == "BACKMARKER":
        tactical_score -= 5
    tactical_score = round(max(0, min(100, tactical_score)), 0)

    fatigue_risk = 35
    if settling_band in ["LEADER", "ON PACE"]:
        fatigue_risk += 10
    if not pd.isna(leader_pct) and leader_pct > 50:
        fatigue_risk += 10
    if not pd.isna(projected_spd) and projected_spd > 9:
        fatigue_risk -= 8
    fatigue_risk = round(max(0, min(100, fatigue_risk)), 0)

    confidence_score = 35
    if dna_confidence == "HIGH":
        confidence_score += 25
    elif dna_confidence == "MEDIUM":
        confidence_score += 15
    elif dna_confidence == "LOW":
        confidence_score += 5
    if not pd.isna(sectional_weapon):
        confidence_score += 12
    if not pd.isna(live_price):
        confidence_score += 8
    confidence_score = round(max(0, min(100, confidence_score)), 0)

    if pd.isna(edge_pct):
        action = "WAIT"
    elif confidence_score < 45 and edge_pct > 15:
        action = "SUPPRESS"
    elif edge_pct >= 20 and confidence_score >= 55:
        action = "EXECUTE"
    elif edge_pct >= 8:
        action = "WATCH"
    else:
        action = "PASS"

    if projected_spd <= 3:
        run_style = "FORWARD"
    elif projected_spd <= 6:
        run_style = "STALKER"
    elif projected_spd <= 9:
        run_style = "MIDFIELD"
    else:
        run_style = "CLOSER"

    rows.append({
        "race_date": first_val(r, ["race_date", "meeting_date", "date"]),
        "track": track,
        "race_no": race_no,
        "horse": horse,
        "horse_canon": canon(horse),
        "horse_no": first_val(r, ["horse_no", "saddlecloth", "runner_number"]),
        "barrier": first_val(r, ["barrier", "bar"]),
        "jockey": first_val(r, ["jockey"]),
        "trainer": first_val(r, ["trainer"]),
        "live_price": live_price,
        "fair_price": rated_price,
        "edge_pct": edge_pct,
        "execution_action": action,
        "projected_spd": projected_spd,
        "settling_band": settling_band,
        "dna_confidence": dna_confidence,
        "archetype": archetype,
        "run_style": run_style,
        "tactical_score": tactical_score,
        "late_power_index": late_power,
        "fatigue_risk_index": fatigue_risk,
        "sectional_weapon_score": sectional_weapon,
        "recent_rating_avg": "",
        "peak_rating": avg_peak,
        "confidence_score": confidence_score,
        "tempo_fit": "GOOD" if settling_band in ["ON PACE", "MIDFIELD"] else "TACTICAL",
        "intelligence_note": f"{settling_band or 'UNKNOWN'} | {archetype or 'NO ARCHETYPE'} | CONF {confidence_score}",
    })

out = pd.DataFrame(rows)
out.to_csv(OUT_PATH, index=False)

diag = pd.DataFrame([{
    "card_source": str(card_source.name if card_source else ""),
    "rows": len(out),
    "with_speed_dna": int(out["projected_spd"].notna().sum()),
    "with_late_power": int(out["late_power_index"].notna().sum()),
    "with_sectional_weapon": int(out["sectional_weapon_score"].notna().sum()),
    "with_live_price": int(out["live_price"].notna().sum()),
    "with_fair_price": int(out["fair_price"].notna().sum()),
    "execute": int((out["execution_action"] == "EXECUTE").sum()),
    "watch": int((out["execution_action"] == "WATCH").sum()),
    "pass": int((out["execution_action"] == "PASS").sum()),
    "wait": int((out["execution_action"] == "WAIT").sum()),
    "suppress": int((out["execution_action"] == "SUPPRESS").sum()),
}])

diag.to_csv(DIAG_PATH, index=False)

print("=" * 100)
print("RUNNER INTELLIGENCE COMPLETE - LIVE SAFE")
print("=" * 100)
print(diag.to_string(index=False))
print(out[[
    "race_date","track","race_no","horse","live_price","fair_price","edge_pct",
    "execution_action","projected_spd","late_power_index","sectional_weapon_score",
    "settling_band","dna_confidence","archetype","confidence_score"
]].head(40).to_string(index=False))
print("WROTE:", OUT_PATH)
print("WROTE:", DIAG_PATH)
