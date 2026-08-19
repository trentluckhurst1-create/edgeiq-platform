import pandas as pd
import numpy as np

df = pd.read_csv(
    r".\public\data\edgeiq_projection_v6_research_prior_rating_backtest.csv",
    low_memory=False
)

for c in ["rating","rank"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

rows = []

for model, g_model in df.groupby("model"):

    for race_key, g in g_model.groupby("race_key"):

        g = g.sort_values("rating", ascending=False)

        if len(g) < 2:
            continue

        r1 = g.iloc[0]
        r2 = g.iloc[1]

        rows.append({
            "model": model,
            "race_key": race_key,
            "top1_horse": r1["horse"],
            "top2_horse": r2["horse"],
            "top1_rating": r1["rating"],
            "top2_rating": r2["rating"],
            "top2_separation": r1["rating"] - r2["rating"],
            "top1_gap": r1["rating_gap"],
            "top2_gap": r2["rating_gap"],
            "top1_won": r1["won"]
        })

out = pd.DataFrame(rows)

out.to_csv(
    r".\public\data\edgeiq_top2_separation_audit.csv",
    index=False
)

v5 = out[out["model"] == "V5_1_PRODUCTION_PRIOR"].copy()
v6 = out[out["model"] == "V6_RESEARCH_PRIOR"].copy()

merged = v5.merge(
    v6,
    on="race_key",
    suffixes=("_v5","_v6")
)

merged["separation_change"] = (
    merged["top2_separation_v6"] -
    merged["top2_separation_v5"]
)

merged["rank_switch"] = (
    merged["top1_horse_v5"] !=
    merged["top1_horse_v6"]
)

summary = []

summary.append({
    "metric":"races",
    "value":len(merged)
})

summary.append({
    "metric":"avg_v5_top2_separation",
    "value":round(
        merged["top2_separation_v5"].mean(),
        4
    )
})

summary.append({
    "metric":"avg_v6_top2_separation",
    "value":round(
        merged["top2_separation_v6"].mean(),
        4
    )
})

summary.append({
    "metric":"avg_separation_change",
    "value":round(
        merged["separation_change"].mean(),
        4
    )
})

switches = merged[merged["rank_switch"]]

summary.append({
    "metric":"switch_races",
    "value":len(switches)
})

summary.append({
    "metric":"switch_avg_v5_separation",
    "value":round(
        switches["top2_separation_v5"].mean(),
        4
    )
})

summary.append({
    "metric":"switch_avg_v6_separation",
    "value":round(
        switches["top2_separation_v6"].mean(),
        4
    )
})

pd.DataFrame(summary).to_csv(
    r".\public\data\edgeiq_top2_separation_audit_summary.csv",
    index=False
)

print(pd.DataFrame(summary).to_string(index=False))
