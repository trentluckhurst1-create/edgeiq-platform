from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_historical_race_shape_archive_v1.csv"

OUTPUT = DATA / "edgeiq_horse_genome_v2.csv"
AUDIT = DATA / "edgeiq_horse_genome_v2_audit.csv"

def num(v):
    try:
        if pd.isna(v):
            return np.nan
        return float(v)
    except:
        return np.nan

def confidence(starts):
    if starts >= 20:
        return "HIGH"
    if starts >= 10:
        return "MEDIUM"
    if starts >= 3:
        return "LOW"
    return "VERY_LOW"

def band(score):
    if score >= 80:
        return "ELITE"
    if score >= 70:
        return "STRONG"
    if score >= 60:
        return "SOLID"
    if score >= 50:
        return "NEUTRAL"
    return "WEAK"

def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing input: {INPUT}")

    df = pd.read_csv(INPUT)

    df = df[df["is_scratched"].astype(str) == "0"].copy()

    df["finish_position_num"] = pd.to_numeric(df["finish_position_num"], errors="coerce")
    df["won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0)
    df["placed"] = pd.to_numeric(df["placed"], errors="coerce").fillna(0)
    df["field_strength_score"] = pd.to_numeric(df["field_strength_score"], errors="coerce")
    df["sectional_strength_rating"] = pd.to_numeric(df["sectional_strength_rating"], errors="coerce")
    df["historical_shape_fit_score_v1"] = pd.to_numeric(df["historical_shape_fit_score_v1"], errors="coerce")
    df["historical_shape_fit_percentile_v1"] = pd.to_numeric(df["historical_shape_fit_percentile_v1"], errors="coerce")

    rows = []

    for horse_key, g in df.groupby("horse_key_join"):
        starts = len(g)
        wins = int(g["won"].sum())
        places = int(g["placed"].sum())

        horse_name = ""
        if "horseName" in g.columns:
            horse_name = str(g["horseName"].dropna().iloc[0]) if len(g["horseName"].dropna()) else ""
        elif "horse" in g.columns:
            horse_name = str(g["horse"].dropna().iloc[0]) if len(g["horse"].dropna()) else ""

        position_style = "UNKNOWN"
        if "historical_position_style_v1" in g.columns:
            vc = g["historical_position_style_v1"].fillna("UNKNOWN").astype(str).str.upper().value_counts()
            if len(vc):
                position_style = vc.index[0]

        preferred_strength_band = ""
        if "sectional_strength_band" in g.columns:
            vc = g["sectional_strength_band"].fillna("").astype(str).str.upper().value_counts()
            if len(vc):
                preferred_strength_band = vc.index[0]

        win_pct = wins / starts if starts else 0
        place_pct = places / starts if starts else 0

        avg_finish = g["finish_position_num"].mean()
        avg_race_strength = g["field_strength_score"].mean()
        avg_sectional_strength = g["sectional_strength_rating"].mean()
        avg_shape_fit = g["historical_shape_fit_score_v1"].mean()
        avg_shape_percentile = g["historical_shape_fit_percentile_v1"].mean()

        genome_score = (
            (win_pct * 100) * 0.25
            + (place_pct * 100) * 0.25
            + (avg_shape_percentile if not np.isnan(avg_shape_percentile) else 0) * 0.20
            + (avg_sectional_strength if not np.isnan(avg_sectional_strength) else 0) * 0.20
            + (avg_race_strength if not np.isnan(avg_race_strength) else 0) * 0.10
        )

        rows.append({
            "horse_key": horse_key,
            "horse_name": horse_name,
            "starts_v2": starts,
            "wins_v2": wins,
            "places_v2": places,
            "win_pct_v2": round(win_pct, 4),
            "place_pct_v2": round(place_pct, 4),
            "avg_finish_v2": round(float(avg_finish), 3) if not np.isnan(avg_finish) else "",
            "avg_race_strength_v2": round(float(avg_race_strength), 3) if not np.isnan(avg_race_strength) else "",
            "avg_sectional_strength_v2": round(float(avg_sectional_strength), 3) if not np.isnan(avg_sectional_strength) else "",
            "avg_shape_fit_v2": round(float(avg_shape_fit), 3) if not np.isnan(avg_shape_fit) else "",
            "avg_shape_percentile_v2": round(float(avg_shape_percentile), 3) if not np.isnan(avg_shape_percentile) else "",
            "preferred_position_style_v2": position_style,
            "common_sectional_strength_band_v2": preferred_strength_band,
            "horse_genome_score_v2": round(float(genome_score), 3),
            "horse_genome_band_v2": band(genome_score),
            "genome_confidence_v2": confidence(starts),
        })

    out = pd.DataFrame(rows)

    out = out.sort_values(
        ["horse_genome_score_v2", "starts_v2"],
        ascending=[False, False]
    )

    out.to_csv(OUTPUT, index=False)

    audit = pd.DataFrame([{
        "input_rows": len(df),
        "output_horses": len(out),
        "high_confidence": int((out["genome_confidence_v2"] == "HIGH").sum()),
        "medium_confidence": int((out["genome_confidence_v2"] == "MEDIUM").sum()),
        "low_confidence": int((out["genome_confidence_v2"] == "LOW").sum()),
        "very_low_confidence": int((out["genome_confidence_v2"] == "VERY_LOW").sum()),
        "elite": int((out["horse_genome_band_v2"] == "ELITE").sum()),
        "strong": int((out["horse_genome_band_v2"] == "STRONG").sum()),
        "solid": int((out["horse_genome_band_v2"] == "SOLID").sum()),
        "neutral": int((out["horse_genome_band_v2"] == "NEUTRAL").sum()),
        "weak": int((out["horse_genome_band_v2"] == "WEAK").sum()),
        "output": str(OUTPUT),
    }])

    audit.to_csv(AUDIT, index=False)

    print("[HORSE_GENOME_V2] COMPLETE")
    print(f"input_rows={len(df)}")
    print(f"output_horses={len(out)}")
    print(f"wrote={OUTPUT}")
    print(f"audit={AUDIT}")
    print(out["horse_genome_band_v2"].value_counts(dropna=False).to_string())

if __name__ == "__main__":
    main()
