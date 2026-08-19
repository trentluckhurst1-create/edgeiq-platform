from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_runner_dna_explainability_feed_v2.csv"

OUT = DATA / "edgeiq_runner_dna_explainability_ui_feed_v1.csv"
SUMMARY = DATA / "edgeiq_runner_dna_explainability_ui_feed_v1_summary.csv"

FACTOR_LABELS = {
    "rating_contribution": "RATING",
    "sectional_contribution": "SECTIONALS",
    "jockey_contribution": "JOCKEY",
    "trainer_contribution": "TRAINER",
    "connection_contribution": "CONNECTION",
    "distance_contribution": "DISTANCE",
    "condition_contribution": "CONDITION",
    "pace_contribution": "PACE",
    "late_power_contribution": "LATE POWER",
    "profile_contribution": "PROFILE",
}

def num(v):
    try:
        s = str(v).replace("$", "").replace("%", "").strip()
        if s == "" or s.lower() == "nan":
            return np.nan
        return float(s)
    except Exception:
        return np.nan

def band(score):
    if pd.isna(score):
        return "UNKNOWN"
    if score >= 80:
        return "ELITE"
    if score >= 70:
        return "STRONG"
    if score >= 60:
        return "POSITIVE"
    if score >= 45:
        return "NEUTRAL"
    if score >= 30:
        return "NEGATIVE"
    return "POOR"

def factor_tone(score):
    if pd.isna(score):
        return "unknown"
    if score >= 70:
        return "positive"
    if score >= 45:
        return "neutral"
    return "negative"

def factor_bar(score):
    if pd.isna(score):
        return "----------"
    blocks = int(round(max(0, min(100, score)) / 10))
    return "█" * blocks + "░" * (10 - blocks)

def build_factor_rows(row):
    factors = []
    for col, label in FACTOR_LABELS.items():
        score = num(row.get(col, ""))
        factors.append({
            "factor": label,
            "score": round(score, 1) if not pd.isna(score) else "",
            "band": band(score),
            "tone": factor_tone(score),
            "bar": factor_bar(score),
        })
    scored = [x for x in factors if x["score"] != ""]
    strongest = sorted(scored, key=lambda x: float(x["score"]), reverse=True)[:3]
    weakest = sorted(scored, key=lambda x: float(x["score"]))[:3]
    return factors, strongest, weakest

def join_factor_list(items):
    return " | ".join([f"{x['factor']} {x['score']}" for x in items])

def explain(dna_score, dna_band, strongest, weakest):
    strong_txt = join_factor_list(strongest)
    weak_txt = join_factor_list(weakest)

    if dna_score >= 70:
        base = "Strong DNA profile with clear positive factors."
    elif dna_score >= 60:
        base = "Positive DNA profile with enough support to respect."
    elif dna_score >= 45:
        base = "Mixed DNA profile with strengths and risks both present."
    elif dna_score >= 30:
        base = "Negative DNA profile; needs market or race-shape support."
    else:
        base = "Poor DNA profile with major underlying risks."

    return f"{base} Strongest: {strong_txt}. Risks: {weak_txt}."

df = pd.read_csv(SRC, dtype=str).fillna("")

rows = []
built_at = datetime.now(timezone.utc).isoformat()

for _, r in df.iterrows():
    dna_score = num(r.get("dna_v6_2_score", ""))
    dna_band = str(r.get("dna_v6_2_band", "")).strip()

    factors, strongest, weakest = build_factor_rows(r)

    out = {
        "race_date": r.get("race_date", ""),
        "track": r.get("track", ""),
        "race_no": r.get("race_no", ""),
        "horse": r.get("horse", ""),
        "horse_key": r.get("horse_key", ""),
        "trainer": r.get("trainer", ""),
        "jockey": r.get("jockey", ""),
        "dna_score": round(dna_score, 1) if not pd.isna(dna_score) else "",
        "dna_band": dna_band,
        "dna_tone": factor_tone(dna_score),
        "strongest_factors_ui": join_factor_list(strongest),
        "weakest_factors_ui": join_factor_list(weakest),
        "dna_explanation": explain(dna_score if not pd.isna(dna_score) else 0, dna_band, strongest, weakest),
        "factor_count": len([x for x in factors if x["score"] != ""]),
        "research_only": "NO",
        "built_at": built_at,
    }

    for i, x in enumerate(strongest, start=1):
        out[f"strong_{i}_factor"] = x["factor"]
        out[f"strong_{i}_score"] = x["score"]
        out[f"strong_{i}_band"] = x["band"]
        out[f"strong_{i}_tone"] = x["tone"]
        out[f"strong_{i}_bar"] = x["bar"]

    for i, x in enumerate(weakest, start=1):
        out[f"weak_{i}_factor"] = x["factor"]
        out[f"weak_{i}_score"] = x["score"]
        out[f"weak_{i}_band"] = x["band"]
        out[f"weak_{i}_tone"] = x["tone"]
        out[f"weak_{i}_bar"] = x["bar"]

    for x in factors:
        key = x["factor"].lower().replace(" ", "_")
        out[f"{key}_score"] = x["score"]
        out[f"{key}_band"] = x["band"]
        out[f"{key}_tone"] = x["tone"]
        out[f"{key}_bar"] = x["bar"]

    rows.append(out)

out_df = pd.DataFrame(rows)
out_df.to_csv(OUT, index=False)

summary = pd.DataFrame([
    {"metric": "status", "value": "RUNNER_DNA_EXPLAINABILITY_UI_FEED_V1_BUILT"},
    {"metric": "source", "value": SRC.name},
    {"metric": "output", "value": OUT.name},
    {"metric": "rows", "value": len(out_df)},
    {"metric": "avg_dna_score", "value": round(pd.to_numeric(out_df["dna_score"], errors="coerce").mean(), 3)},
    {"metric": "elite_count", "value": int((out_df["dna_band"] == "ELITE").sum())},
    {"metric": "strong_count", "value": int((out_df["dna_band"] == "STRONG").sum())},
    {"metric": "positive_count", "value": int((out_df["dna_band"] == "POSITIVE").sum())},
    {"metric": "neutral_count", "value": int((out_df["dna_band"] == "NEUTRAL").sum())},
    {"metric": "negative_count", "value": int((out_df["dna_band"] == "NEGATIVE").sum())},
    {"metric": "poor_count", "value": int((out_df["dna_band"] == "POOR").sum())},
    {"metric": "built_at", "value": built_at},
])
summary.to_csv(SUMMARY, index=False)

print("[RUNNER_DNA_EXPLAINABILITY_UI_FEED_V1] COMPLETE")
print(summary.to_string(index=False))
print(out_df[[
    "horse",
    "dna_score",
    "dna_band",
    "strongest_factors_ui",
    "weakest_factors_ui",
    "dna_explanation"
]].head(20).to_string(index=False))
