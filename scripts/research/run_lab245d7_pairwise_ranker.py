from pathlib import Path
import pandas as pd,numpy as np,math,json
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(__file__).resolve().parents[2];D=R/"outputs/research/profitability_program/lab245b";P=D/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
F=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_worst5","margin_std5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]
def prep(d):
 d=d.copy()
 for c in F:d[c]=pd.to_numeric(d[c],errors="coerce")
 d.hist_runs=d.hist_runs.fillna(0);d["y"]=(pd.to_numeric(d.target_finish_position,errors="coerce")==1).astype(int)
 d["log_hist"]=np.log1p(d.hist_runs);d["hist0"]=(d.hist_runs==0).astype(int);d["hist1"]=(d.hist_runs==1).astype(int);d["hist2"]=(d.hist_runs==2).astype(int);d["hist10p"]=(d.hist_runs>=10).astype(int)
 ff=F+["log_hist","hist0","hist1","hist2","hist10p"]
 for c in F:
  d[c+"_relmed"]=d[c]-d.groupby("_race")[c].transform("median");ff.append(c+"_relmed")
 return d,ff
def pairdata(d,ff,cap=12,seed=2457):
 rng=np.random.default_rng(seed);X=[];y=[]
 for _,g in d.groupby("_race",sort=False):
  w=g[g.y==1]
  if len(w)!=1:continue
  win=w.iloc[0];los=g[g.y==0]
  if len(los)>cap:los=los.iloc[rng.choice(len(los),cap,replace=False)]
  a=win[ff].to_numpy(float)
  for _,q in los.iterrows():
   b=q[ff].to_numpy(float);X.append(a-b);y.append(1);X.append(b-a);y.append(0)
 return np.asarray(X),np.asarray(y)
def met(z):
 a=[]
 for _,g in z.groupby("_race",sort=False):
  w=np.flatnonzero(g.y.to_numpy()==1)
  if len(w)!=1:continue
  s=g.s.to_numpy(float);p=np.exp(np.clip(s-s.max(),-40,40));p/=p.sum();rk=int(pd.Series(s).rank(ascending=False,method="first").iloc[w[0]])
  a.append((rk,-math.log(max(p[w[0]],1e-12))))
 a=np.array(a,float);return len(a),np.mean(a[:,0]<=1),np.mean(a[:,0]<=2),np.mean(a[:,0]<=3),np.mean(1/a[:,0]),np.mean(a[:,1])
def main():
 d,ff=prep(pd.read_csv(P,low_memory=False));d=d[d._year.between(2021,2024)&d.target_lvs.notna()].copy();rows=[]
 for yr in [2022,2023,2024]:
  tr=d[d._year<yr];te=d[d._year==yr];X,y=pairdata(tr,ff)
  mods=[("PAIR_LOGIT",make_pipeline(SimpleImputer(strategy="median",add_indicator=True),StandardScaler(),LogisticRegression(C=.1,max_iter=2500))),
        ("PAIR_HGB",make_pipeline(SimpleImputer(strategy="median",add_indicator=True),HistGradientBoostingClassifier(max_iter=300,learning_rate=.035,max_leaf_nodes=15,min_samples_leaf=40,l2_regularization=15,random_state=2457)))]
  for name,m in mods:
   m.fit(X,y);base=np.zeros((1,len(ff))); # score runner by preference versus zero/reference feature vector
   # Pairwise linear logit has direct utility; HGB utility estimated against race opponents.
   if name=="PAIR_LOGIT":
    imp=m.named_steps["simpleimputer"];sc=m.named_steps["standardscaler"];lr=m.named_steps["logisticregression"]
    Xt=imp.transform(te[ff]);s=lr.decision_function(sc.transform(Xt))
   else:
    s=np.zeros(len(te))
    for _,idx in te.groupby("_race").groups.items():
     ix=np.asarray(list(idx));A=te.loc[ix,ff].to_numpy(float);vals=[]
     for i in range(len(A)):
      dif=A[i]-np.delete(A,i,axis=0);vals.append(m.predict_proba(dif)[:,1].mean() if len(dif) else .5)
     s[te.index.get_indexer(ix)]=vals
   z=te[["_race","y"]].copy();z["s"]=s;n,t1,t2,t3,mrr,ll=met(z);rows.append([yr,name,n,t1,t2,t3,mrr,ll])
 out=pd.DataFrame(rows,columns=["year","model","races","top1","top2","top3","mrr","race_log_loss"]);out.to_csv(D/"LAB245D7_PAIRWISE_RANKER.csv",index=False)
 dev=out[out.year.isin([2022,2023])].groupby("model").mean(numeric_only=True).drop(columns=["year","races"]).sort_values(["top1","mrr"],ascending=False)
 aud={"contract":"LAB245D7_PAIRWISE_RANKER_V1","selection_years":[2022,2023],"2024_role":"OBSERVED_DIAGNOSTIC_ONLY","2025_2026_opened":False,"market_used":False,"dev":dev.reset_index().to_dict("records")}
 (D/"LAB245D7_PAIRWISE_RANKER.json").write_text(json.dumps(aud,indent=2));print(out.to_string(index=False));print("\nDEV\n"+dev.to_string());print("\n"+json.dumps(aud,indent=2))
if __name__=="__main__":main()
