import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_race_intelligence_terminal_feed_v4_graphql.csv"
OUT = DATA / "edgeiq_race_understanding_engine_v3_2_graphql.csv"
SUMMARY = DATA / "edgeiq_race_understanding_engine_v3_2_graphql_summary.csv"

if not SRC.exists():
    raise FileNotFoundError(f"Missing input: {SRC}")

df = pd.read_csv(SRC, dtype=str).fillna("")

def norm(x):
    return str(x).strip().upper()

def num(x, default=0.0):
    try:
        if str(x).strip() == "":
            return default
        return float(x)
    except Exception:
        return default

def listed(horse, text):
    h = norm(horse)
    items = [norm(x) for x in str(text).replace(";", ",").split(",")]
    return h in items

rows = []

for _, r in df.iterrows():
    horse = r.get("horse", "")
    band = r.get("stable_intent_v2_1_graphql_band", "")
    context_count = int(num(r.get("context_signal_count", "0"), 0))
    display_decision = r.get("display_decision", "")
    trainer_signal = r.get("trainer_prep_signal", "")
    combo_signal = r.get("combo_prep_signal", "")
    is_scratched = norm(r.get("is_scratched", "")) == "TRUE" or norm(display_decision) == "SCRATCHED"

    score = 0
    positives = []
    risks = []
    signal_tags = []

    if band == "POSITIVE_INTENT":
        score += 30
        positives.append("Positive stable intent detected")
        signal_tags.append("STABLE_INTENT")
    elif band == "WATCH":
        score += 22
        positives.append("Stable intent watch signal present")
        signal_tags.append("INTENT_WATCH")
    elif band == "LOW_EVIDENCE":
        score += 10
        signal_tags.append("LOW_EVIDENCE")
    else:
        score += 5

    if context_count == 1:
        score += 18
        positives.append("One historical context signal aligns")
        signal_tags.append("CONTEXT_SIGNAL")
    elif context_count == 2:
        score += 30
        positives.append("Two historical context signals align")
        signal_tags.append("MULTI_CONTEXT")
    elif context_count >= 3:
        score += 40
        positives.append("Multiple historical context signals align")
        signal_tags.append("MULTI_CONTEXT")

    context_details = []
    for i in [1, 2, 3]:
        entity_type = r.get(f"context_signal_{i}_entity_type", "")
        context = r.get(f"context_signal_{i}_context", "")
        signal = r.get(f"context_signal_{i}_signal", "")
        insight = r.get(f"context_signal_{i}_insight", "")
        if insight:
            context_details.append(f"{entity_type} {context}: {signal} — {insight}")
            positives.append(f"{context}: {signal}")

    if listed(horse, r.get("runners_helped", "")):
        score += 18
        positives.append("Race setup lists this runner as helped")
        signal_tags.append("RACE_SETUP_HELPED")

    if listed(horse, r.get("runners_hurt", "")):
        score -= 8
        risks.append("Race setup lists this runner as potentially hurt")
        signal_tags.append("RACE_SETUP_HURT")

    if trainer_signal in ["POSITIVE", "STRONG_POSITIVE", "EDGE"]:
        score += 12
        positives.append(f"Trainer prep signal: {trainer_signal}")
        signal_tags.append("TRAINER_PREP")
    elif trainer_signal in ["NEGATIVE", "RISK"]:
        score -= 10
        risks.append(f"Trainer prep signal: {trainer_signal}")

    if combo_signal in ["POSITIVE", "STRONG_POSITIVE", "EDGE"]:
        score += 12
        positives.append(f"Trainer/jockey combo signal: {combo_signal}")
        signal_tags.append("COMBO_PREP")
    elif combo_signal in ["NEGATIVE", "RISK"]:
        score -= 10
        risks.append(f"Trainer/jockey combo signal: {combo_signal}")

    decision_score = {
        "EXECUTE": 18,
        "STRONG_WATCH": 15,
        "WATCH": 12,
        "LEAN": 8,
        "PASS": 0,
        "UNDERLAY": -4,
        "NO MODEL": 0,
        "SCRATCHED": -100,
    }.get(display_decision, 0)

    score += decision_score

    if display_decision in ["WATCH", "LEAN", "EXECUTE", "STRONG_WATCH"]:
        positives.append(f"Market board decision: {display_decision}")
        signal_tags.append("MARKET_INTEREST")
    elif display_decision == "UNDERLAY":
        risks.append("Market board currently marks this runner as an underlay")
    elif display_decision == "NO MODEL":
        risks.append("No model price currently available")

    if is_scratched:
        score = 0
        band_out = "SCRATCHED"
        verdict = "Scratched runner"
    else:
        score = max(0, min(100, score))
        if score >= 70:
            band_out = "STRONG_INTELLIGENCE"
            verdict = "Strong intelligence profile"
        elif score >= 55:
            band_out = "POSITIVE_INTELLIGENCE"
            verdict = "Positive intelligence profile"
        elif score >= 40:
            band_out = "WATCH_INTELLIGENCE"
            verdict = "Worth deeper customer inspection"
        elif score >= 25:
            band_out = "LIGHT_INTEREST"
            verdict = "Some intelligence interest, but not enough for a strong view"
        else:
            band_out = "LOW_CONVICTION"
            verdict = "Limited evidence for a strong view"

    if not positives:
        positives.append("No major positive historical signal detected")
    if not risks:
        risks.append("No major risk flag detected")

    narrative = []
    if r.get("race_setup", ""):
        narrative.append("Race setup: " + r.get("race_setup", ""))
    if r.get("customer_summary", ""):
        narrative.append("Customer summary: " + r.get("customer_summary", ""))
    narrative.append("Stable intent: " + band + " — " + r.get("stable_intent_v2_1_graphql_reason", ""))
    if context_details:
        narrative.append("Historical context: " + " | ".join(context_details[:3]))
    narrative.append("Why inspect: " + " | ".join(positives[:5]))
    narrative.append("Risks: " + " | ".join(risks[:4]))
    narrative.append("EDGEIQ VERDICT: " + verdict + ".")

    rows.append({
        "race_date": r.get("race_date", ""),
        "day_bucket": r.get("day_bucket", ""),
        "track": r.get("track", ""),
        "race_no": r.get("race_no", ""),
        "race_key": r.get("race_key", ""),
        "saddlecloth": r.get("saddlecloth", ""),
        "horse": horse,
        "barrier": r.get("barrier", ""),
        "trainer": r.get("trainer", ""),
        "jockey": r.get("jockey", ""),
        "runner_status": r.get("runner_status", ""),
        "display_decision": display_decision,
        "live_price": r.get("live_price", ""),
        "fair_price": r.get("fair_price", ""),
        "edge_pct": r.get("edge_pct", ""),
        "stable_intent_band": band,
        "stable_intent_score": r.get("stable_intent_v2_1_graphql_score", ""),
        "stable_intent_reason": r.get("stable_intent_v2_1_graphql_reason", ""),
        "context_signal_count": context_count,
        "top_context_signal": r.get("context_signal_1_insight", ""),
        "race_setup": r.get("race_setup", ""),
        "customer_summary": r.get("customer_summary", ""),
        "signal_tags_v3_2": " | ".join(dict.fromkeys(signal_tags)),
        "race_understanding_score_v3_2": score,
        "race_understanding_band_v3_2": band_out,
        "customer_verdict_v3_2": verdict,
        "why_inspect_v3_2": " | ".join(positives[:5]),
        "main_risks_v3_2": " | ".join(risks[:4]),
        "customer_narrative_v3_2": " ".join(narrative),
        "built_at_v3_2": datetime.now(timezone.utc).isoformat()
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    {"metric": "status", "value": "RACE_UNDERSTANDING_ENGINE_V3_2_GRAPHQL_BUILT"},
    {"metric": "rows", "value": len(out)},
    {"metric": "scratched", "value": int((out["race_understanding_band_v3_2"] == "SCRATCHED").sum())},
    {"metric": "strong_intelligence", "value": int((out["race_understanding_band_v3_2"] == "STRONG_INTELLIGENCE").sum())},
    {"metric": "positive_intelligence", "value": int((out["race_understanding_band_v3_2"] == "POSITIVE_INTELLIGENCE").sum())},
    {"metric": "watch_intelligence", "value": int((out["race_understanding_band_v3_2"] == "WATCH_INTELLIGENCE").sum())},
    {"metric": "light_interest", "value": int((out["race_understanding_band_v3_2"] == "LIGHT_INTEREST").sum())},
    {"metric": "low_conviction", "value": int((out["race_understanding_band_v3_2"] == "LOW_CONVICTION").sum())},
    {"metric": "avg_score", "value": round(pd.to_numeric(out["race_understanding_score_v3_2"], errors="coerce").mean(), 2)},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
])
summary.to_csv(SUMMARY, index=False)

print("[RACE_UNDERSTANDING_ENGINE_V3_2_GRAPHQL] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
