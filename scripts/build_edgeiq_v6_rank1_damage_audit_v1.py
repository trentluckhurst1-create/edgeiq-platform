import os
import pandas as pd
import numpy as np

ROOT = os.getcwd()
DATA = os.path.join(ROOT, "public", "data")

INFILE = os.path.join(DATA, "edgeiq_v6_vs_v5_prior_rank1_head_to_head.csv")

OUT = os.path.join(DATA, "edgeiq_v6_rank1_damage_audit_v1.csv")
SUMMARY = os.path.join(DATA, "edgeiq_v6_rank1_damage_audit_v1_summary.csv")

df = pd.read_csv(INFILE, low_memory=False)

diff = df[df["same_rank1"].astype(str).str.upper().isin(["FALSE","False","0"])].copy()

diff["rating_swing_v6_minus_v5"] = pd.to_numeric(diff["v6_rating"], errors="coerce") - pd.to_numeric(diff["v5_rating"], errors="coerce")
diff["gap_swing_v6_minus_v5"] = pd.to_numeric(diff["v6_rating_gap"], errors="coerce") - pd.to_numeric(diff["v5_rating_gap"], errors="coerce")
diff["fair_price_swing_v6_minus_v5"] = pd.to_numeric(diff["v6_fair_price"], errors="coerce") - pd.to_numeric(diff["v5_fair_price"], errors="coerce")

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

diff["decision_outcome"] = diff.apply(outcome, axis=1)

diff.to_csv(OUT, index=False)

rows = []
rows.append({"metric":"different_rank1_races","value":len(diff)})

for k, g in diff.groupby("decision_outcome"):
    rows.append({"metric":f"count_{k}", "value":len(g)})
    rows.append({"metric":f"avg_rating_swing_{k}", "value":round(g["rating_swing_v6_minus_v5"].mean(),4)})
    rows.append({"metric":f"avg_gap_swing_{k}", "value":round(g["gap_swing_v6_minus_v5"].mean(),4)})
    rows.append({"metric":f"avg_fair_price_swing_{k}", "value":round(g["fair_price_swing_v6_minus_v5"].mean(),4)})

band_cross = diff.groupby(["v5_projection_band","v6_projection_band"]).size().reset_index(name="races")
band_cross = band_cross.sort_values("races", ascending=False)
for _, r in band_cross.head(20).iterrows():
    rows.append({
        "metric":f"band_cross_{r['v5_projection_band']}_to_{r['v6_projection_band']}",
        "value":int(r["races"])
    })

pd.DataFrame(rows).to_csv(SUMMARY, index=False)

print("[V6_RANK1_DAMAGE_AUDIT] COMPLETE")
print(pd.DataFrame(rows).to_string(index=False))
