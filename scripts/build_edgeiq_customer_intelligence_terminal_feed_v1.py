import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_intelligence_score_engine_v1_1.csv"
OUT = DATA / "edgeiq_customer_intelligence_terminal_feed_v1.csv"
SUMMARY = DATA / "edgeiq_customer_intelligence_terminal_feed_v1_summary.csv"

if not SRC.exists():
    raise FileNotFoundError(SRC)

df = pd.read_csv(SRC, dtype=str).fillna("")

def clean(x):
    return str(x).strip()

def band_colour(band):
    b = clean(band).upper()
    if b == "ELITE":
        return "gold"
    if b == "STRONG":
        return "green"
    if b == "POSITIVE":
        return "blue"
    if b == "WATCH":
        return "amber"
    if b == "LOW_CONVICTION":
        return "grey"
    if b == "SCRATCHED":
        return "muted"
    return "grey"

rows = []

for _, r in df.iterrows():
    score = clean(r.get("intelligence_score_v1_1", ""))
    band = clean(r.get("intelligence_band_v1_1", ""))
    verdict = clean(r.get("intelligence_verdict_v1_1", ""))

    title = f"{score} / {band}" if band != "SCRATCHED" else "SCRATCHED"

    reasons = clean(r.get("top_reasons_v1_1", ""))
    risks = clean(r.get("top_risks_v1_1", ""))

    line = f"{r.get('horse','')} — {title}. {verdict}."

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
        "edgeiq_score": score,
        "edgeiq_band": band,
        "edgeiq_band_colour": band_colour(band),
        "edgeiq_score_title": title,
        "edgeiq_verdict": verdict,
        "stable_intent_band": r.get("stable_intent_band", ""),
        "context_signal_count": r.get("context_signal_count", ""),
        "dna_band": r.get("dna_v6_2_band_joined", ""),
        "race_understanding_band": r.get("race_understanding_band_v3_2", ""),
        "primary_reasons": reasons,
        "primary_risks": risks,
        "customer_line": line,
        "customer_narrative": r.get("customer_narrative_v1_1", ""),
        "source_customer_narrative_v3_2": r.get("source_customer_narrative_v3_2", ""),
        "built_at_terminal_feed_v1": datetime.now(timezone.utc).isoformat()
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    {"metric": "status", "value": "CUSTOMER_INTELLIGENCE_TERMINAL_FEED_V1_BUILT"},
    {"metric": "rows", "value": len(out)},
    {"metric": "scratched", "value": int((out["edgeiq_band"] == "SCRATCHED").sum())},
    {"metric": "elite", "value": int((out["edgeiq_band"] == "ELITE").sum())},
    {"metric": "strong", "value": int((out["edgeiq_band"] == "STRONG").sum())},
    {"metric": "positive", "value": int((out["edgeiq_band"] == "POSITIVE").sum())},
    {"metric": "watch", "value": int((out["edgeiq_band"] == "WATCH").sum())},
    {"metric": "low_conviction", "value": int((out["edgeiq_band"] == "LOW_CONVICTION").sum())},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
])
summary.to_csv(SUMMARY, index=False)

print("[CUSTOMER_INTELLIGENCE_TERMINAL_FEED_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
