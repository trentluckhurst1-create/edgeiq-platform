from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM");R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
M=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv";P=ROOT/"outputs"/"research"/"model_lab_026"/"edgeiq_certified_flat_walk_forward_epi_026.csv"
b=pd.read_csv(M);b["date"]=pd.to_datetime(b.race_date);b["eval_year"]=b.date.dt.year;b["_horse_s"]=b._horse.astype(str)
h=pd.read_csv(P,usecols=["canonical_horse_id","race_date","weight_carried"]);h["date"]=pd.to_datetime(h.race_date);h["_horse_s"]=h.canonical_horse_id.astype(str);h["weight_carried"]=pd.to_numeric(h.weight_carried,errors="coerce")
# exact horse-date, only unique candidate dates
u=h.groupby(["_horse_s","date"]).agg(today_weight=("weight_carried","first"),n=("weight_carried","size")).reset_index();u.loc[u.n.ne(1),"today_weight"]=np.nan
b=b.merge(u[["_horse_s","date","today_weight"]],on=["_horse_s","date"],how="left")
# prior weight strictly date<today using asof per horse
hist=h.dropna(subset=["weight_carried"]).sort_values(["_horse_s","date"])
parts=[]
for k,g in b.reset_index().rename(columns={"index":"_i"}).groupby("_horse_s",sort=False):
 r=hist[hist._horse_s.eq(k)][["date","weight_carried"]].sort_values("date")
 if r.empty:q=g[["_i"]].assign(last_weight=np.nan)
 else:q=pd.merge_asof(g.sort_values("date"),r,on="date",direction="backward",allow_exact_matches=False)[["_i","weight_carried"]].rename(columns={"weight_carried":"last_weight"})
 parts.append(q)
q=pd.concat(parts).set_index("_i");b["last_weight"]=q.last_weight
b["weight_change"]=b.today_weight-b.last_weight;b["weight_rel_median"]=b.today_weight-b.groupby("_race").today_weight.transform("median");b["weight_rank_pct"]=b.groupby("_race").today_weight.rank(pct=True,method="average")
NEW=["weight_change","weight_rel_median","weight_rank_pct"];print("D55_WEIGHT_COVERAGE",{x:float(b[x].notna().mean()) for x in ["today_weight","last_weight"]+NEW})
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","eval_year"}
num=[c for c in pd.read_csv(M,nrows=20) if c not in meta];num=[c for c in num if c in b and pd.api.types.is_numeric_dtype(b[c])]
context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"};BASE=[c for c in num if c not in context]
for yr in [2022,2023,2024]:
 for fam,F in [("BASE",BASE),("WEIGHT",BASE+NEW)]:
  tr=b.eval_year<yr;te=b.eval_year.eq(yr);m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42));m.fit(b.loc[tr,F],b.loc[tr,"y"]);z=m.decision_function(b.loc[te,F]);qq=b.loc[te,["_race","y"]].copy();qq["z"]=z;qq["p"]=qq.groupby("_race").z.transform(lambda x:np.exp((x-x.max())/.85)/np.exp((x-x.max())/.85).sum());qq["rank"]=qq.groupby("_race").z.rank(ascending=False,method="first");w=qq[qq.y.eq(1)]
  print("RESULT",yr,fam,"TOP1",float((w["rank"]<=1).mean()),"TOP2",float((w["rank"]<=2).mean()),"TOP3",float((w["rank"]<=3).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w.p.clip(1e-12,1)).mean()))
print("D55_WEIGHT_COMPLETE")
