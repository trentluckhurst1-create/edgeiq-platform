from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

CURR = DATA / "edgeiq_current_field_projection_v5_2.csv"
RESEARCH = DATA / "edgeiq_historical_performance_rating_v5_1_recalibration_research.csv"

OUT = DATA / "edgeiq_projection_research_gap_audit.csv"
SUMMARY = DATA / "edgeiq_projection_research_gap_audit_summary.csv"

def n(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return np.nan
        return float(x)
    except:
        return np.nan

def main():

    curr = pd.read_csv(CURR,dtype=str).fillna("")
    hist = pd.read_csv(RESEARCH,dtype=str).fillna("")

    hist["race_date"] = pd.to_datetime(hist["race_date"],errors="coerce")

    rows = []

    for _,r in curr.iterrows():

        horse = str(r.get("horse","")).strip()

        starts = hist[
            hist["horse"].str.upper().str.strip()
            ==
            horse.upper().strip()
        ].copy()

        starts = starts.sort_values("race_date",ascending=False)

        vals = pd.to_numeric(
            starts["performance_rating_v5_1_research"],
            errors="coerce"
        ).dropna().tolist()

        if len(vals) == 0:
            continue

        last = vals[0]
        avg3 = np.mean(vals[:3])
        avg5 = np.mean(vals[:5])
        peak6 = np.max(vals[:6])

        proj_research = (
            0.35 * last +
            0.35 * avg3 +
            0.20 * avg5 +
            0.10 * peak6
        )

        target = n(r.get("race_target_rating_v5_2",""))

        if np.isnan(target):
            continue

        gap_research = proj_research - target

        rows.append({
            "horse": horse,
            "projected_rating_v5_2": r.get("projected_rating_v5_2",""),
            "projection_gap_v5_2": r.get("projection_gap_v5_2",""),
            "projected_rating_research": round(proj_research,2),
            "projection_gap_research": round(gap_research,2),
            "gap_delta": round(
                gap_research - n(r.get("projection_gap_v5_2","")),
                2
            )
        })

    out = pd.DataFrame(rows)

    out.to_csv(OUT,index=False)

    summary = pd.DataFrame([
        {
            "rows": len(out),
            "avg_gap_old":
                round(pd.to_numeric(
                    out["projection_gap_v5_2"],
                    errors="coerce"
                ).mean(),4),

            "avg_gap_research":
                round(pd.to_numeric(
                    out["projection_gap_research"],
                    errors="coerce"
                ).mean(),4),

            "max_gap_old":
                round(pd.to_numeric(
                    out["projection_gap_v5_2"],
                    errors="coerce"
                ).max(),4),

            "max_gap_research":
                round(pd.to_numeric(
                    out["projection_gap_research"],
                    errors="coerce"
                ).max(),4)
        }
    ])

    summary.to_csv(SUMMARY,index=False)

    print("[PROJECTION_RESEARCH_GAP_AUDIT] COMPLETE")
    print(f"rows={len(out)}")
    print(f"audit={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
