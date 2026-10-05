from pathlib import Path
import pandas as pd,numpy as np,math,json
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");O=R/"outputs/research/profitability_program/lab245b";S=O/"LAB245B_WAREHOUSE_RUNNER_LVS.csv"
use=["canonical_race_id","canonical_horse_id","race_date","distance_metres","finish_position","finish_margin","runner_lvs","field_size"]
d=pd.read_csv(S,usecols=use,low_memory=False);d["race_date"]=pd.to_datetime(d.race_date,errors="coerce")
for c in ["distance_metres","finish_position","finish_margin","runner_lvs","field_size"]:d[c]=pd.to_numeric(d[c],errors="coerce")
d=d.dropna(subset=["canonical_race_id","canonical_horse_id","race_date"]).sort_values(["canonical_horse_id","race_date","canonical_race_id"],kind="stable")
rows=[]
def sm(a,n,fn=np.mean):
 x=np.asarray(a[-n:],float);x=x[np.isfinite(x)];return float(fn(x)) if len(x) else np.nan
for horse,g in d.groupby("canonical_horse_id",sort=False):
 hist=[]
 for dt,day in g.groupby("race_date",sort=True):
  lv=[x["lvs"] for x in hist if np.isfinite(x["lvs"])];ma=[x["margin"] for x in hist if np.isfinite(x["margin"])];po=[x["pos"] for x in hist if np.isfinite(x["pos"])]
  for r in day.itertuples(index=False):
   if 2021<=dt.year<=2024:
    last10=np.asarray(lv[-10:],float);peak=max(lv) if lv else np.nan
    peak_idx=int(np.argmax(np.asarray(lv,float))) if lv else -1
    near=float(np.mean(last10>=peak-1.0)) if len(last10) and np.isfinite(peak) else np.nan
    med10=float(np.median(last10)) if len(last10) else np.nan
    above=float(np.mean(last10>=med10)) if len(last10) else np.nan
    slope=np.polyfit(np.arange(min(5,len(lv))),np.asarray(lv[-5:],float),1)[0] if len(lv)>=2 else np.nan
    nearD=[x["lvs"] for x in hist if np.isfinite(x["lvs"]) and np.isfinite(x["distance"]) and pd.notna(r.distance_metres) and abs(x["distance"]-r.distance_metres)<=200]
    rec={"_race":r.canonical_race_id,"_horse":horse,"_year":dt.year,"y":int(pd.notna(r.finish_position) and r.finish_position==1),"hist_runs":len(hist),"current_distance":r.distance_metres,
    "lvs_last1":lv[-1] if lv else np.nan,"lvs_mean3":sm(lv,3),"lvs_best3":sm(lv,3,np.max),"lvs_mean5":sm(lv,5),"lvs_best5":sm(lv,5,np.max),"lvs_second_best5":sorted(lv[-5:],reverse=True)[1] if len(lv)>=2 else np.nan,"lvs_median5":sm(lv,5,np.median),"lvs_worst5":sm(lv,5,np.min),"lvs_std5":sm(lv,5,np.std),
    "lvs_median10":med10,"lvs_best10":sm(lv,10,np.max),"lvs_worst10":sm(lv,10,np.min),"lvs_std10":sm(lv,10,np.std),"lvs_peak":peak,"peak_minus_median10":peak-med10 if np.isfinite(peak) and np.isfinite(med10) else np.nan,"last1_minus_peak":lv[-1]-peak if lv else np.nan,"last1_minus_median5":lv[-1]-sm(lv,5,np.median) if lv else np.nan,"lvs_slope5":slope,
    "margin_mean5":sm(ma,5),"margin_worst5":sm(ma,5,np.max),"margin_std5":sm(ma,5,np.std),"finishpos_mean5":sm(po,5),"days_since_last":(dt-hist[-1]["date"]).days if hist else np.nan,"days_since_peak":(dt-hist[peak_idx]["date"]).days if peak_idx>=0 else np.nan,"peak_age_runs":len(hist)-1-peak_idx if peak_idx>=0 else np.nan,
    "dist200_runs":len(nearD),"dist200_mean":float(np.mean(nearD)) if nearD else np.nan,"dist200_best":max(nearD) if nearD else np.nan,"dist200_best_minus_peak":max(nearD)-peak if nearD and np.isfinite(peak) else np.nan,"near_peak_share_last10":near,"recent_above_last10_median_share":above}
    rows.append(rec)
  for r in day.itertuples(index=False):hist.append({"date":dt,"distance":float(r.distance_metres) if pd.notna(r.distance_metres) else np.nan,"pos":float(r.finish_position) if pd.notna(r.finish_position) else np.nan,"margin":float(r.finish_margin) if pd.notna(r.finish_margin) else np.nan,"lvs":float(r.runner_lvs) if pd.notna(r.runner_lvs) else np.nan})
