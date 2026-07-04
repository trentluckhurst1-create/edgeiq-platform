import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_race_understanding_engine_v3_graphql.csv"
SUMMARY = DATA / "edgeiq_race_understanding_engine_v3_graphql_summary.csv"

terminal_v4 = DATA / "edgeiq_race_intelligence_terminal_feed_v4_graphql.csv"
dna_file = DATA / "edgeiq_live_runner_dna_v6_2.csv"
fallback_dna = DATA / "edgeiq_runner_dna_v6_2.csv"

if not terminal_v4.exists():
    raise FileNotFoundError(f"Missing required input: {terminal_v4}")

df = pd.read_csv(terminal_v4, dtype=str).fillna("")

def norm(s):
    return str(s).strip().upper()

def num(x, default=0.0):
    try:
        if str(x).strip() == "":
            return default
        return float(x)
    except Exception:
        return default

def first_existing(row, names, default=""):
    for n in names:
        if n in row and str(row[n]).strip():
            return str(row[n]).strip()
    return default

df["horse_key"] = df["horse"].map(norm) if "horse" in df.columns else ""

dna_path = dna_file if dna_file.exists() else fallback_dna
if dna_path.exists():
    dna = pd.read_csv(dna_path, dtype=str).fillna("")
    if "horse" in dna.columns:
        dna["horse_key"] = dna["horse"].map(norm)
        keep = [c for c in dna.columns if c in [
            "horse_key",
            "dna_v6_2_score",
            "dna_v6_2_band",
            "dna_score",
            "dna_band",
            "strongest_factor",
            "weakest_factor",
            "positive_1_factor",
            "positive_2_factor",
            "positive_3_factor",
            "negative_1_factor",
            "negative_2_factor",
            "negative_3_factor",
            "dna_narrative",
            "runner_dna_narrative"
        ]]
        dna = dna[keep].drop_duplicates("horse_key")
        df = df.merge(dna, on="horse_key", how="left", suffixes=("", "_dna"))
else:
    print("[WARN] DNA file not found. Continuing without DNA enrichment.")

rows = []

