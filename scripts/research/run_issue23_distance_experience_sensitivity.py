"""Issue23 targeted distance-experience sensitivity: no retraining, no market data.

Exploratory only: 2022-24 outcomes have already been inspected during hypothesis
generation. The 2023/24 results are NOT an untouched confirmation set.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
SCORES = ROOT / "outputs/research/codex_issue5_winning_model"
STAGE006 = ROOT / "outputs/research/model_v2/stage006/V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv"
OUT = Path("outputs/research/issue23_top1_winner_selection")
YEARS = (2022, 2023, 2024)
# Fixed sensitivity grid, not tuned on outcome. The zero coefficient is Stage011.
COEFFICIENTS = (0.0, 0.10, 0.20, 0.30)
def main():
    parts=[]
    for year in YEARS:
        f=SCORES / f"CODEX_BAKEOFF_RUNNER_SCORES_{year}.csv"
        x=pd.read_csv(f,usecols=["year","_race","_horse","y","p","model_id"])
        parts.append(x[x.model_id.eq("CODEX_ISSUE5_A")].drop(columns="model_id"))
    d=pd.concat(parts,ignore_index=True)
    keys=["year","_race","_horse"]
    if set(d.year.unique()) != set(YEARS) or d.duplicated(keys).any():
        raise RuntimeError("Unexpected years or duplicate score keys")
    ctx=pd.read_csv(STAGE006,usecols=keys+["dist200_runs"])
    ctx=ctx[ctx.year.isin(YEARS)]
    if ctx.duplicated(keys).any():
        raise RuntimeError("Duplicate feature keys")
    d=d.merge(ctx,on=keys,how="left",validate="one_to_one",indicator=True)
    if not d._merge.eq("both").all() or d.dist200_runs.isna().any():
        raise RuntimeError("Missing feature join or dist200_runs")
    if (d.dist200_runs<0).any():
        raise RuntimeError("Negative history count")
    d.drop(columns="_merge",inplace=True)
    groups=["year","_race"]
    if not d.groupby(groups).y.sum().eq(1).all():
        raise RuntimeError("Winner count invalid")
    if not np.allclose(d.groupby(groups).p.sum().to_numpy(),1,atol=1e-10,rtol=0):
        raise RuntimeError("Probability mass invalid")
    d["field_size"]=d.groupby(groups)._horse.transform("size")
    d["large_field"]=d.field_size.ge(13)
    # Hypothesis: moderate distance history underrated; extensive overrated.
    # No effect in smaller fields. These bins were selected after inspecting
    # 2022-24 results and therefore this is exploratory sensitivity only.
    d["signal"]=np.select(
        [d.large_field & d.dist200_runs.between(3,5),
         d.large_field & d.dist200_runs.ge(11)],
        [1.0,-1.0],default=0.0)
    rows=[]
    selections=[]
    for coefficient in COEFFICIENTS:
        x=d.copy()
        x["adjusted"]=x.p*np.exp(coefficient*x.signal)
        x["adjusted"]=x.adjusted/x.groupby(groups).adjusted.transform("sum")
        if not np.allclose(x.groupby(groups).adjusted.sum().to_numpy(),1,atol=1e-12,rtol=0):
            raise RuntimeError("Adjusted probability mass invalid")
        x=x.sort_values(["year","_race","adjusted","_horse"],
                        ascending=[True,True,False,True])
        x["rank"]=x.groupby(groups).cumcount()+1
        chosen=x[x["rank"].eq(1)].copy()
        winner=x[x.y.eq(1)].copy()
        for year in YEARS:
            c=chosen[chosen.year.eq(year)]
            w=winner[winner.year.eq(year)]
            rows.append({"coefficient":coefficient,"year":year,
                         "races":len(c),"top1":float(c.y.mean()),
                         "top1_correct":int(c.y.sum()),
                         "winner_log_loss":float(-np.log(w.adjusted.clip(lower=1e-15)).mean()),
                         "winner_top3":float(w["rank"].le(3).mean()),
                         "winner_mean_rank":float(w["rank"].mean())})
        selections.append(chosen[["year","_race","_horse","y","large_field"]].assign(coefficient=coefficient))
    result=pd.DataFrame(rows)
    baseline=result[result.coefficient.eq(0)][["year","top1","winner_log_loss"]].rename(
        columns={"top1":"baseline_top1","winner_log_loss":"baseline_log_loss"})
    result=result.merge(baseline,on="year",validate="many_to_one")
    result["top1_delta_pp"]=(result.top1-result.baseline_top1)*100
    result["log_loss_gain"]=result.baseline_log_loss-result.winner_log_loss
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/"ISSUE23_DISTANCE_EXPERIENCE_SENSITIVITY.csv"
    result.to_csv(target,index=False)
    picks=pd.concat(selections,ignore_index=True)
    base=picks[picks.coefficient.eq(0)][["year","_race","_horse","y"]].rename(
        columns={"_horse":"baseline_horse","y":"baseline_won"})
    comparisons=picks.merge(base,on=["year","_race"],validate="many_to_one")
    comparisons["changed_pick"]=comparisons._horse.ne(comparisons.baseline_horse)
    comparisons["paired_top1_delta"]=comparisons.y-comparisons.baseline_won
    paired=(comparisons.groupby(["coefficient","year","large_field"],as_index=False)
            .agg(races=("_race","size"),changed_picks=("changed_pick","sum"),
                 gained_minus_lost=("paired_top1_delta","sum")))
    paired.to_csv(OUT/"ISSUE23_DISTANCE_EXPERIENCE_PAIRED_PICKS.csv",index=False)
    print("PASS: frozen Stage011 sensitivity only, 2022-24 previously exposed")
    print("No coefficient selected or promoted; no independent validation claim.")
    print(result[["coefficient","year","races","top1","top1_delta_pp","log_loss_gain"]]
          .to_string(index=False,float_format=lambda v:f"{v:.5f}"))
    print("\nPaired changed selections:")
    print(paired.to_string(index=False))
    print("\nSaved:",target.resolve())
if __name__=="__main__":
    main()
