"""Issue23 paired uncertainty for fixed 0.10 distance-experience adjustment.

Exploratory: hypothesis and coefficient were evaluated on these same years.
No independent holdout, training, promotion, odds or market information.
"""
from pathlib import Path
from math import comb
import numpy as np
import pandas as pd

ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
SCORES=ROOT/"outputs/research/codex_issue5_winning_model"
CTX=ROOT/"outputs/research/model_v2/stage006/V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv"
OUT=Path("outputs/research/issue23_top1_winner_selection")
YEARS=(2022,2023,2024)
SEED=23010
N_BOOT=20000

def exact_mcnemar_two_sided(gains,losses):
    n=gains+losses
    if n==0:return 1.0
    tail=sum(comb(n,k) for k in range(min(gains,losses)+1))/(2**n)
    return min(1.0,2*tail)

def main():
    frames=[]
    for year in YEARS:
        p=SCORES/f"CODEX_BAKEOFF_RUNNER_SCORES_{year}.csv"
        d=pd.read_csv(p,usecols=["year","_race","_horse","y","p","model_id"])
        frames.append(d[d.model_id.eq("CODEX_ISSUE5_A")].drop(columns="model_id"))
    d=pd.concat(frames,ignore_index=True)
    keys=["year","_race","_horse"]
    if set(d.year.unique())!=set(YEARS) or d.duplicated(keys).any():
        raise RuntimeError("Invalid score years/keys")
    c=pd.read_csv(CTX,usecols=keys+["dist200_runs"])
    c=c[c.year.isin(YEARS)]
    if c.duplicated(keys).any():raise RuntimeError("Duplicate context keys")
    d=d.merge(c,on=keys,how="left",validate="one_to_one",indicator=True)
    if not d._merge.eq("both").all() or d.dist200_runs.isna().any():
        raise RuntimeError("Incomplete feature joins")
    if not d.groupby(["year","_race"]).y.sum().eq(1).all():
        raise RuntimeError("Invalid winners")
    if not np.allclose(d.groupby(["year","_race"]).p.sum(),1,atol=1e-10,rtol=0):
        raise RuntimeError("Invalid probability mass")
    groups=["year","_race"]
    d["field_size"]=d.groupby(groups)._horse.transform("size")
    d["large_field"]=d.field_size.ge(13)
    d["signal"]=np.select([d.large_field & d.dist200_runs.between(3,5),
                            d.large_field & d.dist200_runs.ge(11)],
                           [1.,-1.],default=0.)
    d["adjusted"]=d.p*np.exp(.10*d.signal)
    d["adjusted"]=d.adjusted/d.groupby(groups).adjusted.transform("sum")
    def selections(column,tag):
        v=d.sort_values(groups+[column,"_horse"],ascending=[True,True,False,True])
        v=v.drop_duplicates(groups)
        return v[groups+["_horse","y","large_field"]].rename(
            columns={"_horse":f"{tag}_horse","y":f"{tag}_won"})
    base=selections("p","baseline")
    candidate=selections("adjusted","candidate")
    pair=base.merge(candidate,on=groups+["large_field"],validate="one_to_one")
    pair["delta"]=pair.candidate_won.astype(int)-pair.baseline_won.astype(int)
    pair["changed"]=pair.baseline_horse.ne(pair.candidate_horse)
    rng=np.random.default_rng(SEED)
    rows=[]
    for label,g in [("all_years",pair)]+[(str(y),pair[pair.year.eq(y)]) for y in YEARS]:
        for band,sub in [("all_fields",g),("large_13plus",g[g.large_field])]:
            delta=sub.delta.to_numpy(dtype=float)
            n=len(delta)
            gains=int((delta==1).sum())
            losses=int((delta==-1).sum())
            if not n:continue
            # Resample paired races, not individual horses.
            boot=np.empty(N_BOOT)
            for i in range(N_BOOT):
                boot[i]=delta[rng.integers(0,n,n)].mean()*100
            rows.append({"year":label,"field_band":band,"races":n,
                         "changed_selections":int(sub.changed.sum()),
                         "gains":gains,"losses":losses,"net_winners":gains-losses,
                         "top1_gain_pp":float(delta.mean()*100),
                         "bootstrap_ci_lower_pp":float(np.quantile(boot,.025)),
                         "bootstrap_ci_upper_pp":float(np.quantile(boot,.975)),
                         "exact_mcnemar_p":exact_mcnemar_two_sided(gains,losses),
                         "resamples":N_BOOT})
    out=pd.DataFrame(rows)
    OUT.mkdir(parents=True,exist_ok=True)
    out.to_csv(OUT/"ISSUE23_DISTANCE_EXPERIENCE_PAIRED_UNCERTAINTY.csv",index=False)
    print("ISSUE23 — PAIRED RACE-LEVEL UNCERTAINTY (coefficient 0.10)")
    print(out.to_string(index=False,float_format=lambda x:f"{x:.5f}"))
    print("\nWARNING: exploratory, not independent validation; no promotion authorized.")
    print("CI is paired race bootstrap; McNemar p is descriptive after hypothesis selection.")
if __name__=="__main__":main()
