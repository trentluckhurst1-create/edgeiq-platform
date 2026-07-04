# build_edgeiq_intelligence_summary_engine_v1_2.py

from pathlib import Path
import pandas as pd

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

src = DATA / "edgeiq_intelligence_summary_engine_v1_1.csv"
out = DATA / "edgeiq_intelligence_summary_engine_v1_2.csv"
summary = DATA / "edgeiq_intelligence_summary_engine_v1_2_summary.csv"

df = pd.read_csv(src)

replacements = {
    "EDGEIQ":"EDGEiQ",
    "Runner DNA":"Runner Profile",
    "Stable intent":"Stable Profile",
    "historical context signals":"historical signals",
    "Historical context signals":"Historical Signals"
}

for c in df.columns:
    if df[c].dtype == object:
        for old, new in replacements.items():
            df[c] = (
                df[c]
                .fillna("")
                .str.replace(old, new, regex=False)
            )

df.to_csv(out, index=False)

pd.DataFrame([{
    "status":
        "EDGEIQ_INTELLIGENCE_SUMMARY_ENGINE_V1_2_BUILT",
    "rows":
        len(df)
}]).to_csv(summary, index=False)

print("[EDGEIQ_INTELLIGENCE_SUMMARY_ENGINE_V1_2] COMPLETE")
print(f"out={out}")
print(f"summary={summary}")
