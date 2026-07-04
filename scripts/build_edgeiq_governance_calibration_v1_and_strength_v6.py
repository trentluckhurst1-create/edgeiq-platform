import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

GOV_AUDIT = DATA / "edgeiq_winner_governance_audit_v1.csv"
V5 = DATA / "edgeiq_strength_adjusted_ratings_v5.csv"

CAL_OUT = DATA / "edgeiq_governance_calibration_v1.csv"
V6_OUT = DATA / "edgeiq_strength_adjusted_ratings_v6.csv"
AUDIT = DATA / "edgeiq_strength_adjusted_ratings_v6_audit.csv"

def clip(x, lo, hi):
    return max(lo, min(hi, x))

def pick_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

def main():
    gov = pd.read_csv(GOV_AUDIT)
    v5 = pd.read_csv(V5)

    rows = []

    for _, r in gov.iterrows():
        band = str(r["governance_band_v7_2"]).strip()
        over = float(r.get("winner_share_vs_runner_share", 1) or 1)

        ability_multiplier = clip(1.0 + ((over - 1.0) * 0.12), 0.94, 1.06)

        if band == "PROVEN":
            confidence_multiplier = 1.00
        elif band == "LIMITED_DATA_3_4_STARTS":
            confidence_multiplier = 0.94
        elif band == "LIMITED_DATA_2_STARTS":
            confidence_multiplier = 0.90
        elif band == "LIMITED_DATA_1_START":
            confidence_multiplier = 0.86
        elif band == "FIRST_STARTER_OR_UNKNOWN":
            confidence_multiplier = 0.80
        elif band == "IMPORT_UNKNOWN":
            confidence_multiplier = 0.82
        else:
            confidence_multiplier = 0.78

        rows.append({
            "governance_band_v7_2": band,
            "runners_sample_v1": r.get("runners", ""),
            "winners_sample_v1": r.get("winners", ""),
            "winner_share_vs_runner_share_v1": round(over, 4),
            "ability_multiplier_v1": round(ability_multiplier, 4),
            "confidence_multiplier_v1": round(confidence_multiplier, 4),
            "calibration_note_v1": "Ability adjusted mildly; confidence handled separately."
        })

    cal = pd.DataFrame(rows)
    cal.to_csv(CAL_OUT, index=False)

    gov_col = pick_col(v5, [
        "governance_band_v7_2",
        "projection_status_v6",
        "projection_status_v5",
        "governance_band",
        "projection_status",
    ])

    if gov_col is None:
        v5["governance_band_v7_2"] = "UNKNOWN"
    else:
        v5["governance_band_v7_2"] = v5[gov_col].astype(str).str.strip().replace("", "UNKNOWN")

    out = v5.merge(
        cal[["governance_band_v7_2", "ability_multiplier_v1", "confidence_multiplier_v1"]],
        on="governance_band_v7_2",
        how="left"
    )

    out["ability_multiplier_v1"] = pd.to_numeric(out["ability_multiplier_v1"], errors="coerce").fillna(0.96)
    out["confidence_multiplier_v1"] = pd.to_numeric(out["confidence_multiplier_v1"], errors="coerce").fillna(0.78)

    out["strength_adjusted_rating_v5"] = pd.to_numeric(out["strength_adjusted_rating_v5"], errors="coerce")
    out["horse_results_strength_v3"] = pd.to_numeric(out["horse_results_strength_v3"], errors="coerce")
    out["live_race_strength_score_v3"] = pd.to_numeric(out["live_race_strength_score_v3"], errors="coerce")

    out["strength_adjusted_rating_v6"] = (
        (
            0.72 * out["strength_adjusted_rating_v5"].fillna(35) +
            0.18 * out["horse_results_strength_v3"].fillna(out["strength_adjusted_rating_v5"]).fillna(35) +
            0.10 * out["live_race_strength_score_v3"].fillna(50)
        ) * out["ability_multiplier_v1"]
    ).clip(0, 100).round(3)

    out["confidence_adjusted_rating_v6"] = (
        out["strength_adjusted_rating_v6"] * out["confidence_multiplier_v1"]
    ).clip(0, 100).round(3)

    out["v6_minus_v5"] = (
        out["strength_adjusted_rating_v6"] - out["strength_adjusted_rating_v5"]
    ).round(3)

    out["strength_rating_band_v6"] = pd.cut(
        out["strength_adjusted_rating_v6"],
        bins=[-1, 35, 45, 55, 65, 75, 101],
        labels=["POOR", "WEAK", "NEUTRAL", "POSITIVE", "STRONG", "ELITE"]
    ).astype(str)

    out["v6_reason"] = (
        "V6 ability/confidence split | gov_source=" + str(gov_col) +
        " | v5=" + out["strength_adjusted_rating_v5"].round(2).astype(str) +
        " | ability_mult=" + out["ability_multiplier_v1"].round(3).astype(str) +
        " | confidence_mult=" + out["confidence_multiplier_v1"].round(3).astype(str) +
        " | horse_results=" + out["horse_results_strength_v3"].round(2).astype(str) +
        " | race_strength=" + out["live_race_strength_score_v3"].round(2).astype(str)
    )

    out.to_csv(V6_OUT, index=False)

    audit = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "governance_source_column_used", "value": gov_col if gov_col else "NONE_DEFAULT_UNKNOWN"},
        {"metric": "rows", "value": len(out)},
        {"metric": "avg_v5", "value": round(out["strength_adjusted_rating_v5"].mean(), 3)},
        {"metric": "avg_v6", "value": round(out["strength_adjusted_rating_v6"].mean(), 3)},
        {"metric": "avg_confidence_adjusted_v6", "value": round(out["confidence_adjusted_rating_v6"].mean(), 3)},
        {"metric": "avg_v6_minus_v5", "value": round(out["v6_minus_v5"].mean(), 3)},
        {"metric": "elite_v6", "value": int((out["strength_rating_band_v6"] == "ELITE").sum())},
        {"metric": "strong_v6", "value": int((out["strength_rating_band_v6"] == "STRONG").sum())},
        {"metric": "positive_v6", "value": int((out["strength_rating_band_v6"] == "POSITIVE").sum())},
        {"metric": "neutral_v6", "value": int((out["strength_rating_band_v6"] == "NEUTRAL").sum())},
        {"metric": "weak_v6", "value": int((out["strength_rating_band_v6"] == "WEAK").sum())},
        {"metric": "poor_v6", "value": int((out["strength_rating_band_v6"] == "POOR").sum())},
    ])
    audit.to_csv(AUDIT, index=False)

    print("[GOVERNANCE_CALIBRATION_V1 + STRENGTH_RATINGS_V6] COMPLETE")
    print(f"governance_source_column_used={gov_col if gov_col else 'NONE_DEFAULT_UNKNOWN'}")
    print(f"rows={len(out)}")
    print(f"avg_v5={round(out['strength_adjusted_rating_v5'].mean(), 3)}")
    print(f"avg_v6={round(out['strength_adjusted_rating_v6'].mean(), 3)}")
    print(f"wrote_calibration={CAL_OUT}")
    print(f"wrote_v6={V6_OUT}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
