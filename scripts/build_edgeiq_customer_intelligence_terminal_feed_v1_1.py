# build_edgeiq_customer_intelligence_terminal_feed_v1_1.py

from pathlib import Path
import pandas as pd

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

src = DATA / "edgeiq_customer_intelligence_terminal_feed_v1.csv"
out = DATA / "edgeiq_customer_intelligence_terminal_feed_v1_1.csv"
summary = DATA / "edgeiq_customer_intelligence_terminal_feed_v1_1_summary.csv"

df = pd.read_csv(src)

replacements = {
    "Race understanding profile is worth inspection":
        "Race profile has some positives",

    "Stable intent is watch":
        "Stable profile worth monitoring",

    "Market board shows LEAN":
        "Market may have overlooked this runner",

    "No major GraphQL context signal":
        "Limited supporting historical evidence",

    "Runner DNA is POOR":
        "Runner profile is poor",

    "Runner DNA is NEGATIVE":
        "Runner profile is below average",

    "Runner DNA is NEUTRAL":
        "Runner profile is average",

    "Runner DNA is POSITIVE":
        "Runner profile is positive",

    "Runner DNA is STRONG":
        "Runner profile is strong",

    "Runner DNA is ELITE":
        "Runner profile is elite"
}

for c in ["primary_reasons", "primary_risks"]:
    if c in df.columns:
        for old, new in replacements.items():
            df[c] = (
                df[c]
                .fillna("")
                .str.replace(old, new, regex=False)
            )

if "display_verdict" in df.columns:
    df["display_verdict"] = (
        df["display_verdict"]
        .fillna("")
        .replace({
            "LEAN": "EDGEiQ Lean",
            "WATCH": "EDGEiQ Watch",
            "PASS": "No Edge"
        })
    )

df.to_csv(out, index=False)

pd.DataFrame([{
    "status":
        "EDGEIQ_CUSTOMER_INTELLIGENCE_TERMINAL_FEED_V1_1_BUILT",
    "rows":
        len(df)
}]).to_csv(summary, index=False)

print("[EDGEIQ_CUSTOMER_INTELLIGENCE_TERMINAL_FEED_V1_1] COMPLETE")
print(f"out={out}")
print(f"summary={summary}")
