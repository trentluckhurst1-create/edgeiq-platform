from pathlib import Path
import pandas as pd
import numpy as np
import re
import unicodedata

ROOT = Path.cwd()
DATA = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

LIVE = DATA / "edgeiq_probability_engine_v4_1.csv"
SPEED = DATA / "speed_map_report.csv"
ENERGY = DATA / "edgeiq_horse_energy_profile_v1.csv"

OUT = DATA / "edgeiq_horse_energy_proxy_v1.csv"
DIAG = DATA / "edgeiq_horse_energy_proxy_v1_diagnostics.csv"

COUNTRY_SUFFIXES = ["NZ","GB","IRE","FR","USA","SAF","GER","JPN","JAP","CAN","AUS","ARG","CHI","BRZ","ITY"]

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
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\([^)]*\)", "", s)
    for suffix in COUNTRY_SUFFIXES:
        s = re.sub(rf"\b{suffix}\b$", "", s).strip()
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def classify_proxy(row):
    map_style = safe(row.get("map_style")).upper()
    bucket = safe(row.get("speed_map_bucket")).upper()
    confidence = safe(row.get("confidence")).upper()
    price = num(row.get("market_price"))
    edge = num(row.get("contextual_overlay_pct"), 0)
    race_shape = safe(row.get("projected_race_shape")).upper()
    bias = safe(row.get("race_shape_bias")).upper()

    if "LEAD" in map_style or "LEADER" in bucket:
        archetype = "PROXY_FRONT_RUNNER"
        closing = 48
        sustain = 66
        pressure = 68
        fatigue = 54
    elif "ON" in map_style or "FORWARD" in map_style or "HANDY" in map_style:
        archetype = "PROXY_ON_PACE_PRESSER"
        closing = 55
        sustain = 68
        pressure = 64
        fatigue = 48
    elif "BACK" in map_style:
        archetype = "PROXY_BACKMARKER_CLOSER"
        closing = 70
        sustain = 58
        pressure = 52
        fatigue = 42
    elif "MID" in map_style:
        archetype = "PROXY_MIDFIELD_BALANCED"
        closing = 62
        sustain = 62
        pressure = 58
        fatigue = 44
    else:
        archetype = "PROXY_UNKNOWN"
        closing = 50
        sustain = 50
        pressure = 50
        fatigue = 55

    if not pd.isna(price):
        if price <= 5:
            closing += 4
            sustain += 4
            pressure += 4
            fatigue -= 4
        elif price >= 40:
            closing -= 8
            sustain -= 8
            pressure -= 8
            fatigue += 8
        elif price >= 20:
            closing -= 4
            sustain -= 4
            pressure -= 4
            fatigue += 4

    tempo_fit = "NEUTRAL"

    if race_shape in ["HOT_TEMPO", "CHAOTIC_PACE"]:
        if archetype == "PROXY_BACKMARKER_CLOSER":
            tempo_fit = "PROXY_ADVANTAGED"
            closing += 6
        elif archetype in ["PROXY_FRONT_RUNNER", "PROXY_ON_PACE_PRESSER"]:
            tempo_fit = "PROXY_PRESSURE_RISK"
            fatigue += 8
            pressure -= 5

    elif race_shape == "SLOW_TEMPO":
        if archetype in ["PROXY_FRONT_RUNNER", "PROXY_ON_PACE_PRESSER"]:
            tempo_fit = "PROXY_ADVANTAGED"
            pressure += 5
        elif archetype == "PROXY_BACKMARKER_CLOSER":
            tempo_fit = "PROXY_DISADVANTAGED"
            closing -= 5

    proxy_score = round(
        closing * 0.25 +
        sustain * 0.25 +
        pressure * 0.25 -
        fatigue * 0.15 +
        20,
        2
    )

    if confidence == "HIGH":
        proxy_conf = 65
    elif confidence == "MEDIUM":
        proxy_conf = 55
    elif confidence == "LOW":
        proxy_conf = 42
    else:
        proxy_conf = 35

    if archetype == "PROXY_UNKNOWN":
        proxy_conf -= 10

    if race_shape:
        proxy_conf += 5

    proxy_conf = max(0, min(75, proxy_conf))

    if proxy_score >= 68 and proxy_conf >= 45:
        tier = "USABLE_PROXY_EDGE"
    elif proxy_score >= 58:
        tier = "NEUTRAL_PROXY"
    else:
        tier = "WEAK_PROXY"

    note = (
        f"{archetype} | tempo={tempo_fit} | close={closing} sustain={sustain} "
        f"pressure={pressure} fatigue={fatigue} proxy_score={proxy_score} confidence={proxy_conf}"
    )

    return {
        "proxy_energy_archetype": archetype,
        "proxy_tempo_fit": tempo_fit,
        "proxy_closing_strength": round(closing, 2),
        "proxy_sustainability": round(sustain, 2),
        "proxy_pressure_tolerance": round(pressure, 2),
        "proxy_fatigue_risk": round(fatigue, 2),
        "proxy_energy_score": proxy_score,
        "proxy_energy_tier": tier,
        "proxy_confidence_score": proxy_conf,
        "proxy_profile_note": note,
    }

