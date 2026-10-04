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
OUTDIR=ROOT/"outputs/research/profitability_program/lab245b"
RESULTS=OUTDIR/"LAB245B1_NEXT_PERFORMANCE_RESULTS.csv"
PRED=OUTDIR/"LAB245B1_OOF_PREDICTIONS.csv"
AUDIT=OUTDIR/"LAB245B1_AUDIT.json"

RAW_FEATURES=[
"h231_hist_perf_runs","h231_epi_last1","h231_epi_last3_mean","h231_epi_last5_mean",
"h231_epi_last5_median","h231_epi_last5_worst","h231_epi_last10_median",
"h231_epi_last10_best","h231_epi_last10_worst","h231_epi_last10_std",
"h231_epi_peak_prior","h231_epi_last1_minus_peak","h231_epi_last1_minus_last5_median",
"h231_epi_last5_slope","h231_margin_last5_mean","h231_margin_last5_worst",
"h231_margin_last5_std","h231_finishpos_last5_mean","h231_days_since_last_perf",
"h231_days_since_peak","h231_peak_age_runs","h231_dist200_count","h231_dist200_mean",
"h231_dist200_best","h231_dist200_best_minus_peak","h231_same_class_count",
"h231_same_class_mean","h231_same_class_best","h231_same_condition_count",
"h231_same_condition_mean","h231_near_peak_share_last10",
"h231_recent_above_last10_median_share"
]

def metrics(d,p):
    ok=np.isfinite(d["target_lvs"].to_numpy(float)) & np.isfinite(p)
    y=d.loc[ok,"target_lvs"].to_numpy(float); q=np.asarray(p)[ok]
    tmp=d.loc[ok,["_race","target_lvs"]].copy(); tmp["pred"]=q
    corrs=[]
    for _,g in tmp.groupby("_race",sort=False):
        if len(g)>=3 and g["target_lvs"].nunique()>1 and g["pred"].nunique()>1:
            corrs.append(g["target_lvs"].corr(g["pred"],method="spearman"))
    return {
      "rows":len(y),"races":tmp["_race"].nunique(),
      "mae":mean_absolute_error(y,q),
      "rmse":math.sqrt(mean_squared_error(y,q)),
      "race_spearman_mean":float(np.nanmean(corrs)) if corrs else np.nan
    }

def main():
    if not INP.exists(): raise FileNotFoundError(INP)
    d=pd.read_csv(INP,low_memory=False)
    if not d["_year"].between(2021,2024).all(): raise RuntimeError("Sealed-year breach.")
    d=d[d["target_lvs"].notna()].copy()
    d=d[pd.to_numeric(d["h231_hist_perf_runs"],errors="coerce").fillna(0)>=3].copy()
    features=[c for c in RAW_FEATURES if c in d.columns]
    if len(features)<20: raise RuntimeError(f"Too few governed features: {len(features)}")
    for c in features+["target_lvs"]:
        d[c]=pd.to_numeric(d[c],errors="coerce")

    simple={
      "HIST_EPI_LAST1":"h231_epi_last1",
      "HIST_EPI_LAST3":"h231_epi_last3_mean",
      "HIST_EPI_LAST5":"h231_epi_last5_mean",
      "HIST_EPI_MEDIAN10":"h231_epi_last10_median",
    }
    # EPI is a linear transform of LVS; simple EPI baselines are compared by fitting
    # a dev-only affine mapping to target LVS, never using validation outcomes.
    rows=[]; preds=[]
    for test_year in [2022,2023,2024]:
        train=d[d["_year"]<test_year].copy(); test=d[d["_year"]==test_year].copy()
        if train.empty or test.empty: continue
        for name,col in simple.items():
            z=train[[col,"target_lvs"]].dropna()
            if len(z)<100: continue
            slope,intercept=np.polyfit(z[col],z["target_lvs"],1)
            p=test[col].to_numpy(float)*slope+intercept
            m=metrics(test,p); rows.append({"year":test_year,"model":name,**m})
            x=test[["_race","_horse","_year","target_lvs"]].copy(); x["model"]=name; x["pred_lvs"]=p; preds.append(x)

        models={
          "RIDGE":make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=10.0)),
          "HGB":HistGradientBoostingRegressor(max_iter=250,learning_rate=.04,max_leaf_nodes=15,l2_regularization=5.0,random_state=245),
        }
        for name,model in models.items():
            model.fit(train[features],train["target_lvs"])
            p=model.predict(test[features])
            m=metrics(test,p); rows.append({"year":test_year,"model":name,**m})
            x=test[["_race","_horse","_year","target_lvs"]].copy(); x["model"]=name; x["pred_lvs"]=p; preds.append(x)

    res=pd.DataFrame(rows)
    pp=pd.concat(preds,ignore_index=True)
    res.to_csv(RESULTS,index=False); pp.to_csv(PRED,index=False)

    v=res[res.year==2024].copy()
    simple_v=v[v.model.str.startswith("HIST_")]
    ml_v=v[v.model.isin(["RIDGE","HGB"])]
    best_simple=simple_v.sort_values(["mae","rmse"],ascending=True).iloc[0]
    best_ml=ml_v.sort_values(["mae","rmse"],ascending=True).iloc[0]
    survive=bool(
      best_ml.mae < best_simple.mae and
      best_ml.rmse < best_simple.rmse and
      best_ml.race_spearman_mean > best_simple.race_spearman_mean
    )
    audit={
      "status":"SURVIVE_TO_LAB245B2" if survive else "REJECT_ML_PERFORMANCE_ENGINE",
      "rows":int(len(d)),"races":int(d["_race"].nunique()),"features":features,
      "best_2024_simple":best_simple.to_dict(),"best_2024_ml":best_ml.to_dict(),
      "holdout_2025_2026_opened":False,"market_used":False
    }
    AUDIT.write_text(json.dumps(audit,indent=2,default=str),encoding="utf-8")
    print(res.to_string(index=False))
    print(json.dumps(audit,indent=2,default=str))

if __name__=="__main__":
    main()