for _, r in df.iterrows():
    horse = first_existing(r, ["horse", "runner", "runner_name"])
    track = first_existing(r, ["track", "venue"])
    race_no = first_existing(r, ["race_no", "race_number"])

    stable_intent = first_existing(r, [
        "stable_intent_label",
        "intent_label",
        "stable_intent",
        "intent_band"
    ], "LOW_EVIDENCE")

    context_count = int(num(first_existing(r, [
        "context_signal_count",
        "top_context_signal_count",
        "signal_count"
    ], "0"), 0))

    top_context = first_existing(r, [
        "top_context_signal",
        "context_signal_1",
        "best_context_signal",
        "context_summary"
    ])

    race_understanding = first_existing(r, [
        "race_understanding",
        "race_understanding_narrative",
        "race_shape_summary",
        "race_command_briefing"
    ])

    dna_score = num(first_existing(r, ["dna_v6_2_score", "dna_score"], "0"), 0)
    dna_band = first_existing(r, ["dna_v6_2_band", "dna_band"], "NO_PROFILE")

    live_price = num(first_existing(r, ["live_price", "sportsbet_price", "market_price", "fixed_win"], ""), 0)
    fair_price = num(first_existing(r, ["fair_price", "rated_price", "edgeiq_fair_price"], ""), 0)

    positive_reasons = []
    risks = []

    if stable_intent == "POSITIVE_INTENT":
        positive_reasons.append("Positive stable intent detected")
    elif stable_intent == "WATCH":
        positive_reasons.append("Stable intent watch signal present")

    if context_count > 0:
        positive_reasons.append(f"{context_count} historical context signal(s) align")

    if top_context:
        positive_reasons.append(top_context)

    if dna_band in ["ELITE", "STRONG", "POSITIVE"]:
        positive_reasons.append(f"Runner DNA profile is {dna_band}")

    if fair_price > 0 and live_price > 0 and live_price > fair_price:
        positive_reasons.append("Market price is above EDGEIQ fair assessment")

    if dna_band in ["NEGATIVE", "POOR"]:
        risks.append(f"Runner DNA profile is {dna_band}")

    if stable_intent == "LOW_EVIDENCE":
        risks.append("Stable intent evidence is limited")

    if context_count == 0:
        risks.append("No strong historical context signal found")

    if fair_price > 0 and live_price > 0 and live_price < fair_price:
        risks.append("Market is shorter than EDGEIQ fair assessment")

    historical_setup_score = 0

    if stable_intent == "POSITIVE_INTENT":
        historical_setup_score += 25
    elif stable_intent == "WATCH":
        historical_setup_score += 15
    else:
        historical_setup_score += 5

    historical_setup_score += min(context_count * 8, 25)

    if dna_band == "ELITE":
        historical_setup_score += 25
    elif dna_band == "STRONG":
        historical_setup_score += 20
    elif dna_band == "POSITIVE":
        historical_setup_score += 15
    elif dna_band == "NEUTRAL":
        historical_setup_score += 8
    elif dna_band in ["NEGATIVE", "POOR"]:
        historical_setup_score -= 8

    if fair_price > 0 and live_price > 0:
        if live_price > fair_price:
            historical_setup_score += 10
        else:
            historical_setup_score -= 5

    historical_setup_score = max(0, min(100, historical_setup_score))

    if historical_setup_score >= 85:
        narrative_strength = "ELITE"
        verdict = "Exceptional historical setup"
    elif historical_setup_score >= 75:
        narrative_strength = "STRONG"
        verdict = "Strong historical setup"
    elif historical_setup_score >= 65:
        narrative_strength = "POSITIVE"
        verdict = "Positive setup with supporting signals"
    elif historical_setup_score >= 50:
        narrative_strength = "WATCH"
        verdict = "Some positives, but evidence remains mixed"
    else:
        narrative_strength = "LOW_CONVICTION"
        verdict = "Insufficient evidence for a strong view"

    why_we_like_it = " | ".join(positive_reasons[:5]) if positive_reasons else "No major positive historical signal detected"
    main_risk = " | ".join(risks[:4]) if risks else "No major risk flag detected"

    full_narrative_parts = []

    if race_understanding:
        full_narrative_parts.append(race_understanding)

    if positive_reasons:
        full_narrative_parts.append("Positive factors: " + "; ".join(positive_reasons[:5]))

    if risks:
        full_narrative_parts.append("Risks: " + "; ".join(risks[:4]))

    full_narrative_parts.append(f"EDGEIQ VERDICT: {verdict}.")

    rows.append({
        "track": track,
        "race_no": race_no,
        "horse": horse,
        "stable_intent_label": stable_intent,
        "context_signal_count": context_count,
        "top_context_signal": top_context,
        "dna_score": round(dna_score, 2),
        "dna_band": dna_band,
        "live_price": live_price,
        "fair_price": fair_price,
        "historical_setup_score": historical_setup_score,
        "narrative_strength": narrative_strength,
        "customer_verdict": verdict,
        "why_we_like_it": why_we_like_it,
        "main_risk": main_risk,
        "full_narrative": " ".join(full_narrative_parts),
        "built_at": datetime.now(timezone.utc).isoformat()
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    {"metric": "status", "value": "RACE_UNDERSTANDING_ENGINE_V3_GRAPHQL_BUILT"},
    {"metric": "rows", "value": len(out)},
    {"metric": "with_positive_reasons", "value": int((out["why_we_like_it"] != "No major positive historical signal detected").sum())},
    {"metric": "with_risks", "value": int((out["main_risk"] != "No major risk flag detected").sum())},
    {"metric": "elite", "value": int((out["narrative_strength"] == "ELITE").sum())},
    {"metric": "strong", "value": int((out["narrative_strength"] == "STRONG").sum())},
    {"metric": "positive", "value": int((out["narrative_strength"] == "POSITIVE").sum())},
    {"metric": "watch", "value": int((out["narrative_strength"] == "WATCH").sum())},
    {"metric": "low_conviction", "value": int((out["narrative_strength"] == "LOW_CONVICTION").sum())},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
])
summary.to_csv(SUMMARY, index=False)

print("[RACE_UNDERSTANDING_ENGINE_V3_GRAPHQL] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
