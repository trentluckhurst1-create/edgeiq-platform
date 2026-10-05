from pathlib import Path
import pandas as pd, numpy as np, json, math
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier, ExtraTreesClassifier
ROOT=Path(__file__).resolve().parents[2]; D=ROOT/"outputs/research/profitability_program/lab245b"
INP=D/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"; OUT=D/"LAB245D2_DIRECT_WIN_CHALLENGERS.csv"; OOF=D/"LAB245D2_DIRECT_WIN_OOF.csv"; AUD=D/"LAB245D2_DIRECT_WIN_CHALLENGERS.json"
BASE=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_worst5","margin_std5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]
def prep(d):
 d=d.copy(); d["hist_runs"]=pd.to_numeric(d.hist_runs,errors="coerce").fillna(0)
 d["log_hist"]=np.log1p(d.hist_runs); d["hist0"]=(d.hist_runs==0).astype(int); d["hist1"]=(d.hist_runs==1).astype(int); d["hist2"]=(d.hist_runs==2).astype(int); d["hist10p"]=(d.hist_runs>=10).astype(int)
 for c in BASE:
  d[c]=pd.to_numeric(d[c],errors="coerce"); med=d[c].groupby(d._race).transform("median"); d[c+"_relmed"]=d[c]-med
 d["field_size"]=d.groupby("_race")["_horse"].transform("size"); d["y"]=(pd.to_numeric(d.target_finish_position,errors="coerce")==1).astype(int)
 f=BASE+[c+"_relmed" for c in BASE]+["log_hist","hist0","hist1","hist2","hist10p","field_size"]
 return d,f
def modelset():
 return {
 "LOGIT_L2_C003":make_pipeline(SimpleImputer(strategy="median",add_indicator=True),StandardScaler(),LogisticRegression(C=.03,max_iter=5000,class_weight="balanced",solver="lbfgs")),
 "LOGIT_L2_C01":make_pipeline(SimpleImputer(strategy="median",add_indicator=True),StandardScaler(),LogisticRegression(C=.1,max_iter=5000,class_weight="balanced",solver="lbfgs")),
 "LOGIT_L2_C03":make_pipeline(SimpleImputer(strategy="median",add_indicator=True),StandardScaler(),LogisticRegression(C=.3,max_iter=5000,class_weight="balanced",solver="lbfgs")),
 "LOGIT_L2_C1":make_pipeline(SimpleImputer(strategy="median",add_indicator=True),StandardScaler(),LogisticRegression(C=1,max_iter=5000,class_weight="balanced",solver="lbfgs")),
 "LOGIT_L1_C01":make_pipeline(SimpleImputer(strategy="median",add_indicator=True),StandardScaler(),LogisticRegression(C=.1,max_iter=5000,class_weight="balanced",solver="liblinear",penalty="l1")),
 "HGB_WIN":make_pipeline(SimpleImputer(strategy="median",add_indicator=True),HistGradientBoostingClassifier(max_iter=350,learning_rate=.035,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=10,random_state=24582)),
 "ET_WIN_FINE":make_pipeline(SimpleImputer(strategy="median",add_indicator=True),ExtraTreesClassifier(n_estimators=700,min_samples_leaf=8,max_features=.85,class_weight="balanced",n_jobs=-1,random_state=24583))
 }
def normalize(g):
 q=np.clip(g.raw.to_numpy(float),1e-12,None); return q/q.sum()
def metrics(z):
 rr=[]
 for _,g in z.groupby("_race",sort=False):
  w=np.flatnonzero(g.y.to_numpy()==1)
  if len(w)!=1:continue
  rank=int(g.raw.rank(method="first",ascending=False).iloc[w[0]]); p=float(g.p.iloc[w[0]])
  rr.append((rank,p,-math.log(max(p,1e-12))))
 a=np.array(rr,float)
 return {"races":len(a),"top1":np.mean(a[:,0]<=1),"top2":np.mean(a[:,0]<=2),"top3":np.mean(a[:,0]<=3),"mrr":np.mean(1/a[:,0]),"race_log_loss":np.mean(a[:,2])}
def main():
 d,f=prep(pd.read_csv(INP,low_memory=False)); d=d[d._year.between(2021,2024)&d.target_lvs.notna()].copy(); rows=[]; oo=[]
 for yr in [2022,2023,2024]:
  tr=d[d._year<yr]; te=d[d._year==yr]
  for name,m in modelset().items():
   m.fit(tr[f],tr.y); raw=m.predict_proba(te[f])[:,1]
   z=te[["_race","_horse","_year","y"]].copy(); z["model"]=name; z["raw"]=raw
   z["p"]=z.groupby("_race",group_keys=False).apply(lambda g:pd.Series(normalize(g),index=g.index),include_groups=False).sort_index()
   rows.append({"year":yr,"model":name,**metrics(z)}); oo.append(z)
 r=pd.DataFrame(rows); r.to_csv(OUT,index=False); pd.concat(oo,ignore_index=True).to_csv(OOF,index=False)
 dev=r[r.year.isin([2022,2023])].groupby("model").agg(top1=("top1","mean"),mrr=("mrr","mean"),top3=("top3","mean"),race_log_loss=("race_log_loss","mean")).reset_index()
 # Predeclared balanced score: top1 primary, MRR secondary; report Pareto rather than pretending tiny differences are certainty.
 max1=dev.top1.max(); pareto=dev[dev.top1>=max1-.003].sort_values(["mrr","race_log_loss"],ascending=[False,True])
 audit={"contract":"LAB245D2_DIRECT_WIN_CHALLENGERS_V1","selection_years":[2022,2023],"selection_policy":"TOP1_WITHIN_0.003_OF_BEST_THEN_MRR_THEN_RACE_LOG_LOSS","selected_model":str(pareto.iloc[0].model),"2024_role":"OBSERVED_DIAGNOSTIC_ONLY","2025_2026_opened":False,"market_used":False,"dev_leaderboard":dev.sort_values("top1",ascending=False).to_dict("records")}
 AUD.write_text(json.dumps(audit,indent=2)); print(r.to_string(index=False)); print("\nDEV"); print(dev.sort_values(["top1","mrr"],ascending=False).to_string(index=False)); print("\n"+json.dumps(audit,indent=2))
if __name__=="__main__":main()
