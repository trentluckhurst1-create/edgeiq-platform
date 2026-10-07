from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
D=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\d45\D45_FROZEN_PIT_FEATURE_MATRIX.csv");B=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv")
d=pd.read_csv(D);b=pd.read_csv(B);z=d.merge(b[["_race","_horse","last_distance","last_finish","last_won","last_top3"]],on=["_race","_horse"],how="left",validate="one_to_one");z["distance_change"]=z.current_distance-z.last_distance;z["abs_distance_change"]=z.distance_change.abs();prep=["days_since_last","distance_change","abs_distance_change","last_finish","last_won","last_top3"];z["date"]=pd.to_datetime(z.race_date);z["year_eval"]=z.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"};num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])];context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"};base=[c for c in num if c not in context];F=base+prep
print("D91_CONTRACT PREP48_PREDECLARED_FAMILY_ABLATION NO_SINGLE_FEATURE_MINING SAME_L5_T1")
print("D91_FEATURES",F)
families={
"FORM_LVS":[c for c in F if c.startswith("lvs_") or c.startswith("dist200_lvs")],
"MARGIN_FINISH":[c for c in F if c.startswith("margin_") or c.startswith("finishpos_") or c in ["last_finish","last_won","last_top3"]],
"DEPTH_RECENCY":[c for c in F if c in ["hist_runs","days_since_last","dist200_runs","distance_change","abs_distance_change"]],
"CONNECTIONS":[c for c in F if c.startswith("jockey_") or c.startswith("trainer_")],
"BARRIER":[c for c in F if "barrier" in c.lower()],
"RACE_CONTEXT":[c for c in F if c in ["current_distance","field_size","current_class_level","today_class_level"] or "class" in c.lower()],
}
print("D91_FAMILIES",families)
for yr in [2022,2023,2024]:
 tr=z.year_eval<yr;te=z.year_eval.eq(yr)
 specs=[("PREP48",F)]+[("DROP_"+k,[c for c in F if c not in v]) for k,v in families.items() if v]
 for name,ff in specs:
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42));m.fit(z.loc[tr,ff],z.loc[tr,"y"]);s=m.decision_function(z.loc[te,ff]);q=z.loc[te,["_race","y"]].copy();q["s"]=s;q["p"]=q.groupby("_race").s.transform(lambda a:np.exp(a-a.max())/np.exp(a-a.max()).sum());q["rank"]=q.groupby("_race").s.rank(ascending=False,method="first");w=q[q.y.eq(1)]
  print("D91_RESULT",yr,name,"NF",len(ff),"TOP1",float((w["rank"]==1).mean()),"TOP2",float((w["rank"]<=2).mean()),"TOP3",float((w["rank"]<=3).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w.p.clip(1e-12,1)).mean()))
print("D91_COMPLETE 2025_2026_SEALED")