x=pd.DataFrame(rows);raw=[c for c in x if c not in ["_race","_horse","_year","y"]]
# add race-relative rank/z only from pre-race features
for c in raw:
 v=pd.to_numeric(x[c],errors="coerce");x[c+"_rank_pct"]=v.groupby(x._race).rank(pct=True,method="average");mu=v.groupby(x._race).transform("mean");sd=v.groupby(x._race).transform("std").replace(0,np.nan);x[c+"_z"]=(v-mu)/sd
families={"RAW":raw,"RAW_RANK":raw+[c+"_rank_pct" for c in raw],"ALL":raw+[c+"_rank_pct" for c in raw]+[c+"_z" for c in raw]}
def model(seed):return make_pipeline(SimpleImputer(strategy="median",add_indicator=True),HistGradientBoostingClassifier(max_iter=350,learning_rate=.035,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=10,random_state=seed))
def met(q):
 a=[]
 for _,g in q.groupby("_race",sort=False):
  w=np.flatnonzero(g.y.to_numpy()==1)
  if len(w)!=1:continue
  s=g.s.to_numpy();p=np.clip(s,1e-12,None);p/=p.sum();rk=int(pd.Series(s).rank(ascending=False,method="first").iloc[w[0]]);a.append((rk,-math.log(max(p[w[0]],1e-12))))
 a=np.asarray(a);return len(a),np.mean(a[:,0]<=1),np.mean(a[:,0]<=2),np.mean(a[:,0]<=3),np.mean(1/a[:,0]),np.mean(a[:,1])
res=[]
for yr in [2022,2023,2024]:
 tr=x[x._year<yr];te=x[x._year==yr]
 for i,(n,ff) in enumerate(families.items()):
  m=model(2900+i);m.fit(tr[ff],tr.y);q=te[["_race","y"]].copy();q["s"]=m.predict_proba(te[ff])[:,1];res.append([yr,n,len(ff),*met(q)])
o=pd.DataFrame(res,columns=["year","model","features","races","top1","top2","top3","mrr","race_log_loss"]);print(o.to_string(index=False));dev=o[o.year.isin([2022,2023])].groupby("model").mean(numeric_only=True).drop(columns=["year","features","races"]).sort_values("top1",ascending=False);print("\nDEV\n"+dev.to_string())
audit={"contract":"LAB245D17_GOVERNED_RICH_HISTORY_V1","rows":len(x),"races":int(x._race.nunique()),"raw_features":raw,"pit_policy":"HORSE_HISTORY_DATE_LT_TARGET_DATE_SAME_DATE_FROZEN","selection_years":[2022,2023],"2024_role":"OBSERVED_DIAGNOSTIC_ONLY","2025_2026_opened":False,"market_used":False,"dev":dev.reset_index().to_dict("records")}
o.to_csv(O/"LAB245D17_GOVERNED_RICH_HISTORY.csv",index=False);(O/"LAB245D17_GOVERNED_RICH_HISTORY.json").write_text(json.dumps(audit,indent=2));print(json.dumps(audit,indent=2))
