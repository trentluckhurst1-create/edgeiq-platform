from pathlib import Path
import pandas as pd

DATA = Path.cwd() / "public" / "data"

df = pd.read_csv(
    DATA / "edgeiq_customer_intelligence_terminal_feed_v1_1.csv"
)

replacements = {
    "EDGEIQ":"EDGEiQ",
    "Stable intent is watch":"Stable profile worth monitoring",
    "Market board shows LEAN":"Market may have overlooked this runner",
    "Market board shows WATCH":"Market interest worth monitoring",
    "No major GraphQL context signal":"Limited supporting historical evidence",
    "Runner DNA is POOR":"Runner profile is poor",
    "Runner DNA is NEGATIVE":"Runner profile is below average",
    "Runner DNA is NEUTRAL":"Runner profile is average",
    "Runner DNA is POSITIVE":"Runner profile is positive",
    "Runner DNA is STRONG":"Runner profile is strong",
    "Runner DNA is ELITE":"Runner profile is elite",
    "Race understanding profile is worth inspection":"Race profile has some positives"
}

for c in df.columns:
    if df[c].dtype == object:
        for old, new in replacements.items():
            df[c] = (
                df[c]
                .fillna("")
                .str.replace(old, new, regex=False)
            )

df.to_csv(
    DATA / "edgeiq_customer_intelligence_terminal_feed_v1_1.csv",
    index=False
)

print("[CUSTOMER_FEED_V1_1_HOTFIX] COMPLETE")
