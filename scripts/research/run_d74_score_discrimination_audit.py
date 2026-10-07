from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv";B=R/"outputs"/"research"/"profitability_program"/"lab245b"/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
d=pd.read_csv(D);b=pd.read_csv(B);x=d.merge(b[["_race","_horse","last_distance","last_finish","last_won","last_top3"]],on=["_race","_horse"],how="left",validate="one_to_one")
x["distance_change"]=x.current_distance-x.last_distance;x["abs_distance_change"]=x.distance_change.abs();prep=["days_since_last","distance_change","abs_distance_change","last_finish","last_won","last_top3"];x["date"]=pd.to_datetime(x.race_date);x["year_eval"]=x.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"};num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])];context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"};F=[c for c in num if c not in context]+prep
print("D75_CONTRACT PREP48_CONTENDER_CLUSTER_DIAGNOSTIC NO_MODEL_CHANGE NO_MARKET NO_THRESHOLD_SELECTION")
for yr in [2022,2023,2024]:
 tr=x.year_eval<yr;te=x.year_eval.eq(yr);m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42));m.fit(x.loc[tr,F],x.loc[tr,"y"]);s=m.decision_function(x.loc[te,F]);z=x.loc[te,["_race","y"]].copy();z["s"]=s;z["rank"]=z.groupby("_race").s.rank(ascending=False,method="first")
 race=[]
 for rid,g in z.groupby("_race",sort=False):
  a=np.sort(g.s.to_numpy())[::-1];w=g[g.y.eq(1)]
  if len(w)!=1:continue
  wr=float(w["rank"].iloc[0]);g12=a[0]-a[1] if len(a)>1 else np.nan;g13=a[0]-a[2] if len(a)>2 else np.nan
  near05=int(np.sum(a>=a[0]-.5));near10=int(np.sum(a>=a[0]-1.0))
  race.append((wr,g12,g13,near05,near10,len(g)))
 q=pd.DataFrame(race,columns=["wr","g12","g13","near05","near10","field"])
 print("D75_YEAR",yr,"RACES",len(q),"WIN_RANK_DIST",q.wr.value_counts(normalize=True).sort_index().head(8).to_dict(),"G12_Q",np.quantile(q.g12,[.1,.25,.5,.75,.9]).tolist(),"NEAR05_Q",np.quantile(q.near05,[.1,.25,.5,.75,.9]).tolist(),"NEAR10_Q",np.quantile(q.near10,[.1,.25,.5,.75,.9]).tolist())
 for label,mask in [("TIGHT_G12_LE_0.10",q.g12<=.10),("MID_G12_0.10_0.30",(q.g12>.10)&(q.g12<=.30)),("CLEAR_G12_GT_0.30",q.g12>.30),("CLUSTER3PLUS_05",q.near05>=3),("CLUSTER2_05",q.near05==2),("SOLO_05",q.near05==1)]:
  a=q[mask]
  if len(a):print("D75_SEG",yr,label,"RACES",len(a),"TOP1",float((a.wr==1).mean()),"TOP2",float((a.wr<=2).mean()),"MRR",float((1/a.wr).mean()))
print("D75_COMPLETE DIAGNOSTIC_ONLY 2025_2026_SEALED")
