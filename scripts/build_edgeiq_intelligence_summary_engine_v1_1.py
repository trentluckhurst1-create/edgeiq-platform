import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_customer_intelligence_terminal_feed_v1.csv"
OUT = DATA / "edgeiq_intelligence_summary_engine_v1_1.csv"
SUMMARY = DATA / "edgeiq_intelligence_summary_engine_v1_1_summary.csv"

if not SRC.exists():
    raise FileNotFoundError(SRC)

df = pd.read_csv(SRC, dtype=str).fillna("")
rows = []

for _, r in df.iterrows():
    status = str(r.get("runner_status", "")).upper()
    band = str(r.get("edgeiq_band", "LOW_CONVICTION")).upper()
    stable = str(r.get("stable_intent_band", "LOW_EVIDENCE")).upper()
    dna = str(r.get("dna_band", "NO_PROFILE")).upper()
    context = int(float(r.get("context_signal_count", 0) or 0))

    if status == "SCRATCHED" or band == "SCRATCHED":
        title = "SCRATCHED"
        positive_text = ""
        risk_text = "Runner is scratched."
        recommendation = "No intelligence recommendation required."
        summary_text = "Runner is scratched. No intelligence recommendation required."
    else:
        positives = []
        risks = []

        if stable == "POSITIVE_INTENT":
            positives.append("Stable intent is positive.")
        elif stable == "WATCH":
            positives.append("Stable intent deserves attention.")

        if context >= 2:
            positives.append("Multiple historical context signals align.")
        elif context == 1:
            positives.append("One historical context signal aligns.")

        if dna in ["ELITE", "STRONG", "POSITIVE"]:
            positives.append(f"Runner DNA profile is {dna.replace('_',' ').lower()}.")

        if dna in ["NEGATIVE", "POOR"]:
            risks.append(f"Runner DNA profile is {dna.lower()}.")
        elif dna == "NO_PROFILE":
            risks.append("Runner DNA profile is unavailable.")

        if stable == "LOW_EVIDENCE":
            risks.append("Stable intent evidence is limited.")

        if context == 0:
            risks.append("No major historical context signals exist.")

        title = band.replace("_", " ")

        positive_text = " ".join(positives)
        risk_text = " ".join(risks)

        if band == "WATCH":
            recommendation = "Keep on watchlists but avoid strong conviction."
        elif band == "POSITIVE":
            recommendation = "Profile deserves deeper consideration."
        elif band == "STRONG":
            recommendation = "Strong intelligence profile with supporting evidence."
        elif band == "ELITE":
            recommendation = "One of the strongest intelligence profiles on the card."
        else:
            recommendation = "EDGEIQ does not currently have enough evidence to support this runner."

        summary_text = f"{positive_text} {risk_text} EDGEIQ recommendation: {recommendation}".strip()

    rows.append({
        "track": r.get("track", ""),
        "race_no": r.get("race_no", ""),
        "horse": r.get("horse", ""),
        "race_key": r.get("race_key", ""),
        "runner_status": r.get("runner_status", ""),
        "intelligence_summary_title": title,
        "intelligence_summary_text": summary_text,
        "intelligence_positive_text": positive_text,
        "intelligence_risk_text": risk_text,
        "customer_action_text": recommendation,
        "built_at": datetime.now(timezone.utc).isoformat()
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    {"metric": "status", "value": "INTELLIGENCE_SUMMARY_ENGINE_V1_1_BUILT"},
    {"metric": "rows", "value": len(out)},
    {"metric": "scratched", "value": int((out["intelligence_summary_title"] == "SCRATCHED").sum())},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
])
summary.to_csv(SUMMARY, index=False)

print("[INTELLIGENCE_SUMMARY_ENGINE_V1_1] COMPLETE")
print(summary.to_string(index=False))
