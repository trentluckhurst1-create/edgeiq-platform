from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM");D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv";B=R/"outputs"/"research"/"profitability_program"/"lab245b"/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv";P=ROOT/"outputs"/"research"/"model_lab_026"/"edgeiq_certified_flat_walk_forward_epi_026.csv";C=ROOT/"outputs"/"research"/"model_lab_031"/"certified_current_race_context_031.csv"
d=pd.read_csv(D);b=pd.read_csv(B);x=d.merge(b[["_race","_horse","last_distance","last_finish","last_won","last_top3"]],on=["_race","_horse"],how="left",validate="one_to_one");x["distance_change"]=x.current_distance-x.last_distance;x["abs_distance_change"]=x.distance_change.abs();prep=["days_since_last","distance_change","abs_distance_change","last_finish","last_won","last_top3"];x["date"]=pd.to_datetime(x.race_date);x["year_eval"]=x.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"};num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])];context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"};F0=[c for c in num if c not in context]+prep
cc=pd.read_csv(C,usecols=["canonical_race_id","canonical_horse_id","current_jockey_id","current_trainer_id"]).rename(columns={"canonical_race_id":"_race","canonical_horse_id":"_horse"}).drop_duplicates(["_race","_horse"]);x=x.merge(cc,on=["_race","_horse"],how="left")
h=pd.read_csv(P,usecols=["race_date","canonical_jockey_id","canonical_trainer_id","canonical_track_id","distance_band","track_condition_group","race_class_group","finish_position"]);h["date"]=pd.to_datetime(h.race_date);fp=pd.to_numeric(h.finish_position,errors="coerce");h=h[fp.notna()].copy();h["win"]=(fp[h.index]==1).astype(int)
rm=pd.read_csv(P,usecols=["canonical_race_id","canonical_track_id","distance_band","track_condition_group","race_class_group"]).drop_duplicates("canonical_race_id").rename(columns={"canonical_race_id":"_race","canonical_track_id":"ctx_track","distance_band":"ctx_dist","track_condition_group":"ctx_cond","race_class_group":"ctx_class"});x=x.merge(rm,on="_race",how="left")
def attach_rate(df,key,current,ctx,curctx,name):
 z=h[[key,ctx,"date","win"]].dropna().copy();z[key]=z[key].astype(str);z[ctx]=z[ctx].astype(str)
 g=z.groupby([key,ctx,"date"]).win.agg(["size","sum"]).reset_index().sort_values([key,ctx,"date"]);g["cs"]=g.groupby([key,ctx])["size"].cumsum();g["cw"]=g.groupby([key,ctx])["sum"].cumsum();g[name]=(g.cw+1)/(g.cs+10)
 left=df.reset_index().rename(columns={"index":"_i"});left[key]=left[current].astype(str);left[ctx]=left[curctx].astype(str);parts=[]
 for kval,a in left.groupby([key,ctx],sort=False):
  r=g[(g[key]==kval[0])&(g[ctx]==kval[1])]
  if r.empty:q=a[["_i"]].assign(**{name:np.nan})
  else:q=pd.merge_asof(a.sort_values("date"),r[["date",name]].sort_values("date"),on="date",direction="backward",allow_exact_matches=False)[["_i",name]]
  parts.append(q)
 q=pd.concat(parts).set_index("_i").sort_index();df[name]=q[name];return df
new=[]
for ent,key,current,prefix in [("J","canonical_jockey_id","current_jockey_id","jockey"),("T","canonical_trainer_id","current_trainer_id","trainer")]:
 for ctx,curctx,suf in [("canonical_track_id","ctx_track","track"),("distance_band","ctx_dist","dist"),("track_condition_group","ctx_cond","cond"),("race_class_group","ctx_class","class")]:
  n=f"{prefix}_{suf}_prior_win_rate";x=attach_rate(x,key,current,ctx,curctx,n);base=f"{prefix}_prior_win_rate";rn=n+"_resid";x[rn]=x[n]-x[base];new.append(rn)
print("D85_CONTRACT PREP48_PLUS_CONTEXT_CONNECTION_RESID8 STRICT_DATE T1 NO_SEARCH PASS_BOTH_SELECTION_YEARS_TOP1_FLOOR_MINUS_0.005")
print("D85_COVERAGE",{c:float(x[c].notna().mean()) for c in new})
for yr in [2022,2023,2024]:
 tr=x.year_eval<yr;te=x.year_eval.eq(yr)
 for name,F in [("PREP48",F0),("PLUS_CTXCONN8",F0+new)]:
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42));m.fit(x.loc[tr,F],x.loc[tr,"y"]);s=m.decision_function(x.loc[te,F]);z=x.loc[te,["_race","y"]].copy();z["s"]=s;z["p"]=z.groupby("_race").s.transform(lambda a:np.exp(a-a.max())/np.exp(a-a.max()).sum());z["rank"]=z.groupby("_race").s.rank(ascending=False,method="first");w=z[z.y.eq(1)]
  print("D85_RESULT",yr,name,"RACES",len(w),"TOP1",float((w["rank"]==1).mean()),"TOP2",float((w["rank"]<=2).mean()),"TOP3",float((w["rank"]<=3).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w.p.clip(1e-12,1)).mean()))
print("D85_COMPLETE 2025_2026_SEALED")
