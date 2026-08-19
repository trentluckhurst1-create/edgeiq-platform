from pathlib import Path
import pandas as pd
import numpy as np
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

DNA = DATA / "edgeiq_runner_dna_v3.csv"
BOARD = DATA / "edgeiq_live_runner_board_governed_v1.csv"

OUT = DATA / "edgeiq_runner_dna_v3_live_race_audit.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v3_live_race_audit_summary.csv"

def num(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return np.nan
        return float(str(x).replace(",", "").strip())
    except Exception:
        return np.nan

def key(df):
    return (
        df["race_date"].astype(str).str.strip() + "|" +
        df["track"].astype(str).str.strip().str.upper() + "|" +
        df["race_no"].astype(str).str.strip() + "|" +
        df["horse"].astype(str).str.strip().str.upper()
    )

dna = pd.read_csv(DNA, dtype=str, keep_default_na=False, low_memory=False)
board = pd.read_csv(BOARD, dtype=str, keep_default_na=False, low_memory=False)

dna["join_key"] = key(dna)
board["join_key"] = key(board)

merged = dna.merge(board, on="join_key", how="left", suffixes=("", "_board"))

merged["dna_score_num"] = pd.to_numeric(merged["runner_dna_v3_score"], errors="coerce")
merged["price_rank_num"] = pd.to_numeric(merged["V6_1_RESEARCH_price_rank"], errors="coerce")
merged["fair_price_num"] = pd.to_numeric(merged["fair_price"], errors="coerce")
merged["live_price_num"] = pd.to_numeric(merged["live_price"], errors="coerce")
merged["edge_pct_num"] = pd.to_numeric(merged["edge_pct"], errors="coerce")

group_cols = ["race_date", "track", "race_no"]

merged["dna_rank"] = (
    merged.groupby(group_cols)["dna_score_num"]
    .rank(method="first", ascending=False)
)

rows = []

for _, g in merged.groupby(group_cols, dropna=False):
    race_date = g.iloc[0].get("race_date", "")
    track = g.iloc[0].get("track", "")
    race_no = g.iloc[0].get("race_no", "")

    dna_top = g.sort_values("dna_rank").head(1)
    price_top = g.sort_values("price_rank_num").head(1)
    edge_top = g.sort_values("edge_pct_num", ascending=False).head(1)

    dna_top_horse = dna_top.iloc[0]["horse"] if len(dna_top) else ""
    price_top_horse = price_top.iloc[0]["horse"] if len(price_top) else ""
    edge_top_horse = edge_top.iloc[0]["horse"] if len(edge_top) else ""

    rows.append({
        "race_date": race_date,
        "track": track,
        "race_no": race_no,
        "runners": len(g),

        "dna_top_horse": dna_top_horse,
        "dna_top_score": dna_top.iloc[0]["runner_dna_v3_score"] if len(dna_top) else "",
        "dna_top_band": dna_top.iloc[0]["runner_dna_v3_band"] if len(dna_top) else "",
        "dna_top_strongest_factor": dna_top.iloc[0].get("strongest_factor", "") if len(dna_top) else "",
        "dna_top_weakest_factor": dna_top.iloc[0].get("weakest_factor", "") if len(dna_top) else "",

        "price_top_horse": price_top_horse,
        "price_top_rank": price_top.iloc[0].get("V6_1_RESEARCH_price_rank", "") if len(price_top) else "",
        "price_top_fair_price": price_top.iloc[0].get("fair_price", "") if len(price_top) else "",
        "price_top_projection_band": price_top.iloc[0].get("projection_band_V6_1_RESEARCH", "") if len(price_top) else "",

        "edge_top_horse": edge_top_horse,
        "edge_top_edge_pct": edge_top.iloc[0].get("edge_pct", "") if len(edge_top) else "",
        "edge_top_live_price": edge_top.iloc[0].get("live_price", "") if len(edge_top) else "",
        "edge_top_fair_price": edge_top.iloc[0].get("fair_price", "") if len(edge_top) else "",

        "dna_equals_price_top": str(dna_top_horse == price_top_horse).upper(),
        "dna_equals_edge_top": str(dna_top_horse == edge_top_horse).upper(),
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    {"metric": "status", "value": "RUNNER_DNA_V3_LIVE_RACE_AUDIT_BUILT"},
    {"metric": "races", "value": len(out)},
    {"metric": "dna_equals_price_top", "value": int(out["dna_equals_price_top"].eq("TRUE").sum())},
    {"metric": "dna_differs_price_top", "value": int(out["dna_equals_price_top"].eq("FALSE").sum())},
    {"metric": "dna_equals_edge_top", "value": int(out["dna_equals_edge_top"].eq("TRUE").sum())},
    {"metric": "dna_differs_edge_top", "value": int(out["dna_equals_edge_top"].eq("FALSE").sum())},
])
summary.to_csv(SUMMARY, index=False)

print("[RUNNER_DNA_V3_LIVE_RACE_AUDIT] COMPLETE")
print(summary.to_string(index=False))
print(f"out={OUT}")
print(f"summary={SUMMARY}")
