import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

RU = DATA / "edgeiq_race_understanding_engine_v3_2_graphql.csv"
OUT = DATA / "edgeiq_intelligence_score_engine_v1.csv"
SUMMARY = DATA / "edgeiq_intelligence_score_engine_v1_summary.csv"

if not RU.exists():
    raise FileNotFoundError(f"Missing input: {RU}")

df = pd.read_csv(RU, dtype=str).fillna("")

def num(x, default=0.0):
    try:
        if str(x).strip() == "":
            return default
        return float(x)
    except Exception:
        return default

def norm(x):
    return str(x).strip().upper()

rows = []

for _, r in df.iterrows():
    status = norm(r.get("runner_status", ""))
    decision = norm(r.get("display_decision", ""))
    scratched = status == "SCRATCHED" or decision == "SCRATCHED"

    ru_score_raw = num(r.get("race_understanding_score_v3_2", ""), 0)
    ru_component = min(30, ru_score_raw * 0.30)

    stable_band = norm(r.get("stable_intent_band", ""))
    if stable_band == "POSITIVE_INTENT":
        stable_component = 20
    elif stable_band == "WATCH":
        stable_component = 14
    elif stable_band == "LOW_EVIDENCE":
        stable_component = 6
    else:
        stable_component = 3

    context_count = int(num(r.get("context_signal_count", "0"), 0))
    if context_count >= 3:
        context_component = 20
    elif context_count == 2:
        context_component = 16
    elif context_count == 1:
        context_component = 10
    else:
        context_component = 0

    # DNA intentionally neutral for now because V3.2 source is GraphQL intelligence only.
    # Kept as an explicit component so V1 matches the future architecture.
    dna_component = 10

    market_component = {
        "EXECUTE": 10,
        "STRONG_WATCH": 8,
        "WATCH": 6,
        "LEAN": 4,
        "PASS": 2,
        "NO MODEL": 1,
        "UNDERLAY": 0,
        "SCRATCHED": 0,
    }.get(decision, 1)

    total = ru_component + stable_component + context_component + dna_component + market_component

    if scratched:
        total = 0
        band = "SCRATCHED"
        verdict = "Scratched runner"
    else:
        total = round(max(0, min(100, total)), 2)
        if total >= 85:
            band = "ELITE"
            verdict = "Elite intelligence profile"
        elif total >= 70:
            band = "STRONG"
            verdict = "Strong intelligence profile"
        elif total >= 55:
            band = "POSITIVE"
            verdict = "Positive intelligence profile"
        elif total >= 40:
            band = "WATCH"
            verdict = "Watchlist intelligence profile"
        else:
            band = "LOW_CONVICTION"
            verdict = "Low conviction intelligence profile"

    reasons = []
    risks = []

    if ru_score_raw >= 55:
        reasons.append("Race understanding profile is positive")
    elif ru_score_raw >= 40:
        reasons.append("Race understanding profile is worth inspection")

    if stable_band == "POSITIVE_INTENT":
        reasons.append("Stable intent is positive")
    elif stable_band == "WATCH":
        reasons.append("Stable intent is watch")

    if context_count > 0:
        reasons.append(f"{context_count} historical context signal(s) identified")

    if decision in ["WATCH", "LEAN", "EXECUTE", "STRONG_WATCH"]:
        reasons.append(f"Market board shows {decision}")

    if decision == "UNDERLAY":
        risks.append("Current market board marks runner as underlay")
    if context_count == 0:
        risks.append("No major GraphQL context signal")
    if stable_band == "LOW_EVIDENCE":
        risks.append("Stable intent evidence is limited")

    if not reasons:
        reasons.append("No major positive intelligence factor")
    if not risks:
        risks.append("No major risk flag")

    rows.append({
        "race_date": r.get("race_date", ""),
        "day_bucket": r.get("day_bucket", ""),
        "track": r.get("track", ""),
        "race_no": r.get("race_no", ""),
        "race_key": r.get("race_key", ""),
        "saddlecloth": r.get("saddlecloth", ""),
        "horse": r.get("horse", ""),
        "barrier": r.get("barrier", ""),
        "trainer": r.get("trainer", ""),
        "jockey": r.get("jockey", ""),
        "runner_status": r.get("runner_status", ""),
        "display_decision": r.get("display_decision", ""),
        "live_price": r.get("live_price", ""),
        "fair_price": r.get("fair_price", ""),
        "edge_pct": r.get("edge_pct", ""),
        "race_understanding_score_v3_2": ru_score_raw,
        "race_understanding_band_v3_2": r.get("race_understanding_band_v3_2", ""),
        "stable_intent_band": r.get("stable_intent_band", ""),
        "context_signal_count": context_count,
        "intelligence_score_v1": total,
        "intelligence_band_v1": band,
        "intelligence_verdict_v1": verdict,
        "race_understanding_component_30": round(ru_component, 2),
        "stable_intent_component_20": round(stable_component, 2),
        "context_component_20": round(context_component, 2),
        "runner_dna_component_20_placeholder": round(dna_component, 2),
        "market_component_10": round(market_component, 2),
        "top_reasons_v1": " | ".join(reasons[:5]),
        "top_risks_v1": " | ".join(risks[:5]),
        "customer_narrative_v1": (
            f"EDGEIQ Intelligence Score: {total} ({band}). "
            f"Verdict: {verdict}. "
            f"Why: {' | '.join(reasons[:5])}. "
            f"Risks: {' | '.join(risks[:5])}."
        ),
        "source_customer_narrative_v3_2": r.get("customer_narrative_v3_2", ""),
        "built_at_v1": datetime.now(timezone.utc).isoformat()
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    {"metric": "status", "value": "INTELLIGENCE_SCORE_ENGINE_V1_BUILT"},
    {"metric": "rows", "value": len(out)},
    {"metric": "scratched", "value": int((out["intelligence_band_v1"] == "SCRATCHED").sum())},
    {"metric": "elite", "value": int((out["intelligence_band_v1"] == "ELITE").sum())},
    {"metric": "strong", "value": int((out["intelligence_band_v1"] == "STRONG").sum())},
    {"metric": "positive", "value": int((out["intelligence_band_v1"] == "POSITIVE").sum())},
    {"metric": "watch", "value": int((out["intelligence_band_v1"] == "WATCH").sum())},
    {"metric": "low_conviction", "value": int((out["intelligence_band_v1"] == "LOW_CONVICTION").sum())},
    {"metric": "avg_score", "value": round(pd.to_numeric(out["intelligence_score_v1"], errors="coerce").mean(), 2)},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
])
summary.to_csv(SUMMARY, index=False)

print("[INTELLIGENCE_SCORE_ENGINE_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
