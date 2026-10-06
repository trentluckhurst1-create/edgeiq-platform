from pathlib import Path
import re
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv"
B=R/"outputs"/"research"/"profitability_program"/"lab245b"/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
P=ROOT/"outputs"/"research"/"model_lab_026"/"edgeiq_certified_flat_walk_forward_epi_026.csv"
d=pd.read_csv(D);b=pd.read_csv(B)
prep0=["last_distance","last_finish","last_won","last_top3"]
x=d.merge(b[["_race","_horse"]+prep0],on=["_race","_horse"],how="left",validate="one_to_one")
x["distance_change"]=x["current_distance"]-x["last_distance"];x["abs_distance_change"]=x["distance_change"].abs()
prep=["days_since_last","distance_change","abs_distance_change","last_finish","last_won","last_top3"]
x["date"]=pd.to_datetime(x.race_date);x["year_eval"]=x.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"}
num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])]
context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"}
base=[c for c in num if c not in context];promoted=base+prep
h=pd.read_csv(P,usecols=["canonical_race_id","canonical_horse_id","race_date","race_class","race_class_group","weight_carried"],low_memory=False)
h["date"]=pd.to_datetime(h.race_date,errors="coerce");h["weight_carried"]=pd.to_numeric(h.weight_carried,errors="coerce")
def clevel(a,b):
 s=str(a if pd.notna(a) else b).upper()
 if "GROUP 1" in s or re.search(r"\bG1\b",s):return 10.0
 if "GROUP 2" in s or re.search(r"\bG2\b",s):return 9.0
 if "GROUP 3" in s or re.search(r"\bG3\b",s):return 8.0
 if "LISTED" in s:return 7.0
 m=re.search(r"(?:BM|BENCHMARK)\s*([0-9]{2,3})",s)
 if m:return float(m.group(1))/10.0
 if "OPEN" in s:return 6.0
 if "MAIDEN" in s:return 1.0
 return np.nan
h["class_level"]= [clevel(a,b) for a,b in zip(h.race_class,h.race_class_group)]
# Exact target horse/race current attributes; these are pre-race race conditions, not outcomes.
cur=h.sort_values("date").drop_duplicates(["canonical_race_id","canonical_horse_id"],keep="last")[["canonical_race_id","canonical_horse_id","weight_carried","class_level"]].rename(columns={"canonical_race_id":"_race","canonical_horse_id":"_horse","weight_carried":"today_weight","class_level":"today_class_level"})
x=x.merge(cur,on=["_race","_horse"],how="left",validate="one_to_one")
# Prior weight/class strictly date < target date, preventing same-day leakage.
hist=h.dropna(subset=["canonical_horse_id","date"]).copy();hist["_horse_s"]=hist.canonical_horse_id.astype(str);x["_horse_s"]=x._horse.astype(str)
parts=[]
for k,g in x.reset_index().rename(columns={"index":"_i"}).groupby("_horse_s",sort=False):
 r=hist[hist._horse_s.eq(k)][["date","weight_carried","class_level"]].sort_values("date")
 if r.empty:q=g[["_i"]].assign(last_weight=np.nan,last_class_level=np.nan)
 else:q=pd.merge_asof(g.sort_values("date"),r,on="date",direction="backward",allow_exact_matches=False)[["_i","weight_carried","class_level"]].rename(columns={"weight_carried":"last_weight","class_level":"last_class_level"})
 parts.append(q)
q=pd.concat(parts).set_index("_i").sort_index();x["last_weight"]=q.last_weight;x["last_class_level"]=q.last_class_level
x["weight_rel_median"]=x.today_weight-x.groupby("_race").today_weight.transform("median")
x["weight_change"]=x.today_weight-x.last_weight
x["class_step"]=x.today_class_level-x.last_class_level
new=["weight_rel_median","weight_change","today_class_level","class_step"]
print("D68_CONTRACT PREP48_PLUS_CURRENT_CLASS_WEIGHT4 T1 NO_SEARCH PASS_BOTH_SELECTION_YEARS_TOP1_FLOOR_MINUS_0.005")
print("D68_COVERAGE",{c:float(x[c].notna().mean()) for c in ["today_weight","last_weight","today_class_level","last_class_level"]+new})
for yr in [2022,2023,2024]:
 tr=x.year_eval<yr;te=x.year_eval.eq(yr)
 for name,F in [("PREP48",promoted),("PLUS_CW4",promoted+new)]:
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42))
  m.fit(x.loc[tr,F],x.loc[tr,"y"]);sc=m.decision_function(x.loc[te,F])
  z=x.loc[te,["_race","y"]].copy();z["s"]=sc;z["p"]=z.groupby("_race").s.transform(lambda a:np.exp(a-a.max())/np.exp(a-a.max()).sum());z["rank"]=z.groupby("_race").s.rank(ascending=False,method="first");w=z[z.y.eq(1)]
  print("D68_RESULT",yr,name,"RACES",len(w),"TOP1",float((w["rank"]==1).mean()),"TOP2",float((w["rank"]<=2).mean()),"TOP3",float((w["rank"]<=3).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w.p.clip(1e-12,1)).mean()))
print("D68_COMPLETE 2025_2026_SEALED")
