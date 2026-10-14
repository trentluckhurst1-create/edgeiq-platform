"""Issue23: all-runner experience calibration diagnostic. Read-only, 2022-24."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
SCORES = ROOT / "outputs/research/codex_issue5_winning_model"
CONTEXT = ROOT / "outputs/research/model_v2/stage006/V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv"
OUT = Path("outputs/research/issue23_top1_winner_selection")
YEARS = (2022, 2023, 2024)
FEATURES = ("hist_runs", "dist200_runs")
BINS = [-np.inf, 0, 2, 5, 10, np.inf]
LABELS = ["0", "1-2", "3-5", "6-10", "11+"]

def main():
    chunks = []
    for year in YEARS:
        path = SCORES / f"CODEX_BAKEOFF_RUNNER_SCORES_{year}.csv"
        d = pd.read_csv(path, usecols=["year", "_race", "_horse", "model_id", "p", "y"])
        chunks.append(d.loc[d.model_id.eq("CODEX_ISSUE5_A")].drop(columns="model_id"))
    scores = pd.concat(chunks, ignore_index=True)
    if set(scores.year.unique()) != set(YEARS):
        raise RuntimeError("Unexpected year set")
    keys = ["year", "_race", "_horse"]
    if scores.duplicated(keys).any():
        raise RuntimeError("Duplicate scored runners")
    if not scores.groupby(["year", "_race"]).y.sum().eq(1).all():
        raise RuntimeError("Race winner count invalid")
    if not np.allclose(scores.groupby(["year", "_race"]).p.sum().to_numpy(), 1.0, atol=1e-10, rtol=0):
        raise RuntimeError("Race probability mass invalid")
    ctx = pd.read_csv(CONTEXT, usecols=keys+list(FEATURES))
    ctx = ctx.loc[ctx.year.isin(YEARS)]
    if ctx.duplicated(keys).any():
        raise RuntimeError("Duplicate Stage006 runner keys")
    d = scores.merge(ctx, on=keys, how="left", validate="one_to_one", indicator=True)
    if not d._merge.eq("both").all():
        raise RuntimeError("Missing context join")
    d.drop(columns="_merge", inplace=True)
    d["field_size"] = d.groupby(["year", "_race"])["_horse"].transform("size")
    d["field_band"] = pd.cut(d.field_size, bins=[0,8,12,np.inf],
                             labels=["small_1_8","medium_9_12","large_13plus"])
    rows = []
    for feature in FEATURES:
        d[feature] = pd.to_numeric(d[feature], errors="coerce")
        if (d[feature].dropna() < 0).any():
            raise RuntimeError(f"Negative count in {feature}")
        d["experience_band"] = pd.cut(d[feature], bins=BINS, labels=LABELS)
        for (year, field_band, exp_band), g in d.groupby(
            ["year", "field_band", "experience_band"], observed=True):
            observed = float(g.y.sum())
            expected = float(g.p.sum())
            rows.append({
                "feature":feature, "year":int(year), "field_band":str(field_band),
                "experience_band":str(exp_band), "runners":len(g),
                "races_represented":int(g._race.nunique()),
                "observed_wins":int(observed), "expected_wins":expected,
                "observed_win_rate":observed/len(g),
                "mean_assigned_probability":expected/len(g),
                "observed_minus_expected_wins":observed-expected,
                "observed_to_expected":observed/expected if expected>0 else np.nan,
                "feature_coverage":float(d.loc[(d.year==year)&(d.field_band==field_band),feature].notna().mean()),
            })
    out = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "ISSUE23_EXPERIENCE_ALL_RUNNER_CALIBRATION.csv"
    out.to_csv(target, index=False)
    print("PASS: Stage011 all-runner experience calibration; no fitting, no odds")
    print(f"Runners={len(d)} Races={d.groupby(['year','_race']).ngroups}")
    print("Feature missingness:", {f:int(d[f].isna().sum()) for f in FEATURES})
    print("\nLARGE FIELDS (13+), descriptive observed vs expected:")
    view=out[out.field_band.eq("large_13plus")]
    print(view[["feature","year","experience_band","runners","observed_wins",
                "expected_wins","observed_minus_expected_wins","observed_to_expected"]]
          .to_string(index=False,float_format=lambda x:f"{x:.3f}"))
    print("\nNOTE: grouped runners within races are dependent; differences alone are not significance tests.")
    print("Saved:",target.resolve())

if __name__ == "__main__":
    main()