live = pd.read_csv(LIVE, low_memory=False)
speed = pd.read_csv(SPEED, low_memory=False)
energy = pd.read_csv(ENERGY, low_memory=False)

for df in [live, speed, energy]:
    df.columns = [c.strip() for c in df.columns]

live["horse_key_proxy"] = live["horse"].apply(canon)
speed["horse_key_proxy"] = speed["horse"].apply(canon)
energy["horse_key_proxy"] = energy["horse"].apply(canon)

speed_small = speed[[
    "race_date","track","race_no","horse_key_proxy",
    "speed_map_bucket","confidence","pace_pressure","map_style","map_comment"
]].drop_duplicates(["track","race_no","horse_key_proxy"], keep="first")

energy_keys = set(energy["horse_key_proxy"].dropna().astype(str))

out = live.merge(
    speed_small,
    how="left",
    on=["track","race_no","horse_key_proxy"]
)

out["has_real_energy_profile"] = out["horse_key_proxy"].isin(energy_keys)

calc_rows = []
for _, row in out.iterrows():
    calc_rows.append(classify_proxy(row))

calc = pd.DataFrame(calc_rows)
out = pd.concat([out, calc], axis=1)

# If real energy exists, proxy remains available but flagged secondary.
out["energy_source_type"] = np.where(
    out["has_real_energy_profile"],
    "REAL_SECTIONAL_PRIMARY",
    "PROXY_ENERGY_PRIMARY"
)

out.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "rows": len(out),
    "real_energy_profiles": int(out["has_real_energy_profile"].sum()),
    "proxy_primary_profiles": int((out["energy_source_type"] == "PROXY_ENERGY_PRIMARY").sum()),
    "usable_proxy_edges": int((out["proxy_energy_tier"] == "USABLE_PROXY_EDGE").sum()),
    "neutral_proxy": int((out["proxy_energy_tier"] == "NEUTRAL_PROXY").sum()),
    "weak_proxy": int((out["proxy_energy_tier"] == "WEAK_PROXY").sum()),
    "avg_proxy_confidence": round(pd.to_numeric(out["proxy_confidence_score"], errors="coerce").mean(), 2),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ HORSE ENERGY PROXY ENGINE V1")
print("=" * 100)
print(diag.to_string(index=False))

print()
print("=" * 100)
print("TOP PROXY ENERGY PROFILES")
print("=" * 100)

cols = [
    "track","race_no","horse","market_price",
    "map_style","speed_map_bucket",
    "projected_race_shape","race_shape_bias",
    "proxy_energy_archetype","proxy_tempo_fit",
    "proxy_energy_score","proxy_energy_tier",
    "proxy_confidence_score","energy_source_type",
    "proxy_profile_note"
]

cols = [c for c in cols if c in out.columns]

print(
    out.sort_values(["proxy_energy_score","proxy_confidence_score"], ascending=False)
    [cols]
    .head(40)
    .to_string(index=False)
)

print()
print("SAVED:")
print(OUT)
print(DIAG)
