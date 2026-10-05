from pathlib import Path
import pandas as pd,numpy as np,math,json
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(__file__).resolve().parents[2]; D=R/"outputs/research/profitability_program/lab245b"; P=D/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
BASE=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_worst5","margin_std5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]
def prep(d):
 d=d.copy()
 for c in BASE:d[c]=pd.to_numeric(d[c],errors="coerce")
 d["hist_runs"]=d.hist_runs.fillna(0);d["y"]=(pd.to_numeric(d.target_finish_position,errors="coerce")==1).astype(int);d["field_size"]=d.groupby("_race")["_horse"].transform("size")
 d["log_hist"]=np.log1p(d.hist_runs);d["hist0"]=(d.hist_runs==0).astype(int);d["hist1"]=(d.hist_runs==1).astype(int);d["hist2"]=(d.hist_runs==2).astype(int);d["hist10p"]=(d.hist_runs>=10).astype(int)
 core=BASE+["log_hist","hist0","hist1","hist2","hist10p","field_size"]; rel=[];pct=[];z=[]
 for c in BASE:
  g=d.groupby("_race")[c]; med=g.transform("median"); mean=g.transform("mean"); sd=g.transform("std").replace(0,np.nan)
  d[c+"_relmed"]=d[c]-med;d[c+"_pct"]=g.rank(pct=True,method="average");d[c+"_zrace"]=(d[c]-mean)/sd
  rel.append(c+"_relmed");pct.append(c+"_pct");z.append(c+"_zrace")
 d["recent_delta"]=d.lvs_last1-d.lvs_mean5;d["short_delta"]=d.lvs_mean3-d.lvs_mean5;d["dist_delta"]=d.dist200_lvs_mean-d.lvs_mean5
 d["std_x_loghist"]=d.lvs_std5*d.log_hist;d["recency_x_loghist"]=d.days_since_last*d.log_hist
 inter=["recent_delta","short_delta","dist_delta","std_x_loghist","recency_x_loghist"]
 return d,{"BASE":core+rel,"PCT":core+rel+pct,"Z":core+rel+z,"INTER":core+rel+inter}
def mk(leaf,minleaf,l2,seed):
 return make_pipeline(SimpleImputer(strategy="median",add_indicator=True),HistGradientBoostingClassifier(max_iter=350,learning_rate=.035,max_leaf_nodes=leaf,min_samples_leaf=minleaf,l2_regularization=l2,random_state=seed))
def metrics(z):
 a=[]
 for _,g in z.groupby("_race",sort=False):
  w=np.flatnonzero(g.y.to_numpy()==1)
  if len(w)!=1:continue
  s=g.s.to_numpy(float);p=np.clip(s,1e-12,None);p/=p.sum();rk=int(pd.Series(s).rank(ascending=False,method="first").iloc[w[0]])
  a.append((rk,-math.log(max(p[w[0]],1e-12))))
 a=np.array(a,float);return len(a),np.mean(a[:,0]<=1),np.mean(a[:,0]<=3),np.mean(1/a[:,0]),np.mean(a[:,1])
def main():
 d,fs=prep(pd.read_csv(P,low_memory=False));d=d[d._year.between(2021,2024)&d.target_lvs.notna()].copy()
 specs=[("BASE",15,30,10),("PCT",15,30,10),("Z",15,30,10),("INTER",15,30,10),("PCT_SHALLOW",7,40,15),("PCT_DEEP",31,50,15)]
 rows=[]
 for yr in [2022,2023,2024]:
  tr=d[d._year<yr];te=d[d._year==yr]
  for i,(name,leaf,ml,l2) in enumerate(specs):
   key="PCT" if name.startswith("PCT_") else name;m=mk(leaf,ml,l2,24600+i);m.fit(tr[fs[key]],tr.y);s=m.predict_proba(te[fs[key]])[:,1]
   z=te[["_race","y"]].copy();z["s"]=s;n,t1,t3,mrr,ll=metrics(z);rows.append([yr,name,n,t1,t3,mrr,ll])
 out=pd.DataFrame(rows,columns=["year","model","races","top1","top3","mrr","race_log_loss"]);out.to_csv(D/"LAB245D6_HGB_FEATURE_ABLATION.csv",index=False)
 dev=out[out.year.isin([2022,2023])].groupby("model").agg(top1=("top1","mean"),top3=("top3","mean"),mrr=("mrr","mean"),race_log_loss=("race_log_loss","mean")).sort_values(["top1","mrr"],ascending=False)
 aud={"contract":"LAB245D6_HGB_FEATURE_ABLATION_V1","selection_years":[2022,2023],"2024_role":"OBSERVED_DIAGNOSTIC_ONLY","2025_2026_opened":False,"market_used":False,"dev_leaderboard":dev.reset_index().to_dict("records")}
 (D/"LAB245D6_HGB_FEATURE_ABLATION.json").write_text(json.dumps(aud,indent=2));print(out.to_string(index=False));print("\nDEV\n"+dev.to_string());print("\n"+json.dumps(aud,indent=2))
if __name__=="__main__":main()
