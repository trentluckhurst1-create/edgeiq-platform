from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

v62 = pd.read_csv(DATA / "edgeiq_live_runner_dna_v6_2.csv", dtype=str).fillna("")
v63 = pd.read_csv(DATA / "edgeiq_live_runner_dna_v6_3_research.csv", dtype=str).fillna("")

a = v62[["join_key","race_date","track","race_no","horse","dna_v6_2_score","dna_v6_2_band","runner_dna_v6_2_rank_in_race"]].copy()
b = v63[["join_key","dna_v6_2_score","dna_v6_2_band","runner_dna_v6_2_rank_in_race"]].copy()

a = a.rename(columns={
    "dna_v6_2_score": "v6_2_score",
    "dna_v6_2_band": "v6_2_band",
    "runner_dna_v6_2_rank_in_race": "v6_2_rank",
})

b = b.rename(columns={
    "dna_v6_2_score": "v6_3_research_score",
    "dna_v6_2_band": "v6_3_research_band",
    "runner_dna_v6_2_rank_in_race": "v6_3_research_rank",
})

out = a.merge(b, on="join_key", how="left")

for c in ["v6_2_score","v6_3_research_score","v6_2_rank","v6_3_research_rank"]:
    out[c] = pd.to_numeric(out[c], errors="coerce")

out["score_delta"] = (out["v6_3_research_score"] - out["v6_2_score"]).round(3)
out["rank_delta"] = out["v6_3_research_rank"] - out["v6_2_rank"]
out["band_changed"] = out["v6_2_band"] != out["v6_3_research_band"]

OUT = DATA / "edgeiq_live_runner_dna_v6_2_vs_v6_3_research_comparison.csv"
out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status","LIVE_RUNNER_DNA_V6_2_VS_V6_3_RESEARCH_COMPARISON_BUILT"],
    ["rows",len(out)],
    ["band_changed_rows",int(out["band_changed"].sum())],
    ["avg_abs_score_delta",round(out["score_delta"].abs().mean(),3)],
    ["max_abs_score_delta",round(out["score_delta"].abs().max(),3)],
    ["avg_abs_rank_delta",round(out["rank_delta"].abs().mean(),3)],
    ["max_abs_rank_delta",round(out["rank_delta"].abs().max(),3)],
], columns=["metric","value"])

SUMMARY = DATA / "edgeiq_live_runner_dna_v6_2_vs_v6_3_research_comparison_summary.csv"
summary.to_csv(SUMMARY,index=False)

print("[LIVE_DNA_V6_2_VS_V6_3_RESEARCH_COMPARISON] COMPLETE")
print(summary.to_string(index=False))
print(f"wrote={OUT}")
print(f"wrote={SUMMARY}")
