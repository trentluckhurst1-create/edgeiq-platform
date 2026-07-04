import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

BASE = DATA / "edgeiq_intelligence_score_engine_v1.csv"
DNA = DATA / "edgeiq_live_runner_dna_v6_2.csv"

OUT = DATA / "edgeiq_intelligence_score_engine_v1_1.csv"
SUMMARY = DATA / "edgeiq_intelligence_score_engine_v1_1_summary.csv"

base = pd.read_csv(BASE, dtype=str).fillna("")
dna = pd.read_csv(DNA, dtype=str).fillna("")

def norm_key(x):
    return "".join(ch for ch in str(x).upper() if ch.isalnum())

def clean(x):
    s = str(x).strip()
    if s.upper() in ["", "NAN", "NONE", "NULL"]:
        return ""
    return s

def num(x, default=0.0):
    s = clean(x)
    try:
        return float(s) if s else default
    except Exception:
        return default

base["horse_key_join"] = base["horse"].map(norm_key)
dna["horse_key_join"] = dna["horse"].map(norm_key)

score_col = "dna_v6_2_score" if "dna_v6_2_score" in dna.columns else "dna_score"
band_col = "dna_v6_2_band" if "dna_v6_2_band" in dna.columns else "dna_band"

dna_small = dna[["horse_key_join", score_col, band_col]].drop_duplicates("horse_key_join")
m = base.merge(dna_small, on="horse_key_join", how="left")

rows = []

for _, r in m.iterrows():
    decision = clean(r.get("display_decision", "")).upper()
    status = clean(r.get("runner_status", "")).upper()
    scratched = decision == "SCRATCHED" or status == "SCRATCHED"

    old_total = num(r.get("intelligence_score_v1", ""), 0)
    old_dna_placeholder = num(r.get("runner_dna_component_20_placeholder", ""), 10)

    dna_band = clean(r.get(band_col, "")).upper()
    dna_score = num(r.get(score_col, ""), 0)

    if not dna_band:
        dna_band = "NO_PROFILE"

    if dna_band == "ELITE":
        dna_component = 20
    elif dna_band == "STRONG":
        dna_component = 17
    elif dna_band == "POSITIVE":
        dna_component = 14
    elif dna_band == "NEUTRAL":
        dna_component = 10
    elif dna_band == "NEGATIVE":
        dna_component = 5
    elif dna_band == "POOR":
        dna_component = 0
    else:
        dna_band = "NO_PROFILE"
        dna_component = 8

    new_total = old_total - old_dna_placeholder + dna_component

    if scratched:
        new_total = 0
        out_band = "SCRATCHED"
        verdict = "Scratched runner"
    else:
        new_total = round(max(0, min(100, new_total)), 2)
        if new_total >= 85:
            out_band = "ELITE"
            verdict = "Elite intelligence profile"
        elif new_total >= 70:
            out_band = "STRONG"
            verdict = "Strong intelligence profile"
        elif new_total >= 55:
            out_band = "POSITIVE"
            verdict = "Positive intelligence profile"
        elif new_total >= 40:
            out_band = "WATCH"
            verdict = "Watchlist intelligence profile"
        else:
            out_band = "LOW_CONVICTION"
            verdict = "Low conviction intelligence profile"

    reasons = clean(r.get("top_reasons_v1", ""))
    risks = clean(r.get("top_risks_v1", ""))

    if dna_band in ["ELITE", "STRONG", "POSITIVE"]:
        reasons = (reasons + " | " if reasons else "") + f"Runner DNA is {dna_band}"
    elif dna_band in ["NEGATIVE", "POOR"]:
        risks = (risks + " | " if risks else "") + f"Runner DNA is {dna_band}"
    elif dna_band == "NO_PROFILE":
        risks = (risks + " | " if risks else "") + "Runner DNA profile unavailable"

    out_row = r.to_dict()
    out_row.pop("horse_key_join", None)
    out_row["dna_v6_2_score_joined"] = dna_score
    out_row["dna_v6_2_band_joined"] = dna_band
    out_row["runner_dna_component_20"] = dna_component
    out_row["intelligence_score_v1_1"] = new_total
    out_row["intelligence_band_v1_1"] = out_band
    out_row["intelligence_verdict_v1_1"] = verdict
    out_row["top_reasons_v1_1"] = reasons
    out_row["top_risks_v1_1"] = risks
    out_row["customer_narrative_v1_1"] = f"EDGEIQ Intelligence Score: {new_total} ({out_band}). Verdict: {verdict}. Why: {reasons}. Risks: {risks}."
    out_row["built_at_v1_1"] = datetime.now(timezone.utc).isoformat()
    rows.append(out_row)

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    {"metric": "status", "value": "INTELLIGENCE_SCORE_ENGINE_V1_1_FIXED_BUILT"},
    {"metric": "rows", "value": len(out)},
    {"metric": "dna_joined", "value": int((out["dna_v6_2_band_joined"] != "NO_PROFILE").sum())},
    {"metric": "no_profile", "value": int((out["dna_v6_2_band_joined"] == "NO_PROFILE").sum())},
    {"metric": "scratched", "value": int((out["intelligence_band_v1_1"] == "SCRATCHED").sum())},
    {"metric": "elite", "value": int((out["intelligence_band_v1_1"] == "ELITE").sum())},
    {"metric": "strong", "value": int((out["intelligence_band_v1_1"] == "STRONG").sum())},
    {"metric": "positive", "value": int((out["intelligence_band_v1_1"] == "POSITIVE").sum())},
    {"metric": "watch", "value": int((out["intelligence_band_v1_1"] == "WATCH").sum())},
    {"metric": "low_conviction", "value": int((out["intelligence_band_v1_1"] == "LOW_CONVICTION").sum())},
    {"metric": "avg_score", "value": round(pd.to_numeric(out["intelligence_score_v1_1"], errors="coerce").mean(), 2)},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
])
summary.to_csv(SUMMARY, index=False)

print("[INTELLIGENCE_SCORE_ENGINE_V1_1_FIXED] COMPLETE")
print(summary.to_string(index=False))
