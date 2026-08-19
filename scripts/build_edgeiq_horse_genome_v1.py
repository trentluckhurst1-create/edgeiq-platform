from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_race_shape_fit_v1.csv"

OUTPUT = DATA / "edgeiq_horse_genome_v1.csv"
AUDIT = DATA / "edgeiq_horse_genome_v1_audit.csv"

def num(v):
    try:
        return float(v)
    except:
        return 0.0

def confidence(runs):
    if runs >= 20:
        return "HIGH"
    if runs >= 10:
        return "MEDIUM"
    return "LOW"

def main():

    df = pd.read_csv(INPUT)

    req = [
        "horse_key",
        "horse",
        "race_shape_v1",
        "race_shape_fit_score_v1"
    ]

    for c in req:
        if c not in df.columns:
            raise ValueError(f"Missing column: {c}")

    rows = []

    for horse_key, g in df.groupby("horse_key"):

        horse_name = g["horse"].iloc[0]

        runs = len(g)

        shape_stats = (
            g.groupby("race_shape_v1")["race_shape_fit_score_v1"]
            .mean()
            .reset_index()
            .sort_values(
                "race_shape_fit_score_v1",
                ascending=False
            )
        )

        preferred_shape = (
            shape_stats.iloc[0]["race_shape_v1"]
            if len(shape_stats)
            else "UNKNOWN"
        )

        preferred_score = (
            float(shape_stats.iloc[0]["race_shape_fit_score_v1"])
            if len(shape_stats)
            else 0
        )

        worst_shape = (
            shape_stats.iloc[-1]["race_shape_v1"]
            if len(shape_stats)
            else "UNKNOWN"
        )

        worst_score = (
            float(shape_stats.iloc[-1]["race_shape_fit_score_v1"])
            if len(shape_stats)
            else 0
        )

        dependency = round(
            preferred_score - worst_score,
            3
        )

        rows.append({
            "horse_key": horse_key,
            "horse_name": horse_name,
            "genome_runs_v1": runs,
            "preferred_shape_v1": preferred_shape,
            "preferred_shape_score_v1": round(preferred_score,3),
            "worst_shape_v1": worst_shape,
            "worst_shape_score_v1": round(worst_score,3),
            "shape_dependency_score_v1": dependency,
            "genome_confidence_v1": confidence(runs)
        })

    out = pd.DataFrame(rows)

    out["shape_dependency_band_v1"] = np.where(
        out["shape_dependency_score_v1"] >= 25,
        "EXTREME",
        np.where(
            out["shape_dependency_score_v1"] >= 15,
            "HIGH",
            np.where(
                out["shape_dependency_score_v1"] >= 8,
                "MODERATE",
                "LOW"
            )
        )
    )

    out = out.sort_values(
        "shape_dependency_score_v1",
        ascending=False
    )

    out.to_csv(OUTPUT, index=False)

    audit = pd.DataFrame([{
        "horses": len(out),
        "high_confidence": int((out["genome_confidence_v1"]=="HIGH").sum()),
        "medium_confidence": int((out["genome_confidence_v1"]=="MEDIUM").sum()),
        "low_confidence": int((out["genome_confidence_v1"]=="LOW").sum()),
        "extreme_dependency": int((out["shape_dependency_band_v1"]=="EXTREME").sum()),
        "high_dependency": int((out["shape_dependency_band_v1"]=="HIGH").sum()),
        "output": str(OUTPUT)
    }])

    audit.to_csv(AUDIT,index=False)

    print("[HORSE_GENOME_V1] COMPLETE")
    print(f"horses={len(out)}")
    print(f"output={OUTPUT}")

if __name__ == "__main__":
    main()
