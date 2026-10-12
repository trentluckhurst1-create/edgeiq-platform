"""Issue 23 follow-up: descriptive winner-rank feature diagnostic, no training."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
SCORES = ROOT / "outputs/research/codex_issue5_winning_model"
CONTEXT = ROOT / "outputs/research/model_v2/stage006/V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv"
OUT = Path("outputs/research/issue23_top1_winner_selection")
FEATURES = [
    "current_distance", "hist_runs", "lvs_last1", "lvs_mean3",
    "lvs_mean5", "lvs_median5", "lvs_std5", "lvs_peak", "lvs_worst5",
    "margin_mean5", "margin_std5", "margin_worst5", "margin_last1",
    "margin_last2", "last_distance", "margin_change_l1_l2",
    "margin_per_runner_last1", "margin_per_runner_last2", "days_since_last",
    "dist200_runs", "dist200_lvs_mean", "dist200_lvs_best",
    "represented_field_size", "barrier_position_pct", "jockey_prior_starts",
    "jockey_prior_win_rate", "jockey_prior_top3_rate", "trainer_prior_starts",
    "trainer_prior_win_rate", "trainer_prior_top3_rate",
    "clean_finish_mean5", "clean_last_finish", "clean_last_won",
    "clean_last_top3", "clean_finish_hist_n"
]

def main():
    if not CONTEXT.is_file():
        raise FileNotFoundError(CONTEXT)
    parts = []
    for year in (2022, 2023, 2024):
        p = SCORES / f"CODEX_BAKEOFF_RUNNER_SCORES_{year}.csv"
        d = pd.read_csv(p, usecols=["_race", "_horse", "year", "y", "p", "model_id"])
        d = d[d.model_id.eq("CODEX_ISSUE5_A")].copy()
        parts.append(d)
    scores = pd.concat(parts, ignore_index=True)
    if scores.year.max() > 2024:
        raise RuntimeError("Sealed years prohibited")
    if scores.duplicated(["year", "_race", "_horse"]).any():
        raise RuntimeError("Duplicate scored runners")
    sums = scores.groupby(["year", "_race"])["y"].sum()
    if not sums.eq(1).all():
        raise RuntimeError("Non-single-winner races")
    scores = scores.sort_values(["year", "_race", "p", "_horse"], ascending=[True, True, False, True])
    scores["model_rank"] = scores.groupby(["year", "_race"]).cumcount().add(1)
    winners = scores[scores.y.eq(1)].copy()
    winners["winner_group"] = np.where(winners.model_rank.eq(1), "rank1",
                                np.where(winners.model_rank.ge(4), "rank4plus", "rank2or3"))
    header = pd.read_csv(CONTEXT, nrows=0).columns.tolist()
    available = [f for f in FEATURES if f in header]
    ctx = pd.read_csv(CONTEXT, usecols=["_race", "_horse", "year"] + available)
    ctx = ctx[ctx.year.isin([2022, 2023, 2024])]
    if ctx.duplicated(["year", "_race", "_horse"]).any():
        raise RuntimeError("Duplicate feature identities: stop, don't pick arbitrary row")
    winners = winners.merge(ctx, on=["year", "_race", "_horse"], how="left",
                            validate="one_to_one", indicator=True)
    matched = int(winners._merge.eq("both").sum())
    if matched != len(winners):
        raise RuntimeError(f"Missing Stage006 feature joins: {len(winners)-matched}/{len(winners)}")
    winners = winners.drop(columns="_merge")
    field = scores.groupby(["year", "_race"]).size().rename("actual_field_size")
    winners = winners.join(field, on=["year", "_race"])
    winners["field_band"] = pd.cut(winners.actual_field_size,
            bins=[0,8,12,np.inf], labels=["small_1_8","medium_9_12","large_13plus"])
    rows = []
    for (year, band), subset in winners.groupby(["year", "field_band"], observed=True):
        a = subset[subset.winner_group.eq("rank1")]
        b = subset[subset.winner_group.eq("rank4plus")]
        for f in available:
            x = pd.to_numeric(a[f], errors="coerce").replace([np.inf,-np.inf],np.nan).dropna()
            z = pd.to_numeric(b[f], errors="coerce").replace([np.inf,-np.inf],np.nan).dropna()
            rows.append({"year":int(year),"field_band":str(band),"feature":f,
                "rank1_n":len(x),"rank4plus_n":len(z),
                "rank1_coverage":len(x)/len(a) if len(a) else np.nan,
                "rank4plus_coverage":len(z)/len(b) if len(b) else np.nan,
                "rank1_median":x.median() if len(x) else np.nan,
                "rank4plus_median":z.median() if len(z) else np.nan,
                "median_diff_rank4plus_minus_rank1":z.median()-x.median() if len(x) and len(z) else np.nan})
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT/"ISSUE23_WINNER_RANK_FEATURE_DIAGNOSTIC.csv", index=False)
    summary = (winners.groupby(["year","field_band","winner_group"],observed=True)
               .size().rename("winners").reset_index())
    summary.to_csv(OUT/"ISSUE23_WINNER_RANK_GROUP_COUNTS.csv", index=False)
    print("PASS: descriptive diagnostic only; no model fit or promotion")
    print(f"Races={len(winners)}; Stage006 features available={len(available)}/{len(FEATURES)}")
    print("Missing Stage011 feature names in Stage006:", sorted(set(FEATURES)-set(available)))
    print(summary.to_string(index=False))
    print("Output:", OUT.resolve())

if __name__ == "__main__":
    main()
