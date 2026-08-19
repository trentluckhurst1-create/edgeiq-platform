import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_customer_intelligence_terminal_feed_v1.csv"
OUT = DATA / "edgeiq_intelligence_summary_engine_v1.csv"
SUMMARY = DATA / "edgeiq_intelligence_summary_engine_v1_summary.csv"

if not SRC.exists():
    raise FileNotFoundError(SRC)

df = pd.read_csv(SRC, dtype=str).fillna("")

rows = []

for _, r in df.iterrows():

    score = float(r.get("edgeiq_score", 0) or 0)

    band = str(r.get("edgeiq_band", "LOW_CONVICTION"))
    stable = str(r.get("stable_intent_band", "LOW_EVIDENCE"))
    dna = str(r.get("dna_band", "NO_PROFILE"))
    context = int(float(r.get("context_signal_count", 0) or 0))

    positives = []
    risks = []

    #
    # positives
    #

    if stable == "POSITIVE_INTENT":
        positives.append(
            "Stable intent is positive."
        )
    elif stable == "WATCH":
        positives.append(
            "Stable intent deserves attention."
        )

    if context >= 2:
        positives.append(
            "Multiple historical context signals align."
        )
    elif context == 1:
        positives.append(
            "One historical context signal aligns."
        )

    if dna in ["ELITE", "STRONG", "POSITIVE"]:
        positives.append(
            f"Runner DNA profile is {dna.replace('_',' ').lower()}."
        )

    #
    # risks
    #

    if dna in ["NEGATIVE", "POOR"]:
        risks.append(
            f"Runner DNA profile is {dna.lower()}."
        )

    if stable == "LOW_EVIDENCE":
        risks.append(
            "Stable intent evidence is limited."
        )

    if context == 0:
        risks.append(
            "No major historical context signals exist."
        )

    #
    # title
    #

    title = band.replace("_", " ").upper()

    #
    # summary
    #

    positive_text = " ".join(positives)
    risk_text = " ".join(risks)

    if band == "WATCH":
        recommendation = (
            "Keep on watchlists but avoid strong conviction."
        )

    elif band == "POSITIVE":
        recommendation = (
            "Profile deserves deeper consideration."
        )

    elif band == "STRONG":
        recommendation = (
            "Strong intelligence profile with supporting evidence."
        )

    elif band == "ELITE":
        recommendation = (
            "One of the strongest intelligence profiles on the card."
        )

    else:
        recommendation = (
            "EDGEIQ does not currently have enough evidence to support this runner."
        )

    summary_text = (
        f"{positive_text} "
        f"{risk_text} "
        f"EDGEIQ recommendation: {recommendation}"
    ).strip()

    rows.append({
        "track": r.get("track", ""),
        "race_no": r.get("race_no", ""),
        "horse": r.get("horse", ""),
        "race_key": r.get("race_key", ""),
        "intelligence_summary_title": title,
        "intelligence_summary_text": summary_text,
        "intelligence_positive_text": positive_text,
        "intelligence_risk_text": risk_text,
        "customer_action_text": recommendation,
        "built_at": datetime.now(
            timezone.utc
        ).isoformat()
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    {
        "metric":"status",
        "value":"INTELLIGENCE_SUMMARY_ENGINE_V1_BUILT"
    },
    {
        "metric":"rows",
        "value":len(out)
    },
    {
        "metric":"built_at",
        "value":datetime.now(
            timezone.utc
        ).isoformat()
    }
])

summary.to_csv(SUMMARY, index=False)

print(
    "[INTELLIGENCE_SUMMARY_ENGINE_V1] COMPLETE"
)
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
