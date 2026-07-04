from pathlib import Path
import pandas as pd
import numpy as np
import re
import unicodedata

ROOT = Path.cwd()
DATA = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

PROB = DATA / "edgeiq_probability_engine_v3.csv"
SHAPE = DATA / "edgeiq_race_shape_engine_v2.csv"
ENERGY = DATA / "edgeiq_horse_energy_profile_v1.csv"

OUT = DATA / "edgeiq_probability_engine_v4.csv"
DIAG = DATA / "edgeiq_probability_engine_v4_diagnostics.csv"

def num(v, default=np.nan):
    try:
        if pd.isna(v):
            return default
        return float(str(v).replace("$","").replace(",","").strip())
    except Exception:
        return default

def safe(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

def canon(v):
    s = str(v or "").strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def track_norm(v):
    s = safe(v).upper()
    aliases = {
        "BET365 STAWELL": "STAWELL",
        "PORT MACQUARIE": "PORT MACQUARIE",
    }
    return aliases.get(s, s)

def race_norm(v):
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s

def adjust(row):
    base_prob = num(row.get("v3_probability"))
    market_price = num(row.get("market_price"))
    market_prob = num(row.get("market_probability"))

    if pd.isna(base_prob):
        return {
            "race_shape_bonus": 0,
            "tempo_penalty": 0,
            "shape_edge": 0,
            "tempo_adjusted_probability": np.nan,
            "dynamic_fair_price": np.nan,
            "dynamic_overlay_pct": np.nan,
            "v4_pricing_action": "NO_BASE_PROBABILITY",
            "v4_reason": "No V3 probability available",
        }

    tempo_fit = safe(row.get("tempo_fit_v2")).upper()
    tempo_grade = safe(row.get("tempo_edge_grade_v2")).upper()
    shape = safe(row.get("projected_race_shape")).upper()
    bias = safe(row.get("race_shape_bias")).upper()
    archetype = safe(row.get("energy_archetype")).upper()
    energy_tier = safe(row.get("energy_edge_tier")).upper()
    confidence = safe(row.get("energy_confidence_band")).upper()

    tempo_edge = num(row.get("tempo_edge_score_v2"), 50)
    collapse = num(row.get("collapse_risk_score"), 0)
    pressure = num(row.get("pace_pressure_score"), 0)
    price = market_price

    bonus = 0.0
    penalty = 0.0

    if tempo_fit == "ADVANTAGED":
        bonus += 0.004
    elif tempo_fit == "DISADVANTAGED":
        penalty += 0.006

    if tempo_grade == "STRONG":
        bonus += 0.006
    elif tempo_grade == "POSITIVE":
        bonus += 0.003
    elif tempo_grade == "NEGATIVE":
        penalty += 0.005

    if shape in {"CHAOTIC_PACE", "HOT_TEMPO"} and bias == "CLOSER_ADVANTAGE":
        if "CLOSER" in archetype:
            bonus += 0.006
        if "PRESSURE_VULNERABLE" in archetype:
            penalty += 0.006

    if shape == "SLOW_TEMPO" and bias == "LEADER_ADVANTAGE":
        if "CLOSER" in archetype:
            penalty += 0.004
        if "SUSTAINER" in archetype or "GRINDER" in archetype:
            bonus += 0.002

    if energy_tier == "STRONG_ENERGY_EDGE":
        bonus += 0.003
    elif energy_tier == "USABLE_ENERGY_EDGE":
        bonus += 0.0015

    if confidence in {"LOW", "VERY_LOW", ""}:
        bonus *= 0.45
        penalty *= 0.75
    elif confidence == "MEDIUM":
        bonus *= 0.75
        penalty *= 0.90

    # Odds-based cap: do not let tempo logic re-inflate longshots.
    max_bonus = 0.010
    if not pd.isna(price):
        if price >= 80:
            max_bonus = 0.0015
        elif price >= 40:
            max_bonus = 0.0025
        elif price >= 20:
            max_bonus = 0.004
        elif price >= 10:
            max_bonus = 0.006
        elif price <= 4:
            max_bonus = 0.014

    bonus = min(bonus, max_bonus)
    penalty = min(penalty, 0.014)

    shape_edge = bonus - penalty

    adjusted = base_prob + shape_edge

    # Keep V4 market-anchored and sane.
    if not pd.isna(market_prob):
        floor = max(0.001, market_prob * 0.65)
        ceiling = min(0.65, market_prob * 1.45 + 0.015)
    else:
        floor = 0.001
        ceiling = 0.65

    adjusted = max(floor, min(ceiling, adjusted))

    fair = 1.0 / adjusted if adjusted > 0 else np.nan

    overlay = np.nan
    if not pd.isna(price) and not pd.isna(fair) and fair > 0:
        overlay = ((price / fair) - 1.0) * 100.0

    if pd.isna(price):
        action = "NO_LIVE_MARKET"
    elif overlay >= 18 and confidence in {"MEDIUM", "HIGH"} and tempo_fit == "ADVANTAGED":
        action = "TEMPO_UPGRADE"
    elif overlay >= 10:
        action = "WATCH_TEMPO_EDGE"
    elif overlay <= -15:
        action = "TEMPO_UNDERLAY"
    else:
        action = "MARKET_ANCHORED_PASS"

    reason = (
        f"V4 race-shape integrated | shape={shape} | bias={bias} | "
        f"tempo_fit={tempo_fit} | tempo_grade={tempo_grade} | "
        f"energy={archetype}/{energy_tier}/{confidence} | "
        f"bonus={bonus:.4f} | penalty={penalty:.4f} | shape_edge={shape_edge:.4f}"
    )

    return {
        "race_shape_bonus": round(bonus, 6),
        "tempo_penalty": round(penalty, 6),
        "shape_edge": round(shape_edge, 6),
        "tempo_adjusted_probability": round(adjusted, 6),
        "dynamic_fair_price": round(fair, 4),
        "dynamic_overlay_pct": round(overlay, 2) if not pd.isna(overlay) else np.nan,
        "v4_pricing_action": action,
        "v4_reason": reason,
    }

prob = pd.read_csv(PROB, low_memory=False)
shape = pd.read_csv(SHAPE, low_memory=False)
energy = pd.read_csv(ENERGY, low_memory=False)

for df in [prob, shape, energy]:
    df.columns = [c.strip() for c in df.columns]

prob["track_key"] = prob["track"].apply(track_norm)
shape["track_key"] = shape["track"].apply(track_norm)

prob["race_key"] = prob["race_no"].apply(race_norm)
shape["race_key"] = shape["race_no"].apply(race_norm)

prob["horse_key_merge"] = prob["horse"].apply(canon)
shape["horse_key_merge"] = shape["horse"].apply(canon)
energy["horse_key_merge"] = energy["horse"].apply(canon)

shape_cols = [
    "track_key","race_key","horse_key_merge",
    "projected_race_shape","race_shape_bias",
    "pace_pressure_score","collapse_risk_score",
    "closer_setup_score","leader_bias_score",
    "tempo_fit_v2","tempo_edge_score_v2","tempo_edge_grade_v2",
    "race_shape_note"
]

shape_small = shape[shape_cols].drop_duplicates(
    ["track_key","race_key","horse_key_merge"],
    keep="first"
)

energy_cols = [
    "horse_key_merge","energy_archetype","tempo_advantage",
    "energy_edge_score","energy_edge_tier",
    "energy_confidence_score","energy_confidence_band",
    "closing_strength","sustainability_rating",
    "pressure_tolerance","collapse_risk",
    "energy_profile_note"
]

energy_small = energy[energy_cols].drop_duplicates(
    ["horse_key_merge"],
    keep="first"
)

out = prob.merge(
    shape_small,
    how="left",
    on=["track_key","race_key","horse_key_merge"]
)

out = out.merge(
    energy_small,
    how="left",
    on="horse_key_merge"
)

calc_rows = []
for _, row in out.iterrows():
    calc_rows.append(adjust(row))

calc = pd.DataFrame(calc_rows)
out = pd.concat([out, calc], axis=1)

out.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "rows": len(out),
    "with_race_shape": int(out["projected_race_shape"].notna().sum()),
    "with_energy_profile": int(out["energy_archetype"].notna().sum()),
    "tempo_upgrades": int((out["v4_pricing_action"] == "TEMPO_UPGRADE").sum()),
    "watch_tempo_edges": int((out["v4_pricing_action"] == "WATCH_TEMPO_EDGE").sum()),
    "tempo_underlays": int((out["v4_pricing_action"] == "TEMPO_UNDERLAY").sum()),
    "avg_shape_edge": round(pd.to_numeric(out["shape_edge"], errors="coerce").mean(), 6),
    "avg_dynamic_overlay": round(pd.to_numeric(out["dynamic_overlay_pct"], errors="coerce").mean(), 2),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ PROBABILITY ENGINE V4 — RACE SHAPE INTEGRATED")
print("=" * 100)
print(diag.to_string(index=False))

print()
print("=" * 100)
print("TOP V4 TEMPO-ADJUSTED EDGES")
print("=" * 100)

cols = [
    "track","race_no","horse","market_price",
    "v3_fair_price","v3_overlay_pct",
    "dynamic_fair_price","dynamic_overlay_pct",
    "projected_race_shape","race_shape_bias",
    "tempo_fit_v2","tempo_edge_score_v2",
    "energy_archetype","energy_edge_tier",
    "energy_confidence_band",
    "v4_pricing_action","v4_reason"
]

cols = [c for c in cols if c in out.columns]

print(
    out.sort_values("dynamic_overlay_pct", ascending=False)
    [cols]
    .head(35)
    .to_string(index=False)
)

print()
print("SAVED:")
print(OUT)
print(DIAG)
