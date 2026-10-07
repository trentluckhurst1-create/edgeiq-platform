from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM");R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv"
B=R/"outputs"/"research"/"profitability_program"/"lab245b"/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
P=ROOT/"outputs"/"research"/"model_lab_026"/"edgeiq_certified_flat_walk_forward_epi_026.csv"
d=pd.read_csv(D);b=pd.read_csv(B)
x=d.merge(b[["_race","_horse","last_distance","last_finish","last_won","last_top3"]],on=["_race","_horse"],how="left",validate="one_to_one")
x["distance_change"]=x["current_distance"]-x["last_distance"];x["abs_distance_change"]=x["distance_change"].abs()
prep=["days_since_last","distance_change","abs_distance_change","last_finish","last_won","last_top3"]
x["date"]=pd.to_datetime(x.race_date);x["year_eval"]=x.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"}
num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])]
context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"}
base=[c for c in num if c not in context];promoted=base+prep
h=pd.read_csv(P,usecols=["canonical_race_id","canonical_horse_id","race_date","weight_carried"],low_memory=False)
h["date"]=pd.to_datetime(h.race_date,errors="coerce")
raw=h["weight_carried"].astype("string")
h["weight_num"]=pd.to_numeric(raw.str.extract(r"([-+]?[0-9]*\.?[0-9]+)",expand=False),errors="coerce")
print("D69_WEIGHT_PARSE","RAW_NON_NULL",float(h.weight_carried.notna().mean()),"PARSED",float(h.weight_num.notna().mean()),"RAW_SAMPLE",raw.dropna().head(10).tolist(),"PARSED_SAMPLE",h.weight_num.dropna().head(10).tolist())
cur=h.sort_values("date").drop_duplicates(["canonical_race_id","canonical_horse_id"],keep="last")[["canonical_race_id","canonical_horse_id","weight_num"]].rename(columns={"canonical_race_id":"_race","canonical_horse_id":"_horse","weight_num":"today_weight"})
x=x.merge(cur,on=["_race","_horse"],how="left",validate="one_to_one")
hist=h.dropna(subset=["canonical_horse_id","date","weight_num"]).copy();hist["_horse_s"]=hist.canonical_horse_id.astype(str);x["_horse_s"]=x._horse.astype(str)
parts=[]
for k,g in x.reset_index().rename(columns={"index":"_i"}).groupby("_horse_s",sort=False):
 r=hist[hist._horse_s.eq(k)][["date","weight_num"]].sort_values("date")
 if r.empty:q=g[["_i"]].assign(last_weight=np.nan)
 else:q=pd.merge_asof(g.sort_values("date"),r,on="date",direction="backward",allow_exact_matches=False)[["_i","weight_num"]].rename(columns={"weight_num":"last_weight"})
 parts.append(q)
q=pd.concat(parts).set_index("_i").sort_index();x["last_weight"]=q.last_weight
x["weight_rel_median"]=x.today_weight-x.groupby("_race").today_weight.transform("median")
x["weight_change"]=x.today_weight-x.last_weight
x["weight_rank_pct"]=x.groupby("_race").today_weight.rank(pct=True,method="average")
new=["weight_rel_median","weight_change","weight_rank_pct"]
print("D69_CONTRACT PREP48_PLUS_WEIGHT3 PARSER_REPAIR T1 NO_SEARCH PASS_BOTH_SELECTION_YEARS_TOP1_FLOOR_MINUS_0.005")
print("D69_COVERAGE",{c:float(x[c].notna().mean()) for c in ["today_weight","last_weight"]+new})
for yr in [2022,2023,2024]:
 tr=x.year_eval<yr;te=x.year_eval.eq(yr)
 for name,F in [("PREP48",promoted),("PLUS_WEIGHT3",promoted+new)]:
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42))
  m.fit(x.loc[tr,F],x.loc[tr,"y"]);sc=m.decision_function(x.loc[te,F])
  z=x.loc[te,["_race","y"]].copy();z["s"]=sc;z["p"]=z.groupby("_race").s.transform(lambda a:np.exp(a-a.max())/np.exp(a-a.max()).sum());z["rank"]=z.groupby("_race").s.rank(ascending=False,method="first");w=z[z.y.eq(1)]
  print("D69_RESULT",yr,name,"RACES",len(w),"TOP1",float((w["rank"]==1).mean()),"TOP2",float((w["rank"]<=2).mean()),"TOP3",float((w["rank"]<=3).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w.p.clip(1e-12,1)).mean()))
print("D69_COMPLETE 2025_2026_SEALED")
