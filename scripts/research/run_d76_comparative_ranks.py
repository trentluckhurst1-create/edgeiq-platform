from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv";B=R/"outputs"/"research"/"profitability_program"/"lab245b"/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
d=pd.read_csv(D);b=pd.read_csv(B);x=d.merge(b[["_race","_horse","last_distance","last_finish","last_won","last_top3"]],on=["_race","_horse"],how="left",validate="one_to_one")
x["distance_change"]=x.current_distance-x.last_distance;x["abs_distance_change"]=x.distance_change.abs();prep=["days_since_last","distance_change","abs_distance_change","last_finish","last_won","last_top3"];x["date"]=pd.to_datetime(x.race_date);x["year_eval"]=x.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"};num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])];context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"};base=[c for c in num if c not in context];promoted=base+prep
core=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_std5","margin_worst5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]
ranks=[]
for c in core:
 n=c+"_race_rank_pct_d76";x[n]=x.groupby("_race")[c].rank(pct=True,method="average");ranks.append(n)
print("D76_CONTRACT PREP48_PLUS_CORE17_RACE_RANKS COMPARATIVE_REPRESENTATION T1 NO_SEARCH PASS_BOTH_SELECTION_YEARS_TOP1_FLOOR_MINUS_0.005")
print("D76_RANKS",ranks)
for yr in [2022,2023,2024]:
 tr=x.year_eval<yr;te=x.year_eval.eq(yr)
 for name,F in [("PREP48",promoted),("PLUS_RANK17",promoted+ranks)]:
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42));m.fit(x.loc[tr,F],x.loc[tr,"y"]);sc=m.decision_function(x.loc[te,F])
  z=x.loc[te,["_race","y"]].copy();z["s"]=sc;z["p"]=z.groupby("_race").s.transform(lambda a:np.exp(a-a.max())/np.exp(a-a.max()).sum());z["rank"]=z.groupby("_race").s.rank(ascending=False,method="first");w=z[z.y.eq(1)]
  print("D76_RESULT",yr,name,"RACES",len(w),"TOP1",float((w["rank"]==1).mean()),"TOP2",float((w["rank"]<=2).mean()),"TOP3",float((w["rank"]<=3).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w.p.clip(1e-12,1)).mean()))
print("D76_COMPLETE 2025_2026_SEALED")
