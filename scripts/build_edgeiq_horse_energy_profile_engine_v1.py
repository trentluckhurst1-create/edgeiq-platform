from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path.cwd()
DATA = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

SRC = DATA / "edgeiq_universal_sectional_memory_v1.csv"
FEATURES = DATA / "edgeiq_sectional_feature_engine_v2.csv"
INTEL = DATA / "edgeiq_sectional_intelligence_v2.csv"

OUT = DATA / "edgeiq_horse_energy_profile_v1.csv"
DIAG = DATA / "edgeiq_horse_energy_profile_v1_diagnostics.csv"

def num(v, default=0):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default

def safe(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

def classify(row):
    late = num(row.get("late_power_index"))
    burst = num(row.get("burst_index"))
    sustain = num(row.get("sustain_index"))
    fatigue = num(row.get("fatigue_risk_index"))
    weapon = num(row.get("sectional_weapon_score"))
    hidden = num(row.get("hidden_run_score"))
    coverage = safe(row.get("coverage_grade")).upper()
    profile = safe(row.get("sectional_profile")).upper()
    cluster = safe(row.get("run_style_cluster")).upper()
    tempo = safe(row.get("best_tempo_setup")).upper()

    closing_strength = round((late * 0.55) + (burst * 0.30) + (weapon * 0.15), 2)
    sustainability = round((sustain * 0.65) + (weapon * 0.25) - (fatigue * 0.20), 2)
    pressure_tolerance = round((sustain * 0.45) + (late * 0.25) + (weapon * 0.20) - (fatigue * 0.30), 2)
    collapse_risk = round((fatigue * 0.75) + max(0, 60 - sustain) * 0.25, 2)

    if "LOW_SAMPLE" in profile or coverage in {"LOW", ""}:
        archetype = "LOW_SAMPLE_UNKNOWN"
    elif closing_strength >= 88 and sustainability >= 82:
        archetype = "ELITE_SUSTAINING_CLOSER"
    elif closing_strength >= 88:
        archetype = "EXPLOSIVE_LATE_CLOSER"
    elif sustainability >= 86 and pressure_tolerance >= 80:
        archetype = "PRESSURE_SUSTAINER"
    elif burst >= 86 and sustain < 75:
        archetype = "SHORT_BURST_RUNNER"
    elif fatigue >= 65:
        archetype = "PRESSURE_VULNERABLE"
    elif sustain >= 80:
        archetype = "ONE_PACE_GRINDER"
    else:
        archetype = "BALANCED_PROFILE"

    if "HOT" in tempo or "HIGH_PRESSURE" in tempo:
        tempo_advantage = "SUITS_HOT_TEMPO" if pressure_tolerance >= 75 else "VULNERABLE_HOT_TEMPO"
    elif "FAST" in tempo:
        tempo_advantage = "SUITS_FAST_TEMPO" if closing_strength >= 75 else "NEUTRAL_FAST_TEMPO"
    elif "SLOW" in tempo:
        tempo_advantage = "SUITS_SLOW_TEMPO" if burst >= 80 else "NEUTRAL_SLOW_TEMPO"
    else:
        tempo_advantage = "UNKNOWN_TEMPO"

    if coverage == "HIGH":
        confidence = 85
    elif coverage == "MEDIUM":
        confidence = 65
    elif coverage == "LOW":
        confidence = 35
    else:
        confidence = 20

    if num(row.get("master_rows")) >= 3:
        confidence += 10
    if num(row.get("feature_rows")) >= 3:
        confidence += 10
    if archetype == "LOW_SAMPLE_UNKNOWN":
        confidence -= 20

    confidence = max(0, min(100, confidence))

    if confidence >= 80:
        confidence_band = "HIGH"
    elif confidence >= 55:
        confidence_band = "MEDIUM"
    elif confidence >= 30:
        confidence_band = "LOW"
    else:
        confidence_band = "VERY_LOW"

    energy_edge_score = round(
        (closing_strength * 0.25)
        + (sustainability * 0.25)
        + (pressure_tolerance * 0.25)
        + (weapon * 0.20)
        - (collapse_risk * 0.10),
        2
    )

    if confidence < 40:
        edge_tier = "UNTRUSTED"
    elif energy_edge_score >= 85:
        edge_tier = "ELITE_ENERGY_EDGE"
    elif energy_edge_score >= 75:
        edge_tier = "STRONG_ENERGY_EDGE"
    elif energy_edge_score >= 62:
        edge_tier = "USABLE_ENERGY_EDGE"
    else:
        edge_tier = "NO_ENERGY_EDGE"

    note = (
        f"{archetype} | tempo={tempo_advantage} | "
        f"close={closing_strength} sustain={sustainability} pressure={pressure_tolerance} "
        f"collapse={collapse_risk} confidence={confidence_band}"
    )

    return {
        "energy_archetype": archetype,
        "tempo_advantage": tempo_advantage,
        "closing_strength": closing_strength,
        "sustainability_rating": sustainability,
        "pressure_tolerance": pressure_tolerance,
        "collapse_risk": collapse_risk,
        "energy_edge_score": energy_edge_score,
        "energy_edge_tier": edge_tier,
        "energy_confidence_score": confidence,
        "energy_confidence_band": confidence_band,
        "energy_profile_note": note,
    }

def main():
    if not SRC.exists():
        raise FileNotFoundError(f"Missing {SRC}")

    memory = pd.read_csv(SRC, low_memory=False)

    rows = []
    for _, row in memory.iterrows():
        calc = classify(row)
        rows.append({
            "horse": row.get("horse", ""),
            "horse_key": row.get("horse_key", ""),
            "sectional_sources": row.get("sectional_sources", ""),
            "coverage_score": row.get("coverage_score", ""),
            "coverage_grade": row.get("coverage_grade", ""),
            "projected_map_style": row.get("projected_map_style", ""),
            "run_style_cluster": row.get("run_style_cluster", ""),
            "sectional_profile": row.get("sectional_profile", ""),
            "preferred_distance_bucket": row.get("preferred_distance_bucket", ""),
            "preferred_track": row.get("preferred_track", ""),
            "best_tempo_setup": row.get("best_tempo_setup", ""),
            "late_power_index": row.get("late_power_index", ""),
            "burst_index": row.get("burst_index", ""),
            "sustain_index": row.get("sustain_index", ""),
            "fatigue_risk_index": row.get("fatigue_risk_index", ""),
            "sectional_weapon_score": row.get("sectional_weapon_score", ""),
            "hidden_run_score": row.get("hidden_run_score", ""),
            **calc,
        })

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)

    diag = pd.DataFrame([{
        "rows": len(out),
        "high_confidence": int((out["energy_confidence_band"] == "HIGH").sum()),
        "medium_confidence": int((out["energy_confidence_band"] == "MEDIUM").sum()),
        "low_confidence": int((out["energy_confidence_band"] == "LOW").sum()),
        "elite_energy_edges": int((out["energy_edge_tier"] == "ELITE_ENERGY_EDGE").sum()),
        "strong_energy_edges": int((out["energy_edge_tier"] == "STRONG_ENERGY_EDGE").sum()),
        "usable_energy_edges": int((out["energy_edge_tier"] == "USABLE_ENERGY_EDGE").sum()),
        "untrusted": int((out["energy_edge_tier"] == "UNTRUSTED").sum()),
    }])

    diag.to_csv(DIAG, index=False)

    print("=" * 100)
    print("EDGEIQ HORSE ENERGY PROFILE ENGINE V1")
    print("=" * 100)
    print(diag.to_string(index=False))

    print()
    print("=" * 100)
    print("TOP HORSE ENERGY PROFILES")
    print("=" * 100)

    cols = [
        "horse","energy_archetype","tempo_advantage",
        "energy_edge_score","energy_edge_tier",
        "energy_confidence_band","closing_strength",
        "sustainability_rating","pressure_tolerance",
        "collapse_risk","energy_profile_note"
    ]

    print(
        out.sort_values(["energy_edge_score","energy_confidence_score"], ascending=False)
        [cols]
        .head(30)
        .to_string(index=False)
    )

    print()
    print("SAVED:")
    print(OUT)
    print(DIAG)

if __name__ == "__main__":
    main()
