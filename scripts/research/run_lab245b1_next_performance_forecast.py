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
OUTDIR=INP.parent
FEATURES=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_worst5","margin_std5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]
BASELINES={"LVS_LAST1":"lvs_last1","LVS_MEAN3":"lvs_mean3","LVS_MEAN5":"lvs_mean5","LVS_MEDIAN5":"lvs_median5","DIST200_LVS":"dist200_lvs_mean"}

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
    if not INP.exists(): raise FileNotFoundError(INP)
    d=pd.read_csv(INP,low_memory=False)
    if not d["_year"].between(2021,2024).all(): raise RuntimeError("Sealed-year breach.")
    d=d[d["target_lvs"].notna()].copy()
    d=d[pd.to_numeric(d["hist_runs"],errors="coerce").fillna(0)>=3].copy()
    feats=[x for x in FEATURES if x in d.columns]
    if len(feats)!=len(FEATURES): raise RuntimeError(f"Missing governed features: {sorted(set(FEATURES)-set(feats))}")
    for x in feats+["target_lvs"]: d[x]=pd.to_numeric(d[x],errors="coerce")
    rows=[]; pp=[]
    for year in [2022,2023,2024]:
        tr=d[d["_year"]<year]; te=d[d["_year"]==year]
        if tr.empty or te.empty: continue
        for name,col in BASELINES.items():
            p=te[col].to_numpy(float)
            rows.append({"year":year,"model":name,**score(te,p)})
            q=te[["_race","_horse","_year","target_lvs"]].copy(); q["model"]=name; q["pred_lvs"]=p; pp.append(q)
        models={"RIDGE":make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=10.0)),"HGB":HistGradientBoostingRegressor(max_iter=250,learning_rate=.04,max_leaf_nodes=15,l2_regularization=5,random_state=245)}
        for name,m in models.items():
            m.fit(tr[feats],tr["target_lvs"]); p=m.predict(te[feats])
            rows.append({"year":year,"model":name,**score(te,p)})
            q=te[["_race","_horse","_year","target_lvs"]].copy(); q["model"]=name; q["pred_lvs"]=p; pp.append(q)
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
    bs_dev=devres[devres["model"].isin(BASELINES)].sort_values(["mae","rmse"]).iloc[0]
    bm_dev=devres[devres["model"].isin(["RIDGE","HGB"])].sort_values(["mae","rmse"]).iloc[0]
    v=res[res["year"]==2024]
    bs=v[v["model"]==bs_dev["model"]].iloc[0]
    bm=v[v["model"]==bm_dev["model"]].iloc[0]
    survive=bool(bm_dev["mae"]<bs_dev["mae"] and bm_dev["rmse"]<bs_dev["rmse"] and bm_dev["race_spearman_mean"]>bs_dev["race_spearman_mean"] and bm["mae"]<bs["mae"] and bm["rmse"]<bs["rmse"] and bm["race_spearman_mean"]>bs["race_spearman_mean"])
    audit={"status":"SURVIVE_TO_LAB245B2" if survive else "REJECT_ML_PERFORMANCE_ENGINE","rows":int(len(d)),"races":int(d["_race"].nunique()),"feature_count":len(feats),"development_selection_rule":"EQUAL_RANK_MAE_RMSE_RACE_SPEARMAN_2022_2023_ONLY","dev_selected_simple":bs_dev.to_dict(),"dev_selected_ml":bm_dev.to_dict(),"validation_2024_simple":bs.to_dict(),"validation_2024_ml":bm.to_dict(),"holdout_2025_2026_opened":False,"market_used":False,"coverage_by_year":coverage}
    (OUTDIR/"LAB245B1_AUDIT.json").write_text(json.dumps(audit,indent=2,default=str),encoding="utf-8")
    print(res.to_string(index=False)); print(json.dumps(audit,indent=2,default=str))
if __name__=="__main__": main()