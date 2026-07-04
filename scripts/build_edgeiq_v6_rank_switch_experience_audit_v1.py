import pandas as pd
import numpy as np

BASE = r".\public\data"

DETAIL = BASE + r"\edgeiq_projection_v6_research_prior_rating_backtest.csv"
SWITCH = BASE + r"\edgeiq_v6_vs_v5_prior_rank1_head_to_head.csv"

OUT = BASE + r"\edgeiq_v6_rank_switch_experience_audit_v1.csv"
SUMMARY = BASE + r"\edgeiq_v6_rank_switch_experience_audit_v1_summary.csv"

detail = pd.read_csv(DETAIL, low_memory=False)
switch = pd.read_csv(SWITCH, low_memory=False)

diff = switch[switch["same_rank1"].astype(str).str.upper().isin(["FALSE","0"])].copy()

for c in ["prior_starts","rating","rating_gap","won","placed"]:
    detail[c] = pd.to_numeric(detail[c], errors="coerce")

v5d = detail[detail["model"] == "V5_1_PRODUCTION_PRIOR"].copy()
v6d = detail[detail["model"] == "V6_RESEARCH_PRIOR"].copy()

v5p = v5d[[
    "race_key","horse","prior_starts","rating","rating_gap","projection_band","rank","won","placed"
]].rename(columns={
    "race_key":"v5_race_key",
    "horse":"v5_horse",
    "prior_starts":"v5_prior_starts",
    "rating":"v5_prior_rating",
    "rating_gap":"v5_prior_gap",
    "projection_band":"v5_prior_band",
    "rank":"v5_prior_rank",
    "won":"v5_actual_won",
    "placed":"v5_actual_placed"
})

v6p = v6d[[
    "race_key","horse","prior_starts","rating","rating_gap","projection_band","rank","won","placed"
]].rename(columns={
    "race_key":"v6_race_key",
    "horse":"v6_horse",
    "prior_starts":"v6_prior_starts",
    "rating":"v6_prior_rating",
    "rating_gap":"v6_prior_gap",
    "projection_band":"v6_prior_band",
    "rank":"v6_prior_rank",
    "won":"v6_actual_won",
    "placed":"v6_actual_placed"
})

m = diff.merge(v5p, on=["v5_race_key","v5_horse"], how="left")
m = m.merge(v6p, on=["v6_race_key","v6_horse"], how="left")

for c in [
    "v5_prior_starts","v6_prior_starts",
    "v5_prior_rating","v6_prior_rating",
    "v5_prior_gap","v6_prior_gap",
    "v5_won","v6_won","v5_placed","v6_placed"
]:
    if c in m.columns:
        m[c] = pd.to_numeric(m[c], errors="coerce")

m["starts_delta_v6_minus_v5"] = m["v6_prior_starts"] - m["v5_prior_starts"]
m["rating_delta_v6_minus_v5"] = m["v6_prior_rating"] - m["v5_prior_rating"]
m["gap_delta_v6_minus_v5"] = m["v6_prior_gap"] - m["v5_prior_gap"]

def outcome(row):
    if row["v5_won"] == 1 and row["v6_won"] != 1:
        return "V6_DAMAGED_WINNER"
    if row["v6_won"] == 1 and row["v5_won"] != 1:
        return "V6_FOUND_WINNER"
    if row["v5_placed"] == 1 and row["v6_placed"] != 1:
        return "V6_DAMAGED_PLACE"
    if row["v6_placed"] == 1 and row["v5_placed"] != 1:
        return "V6_FOUND_PLACE"
    return "BOTH_MISSED"

m["decision_outcome"] = m.apply(outcome, axis=1)

m.to_csv(OUT, index=False)

rows = []

for name, g in m.groupby("decision_outcome"):
    rows.append({
        "decision_outcome": name,
        "races": len(g),
        "v5_avg_prior_starts": round(g["v5_prior_starts"].mean(), 2),
        "v6_avg_prior_starts": round(g["v6_prior_starts"].mean(), 2),
        "avg_starts_delta_v6_minus_v5": round(g["starts_delta_v6_minus_v5"].mean(), 2),
        "v5_avg_prior_rating": round(g["v5_prior_rating"].mean(), 4),
        "v6_avg_prior_rating": round(g["v6_prior_rating"].mean(), 4),
        "avg_rating_delta_v6_minus_v5": round(g["rating_delta_v6_minus_v5"].mean(), 4),
        "v5_avg_gap": round(g["v5_prior_gap"].mean(), 4),
        "v6_avg_gap": round(g["v6_prior_gap"].mean(), 4),
        "avg_gap_delta_v6_minus_v5": round(g["gap_delta_v6_minus_v5"].mean(), 4),
    })

summary = pd.DataFrame(rows)
summary.to_csv(SUMMARY, index=False)

print("[V6_RANK_SWITCH_EXPERIENCE_AUDIT] COMPLETE")
print(summary.to_string(index=False))
