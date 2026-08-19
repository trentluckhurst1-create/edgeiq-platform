from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROJ_AUDIT = DATA / "edgeiq_projection_join_audit_v1.csv"
GOV_AUDIT = DATA / "edgeiq_live_governance_clean_audit_v1.csv"
TJ = DATA / "edgeiq_live_trainer_jockey_factor_feed_v3.csv"
TRACK = DATA / "edgeiq_live_track_intelligence_v1.csv"

OUT = DATA / "edgeiq_first_starter_intelligence_v1.csv"
SUMMARY = DATA / "edgeiq_first_starter_intelligence_v1_summary.csv"

def safe(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def num(x):
    return pd.to_numeric(x, errors="coerce")

def canon_horse(x):
    s = safe(x).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[^A-Z0-9]", "", s)

def key(df):
    out = df.copy()
    out["_track"] = out["track"].astype(str).str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)
    out["_race"] = out["race_no"].astype(str).str.replace(r"[^0-9]", "", regex=True)
    out["_horse"] = out["horse"].map(canon_horse)
    return out

def band_score(x):
    s = safe(x).upper()
    if "ELITE" in s:
        return 18
    if "STRONG" in s:
        return 13
    if "POSITIVE" in s:
        return 8
    if "NEUTRAL" in s or "STANDARD" in s:
        return 3
    if "NEGATIVE" in s:
        return -6
    if "POOR" in s:
        return -10
    return 0

def market_score(x):
    p = num(x)
    if pd.isna(p) or p <= 0:
        return 0
    if p <= 4:
        return 25
    if p <= 8:
        return 18
    if p <= 15:
        return 10
    if p <= 26:
        return 4
    if p <= 51:
        return -4
    return -10

def confidence_band(score):
    if score >= 70:
        return "ELITE"
    if score >= 55:
        return "STRONG"
    if score >= 40:
        return "SOLID"
    if score >= 25:
        return "SPECULATIVE"
    return "AVOID"

def view(row):
    b = row["first_starter_confidence_band"]
    live = safe(row.get("live_price"))
    if b in {"ELITE", "STRONG"}:
        return "MARKET RESPECT / REVIEW"
    if b == "SOLID":
        return "MARKET GUIDE ONLY"
    if live:
        return "UNKNOWN / MARKET ONLY"
    return "UNKNOWN / NO LIVE MARKET"

def comment(row):
    bits = []
    bits.append("No historical projection. Do not use an official model fair price.")
    if safe(row.get("live_price")):
        bits.append(f"Market guide is ${safe(row.get('live_price'))}.")
    else:
        bits.append("No reliable live market guide.")
    tj = []
    for c, label in [
        ("trainer_edge_band_v3", "trainer"),
        ("jockey_edge_band_v3", "jockey"),
        ("combo_edge_band_v3", "combo"),
    ]:
        v = safe(row.get(c))
        if v:
            tj.append(f"{label} {v.replace('_',' ')}")
    if tj:
        bits.append("TJ context: " + ", ".join(tj) + ".")
    tf = safe(row.get("track_fit_band"))
    if tf:
        bits.append(f"Track fit: {tf.replace('_',' ')}.")
    bits.append(f"First-starter confidence: {row['first_starter_confidence_band']} ({row['first_starter_confidence_score']}).")
    return " ".join(bits)

