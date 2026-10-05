from pathlib import Path
import json, math
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[2]
INP=ROOT/"outputs/research/profitability_program/lab245b/LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
OUTDIR=INP.parent\nTARGET_MANIFEST=OUTDIR/"LAB245B_WAREHOUSE_RUNNER_LVS.manifest.json"
FEATURES=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_worst5","margin_std5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]
BASELINES={"LVS_LAST1":"lvs_last1","LVS_MEAN3":"lvs_mean3","LVS_MEAN5":"lvs_mean5","LVS_MEDIAN5":"lvs_median5","DIST200_LVS":"dist200_lvs_mean"}
SELECTABLE_BASELINES={"LVS_LAST1","LVS_MEAN3","LVS_MEAN5","LVS_MEDIAN5"}

def score(d,p):
    y=d["target_lvs"].to_numpy(float); p=np.asarray(p,float)
    ok=np.isfinite(y)&np.isfinite(p); y=y[ok]; p=p[ok]
    t=d.loc[ok,["_race","target_lvs"]].copy(); t["pred"]=p
    rho=[]
    for _,g in t.groupby("_race",sort=False):
        if len(g)>=3 and g["target_lvs"].nunique()>1 and g["pred"].nunique()>1:
            rho.append(g["target_lvs"].corr(g["pred"],method="spearman"))
    return {"rows":len(y),"races":t["_race"].nunique(),"mae":mean_absolute_error(y,p),"rmse":math.sqrt(mean_squared_error(y,p)),"race_spearman_mean":float(np.nanmean(rho)) if rho else np.nan}

