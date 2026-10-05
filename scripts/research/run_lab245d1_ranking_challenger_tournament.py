from pathlib import Path
import pandas as pd, numpy as np, json, math
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor, HistGradientBoostingRegressor, RandomForestClassifier, ExtraTreesClassifier
from sklearn.metrics import log_loss, brier_score_loss
from sklearn.linear_model import LogisticRegression

ROOT=Path(__file__).resolve().parents[2]; D=ROOT/"outputs/research/profitability_program/lab245b"
INP=D/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"; OUT=D/"LAB245D1_RANKING_TOURNAMENT.csv"; OOF=D/"LAB245D1_RANKING_TOURNAMENT_OOF.csv"; AUD=D/"LAB245D1_RANKING_TOURNAMENT.json"
BASE=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_worst5","margin_std5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]

def prep(d):
 d=d.copy(); d["hist_runs"]=pd.to_numeric(d.hist_runs,errors="coerce").fillna(0)
 d["log_hist"]=np.log1p(d.hist_runs); d["hist0"]=(d.hist_runs==0).astype(int); d["hist1"]=(d.hist_runs==1).astype(int); d["hist2"]=(d.hist_runs==2).astype(int); d["hist10p"]=(d.hist_runs>=10).astype(int)
 for c in BASE:
  d[c]=pd.to_numeric(d[c],errors="coerce"); med=d[c].groupby(d._race).transform("median"); d[c+"_relmed"]=d[c]-med
 d["field_size"]=d.groupby("_race")["_horse"].transform("size")
 d["y"]=(pd.to_numeric(d.target_finish_position,errors="coerce")==1).astype(int)
 f=BASE+[c+"_relmed" for c in BASE]+["log_hist","hist0","hist1","hist2","hist10p","field_size"]
 return d,f

def models():
 return {
 "ET_LVS":("reg",make_pipeline(SimpleImputer(strategy="median",add_indicator=True),ExtraTreesRegressor(n_estimators=600,min_samples_leaf=8,max_features=.85,n_jobs=-1,random_state=24571)),"target_lvs"),
 "HGB_LVS":("reg",make_pipeline(SimpleImputer(strategy="median",add_indicator=True),HistGradientBoostingRegressor(max_iter=350,learning_rate=.035,max_leaf_nodes=15,min_samples_leaf=20,l2_regularization=8,random_state=24572)),"target_lvs"),
 "RF_LVS":("reg",make_pipeline(SimpleImputer(strategy="median",add_indicator=True),RandomForestRegressor(n_estimators=450,min_samples_leaf=10,max_features=.75,n_jobs=-1,random_state=24573)),"target_lvs"),
 "ET_WIN":("clf",make_pipeline(SimpleImputer(strategy="median",add_indicator=True),ExtraTreesClassifier(n_estimators=600,min_samples_leaf=12,max_features=.85,class_weight="balanced",n_jobs=-1,random_state=24574)),"y"),
 "RF_WIN":("clf",make_pipeline(SimpleImputer(strategy="median",add_indicator=True),RandomForestClassifier(n_estimators=450,min_samples_leaf=12,max_features=.75,class_weight="balanced",n_jobs=-1,random_state=24575)),"y"),
 "LOGIT_WIN":("clf",make_pipeline(SimpleImputer(strategy="median",add_indicator=True),LogisticRegression(C=.3,max_iter=2000,class_weight="balanced")),"y")
 }

def norm(g):
 q=np.exp(np.clip(g.score.to_numpy(float)-g.score.max(),-50,50)); return q/q.sum()
def met(g):
 winners=np.flatnonzero(g.y.to_numpy()==1)
 if len(winners)!=1:return None
 rank=int(g.score.rank(method="first",ascending=False).iloc[winners[0]])
 p=float(g.p.iloc[winners[0]])
 return rank,p,-math.log(max(p,1e-12))
def main():
 d,f=prep(pd.read_csv(INP,low_memory=False)); d=d[d._year.between(2021,2024)&d.target_lvs.notna()].copy()
 rows=[]; oo=[]
 for yr in [2022,2023,2024]:
  tr=d[d._year<yr]; te=d[d._year==yr].copy()
  for name,(typ,m,tgt) in models().items():
   m.fit(tr[f],tr[tgt])
   if typ=="clf": score=m.predict_proba(te[f])[:,1]
   else: score=m.predict(te[f])
   z=te[["_race","_horse","_year","y"]].copy(); z["model"]=name; z["score"]=score
   z["p"]=z.groupby("_race",group_keys=False).apply(lambda g:pd.Series(norm(g),index=g.index),include_groups=False).sort_index()
   rr=[v for _,g in z.groupby("_race",sort=False) if (v:=met(g)) is not None]
   a=np.array(rr,float); rows.append({"year":yr,"model":name,"races":len(a),"top1":np.mean(a[:,0]<=1),"top2":np.mean(a[:,0]<=2),"top3":np.mean(a[:,0]<=3),"mrr":np.mean(1/a[:,0]),"race_log_loss":np.mean(a[:,2])}); oo.append(z)
 r=pd.DataFrame(rows); r.to_csv(OUT,index=False); pd.concat(oo).to_csv(OOF,index=False)
 # Selection is 2022-23 only; rank by average top1 then MRR. 2024 diagnostic only.
 dev=r[r.year.isin([2022,2023])].groupby("model").agg(top1=("top1","mean"),mrr=("mrr","mean"),top3=("top3","mean"),race_log_loss=("race_log_loss","mean")).reset_index().sort_values(["top1","mrr"],ascending=False)
 selected=str(dev.iloc[0].model)
 audit={"contract":"LAB245D1_RANKING_CHALLENGER_TOURNAMENT_V1","selection_years":[2022,2023],"selected_by":"MEAN_TOP1_THEN_MRR","selected_model":selected,"2024_role":"OBSERVED_DIAGNOSTIC_ONLY","2025_2026_opened":False,"market_used":False,"models":list(models()),"dev_leaderboard":dev.to_dict("records")}
 AUD.write_text(json.dumps(audit,indent=2)); print(r.to_string(index=False)); print("\nDEV LEADERBOARD"); print(dev.to_string(index=False)); print("\n"+json.dumps(audit,indent=2))
if __name__=="__main__":main()
