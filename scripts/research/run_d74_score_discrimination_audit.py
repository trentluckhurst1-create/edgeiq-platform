from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv";B=R/"outputs"/"research"/"profitability_program"/"lab245b"/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
d=pd.read_csv(D);b=pd.read_csv(B);x=d.merge(b[["_race","_horse","last_distance","last_finish","last_won","last_top3"]],on=["_race","_horse"],how="left",validate="one_to_one")
x["distance_change"]=x.current_distance-x.last_distance;x["abs_distance_change"]=x.distance_change.abs();prep=["days_since_last","distance_change","abs_distance_change","last_finish","last_won","last_top3"];x["date"]=pd.to_datetime(x.race_date);x["year_eval"]=x.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"};num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])];context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"};F=[c for c in num if c not in context]+prep
print("D74_CONTRACT PREP48_SCORE_DISCRIMINATION_DIAGNOSTIC NO_MODEL_CHANGE NO_CALIBRATION NO_MARKET")
for yr in [2022,2023,2024]:
 tr=x.year_eval<yr;te=x.year_eval.eq(yr);m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42));m.fit(x.loc[tr,F],x.loc[tr,"y"]);s=m.decision_function(x.loc[te,F]);z=x.loc[te,["_race","y"]].copy();z["s"]=s
 g=z.groupby("_race").s;z["range"]=g.transform("max")-g.transform("min");z["sd"]=g.transform("std");z["topgap"]=g.transform(lambda a:a.nlargest(2).iloc[0]-a.nlargest(2).iloc[1] if len(a)>=2 else np.nan);z["p"]=g.transform(lambda a:np.exp(a-a.max())/np.exp(a-a.max()).sum());w=z[z.y.eq(1)]
 print("D74_YEAR",yr,"RACES",len(w),"SCORE_RANGE_MED",float(w.range.median()),"SCORE_SD_MED",float(w.sd.median()),"TOPGAP_MED",float(w.topgap.median()),"WINNER_SCORE_Q",np.quantile(w.s,[.1,.25,.5,.75,.9]).tolist(),"WINNER_P_Q",np.quantile(w.p,[.1,.25,.5,.75,.9]).tolist(),"MAXP_RACE_Q",np.quantile(z.groupby("_race").p.max(),[.1,.25,.5,.75,.9]).tolist())
print("D74_COMPLETE 2025_2026_SEALED")
