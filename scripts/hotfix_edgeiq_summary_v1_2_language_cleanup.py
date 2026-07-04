from pathlib import Path
import pandas as pd

DATA = Path.cwd() / "public" / "data"

df = pd.read_csv(
    DATA / "edgeiq_intelligence_summary_engine_v1_2.csv"
)

replacements = {
    "EDGEIQ":"EDGEiQ",
    "Runner DNA profile is poor":"Runner profile is poor",
    "Runner DNA":"Runner Profile",
    "Stable intent deserves attention":"Stable profile deserves attention",
    "Stable intent evidence is limited":"Stable profile evidence is limited",
    "historical context signals":"historical signals",
    "Historical context signals":"Historical Signals",
    "EDGEIQ recommendation":"EDGEiQ Assessment"
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
    DATA / "edgeiq_intelligence_summary_engine_v1_2.csv",
    index=False
)

print("[SUMMARY_ENGINE_V1_2_HOTFIX] COMPLETE")
