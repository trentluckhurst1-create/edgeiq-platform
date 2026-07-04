import os
import pandas as pd
import numpy as np

ROOT = os.getcwd()
DATA = os.path.join(ROOT, "public", "data")

INFILE = os.path.join(DATA, "edgeiq_projection_v6_1_research_prior_rating_backtest.csv")

OUT = os.path.join(DATA, "edgeiq_v6_1_vs_v5_prior_rank1_head_to_head.csv")
SUMMARY = os.path.join(DATA, "edgeiq_v6_1_vs_v5_prior_rank1_head_to_head_summary.csv")

df = pd.read_csv(INFILE, low_memory=False)

rank1 = df[df["rank"].astype(float) == 1].copy()

v5 = rank1[rank1["model"] == "V5_1_PRODUCTION_PRIOR"].copy()
v6 = rank1[rank1["model"] == "V6_1_RESEARCH_PRIOR"].copy()

keep = [
    "race_key","race_date","track","distance","race_name",
    "horse","finish_position_num","field_size","rating",
    "rating_gap","projection_band","fair_price","won","placed"
]

v5 = v5[[c for c in keep if c in v5.columns]].copy()
v6 = v6[[c for c in keep if c in v6.columns]].copy()

v5 = v5.add_prefix("v5_")
v6 = v6.add_prefix("v6_")

m = v5.merge(
    v6,
    left_on="v5_race_key",
    right_on="v6_race_key",
    how="inner"
)

m["same_rank1"] = m["v5_horse"] == m["v6_horse"]
m["v5_right_v6_wrong"] = (m["v5_won"] == 1) & (m["v6_won"] != 1)
m["v6_right_v5_wrong"] = (m["v6_won"] == 1) & (m["v5_won"] != 1)
m["both_lost"] = (m["v5_won"] != 1) & (m["v6_won"] != 1)
m["both_won"] = (m["v5_won"] == 1) & (m["v6_won"] == 1)

m.to_csv(OUT, index=False)

rows = []
allr = m
diff = m[m["same_rank1"] == False]

rows.append({"metric":"races_compared","value":len(allr)})
rows.append({"metric":"same_rank1_count","value":int(allr["same_rank1"].sum())})
rows.append({"metric":"same_rank1_pct","value":round(allr["same_rank1"].mean()*100,2)})
rows.append({"metric":"different_rank1_count","value":len(diff)})
rows.append({"metric":"different_rank1_pct","value":round(len(diff)/len(allr)*100,2) if len(allr) else 0})

rows.append({"metric":"all_v5_right_v6_wrong","value":int(allr["v5_right_v6_wrong"].sum())})
rows.append({"metric":"all_v6_right_v5_wrong","value":int(allr["v6_right_v5_wrong"].sum())})

rows.append({"metric":"different_v5_right_v6_wrong","value":int(diff["v5_right_v6_wrong"].sum())})
rows.append({"metric":"different_v6_right_v5_wrong","value":int(diff["v6_right_v5_wrong"].sum())})
rows.append({"metric":"different_both_lost","value":int(diff["both_lost"].sum())})

if len(diff):
    rows.append({"metric":"different_v5_win_pct","value":round(diff["v5_won"].mean()*100,2)})
    rows.append({"metric":"different_v6_win_pct","value":round(diff["v6_won"].mean()*100,2)})
    rows.append({"metric":"different_v5_place_pct","value":round(diff["v5_placed"].mean()*100,2)})
    rows.append({"metric":"different_v6_place_pct","value":round(diff["v6_placed"].mean()*100,2)})

pd.DataFrame(rows).to_csv(SUMMARY, index=False)

print("[V6_VS_V5_HEAD_TO_HEAD] COMPLETE")
print(pd.DataFrame(rows).to_string(index=False))
