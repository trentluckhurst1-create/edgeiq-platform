"""Summarize existing Issue23 winner-rank diagnostic without fitting or selecting a model."""
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path("outputs/research/issue23_top1_winner_selection")
SOURCE = BASE / "ISSUE23_WINNER_RANK_FEATURE_DIAGNOSTIC.csv"
OUT = BASE / "ISSUE23_WINNER_RANK_CROSS_YEAR_CONSISTENCY.csv"

def main():
    d = pd.read_csv(SOURCE)
    required = {"year", "field_band", "feature", "rank1_n", "rank4plus_n",
                "rank1_coverage", "rank4plus_coverage", "rank1_median",
                "rank4plus_median", "median_diff_rank4plus_minus_rank1"}
    if not required.issubset(d.columns):
        raise RuntimeError("Unexpected diagnostic schema")
    if set(d.year) != {2022, 2023, 2024}:
        raise RuntimeError("Unexpected years; sealed years prohibited")
    if d.duplicated(["year", "field_band", "feature"]).any():
        raise RuntimeError("Duplicate feature/year/band")
    rows = []
    for (band, feature), g in d.groupby(["field_band", "feature"], sort=True):
        g = g.sort_values("year")
        diffs = pd.to_numeric(g["median_diff_rank4plus_minus_rank1"], errors="coerce")
        valid = diffs.notna() & diffs.ne(0)
        signs = np.sign(diffs[valid])
        rows.append({
            "field_band": band, "feature": feature,
            "years_observed": len(g),
            "years_with_nonzero_difference": int(valid.sum()),
            "same_direction_all_three_years": bool(len(g)==3 and valid.sum()==3 and signs.nunique()==1),
            "direction": ("rank4plus_higher" if signs.iloc[0]>0 else "rank4plus_lower") if len(signs)==3 and signs.nunique()==1 else "mixed_or_insufficient",
            "minimum_rank1_n": int(g.rank1_n.min()),
            "minimum_rank4plus_n": int(g.rank4plus_n.min()),
            "minimum_rank1_coverage": float(g.rank1_coverage.min()),
            "minimum_rank4plus_coverage": float(g.rank4plus_coverage.min()),
            "median_difference_2022": float(diffs.iloc[0]) if len(g)==3 else np.nan,
            "median_difference_2023": float(diffs.iloc[1]) if len(g)==3 else np.nan,
            "median_difference_2024": float(diffs.iloc[2]) if len(g)==3 else np.nan,
        })
    result = pd.DataFrame(rows)
    result["descriptive_complete_coverage"] = (result.minimum_rank1_coverage >= 0.9) & (result.minimum_rank4plus_coverage >= 0.9)
    result.to_csv(OUT, index=False)
    print("ISSUE23 FEATURE DIRECTION CHECK — DESCRIPTIVE ONLY")
    print("Features with consistent median direction across all three years (large fields):")
    selected = result[(result.field_band=="large_13plus") & result.same_direction_all_three_years & result.descriptive_complete_coverage]
    print(selected[["feature","direction","minimum_rank1_n","minimum_rank4plus_n","median_difference_2022","median_difference_2023","median_difference_2024"]].to_string(index=False) if len(selected) else "None")
    print(f"\nAll features compared: {result.feature.nunique()}")
    print(f"Output: {OUT.resolve()}")
    print("Differences between winner groups do NOT establish predictive value or causality.")

if __name__ == "__main__":
    main()
