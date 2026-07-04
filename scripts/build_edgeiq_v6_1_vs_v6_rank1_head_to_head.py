import pandas as pd

BASE = r".\public\data"

v6 = pd.read_csv(BASE + r"\edgeiq_projection_v6_research_prior_rating_backtest.csv", low_memory=False)
v61 = pd.read_csv(BASE + r"\edgeiq_projection_v6_1_research_prior_rating_backtest.csv", low_memory=False)

v6 = v6[v6["model"] == "V6_RESEARCH_PRIOR"].copy()
v61 = v61[v61["model"] == "V6_1_RESEARCH_PRIOR"].copy()

for c in ["rank","won","placed","rating","rating_gap","fair_price"]:
    v6[c] = pd.to_numeric(v6[c], errors="coerce")
    v61[c] = pd.to_numeric(v61[c], errors="coerce")

r6 = v6[v6["rank"] == 1].copy()
r61 = v61[v61["rank"] == 1].copy()

keep = [
    "race_key","race_date","track","distance","race_name",
    "horse","rating","rating_gap","projection_band","fair_price","won","placed"
]

r6 = r6[keep].add_prefix("v6_")
r61 = r61[keep].add_prefix("v61_")

m = r6.merge(
    r61,
    left_on="v6_race_key",
    right_on="v61_race_key",
    how="inner"
)

m["same_rank1"] = m["v6_horse"] == m["v61_horse"]
m["v61_found_winner"] = (m["v61_won"] == 1) & (m["v6_won"] != 1)
m["v61_lost_winner"] = (m["v6_won"] == 1) & (m["v61_won"] != 1)
m["both_lost"] = (m["v6_won"] != 1) & (m["v61_won"] != 1)

m.to_csv(BASE + r"\edgeiq_v6_1_vs_v6_rank1_head_to_head.csv", index=False)

diff = m[m["same_rank1"] == False].copy()

rows = [
    {"metric":"races_compared","value":len(m)},
    {"metric":"same_rank1_count","value":int(m["same_rank1"].sum())},
    {"metric":"same_rank1_pct","value":round(m["same_rank1"].mean()*100,2)},
    {"metric":"different_rank1_count","value":len(diff)},
    {"metric":"different_rank1_pct","value":round(len(diff)/len(m)*100,2)},
    {"metric":"v61_found_winner","value":int(m["v61_found_winner"].sum())},
    {"metric":"v61_lost_winner","value":int(m["v61_lost_winner"].sum())},
    {"metric":"net_v61_vs_v6","value":int(m["v61_found_winner"].sum() - m["v61_lost_winner"].sum())},
    {"metric":"diff_v6_win_pct","value":round(diff["v6_won"].mean()*100,2) if len(diff) else 0},
    {"metric":"diff_v61_win_pct","value":round(diff["v61_won"].mean()*100,2) if len(diff) else 0},
    {"metric":"diff_v6_place_pct","value":round(diff["v6_placed"].mean()*100,2) if len(diff) else 0},
    {"metric":"diff_v61_place_pct","value":round(diff["v61_placed"].mean()*100,2) if len(diff) else 0},
]

summary = pd.DataFrame(rows)
summary.to_csv(BASE + r"\edgeiq_v6_1_vs_v6_rank1_head_to_head_summary.csv", index=False)

print("[V6_1_VS_V6_HEAD_TO_HEAD] COMPLETE")
print(summary.to_string(index=False))
