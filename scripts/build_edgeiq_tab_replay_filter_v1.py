import pandas as pd
from pathlib import Path
from datetime import datetime

df = pd.read_csv(
    r".\public\data\edgeiq_pricing_replay_spine_v3_3_temperature6.csv",
    low_memory=False
)

tab = df[
    (pd.to_numeric(df["field_size"], errors="coerce") >= 6)
].copy()

summary = pd.DataFrame([{
    "built_at": datetime.utcnow().isoformat(),
    "all_rows": len(df),
    "all_races": df["_replay_join_key_v3_1"].str.rsplit("|", n=1).str[0].nunique(),
    "tab_rows": len(tab),
    "tab_races": tab["_replay_join_key_v3_1"].str.rsplit("|", n=1).str[0].nunique(),
    "removed_rows": len(df)-len(tab),
    "removed_pct": round(
        (len(df)-len(tab))/len(df)*100,
        2
    )
}])

summary.to_csv(
    r".\public\data\edgeiq_tab_replay_filter_summary_v1.csv",
    index=False
)

print(summary.to_string(index=False))