def main():
    if not INP.exists(): raise FileNotFoundError(INP)\n    if not TARGET_MANIFEST.exists(): raise FileNotFoundError(TARGET_MANIFEST)\n    target_manifest=json.loads(TARGET_MANIFEST.read_text(encoding="utf-8"))\n    if target_manifest.get("contract_version")!="LAB245B_STRICT_PIT_LVS_V8_V1_LENGTH_CONVERSION_TRACK_DISTANCE_CONDITION_MIN20": raise RuntimeError("LAB245B1 target manifest contract mismatch")
    d=pd.read_csv(INP,low_memory=False)
    required={"_race","_horse","_year","race_date","target_lvs","target_finish_position","target_field_size","hist_runs",*FEATURES}
    missing=sorted(required-set(d.columns))
    if missing: raise RuntimeError(f"LAB245B1 input contract missing columns: {missing}")
    if not d["_year"].between(2021,2024).all(): raise RuntimeError("Sealed-year breach.")
    raw=d.copy()
    raw["hist_runs"]=pd.to_numeric(raw["hist_runs"],errors="coerce").fillna(0)
    d=d[d["target_lvs"].notna()].copy()
    d=d[pd.to_numeric(d["hist_runs"],errors="coerce").fillna(0)>=3].copy()
    # Common evaluation universe for simple-vs-ML selection: require a finite recency LVS history.
    # DIST200 remains diagnostic because its availability is conditional on distance-near history.
    d=d[np.isfinite(pd.to_numeric(d["lvs_mean3"],errors="coerce"))].copy()
    coverage={str(int(y)):{"rows":int(len(g)),"races":int(g["_race"].nunique())} for y,g in d.groupby("_year",sort=True)}
    history_depth={}
    for y,g in raw.groupby("_year",sort=True):
        yy=str(int(y)); total_races=int(g["_race"].nunique())
        eligible=g[(g["target_lvs"].notna())&(g["hist_runs"]>=3)]
        fs=g.groupby("_race")["_horse"].nunique(); es=eligible.groupby("_race")["_horse"].nunique()
        complete=int(sum(int(es.get(r,0))==int(n) for r,n in fs.items()))
        history_depth[yy]={"all_rows":int(len(g)),"zero_prior_rows":int((g["hist_runs"]==0).sum()),"one_two_prior_rows":int(g["hist_runs"].between(1,2).sum()),"three_plus_prior_rows":int((g["hist_runs"]>=3).sum()),"all_races":total_races,"three_plus_complete_target_races":complete,"three_plus_complete_race_pct":100.0*complete/total_races if total_races else 0.0}
    feats=[x for x in FEATURES if x in d.columns]
    if len(feats)!=len(FEATURES): raise RuntimeError(f"Missing governed features: {sorted(set(FEATURES)-set(feats))}")
    for x in feats+["target_lvs"]: d[x]=pd.to_numeric(d[x],errors="coerce")
    d=d[np.isfinite(d["target_lvs"])].copy()
    if d.empty: raise RuntimeError("No finite governed performance targets after coercion.")
    rows=[]; pp=[]
    for year in [2022,2023,2024]:
        tr=d[d["_year"]<year]; te=d[d["_year"]==year]
        if tr.empty or te.empty: continue
        for name,col in BASELINES.items():
            p=te[col].to_numpy(float)
            rows.append({"year":year,"model":name,**score(te,p)})
            q=te[["_race","_horse","_year","race_date","target_lvs","target_finish_position","target_field_size"]].copy(); q["model"]=name; q["pred_lvs"]=p; pp.append(q)
        models={"RIDGE":make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=10.0)),"HGB":HistGradientBoostingRegressor(max_iter=250,learning_rate=.04,max_leaf_nodes=15,l2_regularization=5,random_state=245)}
        for name,m in models.items():
            m.fit(tr[feats],tr["target_lvs"]); p=m.predict(te[feats])
            rows.append({"year":year,"model":name,**score(te,p)})
            q=te[["_race","_horse","_year","race_date","target_lvs","target_finish_position","target_field_size"]].copy(); q["model"]=name; q["pred_lvs"]=p; pp.append(q)
    res=pd.DataFrame(rows); pred=pd.concat(pp,ignore_index=True)
    res.to_csv(OUTDIR/"LAB245B1_NEXT_PERFORMANCE_RESULTS.csv",index=False)
    pred.to_csv(OUTDIR/"LAB245B1_OOF_PREDICTIONS.csv",index=False)
    # Architecture/model choice is development-only (2022-23). 2024 is a single fixed confirmation.
    dev=pred[pred["_year"].isin([2022,2023])]
    dev_rows=[]
    for name,g in dev.groupby("model",sort=False):
        dev_rows.append({"model":name,**score(g,g["pred_lvs"].to_numpy(float))})
    devres=pd.DataFrame(dev_rows)
    devres.to_csv(OUTDIR/"LAB245B1_DEVELOPMENT_SELECTION.csv",index=False)
    bs_dev=devres[devres["model"].isin(SELECTABLE_BASELINES)].sort_values(["mae","rmse"]).iloc[0]
    bm_dev=devres[devres["model"].isin(["RIDGE","HGB"])].sort_values(["mae","rmse"]).iloc[0]
    v=res[res["year"]==2024]
    bs=v[v["model"]==bs_dev["model"]].iloc[0]
    bm=v[v["model"]==bm_dev["model"]].iloc[0]
    # Stability gate: pooled development gain must not be created by a single development year reversal.
    yearly_ok=True; yearly_deltas={}
    for yy in [2022,2023]:
        sy=res[(res.year==yy)&(res.model==bs_dev["model"])].iloc[0]; my=res[(res.year==yy)&(res.model==bm_dev["model"])].iloc[0]
        yearly_deltas[str(yy)]={"mae_gain":float(sy.mae-my.mae),"rmse_gain":float(sy.rmse-my.rmse),"spearman_gain":float(my.race_spearman_mean-sy.race_spearman_mean)}
        yearly_ok=yearly_ok and my.mae<sy.mae and my.rmse<sy.rmse and my.race_spearman_mean>sy.race_spearman_mean
    survive=bool(yearly_ok and bm_dev["mae"]<bs_dev["mae"] and bm_dev["rmse"]<bs_dev["rmse"] and bm_dev["race_spearman_mean"]>bs_dev["race_spearman_mean"] and bm["mae"]<bs["mae"] and bm["rmse"]<bs["rmse"] and bm["race_spearman_mean"]>bs["race_spearman_mean"])
    audit={"contract_version":"LAB245B1_ACTUAL_LVS_FORECAST_V1","status":"SURVIVE_TO_LAB245B2" if survive else "REJECT_ML_PERFORMANCE_ENGINE","rows":int(len(d)),"races":int(d["_race"].nunique()),"feature_count":len(feats),"development_selection_rule":"COMMON_COVERAGE_2022_2023_SELECT_LOWEST_MAE_THEN_RMSE; SURVIVAL_REQUIRES_MAE_RMSE_AND_RACE_SPEARMAN","dev_selected_simple":bs_dev.to_dict(),"dev_selected_ml":bm_dev.to_dict(),"validation_2024_simple":bs.to_dict(),"validation_2024_ml":bm.to_dict(),"holdout_2025_2026_opened":False,"market_used":False,"target_contract_version":target_manifest.get("contract_version"),"target_output_sha256":target_manifest.get("output_sha256"),"coverage_by_year":coverage,"history_depth_and_full_field_coverage":history_depth,"development_yearly_stability_required":True,"development_yearly_deltas":yearly_deltas}
    (OUTDIR/"LAB245B1_AUDIT.json").write_text(json.dumps(audit,indent=2,default=str),encoding="utf-8")
    print(res.to_string(index=False)); print(json.dumps(audit,indent=2,default=str))
if __name__=="__main__": main()