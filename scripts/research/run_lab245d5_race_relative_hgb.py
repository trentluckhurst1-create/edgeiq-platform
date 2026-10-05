from pathlib import Path
import pandas as pd, numpy as np, json, math
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
ROOT=Path(__file__).resolve().parents[2]; D=ROOT/"outputs/research/profitability_program/lab245b"
P=D/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"; OUT=D/"LAB245D5_RACE_RELATIVE_HGB.csv"; OOF=D/"LAB245D5_RACE_RELATIVE_HGB_OOF.csv"; AUD=D/"LAB245D5_RACE_RELATIVE_HGB.json"
BASE=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_worst5","margin_std5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]
def prep(d):
 d=d.copy(); d["hist_runs"]=pd.to_numeric(d.hist_runs,errors="coerce").fillna(0)
 for c in BASE: d[c]=pd.to_numeric(d[c],errors="coerce")
 d["y"]=(pd.to_numeric(d.target_finish_position,errors="coerce")==1).astype(int); d["field_size"]=d.groupby("_race")["_horse"].transform("size")
 d["log_hist"]=np.log1p(d.hist_runs); d["hist0"]=(d.hist_runs==0).astype(int); d["hist1"]=(d.hist_runs==1).astype(int); d["hist2"]=(d.hist_runs==2).astype(int); d["hist10p"]=(d.hist_runs>=10).astype(int)
 core=BASE+["log_hist","hist0","hist1","hist2","hist10p","field_size"]; rich=list(core)
 # Full race-relative representation: deviation, percentile and ordinal position.
 for c in BASE:
  g=d.groupby("_race")[c]; med=g.transform("median"); mean=g.transform("mean"); std=g.transform("std").replace(0,np.nan)
  d[c+"_relmed"]=d[c]-med; d[c+"_zrace"]=(d[c]-mean)/std; d[c+"_pct"]=g.rank(pct=True,method="average")
  rich += [c+"_relmed",c+"_zrace",c+"_pct"]
 # Explicit form/uncertainty interactions.
 d["mean3_x_loghist"]=d.lvs_mean3*d.log_hist
 d["mean5_x_loghist"]=d.lvs_mean5*d.log_hist
 d["std5_x_loghist"]=d.lvs_std5*d.log_hist
 d["distmean_x_logdist"]=d.dist200_lvs_mean*np.log1p(d.dist200_runs.clip(lower=0))
 d["recency_x_loghist"]=d.days_since_last*d.log_hist
 rich += ["mean3_x_loghist","mean5_x_loghist","std5_x_loghist","distmean_x_logdist","recency_x_loghist"]
 return d,core+[c+"_relmed" for c in BASE],rich
def model(seed):
 return make_pipeline(SimpleImputer(strategy="median",add_indicator=True),HistGradientBoostingClassifier(max_iter=400,learning_rate=.03,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=10,random_state=seed))
def met(z):
 rr=[]
 for _,g in z.groupby("_race",sort=False):
  w=np.flatnonzero(g.y.to_numpy()==1)
  if len(w)!=1:continue
  s=g.raw.to_numpy(float); p=np.clip(s,1e-12,None); p/=p.sum(); rank=int(pd.Series(s).rank(method="first",ascending=False).iloc[w[0]])
  rr.append((rank,p[w[0]],-math.log(max(p[w[0]],1e-12))))
 a=np.array(rr,float); return {"races":len(a),"top1":np.mean(a[:,0]<=1),"top2":np.mean(a[:,0]<=2),"top3":np.mean(a[:,0]<=3),"mrr":np.mean(1/a[:,0]),"race_log_loss":np.mean(a[:,2])}
def main():
 d,legacy,rich=prep(pd.read_csv(P,low_memory=False)); d=d[d._year.between(2021,2024)&d.target_lvs.notna()].copy(); rows=[]; oo=[]
 for yr in [2022,2023,2024]:
  tr=d[d._year<yr]; te=d[d._year==yr]
  for name,ff,seed in [("HGB_D2_REPLICA",legacy,24582),("HGB_RACE_RICH",rich,24591)]:
   m=model(seed); m.fit(tr[ff],tr.y); raw=m.predict_proba(te[ff])[:,1]
   z=te[["_race","_horse","_year","y"]].copy(); z["model"]=name; z["raw"]=raw; rows.append({"year":yr,"model":name,**met(z)}); oo.append(z)
 r=pd.DataFrame(rows); r.to_csv(OUT,index=False); pd.concat(oo,ignore_index=True).to_csv(OOF,index=False)
 gains=[]
 for yr in [2022,2023,2024]:
  a=r[(r.year==yr)&(r.model=="HGB_D2_REPLICA")].iloc[0]; b=r[(r.year==yr)&(r.model=="HGB_RACE_RICH")].iloc[0]
  gains.append({"year":yr,"top1_gain":float(b.top1-a.top1),"top3_gain":float(b.top3-a.top3),"mrr_gain":float(b.mrr-a.mrr),"race_log_loss_gain":float(a.race_log_loss-b.race_log_loss)})
 audit={"contract":"LAB245D5_RACE_RELATIVE_HGB_V1","hypothesis":"Richer within-race comparative representation improves direct-win HGB","selection_years":[2022,2023],"2024_role":"OBSERVED_DIAGNOSTIC_ONLY","2025_2026_opened":False,"market_used":False,"gains_vs_d2_hgb":gains}
 AUD.write_text(json.dumps(audit,indent=2)); print(r.to_string(index=False)); print("\nGAINS"); print(pd.DataFrame(gains).to_string(index=False)); print("\n"+json.dumps(audit,indent=2))
if __name__=="__main__":main()
