import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_BET_QUALITY = DATA / "edgeiq_live_bet_quality_v1_1.csv"

OUT_CSV = DATA / "edgeiq_live_intelligence_score_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_live_intelligence_score_v1_summary.csv"
OUT_JSON = DATA / "edgeiq_live_intelligence_score_v1.json"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")


def n(x, default=0.0):
    try:
        s = str(x).strip()
        if s == "":
            return default
        return float(s)
    except Exception:
        return default


def clean(x):
    return str(x or "").strip()


def upper(x):
    return clean(x).upper()


def clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(x)))


def norm_component(value, max_value):
    return clamp((n(value) / max_value) * 100.0)


def tj_score(row):
    trainer = upper(row.get("trainer_factor_band_v1", ""))
    jockey = upper(row.get("jockey_factor_band_v1", ""))
    blend = upper(row.get("trainer_jockey_blend_band_v1", ""))

    score = 50.0

    for band in [trainer, jockey, blend]:
        if "ELITE" in band:
            score += 18
        elif "POSITIVE" in band or "STRONG" in band:
            score += 12
        elif "NEGATIVE" in band or "POOR" in band:
            score -= 12
        elif "WEAK" in band:
            score -= 8

    raw = n(row.get("trainer_jockey_blend_score_v1", ""), math.nan)
    if not math.isnan(raw):
        if raw <= 100:
            score = (score * 0.45) + (raw * 0.55)

    return clamp(score)


def tempo_score(row):
    grade = upper(row.get("tempo_edge_grade", ""))
    fit = upper(row.get("tempo_fit", ""))
    raw = n(row.get("tempo_edge_score", ""), math.nan)

    if not math.isnan(raw):
        if raw <= 10:
            base = raw * 10.0
        elif raw <= 100:
            base = raw
        else:
            base = 50.0
    else:
        base = 50.0

    if "ELITE" in grade:
        base += 18
    elif "STRONG" in grade or "GOOD" in grade:
        base += 12
    elif "POSITIVE" in grade:
        base += 8
    elif "NEGATIVE" in grade or "POOR" in grade:
        base -= 12

    if "SUITS" in fit or "POSITIVE" in fit or "ADVANTAGE" in fit:
        base += 8
    elif "RISK" in fit or "NEGATIVE" in fit:
        base -= 8

    return clamp(base)


def reliability_score(row):
    component = n(row.get("reliability_score_component_v1_1", ""), math.nan)
    if not math.isnan(component):
        return norm_component(component, 20.0)

    raw = n(row.get("race_reliability_score_v1", ""), math.nan)
    if not math.isnan(raw):
        if raw <= 20:
            return norm_component(raw, 20.0)
        return clamp(raw)

    band = upper(row.get("race_reliability_band_v1", ""))
    if "ELITE" in band:
        return 100
    if "STRONG" in band or "HIGH" in band:
        return 80
    if "SOLID" in band or "MEDIUM" in band:
        return 60
    if "WEAK" in band or "LOW" in band:
        return 35
    return 50


def sectional_score(row):
    component = n(row.get("sectional_score_component_v1_1", ""), math.nan)
    if not math.isnan(component):
        return norm_component(component, 15.0)

    weapon = n(row.get("sectional_weapon_score", ""), math.nan)
    strength = n(row.get("sectional_strength_score", ""), math.nan)
    conf = n(row.get("sectional_confidence", ""), math.nan)

    vals = []
    if not math.isnan(weapon):
        vals.append(weapon if weapon <= 100 else 50)
    if not math.isnan(strength):
        vals.append(strength if strength <= 100 else 50)
    if not math.isnan(conf):
        vals.append(conf if conf <= 100 else 50)

    if vals:
        return clamp(sum(vals) / len(vals))

    archetype = upper(row.get("sectional_archetype", ""))
    if "ELITE" in archetype:
        return 100
    if "STRONG" in archetype:
        return 80
    if "LOW" in archetype:
        return 35
    return 50


