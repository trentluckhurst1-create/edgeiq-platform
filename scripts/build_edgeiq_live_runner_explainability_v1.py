from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

DNA = DATA / "edgeiq_live_runner_dna_v6_2.csv"
FACTORS = DATA / "edgeiq_live_runner_factor_scorecard_v2.csv"

OUT = DATA / "edgeiq_live_runner_explainability_v1.csv"
SUMMARY = DATA / "edgeiq_live_runner_explainability_v1_summary.csv"

def num(x):
    try:
        s = str(x).replace("$","").replace("%","").strip()
        if s == "" or s.lower() == "nan":
            return np.nan
        return float(s)
    except Exception:
        return np.nan

def txt(row, key):
    return str(row.get(key, "")).strip()

def label_factor(factor, score, direction):
    score_txt = "—" if pd.isna(score) else str(round(score, 1))
    name = str(factor).replace("_", " ").title()

    if direction == "edge":
        if score >= 85:
            return f"Elite {name} ({score_txt})"
        if score >= 70:
            return f"Strong {name} ({score_txt})"
        return f"Positive {name} ({score_txt})"

    if score <= 25:
        return f"Major {name} Risk ({score_txt})"
    if score <= 40:
        return f"{name} Risk ({score_txt})"
    return f"{name} Query ({score_txt})"

def market_summary(row):
    fair = num(row.get("fair_price", ""))
    live = num(row.get("live_price", ""))
    edge = num(row.get("edge_pct", ""))

    if pd.isna(fair) or pd.isna(live):
        return "Market price unavailable."

    if not pd.isna(edge):
        if edge >= 10:
            return f"Market appears to be underestimating this runner. Fair ${fair:.2f}, live ${live:.2f}, edge +{edge:.1f}%."
        if edge <= -10:
            return f"Market is shorter than EDGEiQ assessment. Fair ${fair:.2f}, live ${live:.2f}, edge {edge:.1f}%."

    return f"Market is close to EDGEiQ assessment. Fair ${fair:.2f}, live ${live:.2f}."

dna = pd.read_csv(DNA, dtype=str).fillna("")
factors = pd.read_csv(FACTORS, dtype=str).fillna("")

factor_groups = {
    jk: g.copy()
    for jk, g in factors.groupby("join_key")
}

rows = []
built_at = datetime.now(timezone.utc).isoformat()

for _, r in dna.iterrows():
    jk = txt(r, "join_key")
    g = factor_groups.get(jk, pd.DataFrame())

    if g.empty:
        edge_rows = []
        risk_rows = []
    else:
        g["score_num"] = g["factor_score"].apply(num)

        edge_rows = (
            g[g["score_num"].notna() & (g["score_num"] >= 65)]
            .sort_values("score_num", ascending=False)
            .head(3)
            .to_dict("records")
        )

        risk_rows = (
            g[g["score_num"].notna() & (g["score_num"] < 50)]
            .sort_values("score_num", ascending=True)
            .head(3)
            .to_dict("records")
        )

    edge_labels = [
        label_factor(x.get("factor", ""), num(x.get("factor_score", "")), "edge")
        for x in edge_rows
    ]

    risk_labels = [
        label_factor(x.get("factor", ""), num(x.get("factor_score", "")), "risk")
        for x in risk_rows
    ]

    while len(edge_labels) < 3:
        edge_labels.append("")
    while len(risk_labels) < 3:
        risk_labels.append("")

    why = " | ".join([x for x in edge_labels if x]) or "No clear positive driver identified."
    risk = " | ".join([x for x in risk_labels if x]) or "No major risk driver identified."

    rows.append({
        "race_date": txt(r, "race_date"),
        "track": txt(r, "track"),
        "race_no": txt(r, "race_no"),
        "horse": txt(r, "horse"),
        "horse_key": txt(r, "horse_key"),
        "join_key": jk,
        "dna_v6_2_score": txt(r, "dna_v6_2_score"),
        "dna_v6_2_band": txt(r, "dna_v6_2_band"),
        "runner_dna_v6_2_rank_in_race": txt(r, "runner_dna_v6_2_rank_in_race"),
        "edge_driver_1": edge_labels[0],
        "edge_driver_2": edge_labels[1],
        "edge_driver_3": edge_labels[2],
        "risk_driver_1": risk_labels[0],
        "risk_driver_2": risk_labels[1],
        "risk_driver_3": risk_labels[2],
        "why_edgeiq_likes_it": why,
        "risk_summary": risk,
        "market_summary": market_summary(r),
        "dna_narrative": txt(r, "runner_dna_v6_2_narrative"),
        "strongest_factor_v6_2": txt(r, "strongest_factor_v6_2"),
        "weakest_factor_v6_2": txt(r, "weakest_factor_v6_2"),
        "built_at": built_at,
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status", "RUNNER_EXPLAINABILITY_V1_BUILT"],
    ["rows", len(out)],
    ["edge_driver_1_nonblank", int((out["edge_driver_1"] != "").sum())],
    ["risk_driver_1_nonblank", int((out["risk_driver_1"] != "").sum())],
    ["market_summary_nonblank", int((out["market_summary"] != "").sum())],
    ["source_dna", DNA.name],
    ["source_factors", FACTORS.name],
    ["built_at", built_at],
], columns=["metric", "value"])

summary.to_csv(SUMMARY, index=False)

print("[RUNNER_EXPLAINABILITY_V1] COMPLETE")
print(summary.to_string(index=False))
print(f"wrote={OUT}")
print(f"wrote={SUMMARY}")
