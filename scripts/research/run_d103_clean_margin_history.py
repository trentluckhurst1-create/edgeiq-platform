from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM");D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv";B=R/"outputs"/"research"/"profitability_program"/"lab245b"/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv";P=ROOT/"outputs"/"research"/"model_lab_026"/"edgeiq_certified_flat_walk_forward_epi_026.csv"
d=pd.read_csv(D);b=pd.read_csv(B);z=d.merge(b[["_race","_horse","last_distance","last_finish","last_won","last_top3"]],on=["_race","_horse"],how="left",validate="one_to_one");z["date"]=pd.to_datetime(z.race_date);z["year_eval"]=z.date.dt.year
# D99 clean placing history
h=pd.read_csv(P,usecols=["canonical_horse_id","race_date","finish_position","finish_margin"],low_memory=False);h["date"]=pd.to_datetime(h.race_date);h["pos"]=pd.to_numeric(h.finish_position,errors="coerce");h["margin"]=pd.to_numeric(h.finish_margin,errors="coerce");h=h[h.pos.between(1,99)].dropna(subset=["canonical_horse_id","date"]).sort_values(["canonical_horse_id","date"])
g=h.groupby("canonical_horse_id",group_keys=False)
h["finishpos_mean5_clean"]=g.pos.transform(lambda s:s.rolling(5,min_periods=1).mean());h["last_finish_clean"]=h.pos;h["last_won_clean"]=(h.pos==1).astype(float);h["last_top3_clean"]=(h.pos<=3).astype(float)
h["margin_mean5_clean"]=g.margin.transform(lambda s:s.rolling(5,min_periods=1).mean());h["margin_std5_clean"]=g.margin.transform(lambda s:s.rolling(5,min_periods=2).std());h["margin_worst5_clean"]=g.margin.transform(lambda s:s.rolling(5,min_periods=1).max())
h=h.drop_duplicates(["canonical_horse_id","date"],keep="last")
parts=[]
cols=["finishpos_mean5_clean","last_finish_clean","last_won_clean","last_top3_clean","margin_mean5_clean","margin_std5_clean","margin_worst5_clean"]
for horse,a in z.groupby("_horse",sort=False):
 a=a.sort_values("date");hh=h[h.canonical_horse_id.eq(horse)]
 if hh.empty:
  q=a[["_race","_horse"]].copy()
  for c in cols:q[c]=np.nan
 else:q=pd.merge_asof(a,hh[["date"]+cols],on="date",direction="backward",allow_exact_matches=False)[["_race","_horse"]+cols]
 parts.append(q)
z=z.merge(pd.concat(parts),on=["_race","_horse"],how="left",validate="one_to_one");z["distance_change"]=z.current_distance-z.last_distance;z["abs_distance_change"]=z.distance_change.abs();z["finishpos_mean5_clean_rel"]=z.finishpos_mean5_clean-z.groupby("_race").finishpos_mean5_clean.transform("median")
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"};num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])];ctx={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"};base=[c for c in num if c not in ctx];raw=["days_since_last","distance_change","abs_distance_change","last_finish","last_won","last_top3"];F0=list(dict.fromkeys(base+raw));F99=[c for c in F0 if c not in ["finishpos_mean5","finishpos_mean5_rel","last_finish","last_won","last_top3"]]+["finishpos_mean5_clean","finishpos_mean5_clean_rel","last_finish_clean","last_won_clean","last_top3_clean"];F103=[c for c in F99 if c not in ["margin_mean5","margin_std5","margin_worst5"]]+["margin_mean5_clean","margin_std5_clean","margin_worst5_clean"]
print("D103_CONTRACT D99_PLUS_VALID_FINISH_MARGIN_HISTORY SAME_L5_T1 NO_SEARCH PASS_BOTH_SELECTION_YEARS_TOP1_FLOOR_MINUS_0.005")
for yr in [2022,2023,2024]:
 tr=z.year_eval<yr;te=z.year_eval.eq(yr)
 for name,ff in [("D99_CLEAN_PLACE",F99),("D103_CLEAN_MARGIN",F103)]:
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42));m.fit(z.loc[tr,ff],z.loc[tr,"y"]);s=m.decision_function(z.loc[te,ff]);q=z.loc[te,["_race","y"]].copy();q["s"]=s;q["p"]=q.groupby("_race").s.transform(lambda a:np.exp(a-a.max())/np.exp(a-a.max()).sum());q["rank"]=q.groupby("_race").s.rank(ascending=False,method="first");w=q[q.y.eq(1)]
  print("D103_RESULT",yr,name,"TOP1",float((w["rank"]==1).mean()),"TOP2",float((w["rank"]<=2).mean()),"TOP3",float((w["rank"]<=3).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w.p.clip(1e-12,1)).mean()))
print("D103_COMPLETE 2025_2026_SEALED")
