from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM");D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv";B=R/"outputs"/"research"/"profitability_program"/"lab245b"/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv";P=ROOT/"outputs"/"research"/"model_lab_026"/"edgeiq_certified_flat_walk_forward_epi_026.csv"
d=pd.read_csv(D);b=pd.read_csv(B);z=d.merge(b[["_race","_horse","last_distance","last_finish","last_won","last_top3"]],on=["_race","_horse"],how="left",validate="one_to_one");z["date"]=pd.to_datetime(z.race_date);z["year_eval"]=z.date.dt.year
h=pd.read_csv(P,usecols=["canonical_horse_id","race_date","finish_position"],low_memory=False);h["date"]=pd.to_datetime(h.race_date);h["pos"]=pd.to_numeric(h.finish_position,errors="coerce");h=h[h.pos.between(1,99)].dropna(subset=["canonical_horse_id","date"]).sort_values(["canonical_horse_id","date"]);h["finishpos_mean5_clean"]=h.groupby("canonical_horse_id").pos.transform(lambda s:s.rolling(5,min_periods=1).mean());h["last_finish_clean"]=h.pos;h["last_won_clean"]=(h.pos==1).astype(float);h["last_top3_clean"]=(h.pos<=3).astype(float);h=h.drop_duplicates(["canonical_horse_id","date"],keep="last")
parts=[]
for horse,g in z.groupby("_horse",sort=False):
 hh=h[h.canonical_horse_id.eq(horse)]
 if hh.empty:
  q=g[["_race","_horse"]].copy()
  for c in ["finishpos_mean5_clean","finishpos_mean5_clean_rel","last_finish_clean","last_won_clean","last_top3_clean"]:q[c]=np.nan
 else:
  a=g.sort_values("date");q=pd.merge_asof(a,hh[["date","finishpos_mean5_clean","last_finish_clean","last_won_clean","last_top3_clean"]],on="date",direction="backward",allow_exact_matches=False)[["_race","_horse","finishpos_mean5_clean","last_finish_clean","last_won_clean","last_top3_clean"]]
 parts.append(q)
cl=pd.concat(parts);z=z.merge(cl,on=["_race","_horse"],how="left",validate="one_to_one");z["distance_change"]=z.current_distance-z.last_distance;z["abs_distance_change"]=z.distance_change.abs()

# Explicit 109 is governed scratching/non-start: rebuild last actual-start date/distance excluding only 109.
hs=pd.read_csv(P,usecols=["canonical_horse_id","race_date","finish_position","distance_metres"],low_memory=False);hs["date"]=pd.to_datetime(hs.race_date);hs["pos"]=pd.to_numeric(hs.finish_position,errors="coerce");hs["dist"]=pd.to_numeric(hs.distance_metres,errors="coerce");hs=hs[~hs.pos.eq(109)].dropna(subset=["canonical_horse_id","date"]).sort_values(["canonical_horse_id","date"]).drop_duplicates(["canonical_horse_id","date"],keep="last")
sp=[]
for horse,g in z.groupby("_horse",sort=False):
 hh=hs[hs.canonical_horse_id.eq(horse)]
 if hh.empty:q=g[["_race","_horse"]].assign(last_distance_clean=np.nan,days_since_last_clean=np.nan)
 else:
  a=g.sort_values("date");q=pd.merge_asof(a,hh[["date","dist"]],on="date",direction="backward",allow_exact_matches=False);q["last_distance_clean"]=q["dist"];q["days_since_last_clean"]=(q["date"]-pd.to_datetime(q["date"].where(q["dist"].notna()))).dt.days
  # merge_asof loses prior-date identity above; compute prior date separately
  hp=hh[["date","dist"]].rename(columns={"date":"prior_date"});aa=a.copy();aa["lookup_date"]=aa["date"];q2=pd.merge_asof(aa.sort_values("lookup_date"),hp.sort_values("prior_date"),left_on="lookup_date",right_on="prior_date",direction="backward",allow_exact_matches=False);q=q2[["_race","_horse"]].copy();q["last_distance_clean"]=q2["dist"];q["days_since_last_clean"]=(q2["lookup_date"]-q2["prior_date"]).dt.days
 sp.append(q)
ss=pd.concat(sp);z=z.merge(ss,on=["_race","_horse"],how="left",validate="one_to_one");z["distance_change_clean"]=z.current_distance-z.last_distance_clean;z["abs_distance_change_clean"]=z.distance_change_clean.abs()
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"};num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])];ctx={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"};base=[c for c in num if c not in ctx];rawprep=["days_since_last","distance_change","abs_distance_change","last_finish","last_won","last_top3"];Fraw=list(dict.fromkeys(base+rawprep));z["finishpos_mean5_clean_rel"]=z["finishpos_mean5_clean"]-z.groupby("_race")["finishpos_mean5_clean"].transform("median");Fclean=[c for c in Fraw if c not in ["finishpos_mean5","finishpos_mean5_rel","last_finish","last_won","last_top3","days_since_last","distance_change","abs_distance_change"]]+["finishpos_mean5_clean","finishpos_mean5_clean_rel","last_finish_clean","last_won_clean","last_top3_clean","days_since_last_clean","distance_change_clean","abs_distance_change_clean"]
print("D101_CONTRACT STATUS_CODE_SAFE_PLACING_FEATURE_REPAIR STRICT_DATE NO_STATUS_LABEL_INFERENCE SAME_L5_T1")
print("D101_COVERAGE",{c:float(z[c].notna().mean()) for c in ["finishpos_mean5_clean","last_finish_clean","last_won_clean","last_top3_clean"]})
for yr in [2022,2023,2024]:
 tr=z.year_eval<yr;te=z.year_eval.eq(yr)
 for name,F in [("PREP47_RAW",Fraw),("CLEAN_PLACE_PLUS_ACTUAL_START",Fclean)]:
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42));m.fit(z.loc[tr,F],z.loc[tr,"y"]);s=m.decision_function(z.loc[te,F]);q=z.loc[te,["_race","y"]].copy();q["s"]=s;q["p"]=q.groupby("_race").s.transform(lambda a:np.exp(a-a.max())/np.exp(a-a.max()).sum());q["rank"]=q.groupby("_race").s.rank(ascending=False,method="first");w=q[q.y.eq(1)]
  print("D101_RESULT",yr,name,"TOP1",float((w["rank"]==1).mean()),"TOP2",float((w["rank"]<=2).mean()),"TOP3",float((w["rank"]<=3).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w.p.clip(1e-12,1)).mean()))
print("D101_COMPLETE 2025_2026_SEALED")
