from pathlib import Path
import pandas as pd,numpy as np,math,json
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(__file__).resolve().parents[2];D=R/"outputs/research/profitability_program/lab245b";P=D/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
F=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_worst5","margin_std5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]
def prep(d):
 d=d.copy()
 for c in F:d[c]=pd.to_numeric(d[c],errors="coerce")
 d.hist_runs=d.hist_runs.fillna(0);d["y"]=(pd.to_numeric(d.target_finish_position,errors="coerce")==1).astype(int);d["field_size"]=d.groupby("_race")["_horse"].transform("size")
 d["log_hist"]=np.log1p(d.hist_runs);d["hist0"]=(d.hist_runs==0).astype(int);d["hist1"]=(d.hist_runs==1).astype(int);d["hist2"]=(d.hist_runs==2).astype(int);d["hist10p"]=(d.hist_runs>=10).astype(int)
 ff=F+["log_hist","hist0","hist1","hist2","hist10p","field_size"]
 for c in F:d[c+"_relmed"]=d[c]-d.groupby("_race")[c].transform("median");ff.append(c+"_relmed")
 d["dist_band"]=pd.cut(d.current_distance,[-1,1200,1600,2200,99999],labels=["SPRINT","MILE","MIDDLE","STAY"])
 d["field_band"]=pd.cut(d.field_size,[0,8,12,999],labels=["SMALL","MEDIUM","LARGE"])
 return d,ff
def model(seed):return make_pipeline(SimpleImputer(strategy="median",add_indicator=True),HistGradientBoostingClassifier(max_iter=350,learning_rate=.035,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=10,random_state=seed))
def met(z):
 a=[]
 for _,g in z.groupby("_race",sort=False):
  w=np.flatnonzero(g.y.to_numpy()==1)
  if len(w)!=1:continue
  s=g.s.to_numpy(float);p=np.clip(s,1e-12,None);p/=p.sum();rk=int(pd.Series(s).rank(ascending=False,method="first").iloc[w[0]])
  a.append((rk,-math.log(max(p[w[0]],1e-12))))
 a=np.asarray(a,float);return len(a),np.mean(a[:,0]<=1),np.mean(a[:,0]<=2),np.mean(a[:,0]<=3),np.mean(1/a[:,0]),np.mean(a[:,1])
def score_special(tr,te,ff,groupcol,minr=120):
 glob=model(2480);glob.fit(tr[ff],tr.y);s=glob.predict_proba(te[ff])[:,1]
 for val in te[groupcol].dropna().unique():
  trr=tr[tr[groupcol]==val];ter=te[te[groupcol]==val]
  if trr._race.nunique()<minr or trr.y.sum()<40:continue
  m=model(2481+len(str(val)));m.fit(trr[ff],trr.y);s[te.index.get_indexer(ter.index)]=m.predict_proba(ter[ff])[:,1]
 return s
def main():
 d,ff=prep(pd.read_csv(P,low_memory=False));d=d[d._year.between(2021,2024)&d.target_lvs.notna()].copy();rows=[]
 for yr in [2022,2023,2024]:
  tr=d[d._year<yr];te=d[d._year==yr]
  g=model(2480);g.fit(tr[ff],tr.y)
  specs=[("GLOBAL",g.predict_proba(te[ff])[:,1]),("DIST_SPECIALIST",score_special(tr,te,ff,"dist_band")),("FIELD_SPECIALIST",score_special(tr,te,ff,"field_band"))]
  for name,s in specs:
   z=te[["_race","y"]].copy();z["s"]=s;n,t1,t2,t3,mrr,ll=met(z);rows.append([yr,name,n,t1,t2,t3,mrr,ll])
 out=pd.DataFrame(rows,columns=["year","model","races","top1","top2","top3","mrr","race_log_loss"]);out.to_csv(D/"LAB245D8_RACE_SPECIALISTS.csv",index=False)
 dev=out[out.year.isin([2022,2023])].groupby("model").mean(numeric_only=True).drop(columns=["year","races"]).sort_values(["top1","mrr"],ascending=False)
 aud={"contract":"LAB245D8_RACE_SPECIALISTS_V1","selection_years":[2022,2023],"2024_role":"OBSERVED_DIAGNOSTIC_ONLY","2025_2026_opened":False,"market_used":False,"dev":dev.reset_index().to_dict("records")}
 (D/"LAB245D8_RACE_SPECIALISTS.json").write_text(json.dumps(aud,indent=2));print(out.to_string(index=False));print("\nDEV\n"+dev.to_string());print("\n"+json.dumps(aud,indent=2))
if __name__=="__main__":main()
