import pandas as pd
import numpy as np

BASE = r".\public\data"

H2H = BASE + r"\edgeiq_v6_1_vs_v6_rank1_head_to_head.csv"
DETAIL_V61 = BASE + r"\edgeiq_projection_v6_1_research_prior_rating_backtest.csv"
DETAIL_V6 = BASE + r"\edgeiq_projection_v6_research_prior_rating_backtest.csv"

OUT_FOUND = BASE + r"\edgeiq_v6_1_found_winners_vs_v6_v1.csv"
OUT_LOST = BASE + r"\edgeiq_v6_1_lost_winners_vs_v6_v1.csv"
SUMMARY = BASE + r"\edgeiq_v6_1_found_lost_winners_vs_v6_v1_summary.csv"

h = pd.read_csv(H2H, low_memory=False)

for c in ["v6_won","v61_won","v6_placed","v61_placed"]:
    h[c] = pd.to_numeric(h[c], errors="coerce").fillna(0)

h["v61_found_winner"] = (h["v61_won"] == 1) & (h["v6_won"] != 1)
h["v61_lost_winner"] = (h["v6_won"] == 1) & (h["v61_won"] != 1)

found = h[h["v61_found_winner"]].copy()
lost = h[h["v61_lost_winner"]].copy()

def enrich(df, side):
    out = df.copy()

    for c in [
        f"{side}_rating",
        f"{side}_rating_gap",
        f"{side}_fair_price",
        f"{side}_won",
        f"{side}_placed",
    ]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    return out

found = enrich(found, "v61")
lost = enrich(lost, "v61")

found.to_csv(OUT_FOUND, index=False)
lost.to_csv(OUT_LOST, index=False)

rows = []

for name, x in [("FOUND", found), ("LOST", lost)]:
    rows.append({
        "group": name,
        "races": len(x),
        "avg_v6_rating": round(pd.to_numeric(x["v6_rating"], errors="coerce").mean(),4) if len(x) else np.nan,
        "avg_v61_rating": round(pd.to_numeric(x["v61_rating"], errors="coerce").mean(),4) if len(x) else np.nan,
        "avg_v6_gap": round(pd.to_numeric(x["v6_rating_gap"], errors="coerce").mean(),4) if len(x) else np.nan,
        "avg_v61_gap": round(pd.to_numeric(x["v61_rating_gap"], errors="coerce").mean(),4) if len(x) else np.nan,
        "avg_v6_fair": round(pd.to_numeric(x["v6_fair_price"], errors="coerce").mean(),4) if len(x) else np.nan,
        "avg_v61_fair": round(pd.to_numeric(x["v61_fair_price"], errors="coerce").mean(),4) if len(x) else np.nan,
        "elite_count": int((x["v61_projection_band"] == "ELITE").sum()) if len(x) else 0,
        "strong_count": int((x["v61_projection_band"] == "STRONG").sum()) if len(x) else 0,
        "positive_count": int((x["v61_projection_band"] == "POSITIVE").sum()) if len(x) else 0,
    })

summary = pd.DataFrame(rows)
summary.to_csv(SUMMARY, index=False)

print("[V6_1_FOUND_LOST_WINNERS_AUDIT] COMPLETE")
print(summary.to_string(index=False))
