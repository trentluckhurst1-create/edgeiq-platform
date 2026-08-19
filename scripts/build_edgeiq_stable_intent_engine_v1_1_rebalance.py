import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INP = DATA / "edgeiq_stable_intent_engine_v1.csv"
OUT = DATA / "edgeiq_stable_intent_engine_v1_1_rebalance.csv"
SUMMARY = DATA / "edgeiq_stable_intent_engine_v1_1_rebalance_summary.csv"

def fnum(x, default=0):
    try:
        if pd.isna(x) or x == "":
            return default
        return float(x)
    except Exception:
        return default

def score_row(r):
    score = 40.0

    trainer_sig = str(r.get("trainer_prep_signal", "NO_PROFILE"))
    combo_sig = str(r.get("stable_intent_signal", "NO_PROFILE"))
    conn_band = str(r.get("connection_band", "NO_PROFILE"))

    trainer_score = fnum(r.get("trainer_prep_score"), 40)
    combo_score = fnum(r.get("stable_intent_score"), 40)
    conn_score = fnum(r.get("connection_score"), 50)

    score = max(score, trainer_score * 0.75)
    score = max(score, combo_score * 0.80)

    if conn_band in ["ELITE", "STRONG", "POSITIVE"]:
        score += 8
    elif conn_band in ["POOR"]:
        score -= 10
    elif conn_band in ["NEGATIVE"]:
        score -= 5

    if trainer_sig == "MILD_PREP_CONTEXT_EDGE":
        score = max(score, 52)
    if "EDGE" in trainer_sig:
        score = max(score, 56)
    if combo_sig == "COMBO_PREP_EDGE":
        score = max(score, 75)
    if combo_sig == "MILD_COMBO_PREP_EDGE":
        score = max(score, 64)

    if "RISK" in trainer_sig:
        score = min(score, 45)
    if combo_sig == "COMBO_PREP_RISK":
        score = min(score, 35)

    return round(max(0, min(100, score)), 1)

def band_row(r):
    score = fnum(r["stable_intent_v1_1_score"])
    trainer_sig = str(r.get("trainer_prep_signal", "NO_PROFILE"))
    combo_sig = str(r.get("stable_intent_signal", "NO_PROFILE"))
    conn_band = str(r.get("connection_band", "NO_PROFILE"))

    has_actual_risk = (
        trainer_sig == "PREP_CONTEXT_RISK" or
        combo_sig == "COMBO_PREP_RISK" or
        conn_band == "POOR"
    )

    if score >= 75:
        return "STRONG_INTENT"
    if score >= 62:
        return "POSITIVE_INTENT"
    if score >= 50:
        return "WATCH"
    if score >= 38:
        if has_actual_risk:
            return "CAUTION"
        return "WATCH"
    return "LOW_EVIDENCE"

def reason_row(r):
    bits = []

    if str(r.get("trainer_prep_signal", "")) not in ["", "NO_PROFILE"]:
        bits.append(f"Trainer prep: {r.get('trainer_prep_signal')}")

    if str(r.get("stable_intent_signal", "")) not in ["", "NO_PROFILE"]:
        bits.append(f"Trainer/jockey prep: {r.get('stable_intent_signal')}")

    if str(r.get("connection_band", "")) not in ["", "NO_PROFILE"]:
        bits.append(f"Connection: {r.get('connection_band')}")

    if not bits:
        return "Low evidence stable-intent profile."

    return " | ".join(bits)

print("[STABLE_INTENT_ENGINE_V1_1_REBALANCE] loading V1...")
df = pd.read_csv(INP, low_memory=False)

df["stable_intent_v1_1_score"] = df.apply(score_row, axis=1)
df["stable_intent_v1_1_band"] = df.apply(band_row, axis=1)
df["stable_intent_v1_1_reason"] = df.apply(reason_row, axis=1)
df["rebalance_status"] = "RESEARCH_REBALANCE_ONLY"
df["built_at_v1_1"] = datetime.now(timezone.utc).isoformat()

df.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "STABLE_INTENT_ENGINE_V1_1_REBALANCE_BUILT",
    "rows": len(df),
    "strong_intent": int((df["stable_intent_v1_1_band"] == "STRONG_INTENT").sum()),
    "positive_intent": int((df["stable_intent_v1_1_band"] == "POSITIVE_INTENT").sum()),
    "watch": int((df["stable_intent_v1_1_band"] == "WATCH").sum()),
    "caution": int((df["stable_intent_v1_1_band"] == "CAUTION").sum()),
    "low_evidence": int((df["stable_intent_v1_1_band"] == "LOW_EVIDENCE").sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[STABLE_INTENT_ENGINE_V1_1_REBALANCE] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))