def band(score):
    s = n(score)
    if s >= 90:
        return "ELITE"
    if s >= 80:
        return "STRONG"
    if s >= 70:
        return "GOOD"
    if s >= 60:
        return "SOLID"
    if s >= 50:
        return "RISKY"
    return "WEAK"


def action(score, grade, overlay):
    s = n(score)
    g = upper(grade)
    o = n(overlay)

    if s >= 80 and g in ["A+", "A", "B"] and o > 0:
        return "PRIORITY REVIEW"
    if s >= 70 and o > 0:
        return "VALUE WATCH"
    if s >= 60 and o > 0:
        return "WATCH"
    if s >= 50:
        return "NEUTRAL"
    return "AVOID"


def main():
    df = read_csv(LIVE_BET_QUALITY)
    if df.empty:
        raise SystemExit("[INTELLIGENCE_SCORE_V1] ERROR missing edgeiq_live_bet_quality_v1_1.csv")

    rows = []

    for _, row in df.iterrows():
        bet_quality = n(row.get("bet_quality_score_v1_1", ""), 0.0)
        rel = reliability_score(row)
        sec = sectional_score(row)
        tj = tj_score(row)
        tempo = tempo_score(row)

        total = (
            bet_quality * 0.40
            + rel * 0.20
            + sec * 0.20
            + tj * 0.10
            + tempo * 0.10
        )

        b = band(total)
        overlay = n(row.get("bet_quality_overlay_pct_v1_1", ""), 0.0)
        grade = clean(row.get("bet_quality_grade_v1_1", "PASS"))

        out = row.to_dict()
        out.update(
            {
                "intelligence_score_v1": round(total, 2),
                "intelligence_band_v1": b,
                "intelligence_action_v1": action(total, grade, overlay),
                "intelligence_bet_quality_component_v1": round(bet_quality, 2),
                "intelligence_reliability_component_v1": round(rel, 2),
                "intelligence_sectional_component_v1": round(sec, 2),
                "intelligence_tj_component_v1": round(tj, 2),
                "intelligence_tempo_component_v1": round(tempo, 2),
                "official_fair_price_replaced": "NO",
                "edge_execution_staking_changed": "NO",
                "intelligence_status_v1": "OBSERVATION_ONLY",
            }
        )

        rows.append(out)

    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUT_CSV, index=False)

    summary = {
        "status": "COMPLETE",
        "rows": int(len(out_df)),
        "elite_rows": int((out_df["intelligence_band_v1"] == "ELITE").sum()),
        "strong_rows": int((out_df["intelligence_band_v1"] == "STRONG").sum()),
        "good_rows": int((out_df["intelligence_band_v1"] == "GOOD").sum()),
        "solid_rows": int((out_df["intelligence_band_v1"] == "SOLID").sum()),
        "risky_rows": int((out_df["intelligence_band_v1"] == "RISKY").sum()),
        "weak_rows": int((out_df["intelligence_band_v1"] == "WEAK").sum()),
        "avg_intelligence_score": round(float(pd.to_numeric(out_df["intelligence_score_v1"], errors="coerce").mean()), 4),
        "max_intelligence_score": round(float(pd.to_numeric(out_df["intelligence_score_v1"], errors="coerce").max()), 4),
        "official_fair_price_replaced": "NO",
        "edge_execution_staking_changed": "NO",
        "verdict": "LIVE_INTELLIGENCE_SCORE_V1_BUILT_OBSERVATION_ONLY",
    }

    pd.DataFrame([{"metric": k, "value": v} for k, v in summary.items()]).to_csv(OUT_SUMMARY, index=False)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("[INTELLIGENCE_SCORE_V1] COMPLETE")
    for k, v in summary.items():
        print(f"{k}={v}")
    print(f"wrote={OUT_CSV}")


if __name__ == "__main__":
    main()
