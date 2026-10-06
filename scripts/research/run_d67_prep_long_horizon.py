from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
D=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\d45\D45_FROZEN_PIT_FEATURE_MATRIX.csv")
B=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv")
S=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_WAREHOUSE_RUNNER_LVS.csv")
d=pd.read_csv(D); b=pd.read_csv(B)
prep0=["last_distance","last_finish","last_won","last_top3"]
x=d.merge(b[["_race","_horse"]+prep0],on=["_race","_horse"],how="left",validate="one_to_one")
x["distance_change"]=x["current_distance"]-x["last_distance"];x["abs_distance_change"]=x["distance_change"].abs()
prep=["days_since_last","distance_change","abs_distance_change","last_finish","last_won","last_top3"]
x["date"]=pd.to_datetime(x.race_date);x["year_eval"]=x.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"}
num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])]
context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"}
base=[c for c in num if c not in context]; promoted=base+prep
# Strict-date long-horizon LVS summaries from the same governed historical warehouse used previously.
s=pd.read_csv(S,usecols=["canonical_race_id","canonical_horse_id","race_date","runner_lvs"],low_memory=False)
s["race_date"]=pd.to_datetime(s.race_date,errors="coerce");s["runner_lvs"]=pd.to_numeric(s.runner_lvs,errors="coerce")
s=s.dropna(subset=["canonical_race_id","canonical_horse_id","race_date"]).sort_values(["canonical_horse_id","race_date","canonical_race_id"],kind="stable")
targets=set(zip(x["_race"].astype(str),x["_horse"].astype(str))); out={}
for horse,g in s.groupby("canonical_horse_id",sort=False):
 horse=str(horse); hist=[]
 for dt,day in g.groupby("race_date",sort=True):
  v=np.asarray(hist[-10:],float)
  for r in day.itertuples(index=False):
   key=(str(r.canonical_race_id),horse)
   if key in targets:
    out[key]={"lh_mean10":float(np.mean(v)) if len(v) else np.nan,
              "lh_median10":float(np.median(v)) if len(v) else np.nan,
              "lh_best10":float(np.max(v)) if len(v) else np.nan,
              "lh_std10":float(np.std(v)) if len(v)>=2 else np.nan,
              "lh_slope10":float(np.polyfit(np.arange(len(v)),v,1)[0]) if len(v)>=2 else np.nan}
  hist.extend([float(vv) for vv in pd.to_numeric(day.runner_lvs,errors="coerce").dropna()])
e=pd.DataFrame.from_dict(out,orient="index");e.index=pd.MultiIndex.from_tuples(e.index,names=["_race","_horse"]);e=e.reset_index()
x["_race"]=x["_race"].astype(str);x["_horse"]=x["_horse"].astype(str);x=x.merge(e,on=["_race","_horse"],how="left",validate="one_to_one")
lh=["lh_mean10","lh_median10","lh_best10","lh_std10","lh_slope10"]
print("D67_CONTRACT PREP48_PLUS_LONG_HORIZON5 NO_SEARCH PASS_BOTH_SELECTION_YEARS_TOP1_FLOOR_MINUS_0.005")
print("D67_COVERAGE",{c:float(x[c].notna().mean()) for c in lh})
for yr in [2022,2023,2024]:
 tr=x.year_eval<yr;te=x.year_eval.eq(yr)
 for name,F in [("PREP48",promoted),("PLUS_LH5",promoted+lh)]:
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42))
  m.fit(x.loc[tr,F],x.loc[tr,"y"]);sc=m.decision_function(x.loc[te,F])
  q=x.loc[te,["_race","y"]].copy();q["s"]=sc;q["p"]=q.groupby("_race").s.transform(lambda z:np.exp(z-z.max())/np.exp(z-z.max()).sum());q["rank"]=q.groupby("_race").s.rank(ascending=False,method="first");w=q[q.y.eq(1)]
  print("D67_RESULT",yr,name,"RACES",len(w),"TOP1",float((w["rank"]==1).mean()),"TOP2",float((w["rank"]<=2).mean()),"TOP3",float((w["rank"]<=3).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w.p.clip(1e-12,1)).mean()))
print("D67_COMPLETE 2025_2026_SEALED")
