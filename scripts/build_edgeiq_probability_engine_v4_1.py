from pathlib import Path
import pandas as pd
import numpy as np
import re
import unicodedata

ROOT = Path.cwd()
DATA = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

IDENTITY = DATA / "edgeiq_universal_race_identity_v2.csv"
PROB_V3 = DATA / "edgeiq_probability_engine_v3.csv"
RACE_SHAPE = DATA / "edgeiq_race_shape_engine_v2.csv"
ENERGY = DATA / "edgeiq_horse_energy_profile_v1.csv"

OUT = DATA / "edgeiq_probability_engine_v4_1.csv"
DIAG = DATA / "edgeiq_probability_engine_v4_1_diagnostics.csv"

COUNTRY_SUFFIXES = [
    "NZ","GB","IRE","FR","USA","SAF","GER","JPN","JAP",
    "CAN","AUS","ARG","CHI","BRZ","ITY"
]

TRACK_ALIASES = {
    "BET365 STAWELL": "STAWELL",
    "SPORTSBET GAWLER": "GAWLER",
    "PICKLEBET PARK WERRIBEE": "WERRIBEE",
}

def safe(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

def num(v, default=np.nan):
    try:
        if pd.isna(v):
            return default
        return float(str(v).replace("$","").replace(",","").strip())
    except Exception:
        return default

def canon(v):
    s = safe(v).upper()

    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")

    s = re.sub(r"\([^)]*\)", "", s)

    for suffix in COUNTRY_SUFFIXES:
        s = re.sub(rf"\b{suffix}\b$", "", s).strip()

    s = s.replace("&", "AND")
    s = re.sub(r"[^A-Z0-9]", "", s)

    return s

def norm_track(v):
    s = safe(v).upper()
    return TRACK_ALIASES.get(s, s)

def norm_race(v):
    s = safe(v)
    if s.endswith(".0"):
        s = s[:-2]
    return s

def build_key(track, race_no, horse):

    track_key = norm_track(track)
    race_key = norm_race(race_no)
    horse_key = canon(horse)

    race_id = f"{track_key}_R{race_key}"

    return f"{race_id}_{horse_key}"

def contextual_adjust(row):

    base_prob = num(row.get("v3_probability"))
    market_prob = num(row.get("market_probability"))
    market_price = num(row.get("market_price"))

    if pd.isna(base_prob):
        return {
            "shape_bonus": 0,
            "shape_penalty": 0,
            "contextual_edge": 0,
            "contextual_probability": np.nan,
            "contextual_fair_price": np.nan,
            "contextual_overlay_pct": np.nan,
            "contextual_rating": "NO_PROBABILITY",
            "contextual_reason": "missing_base_probability"
        }

    tempo_fit = safe(row.get("tempo_fit_v2")).upper()
    shape = safe(row.get("projected_race_shape")).upper()
    bias = safe(row.get("race_shape_bias")).upper()

    energy_tier = safe(row.get("energy_edge_tier")).upper()
    confidence = safe(row.get("energy_confidence_band")).upper()
    archetype = safe(row.get("energy_archetype")).upper()

    tempo_score = num(row.get("tempo_edge_score_v2"), 50)
    collapse = num(row.get("collapse_risk_score"), 0)
    pressure = num(row.get("pace_pressure_score"), 0)

    bonus = 0.0
    penalty = 0.0

    # =============================================================================
    # TEMPO FIT
    # =============================================================================

    if tempo_fit == "ADVANTAGED":
        bonus += 0.0045

    elif tempo_fit == "DISADVANTAGED":
        penalty += 0.0065

    # =============================================================================
    # RACE SHAPE
    # =============================================================================

    if shape == "CHAOTIC_PACE":

        if "CLOSER" in archetype:
            bonus += 0.006

        if "PRESSURE_VULNERABLE" in archetype:
            penalty += 0.007

    elif shape == "HOT_TEMPO":

        if "SUSTAINER" in archetype:
            bonus += 0.004

        if "SHORT_BURST" in archetype:
            penalty += 0.004

    elif shape == "SLOW_TEMPO":

        if "CLOSER" in archetype:
            penalty += 0.003

    # =============================================================================
    # ENERGY TIER
    # =============================================================================

    if energy_tier == "ELITE_ENERGY_EDGE":
        bonus += 0.006

    elif energy_tier == "STRONG_ENERGY_EDGE":
        bonus += 0.004

    elif energy_tier == "USABLE_ENERGY_EDGE":
        bonus += 0.002

    # =============================================================================
    # CONFIDENCE MODULATION
    # =============================================================================

    if confidence == "HIGH":
        bonus *= 1.00

    elif confidence == "MEDIUM":
        bonus *= 0.75
        penalty *= 0.85

    elif confidence == "LOW":
        bonus *= 0.40
        penalty *= 0.70

    else:
        bonus *= 0.20
        penalty *= 0.60

    # =============================================================================
    # ODDS PROTECTION
    # =============================================================================

    max_bonus = 0.012

    if not pd.isna(market_price):

        if market_price >= 80:
            max_bonus = 0.0015

        elif market_price >= 40:
            max_bonus = 0.0025

        elif market_price >= 20:
            max_bonus = 0.004

        elif market_price >= 10:
            max_bonus = 0.006

    bonus = min(bonus, max_bonus)
    penalty = min(penalty, 0.014)

    edge = bonus - penalty

    contextual_prob = base_prob + edge

    # =============================================================================
    # MARKET ANCHORING
    # =============================================================================

    if not pd.isna(market_prob):

        floor = max(0.001, market_prob * 0.65)
        ceiling = min(0.70, market_prob * 1.45 + 0.02)

        contextual_prob = max(
            floor,
            min(ceiling, contextual_prob)
        )

    fair = np.nan

    if contextual_prob > 0:
        fair = 1.0 / contextual_prob

    overlay = np.nan

    if not pd.isna(market_price) and not pd.isna(fair) and fair > 0:
        overlay = ((market_price / fair) - 1.0) * 100.0

    rating = "PASS"

    if (
        not pd.isna(overlay)
        and overlay >= 18
        and tempo_fit == "ADVANTAGED"
        and confidence in ["MEDIUM", "HIGH"]
    ):
        rating = "ELITE_CONTEXTUAL_EDGE"

    elif not pd.isna(overlay) and overlay >= 10:
        rating = "POSITIVE_CONTEXTUAL_EDGE"

    elif not pd.isna(overlay) and overlay <= -15:
        rating = "NEGATIVE_CONTEXTUAL_EDGE"

    reason = (
        f"shape={shape} | fit={tempo_fit} | "
        f"energy={archetype}/{energy_tier}/{confidence} | "
        f"bonus={round(bonus,4)} | penalty={round(penalty,4)}"
    )

    return {
        "shape_bonus": round(bonus, 6),
        "shape_penalty": round(penalty, 6),
        "contextual_edge": round(edge, 6),
        "contextual_probability": round(contextual_prob, 6),
        "contextual_fair_price": round(fair, 4) if not pd.isna(fair) else np.nan,
        "contextual_overlay_pct": round(overlay, 2) if not pd.isna(overlay) else np.nan,
        "contextual_rating": rating,
        "contextual_reason": reason
    }

print("=" * 100)
print("EDGEIQ PROBABILITY ENGINE V4.1")
print("=" * 100)

identity = pd.read_csv(IDENTITY, low_memory=False)
prob = pd.read_csv(PROB_V3, low_memory=False)
shape = pd.read_csv(RACE_SHAPE, low_memory=False)
energy = pd.read_csv(ENERGY, low_memory=False)

for df in [identity, prob, shape, energy]:
    df.columns = [c.strip() for c in df.columns]

prob["universal_runner_key"] = prob.apply(
    lambda r: build_key(
        r.get("track"),
        r.get("race_no"),
        r.get("horse")
    ),
    axis=1
)

shape["universal_runner_key"] = shape.apply(
    lambda r: build_key(
        r.get("track"),
        r.get("race_no"),
        r.get("horse")
    ),
    axis=1
)

energy["horse_key"] = energy["horse"].apply(canon)

identity_small = identity[[
    "universal_runner_key",
    "source_count",
    "identity_quality"
]].drop_duplicates(
    ["universal_runner_key"],
    keep="first"
)

shape_small = shape[[
    "universal_runner_key",
    "projected_race_shape",
    "race_shape_bias",
    "pace_pressure_score",
    "collapse_risk_score",
    "tempo_fit_v2",
    "tempo_edge_score_v2",
    "tempo_edge_grade_v2",
    "race_shape_note"
]].drop_duplicates(
    ["universal_runner_key"],
    keep="first"
)

energy_small = energy[[
    "horse_key",
    "energy_archetype",
    "tempo_advantage",
    "energy_edge_score",
    "energy_edge_tier",
    "energy_confidence_score",
    "energy_confidence_band",
    "energy_profile_note"
]].drop_duplicates(
    ["horse_key"],
    keep="first"
)

out = prob.merge(
    identity_small,
    how="left",
    on="universal_runner_key"
)

out = out.merge(
    shape_small,
    how="left",
    on="universal_runner_key"
)

out["horse_key"] = out["horse"].apply(canon)

out = out.merge(
    energy_small,
    how="left",
    on="horse_key"
)

calc_rows = []

for _, row in out.iterrows():
    calc_rows.append(contextual_adjust(row))

calc = pd.DataFrame(calc_rows)

out = pd.concat([out, calc], axis=1)

out.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "rows": len(out),
    "with_identity": int(out["identity_quality"].notna().sum()),
    "with_shape": int(out["projected_race_shape"].notna().sum()),
    "with_energy": int(out["energy_archetype"].notna().sum()),
    "elite_contextual": int((out["contextual_rating"] == "ELITE_CONTEXTUAL_EDGE").sum()),
    "positive_contextual": int((out["contextual_rating"] == "POSITIVE_CONTEXTUAL_EDGE").sum()),
    "negative_contextual": int((out["contextual_rating"] == "NEGATIVE_CONTEXTUAL_EDGE").sum()),
    "avg_contextual_edge": round(
        pd.to_numeric(out["contextual_edge"], errors="coerce").mean(),
        6
    ),
    "avg_overlay": round(
        pd.to_numeric(out["contextual_overlay_pct"], errors="coerce").mean(),
        2
    )
}])

diag.to_csv(DIAG, index=False)

print(diag.to_string(index=False))

print()
print("=" * 100)
print("TOP CONTEXTUAL EDGES")
print("=" * 100)

cols = [
    "track",
    "race_no",
    "horse",
    "market_price",
    "contextual_fair_price",
    "contextual_overlay_pct",
    "projected_race_shape",
    "tempo_fit_v2",
    "energy_archetype",
    "energy_edge_tier",
    "energy_confidence_band",
    "identity_quality",
    "source_count",
    "contextual_rating",
    "contextual_reason"
]

print(
    out.sort_values(
        "contextual_overlay_pct",
        ascending=False
    )[cols]
    .head(40)
    .to_string(index=False)
)

print()
print("SAVED:")
print(OUT)
print(DIAG)

