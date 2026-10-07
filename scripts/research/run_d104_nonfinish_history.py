from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM");D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv";B=R/"outputs"/"research"/"profitability_program"/"lab245b"/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv";P=ROOT/"outputs"/"research"/"model_lab_026"/"edgeiq_certified_flat_walk_forward_epi_026.csv"
d=pd.read_csv(D);b=pd.read_csv(B);z=d.merge(b[["_race","_horse","last_distance","last_finish","last_won","last_top3"]],on=["_race","_horse"],how="left",validate="one_to_one");z["date"]=pd.to_datetime(z.race_date);z["year_eval"]=z.date.dt.year
h=pd.read_csv(P,usecols=["canonical_horse_id","race_date","finish_position"],low_memory=False);h["date"]=pd.to_datetime(h.race_date);h["pos"]=pd.to_numeric(h.finish_position,errors="coerce");h["nf"]=(~h.pos.between(1,99)).astype(float);h=h.dropna(subset=["canonical_horse_id","date"]).sort_values(["canonical_horse_id","date"])
g=h.groupby("canonical_horse_id",group_keys=False);h["nf_rate5"]=g.nf.transform(lambda s:s.rolling(5,min_periods=1).mean());h["nf_count5"]=g.nf.transform(lambda s:s.rolling(5,min_periods=1).sum());h["last_was_nf"]=h.nf
# D99 clean placing fields on valid finishes, merged onto all-date status frame separately
v=h[h.nf.eq(0)].copy();gv=v.groupby("canonical_horse_id",group_keys=False);v["finishpos_mean5_clean"]=gv.pos.transform(lambda s:s.rolling(5,min_periods=1).mean());v["last_finish_clean"]=v.pos;v["last_won_clean"]=(v.pos==1).astype(float);v["last_top3_clean"]=(v.pos<=3).astype(float);v=v.drop_duplicates(["canonical_horse_id","date"],keep="last")
h=h.drop_duplicates(["canonical_horse_id","date"],keep="last")
parts=[]
for horse,a in z.groupby("_horse",sort=False):
 a=a.sort_values("date");hh=h[h.canonical_horse_id.eq(horse)];vv=v[v.canonical_horse_id.eq(horse)]
 q=a[["_race","_horse","date"]].copy()
 if hh.empty:
  for c in ["nf_rate5","nf_count5","last_was_nf"]:q[c]=np.nan
 else:q=pd.merge_asof(q,hh[["date","nf_rate5","nf_count5","last_was_nf"]],on="date",direction="backward",allow_exact_matches=False)
 if vv.empty:
  for c in ["finishpos_mean5_clean","last_finish_clean","last_won_clean","last_top3_clean"]:q[c]=np.nan
 else:q=pd.merge_asof(q.sort_values("date"),vv[["date","finishpos_mean5_clean","last_finish_clean","last_won_clean","last_top3_clean"]],on="date",direction="backward",allow_exact_matches=False)
 parts.append(q[["_race","_horse","nf_rate5","nf_count5","last_was_nf","finishpos_mean5_clean","last_finish_clean","last_won_clean","last_top3_clean"]])
z=z.merge(pd.concat(parts),on=["_race","_horse"],how="left",validate="one_to_one");z["distance_change"]=z.current_distance-z.last_distance;z["abs_distance_change"]=z.distance_change.abs();z["finishpos_mean5_clean_rel"]=z.finishpos_mean5_clean-z.groupby("_race").finishpos_mean5_clean.transform("median")
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"};num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])];ctx={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"};base=[c for c in num if c not in ctx];raw=["days_since_last","distance_change","abs_distance_change","last_finish","last_won","last_top3"];F0=list(dict.fromkeys(base+raw));F99=[c for c in F0 if c not in ["finishpos_mean5","finishpos_mean5_rel","last_finish","last_won","last_top3"]]+["finishpos_mean5_clean","finishpos_mean5_clean_rel","last_finish_clean","last_won_clean","last_top3_clean"];F104=F99+["nf_rate5","nf_count5","last_was_nf"]
print("D104_CONTRACT D99_PLUS_RECENT_NONFINISH3 STRICT_DATE SAME_L5_T1 NO_SEARCH PASS_BOTH_SELECTION_YEARS_TOP1_FLOOR_MINUS_0.005")
for yr in [2022,2023,2024]:
 tr=z.year_eval<yr;te=z.year_eval.eq(yr)
 for name,ff in [("D99_CLEAN_PLACE",F99),("D104_NONFINISH3",F104)]:
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42));m.fit(z.loc[tr,ff],z.loc[tr,"y"]);s=m.decision_function(z.loc[te,ff]);q=z.loc[te,["_race","y"]].copy();q["s"]=s;q["p"]=q.groupby("_race").s.transform(lambda a:np.exp(a-a.max())/np.exp(a-a.max()).sum());q["rank"]=q.groupby("_race").s.rank(ascending=False,method="first");w=q[q.y.eq(1)]
  print("D104_RESULT",yr,name,"TOP1",float((w["rank"]==1).mean()),"TOP2",float((w["rank"]<=2).mean()),"TOP3",float((w["rank"]<=3).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w.p.clip(1e-12,1)).mean()))
print("D104_COMPLETE 2025_2026_SEALED")
