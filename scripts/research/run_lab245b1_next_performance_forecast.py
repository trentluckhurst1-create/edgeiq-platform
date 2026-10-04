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
RESULTS=OUTDIR/"LAB245B1_NEXT_PERFORMANCE_RESULTS.csv"
PRED=OUTDIR/"LAB245B1_OOF_PREDICTIONS.csv"
AUDIT=OUTDIR/"LAB245B1_AUDIT.json"

FEATURES=[
"h179_epi_career_mean","h179_epi_recent_mean3","h179_epi_recent_mean5","h179_epi_career_median",
"h179_epi_q75","h179_epi_peak","h179_recent_peak5","h179_best_recent_performance",
"h179_history_runs","h179_recent_obs_90d","h179_recent_obs_180d","h179_age_peak_days",
"h179_runs_since_peak","h179_days_since_meaningful_epi","h179_epi_std_career","h179_epi_std_last5",
"h179_margin_std_last5","h179_pos_mean_last5","h179_peak_minus_recent5","h179_peak_minus_median",
"h179_career_minus_recent5","h179_recent5_minus_peak","h179_peak_age_x_gap","h179_days_since_last_run",
"h179_recency_decay_60","h179_recency_decay_120","h179_recency_weighted_ability",
"h179_reliability_weight","h179_recent_reliability_weight","h179_shrunk_career_ability",
"h179_shrunk_recent_ability","h179_volatility_penalty","h179_current_ability_state",
"h179_distance_relevant_epi","h179_distance_relevant_peak","h179_distance_relevant_observations",
"h179_distance_relevant_reliability","h179_distance_shrunk_ability","h179_distance_minus_recent",
"h179_distance_minus_career","h179_peak_minus_distance"]

def score(d,p):
    y=d.target_lvs.to_numpy(float); p=np.asarray(p,float)
    ok=np.isfinite(y)&np.isfinite(p); y=y[ok]; p=p[ok]
    t=d.loc[ok,["_race","target_lvs"]].copy(); t["pred"]=p
    rho=[]
    for _,g in t.groupby("_race",sort=False):
        if len(g)>=3 and g.target_lvs.nunique()>1 and g.pred.nunique()>1:
            rho.append(g.target_lvs.corr(g.pred,method="spearman"))
    return dict(rows=len(y),races=t._race.nunique(),mae=mean_absolute_error(y,p),
      rmse=math.sqrt(mean_squared_error(y,p)),
      race_spearman_mean=float(np.nanmean(rho)) if rho else np.nan)

def main():
    if not INP.exists(): raise FileNotFoundError(INP)
    d=pd.read_csv(INP,low_memory=False)
    if not d._year.between(2021,2024).all(): raise RuntimeError("Sealed-year breach.")
    d=d[d.target_lvs.notna()].copy()
    d=d[pd.to_numeric(d.h179_history_runs,errors="coerce").fillna(0)>=3].copy()
    feats=[c for c in FEATURES if c in d]
    if len(feats)<35: raise RuntimeError(f"Too few LAB179 features: {len(feats)}")
    for c in feats+["target_lvs"]: d[c]=pd.to_numeric(d[c],errors="coerce")

    simple={"CAREER":"h179_epi_career_mean","LAST3":"h179_epi_recent_mean3",
            "LAST5":"h179_epi_recent_mean5","RECENCY":"h179_recency_weighted_ability",
            "DISTANCE":"h179_distance_shrunk_ability"}
    rows=[]; predrows=[]
    for year in [2022,2023,2024]:
        tr=d[d._year<year]; te=d[d._year==year]
        if tr.empty or te.empty: continue
        for name,col in simple.items():
            z=tr[[col,"target_lvs"]].dropna()
            if len(z)<100: continue
            a,b=np.polyfit(z[col],z.target_lvs,1)
            p=te[col].to_numpy(float)*a+b
            rows.append({"year":year,"model":"HIST_"+name,**score(te,p)})
            q=te[["_race","_horse","_year","target_lvs"]].copy(); q["model"]="HIST_"+name;q["pred_lvs"]=p;predrows.append(q)
        models={
          "RIDGE":make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=10.0)),
          "HGB":HistGradientBoostingRegressor(max_iter=250,learning_rate=.04,max_leaf_nodes=15,l2_regularization=5,random_state=245)}
        for name,m in models.items():
            m.fit(tr[feats],tr.target_lvs); p=m.predict(te[feats])
            rows.append({"year":year,"model":name,**score(te,p)})
            q=te[["_race","_horse","_year","target_lvs"]].copy();q["model"]=name;q["pred_lvs"]=p;predrows.append(q)

    res=pd.DataFrame(rows); pred=pd.concat(predrows,ignore_index=True)
    res.to_csv(RESULTS,index=False); pred.to_csv(PRED,index=False)
    v=res[res.year==2024]; bs=v[v.model.str.startswith("HIST_")].sort_values(["mae","rmse"]).iloc[0]
    bm=v[v.model.isin(["RIDGE","HGB"])].sort_values(["mae","rmse"]).iloc[0]
    survive=bool(bm.mae<bs.mae and bm.rmse<bs.rmse and bm.race_spearman_mean>bs.race_spearman_mean)
    audit={"status":"SURVIVE_TO_LAB245B2" if survive else "REJECT_ML_PERFORMANCE_ENGINE",
      "rows":int(len(d)),"races":int(d._race.nunique()),"feature_count":len(feats),
      "best_2024_simple":bs.to_dict(),"best_2024_ml":bm.to_dict(),
      "holdout_2025_2026_opened":False,"market_used":False}
    AUDIT.write_text(json.dumps(audit,indent=2,default=str),encoding="utf-8")
    print(res.to_string(index=False));print(json.dumps(audit,indent=2,default=str))
if __name__=="__main__":main()