def main():
    proj = key(pd.read_csv(PROJ_AUDIT, dtype=str, low_memory=False))
    gov = key(pd.read_csv(GOV_AUDIT, dtype=str, low_memory=False))

    fs = proj[proj["recommended_fix"].eq("FIRST_STARTER_INTELLIGENCE_MODEL")].copy()

    keep = [
        "_track","_race","_horse",
        "race_date","track","race_no","horse","live_price",
        "fair_price_display","guide_price_display",
        "recommended_display_action",
        "no_history_governance_display"
    ]
    keep = [c for c in keep if c in gov.columns]

    out = fs.merge(
        gov[keep].drop_duplicates(["_track","_race","_horse"]),
        on=["_track","_race","_horse"],
        how="left",
        suffixes=("", "_gov")
    )

    if TJ.exists():
        tj = key(pd.read_csv(TJ, dtype=str, low_memory=False))
        tj_keep = [
            "_track","_race","_horse",
            "trainer_edge_band_v3","jockey_edge_band_v3","combo_edge_band_v3",
            "trainer_match_status_v3","jockey_match_status_v3","combo_match_status_v3"
        ]
        tj_keep = [c for c in tj_keep if c in tj.columns]
        out = out.merge(
            tj[tj_keep].drop_duplicates(["_track","_race","_horse"]),
            on=["_track","_race","_horse"],
            how="left"
        )

    if TRACK.exists():
        tr = key(pd.read_csv(TRACK, dtype=str, low_memory=False))
        tr_keep = [
            "_track","_race","_horse",
            "track_fit_score","track_fit_band",
            "run_style_alignment","barrier_alignment",
            "track_intelligence_comment"
        ]
        tr_keep = [c for c in tr_keep if c in tr.columns]
        out = out.merge(
            tr[tr_keep].drop_duplicates(["_track","_race","_horse"]),
            on=["_track","_race","_horse"],
            how="left"
        )

    out["market_score"] = out.get("live_price", "").map(market_score)
    out["trainer_score"] = out.get("trainer_edge_band_v3", "").map(band_score) if "trainer_edge_band_v3" in out.columns else 0
    out["jockey_score"] = out.get("jockey_edge_band_v3", "").map(band_score) if "jockey_edge_band_v3" in out.columns else 0
    out["combo_score"] = out.get("combo_edge_band_v3", "").map(band_score) if "combo_edge_band_v3" in out.columns else 0
    out["track_fit_component"] = pd.to_numeric(out.get("track_fit_score", 0), errors="coerce").fillna(0) * 0.20

    out["first_starter_confidence_score"] = (
        25
        + out["market_score"]
        + out["trainer_score"]
        + out["jockey_score"]
        + out["combo_score"]
        + out["track_fit_component"]
    ).round(1)

    out["first_starter_confidence_score"] = out["first_starter_confidence_score"].clip(lower=0, upper=100)
    out["first_starter_confidence_band"] = out["first_starter_confidence_score"].map(confidence_band)
    out["first_starter_edgeiq_view"] = out.apply(view, axis=1)
    out["first_starter_comment"] = out.apply(comment, axis=1)
    out["official_fair_price_policy"] = "UNKNOWN_NOT_PRICED"
    out["pricing_rule"] = "FIRST_STARTER_INTELLIGENCE_ONLY_NO_FAIR_PRICE"

    final_cols = [
        "race_date","track","race_no","horse",
        "live_price","guide_price_display","official_fair_price_policy","pricing_rule",
        "first_starter_confidence_score","first_starter_confidence_band","first_starter_edgeiq_view",
        "trainer_edge_band_v3","jockey_edge_band_v3","combo_edge_band_v3",
        "track_fit_score","track_fit_band","run_style_alignment","barrier_alignment",
        "first_starter_comment"
    ]
    final_cols = [c for c in final_cols if c in out.columns]
    final = out[final_cols].copy()

    final.to_csv(OUT, index=False)

    summary = [
        ("status", "COMPLETE"),
        ("rows", len(final)),
    ]

    for k, v in final["first_starter_confidence_band"].value_counts(dropna=False).to_dict().items():
        summary.append((f"band_{k}", v))

    for k, v in final["first_starter_edgeiq_view"].value_counts(dropna=False).to_dict().items():
        summary.append((f"view_{k}", v))

    pd.DataFrame(summary, columns=["metric","value"]).to_csv(SUMMARY, index=False)

    print("[FIRST_STARTER_INTELLIGENCE_V1] COMPLETE")
    print(f"rows={len(final)}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
