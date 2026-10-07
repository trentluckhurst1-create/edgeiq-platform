from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
D=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\d45\D45_FROZEN_PIT_FEATURE_MATRIX.csv");B=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv")
d=pd.read_csv(D);b=pd.read_csv(B);z=d.merge(b[["_race","_horse","last_distance","last_finish","last_won","last_top3"]],on=["_race","_horse"],how="left",validate="one_to_one");z["distance_change"]=z.current_distance-z.last_distance;z["abs_distance_change"]=z.distance_change.abs();prep=["days_since_last","distance_change","abs_distance_change","last_finish","last_won","last_top3"];z["date"]=pd.to_datetime(z.race_date);z["year_eval"]=z.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"};num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])];context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"};F=[c for c in num if c not in context]+prep
print("D92_CONTRACT PREP48_EQUAL_RACE_MASS_HGB SAME_ARCHITECTURE_T1 NO_SEARCH")
for yr in [2022,2023,2024]:
 tr=z.year_eval<yr;te=z.year_eval.eq(yr);fs=z.loc[tr].groupby("_race")["_horse"].transform("size");w=1.0/fs
 for name,sw in [("PREP48",None),("EQUAL_RACE_MASS",w)]:
  imp=SimpleImputer(strategy="median");X=imp.fit_transform(z.loc[tr,F]);Xt=imp.transform(z.loc[te,F]);m=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42);m.fit(X,z.loc[tr,"y"],sample_weight=sw);s=m.decision_function(Xt);q=z.loc[te,["_race","y"]].copy();q["s"]=s;q["p"]=q.groupby("_race").s.transform(lambda a:np.exp(a-a.max())/np.exp(a-a.max()).sum());q["rank"]=q.groupby("_race").s.rank(ascending=False,method="first");ww=q[q.y.eq(1)]
  print("D92_RESULT",yr,name,"RACES",len(ww),"TOP1",float((ww["rank"]==1).mean()),"TOP2",float((ww["rank"]<=2).mean()),"TOP3",float((ww["rank"]<=3).mean()),"MRR",float((1/ww["rank"]).mean()),"LL",float(-np.log(ww.p.clip(1e-12,1)).mean()))
print("D92_COMPLETE 2025_2026_SEALED")
