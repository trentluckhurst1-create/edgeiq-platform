from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

R = Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
P = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
W = R / "outputs/research/model_v2/stage006/V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv"
D = R / "outputs/research/profitability_program/d45/D45_FROZEN_PIT_FEATURE_MATRIX.csv"
A = P / "outputs/research/model_lab_026/edgeiq_certified_flat_walk_forward_epi_026.csv"
OUT = R / "outputs/research/model_v2/stage011_reproduction"
REF = {2022:2.1250604024, 2023:2.1314274279, 2024:2.1022229250}
EVIDENCE = "REUSED_DEVELOPMENT"
def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
    return h.hexdigest()
def sm(v):
    v=np.asarray(v,float)
    e=np.exp(v-np.max(v))
    return e/e.sum()
def main():
    for path in (W,D,A):
        if not path.is_file(): raise FileNotFoundError(path)
    OUT.mkdir(parents=True,exist_ok=True)
    x=pd.read_csv(W)
    x["race_date"]=pd.to_datetime(x.race_date)
    x["year"]=x.race_date.dt.year
    if not x.year.between(2021,2024).all(): raise RuntimeError("Stage006 contains out-of-scope years; STOP")
    d=pd.read_csv(D)
    ctx=[c for c in d.columns if any(k in c.lower() for k in ["barrier","jockey_prior","trainer_prior"]) and pd.api.types.is_numeric_dtype(d[c])]
    x=x.merge(d[["_race","_horse"]+ctx].drop_duplicates(["_race","_horse"]),on=["_race","_horse"],how="left",validate="one_to_one")
    base=["current_distance","hist_runs","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_std5","margin_worst5","margin_last1","margin_last2","last_distance","margin_change_l1_l2","margin_per_runner_last1","margin_per_runner_last2","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best","represented_field_size"]+ctx
    base=[c for c in base if c in x.columns]
    need={"canonical_horse_id","race_date","finish_position"}
    parts=[]
    for z in pd.read_csv(A,usecols=lambda c:c in need,chunksize=500000):
        z["race_date"]=pd.to_datetime(z.race_date,errors="coerce")
        z["finish_position"]=pd.to_numeric(z.finish_position,errors="coerce")
        z=z[z.finish_position.between(1,99)].dropna(subset=["canonical_horse_id","race_date"])
        z=z[z.race_date.dt.year<=2024]
        parts.append(z)
    if not parts: raise RuntimeError("No eligible historical placing rows")
    h=pd.concat(parts,ignore_index=True).sort_values(["canonical_horse_id","race_date"])
    h=h.groupby(["canonical_horse_id","race_date"],as_index=False).agg(finish_position=("finish_position",lambda s:s.iloc[0] if s.nunique()==1 else np.nan)).dropna()
    by={k:g[["race_date","finish_position"]].sort_values("race_date") for k,g in h.groupby("canonical_horse_id")}
    def feats(row):
        g=by.get(row["_horse"])
        if g is None:return pd.Series([np.nan]*5)
        q=g[g.race_date<row.race_date].tail(5).finish_position.to_numpy(float)
        if len(q)==0:return pd.Series([np.nan]*5)
        return pd.Series([q.mean(),q[-1],float(q[-1]==1),float(q[-1]<=3),float(len(q))])
    clean=x[["_horse","race_date"]].apply(feats,axis=1)
    clean.columns=["clean_finish_mean5","clean_last_finish","clean_last_won","clean_last_top3","clean_finish_hist_n"]
    x=pd.concat([x.reset_index(drop=True),clean.reset_index(drop=True)],axis=1)
    features=base+list(clean.columns)
    if x.duplicated(["_race","_horse"]).any(): raise RuntimeError("Duplicate runner identity")
    if x.y.isna().any() or not x.y.isin([0,1]).all():raise RuntimeError("Invalid winner targets")
    if (x.groupby("_race").y.sum()!=1).any():raise RuntimeError("Not single-winner races")
    print("STAGE011_REPRODUCTION_ONLY SEED=42 EVIDENCE_CLASS=REUSED_DEVELOPMENT")
    results=[]
    for yr in [2022,2023,2024]:
        tr=x[x.year<yr]
        te=x[x.year==yr].copy()
        if tr.empty or te.empty:raise RuntimeError(f"Empty train/test year {yr}")
        m=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42)
        m.fit(tr[features].replace([np.inf,-np.inf],np.nan),tr.y.astype(int))
        te["raw"]=m.decision_function(te[features].replace([np.inf,-np.inf],np.nan))
        te["p"]=te.groupby("_race").raw.transform(lambda s:sm(s.values))
        if not np.isfinite(te.p).all() or (te.p<=0).any():raise RuntimeError(f"Invalid probabilities {yr}")
        mass=(te.groupby("_race").p.sum()-1).abs().max()
        ll=float(np.mean([-np.log(max(float(g.loc[g.y.eq(1),"p"].iloc[0]),1e-15)) for _,g in te.groupby("_race")]))
        delta=abs(ll-REF[yr])
        te["evaluation_year"]=yr
        te["evidence_class"]=EVIDENCE
        te["training_year_max"]=int(tr.year.max())
        te["model_name"]="V2_STAGE011_CLEAN_PLACING"
        te["model_seed"]=42
        te["feature_manifest_sha256"]=hashlib.sha256(json.dumps(features,separators=(",",":")).encode()).hexdigest()
        te["source_stage006_sha256"]=sha(W)
        te["source_d45_sha256"]=sha(D)
        te["source_perf026_sha256"]=sha(A)
        cols=["_race","_horse","race_date","evaluation_year","training_year_max","y","raw","p","evidence_class","model_name","model_seed","feature_manifest_sha256","source_stage006_sha256","source_d45_sha256","source_perf026_sha256"]
        if te[cols].isna().any().any():raise RuntimeError(f"Missing protocol fields {yr}")
        te[cols].to_csv(OUT/f"STAGE011_RUNNER_PROBABILITIES_{yr}.csv",index=False)
        passed=delta<=.001 and mass<=1e-12
        results.append(dict(year=yr,train_rows=len(tr),runner_rows=len(te),races=te._race.nunique(),log_loss=ll,reference=REF[yr],abs_delta=delta,max_race_mass_error=float(mass),pass_reproduction=bool(passed),evidence_class=EVIDENCE))
        print(f"YEAR={yr} RACES={te._race.nunique()} LL={ll:.12f} DELTA={delta:.12f} MAX_MASS_ERROR={mass:.3g} STATUS={'PASS' if passed else 'FAIL'}",flush=True)
    report={"status":"PASS" if all(r["pass_reproduction"] for r in results) else "FAIL","scope":"REUSED_DEVELOPMENT_ONLY","years":results,"features":features,"seed":42,"model_settings":{"max_iter":200,"learning_rate":.05,"max_leaf_nodes":5,"l2_regularization":1},"no_independent_validation":True,"no_profitability_claim":True}
    (OUT/"STAGE011_REPRODUCTION_REPORT.json").write_text(json.dumps(report,indent=2))
    print("FINAL_STATUS="+report["status"])
    print("OUTPUT="+str(OUT))
if __name__=="__main__":main()
