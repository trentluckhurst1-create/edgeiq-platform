from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
RROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
M=RROOT/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv"
P=ROOT/"outputs"/"research"/"model_lab_026"/"edgeiq_certified_flat_walk_forward_epi_026.csv"
b=pd.read_csv(M);b["date"]=pd.to_datetime(b.race_date);b["eval_year"]=b.date.dt.year
h=pd.read_csv(P,usecols=["canonical_race_id","canonical_horse_id","race_date","race_class","race_class_group","weight_carried","finish_position"])
h["date"]=pd.to_datetime(h.race_date);h=h.sort_values(["canonical_horse_id","date"])
h["weight_carried"]=pd.to_numeric(h.weight_carried,errors="coerce")
# current exact-race attributes
cur=h.sort_values("date").drop_duplicates(["canonical_race_id","canonical_horse_id"],keep="last")[["canonical_race_id","canonical_horse_id","weight_carried","race_class","race_class_group"]]
cur=cur.rename(columns={"canonical_race_id":"_race","canonical_horse_id":"_horse","weight_carried":"today_weight","race_class":"today_class","race_class_group":"today_class_group"})
b=b.merge(cur,on=["_race","_horse"],how="left")
b["weight_rel_median"]=b.today_weight-b.groupby("_race").today_weight.transform("median")
b["weight_rank_pct"]=b.groupby("_race").today_weight.rank(pct=True,method="average")
# strict prior horse history via shift
hh=h.copy();g=hh.groupby("canonical_horse_id",sort=False)
hh["last_weight"]=g.weight_carried.shift(1);hh["last_class"]=g.race_class.shift(1);hh["last_class_group"]=g.race_class_group.shift(1)
# class labels are categorical; derive strictly historical frequency/target-free ordinal proxy from normalized text patterns only
def class_level(x):
 s=str(x).upper()
 import re
 if "GROUP 1" in s or "G1" in s:return 10
 if "GROUP 2" in s or "G2" in s:return 9
 if "GROUP 3" in s or "G3" in s:return 8
 if "LISTED" in s:return 7
 m=re.search(r"(?:BM|BENCHMARK)\s*([0-9]{2,3})",s)
 if m:return float(m.group(1))/10
 if "OPEN" in s:return 6
 if "MAIDEN" in s:return 1
 return np.nan
hh["class_level"]=hh.race_class.fillna(hh.race_class_group).map(class_level);hh["last_class_level"]=g.class_level.shift(1)
hh["prev2_class_level"]=g.class_level.shift(2);hh["prev3_class_level"]=g.class_level.shift(3)
prior=hh[["canonical_race_id","canonical_horse_id","last_weight","last_class_level","prev2_class_level","prev3_class_level"]].rename(columns={"canonical_race_id":"_race","canonical_horse_id":"_horse"})
b=b.merge(prior,on=["_race","_horse"],how="left")
b["weight_change"]=b.today_weight-b.last_weight
b["today_class_level"]=b.today_class.fillna(b.today_class_group).map(class_level)
b["class_step"]=b.today_class_level-b.last_class_level
b["class_traj3"]=b.last_class_level-b[["prev2_class_level","prev3_class_level"]].mean(axis=1)
NEW=["weight_rel_median","weight_rank_pct","weight_change","today_class_level","class_step","class_traj3"]
for x in NEW:b[x+"_missing"]=b[x].isna().astype(int)
print("D54_COVERAGE", {x:float(b[x].notna().mean()) for x in NEW})
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","eval_year"}
num=[c for c in pd.read_csv(M,nrows=20) if c not in meta]
num=[c for c in num if c in b and pd.api.types.is_numeric_dtype(b[c])]
context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"}
BASE=[c for c in num if c not in context]
for yr in [2022,2023,2024]:
 tr=b.eval_year<yr;te=b.eval_year.eq(yr)
 for fam,F in [("BASE",BASE),("CLASS_WEIGHT",BASE+NEW+[x+"_missing" for x in NEW])]:
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42))
  m.fit(b.loc[tr,F],b.loc[tr,"y"]);z=m.decision_function(b.loc[te,F]);q=b.loc[te,["_race","y"]].copy();q["z"]=z;q["p"]=q.groupby("_race").z.transform(lambda x:np.exp((x-x.max())/.85)/np.exp((x-x.max())/.85).sum());q["rank"]=q.groupby("_race").z.rank(ascending=False,method="first");w=q[q.y.eq(1)]
  print("RESULT",yr,fam,"TOP1",float((w["rank"]<=1).mean()),"TOP2",float((w["rank"]<=2).mean()),"TOP3",float((w["rank"]<=3).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w.p.clip(1e-12,1)).mean()))
print("D54_CLASS_WEIGHT_COMPLETE")
