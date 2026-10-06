from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
BR=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv")
if not BR.exists(): BR=ROOT/"outputs"/"research"/"profitability_program"/"lab245b"/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
CTX=ROOT/"outputs"/"research"/"model_lab_031"/"certified_current_race_context_031.csv"
PERF=ROOT/"outputs"/"research"/"model_lab_026"/"edgeiq_certified_flat_walk_forward_epi_026.csv"
b=pd.read_csv(BR);b=b[pd.to_numeric(b.target_finish_position,errors="coerce").notna()].copy();b["y"]=(pd.to_numeric(b.target_finish_position)==1).astype(int);b["date"]=pd.to_datetime(b["race_date"])
base0=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_std5","margin_worst5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]
base=base0.copy()
for x in base0:
 b[x+"_rel"]=b[x]-b.groupby("_race")[x].transform("median");base.append(x+"_rel")
base.append("target_field_size")
cc=["canonical_race_id","canonical_horse_id","current_barrier","barrier_position_pct","current_jockey_id","current_trainer_id"]
c=pd.read_csv(CTX,usecols=cc).rename(columns={"canonical_race_id":"_race","canonical_horse_id":"_horse"}).drop_duplicates(["_race","_horse"])
b=b.merge(c,on=["_race","_horse"],how="left")
# certified historical connection outcomes
use=["race_date","canonical_jockey_id","canonical_trainer_id","finish_position","epi_status_026"]
h=pd.read_csv(PERF,usecols=use);h=h[h.epi_status_026.eq("CALCULATED")].copy();h["date"]=pd.to_datetime(h.race_date);fp=pd.to_numeric(h.finish_position,errors="coerce");h=h[fp.notna()].copy();h["win"]=(fp[h.index]==1).astype(int);h["top3"]=(fp[h.index]<=3).astype(int)
def attach(df,h,key,prefix,current):
 hh=h[[key,"date","win","top3"]].dropna(subset=[key,"date"]).copy();hh[key]=hh[key].astype(str)
 d=hh.groupby([key,"date"]).agg(starts=("win","size"),wins=("win","sum"),top3=("top3","sum")).reset_index().sort_values([key,"date"])
 for z in ["starts","wins","top3"]: d[z]=d.groupby(key)[z].cumsum()
 d[prefix+"_prior_starts"]=d["starts"];d[prefix+"_prior_win_rate"]=(d["wins"]+1)/(d["starts"]+10);d[prefix+"_prior_top3_rate"]=(d["top3"]+3)/(d["starts"]+10)
 left=df.reset_index().rename(columns={"index":"_i",current:key});left[key]=left[key].astype(str)
 parts=[]
 for kval,g in left.groupby(key,sort=False):
  r=d[d[key].eq(kval)]
  if r.empty:
   q=g[["_i"]].copy()
   for z in [prefix+"_prior_starts",prefix+"_prior_win_rate",prefix+"_prior_top3_rate"]:q[z]=np.nan
  else:q=pd.merge_asof(g.sort_values("date"),r[["date",prefix+"_prior_starts",prefix+"_prior_win_rate",prefix+"_prior_top3_rate"]].sort_values("date"),on="date",direction="backward",allow_exact_matches=False)[["_i",prefix+"_prior_starts",prefix+"_prior_win_rate",prefix+"_prior_top3_rate"]]
  parts.append(q)
 q=pd.concat(parts).set_index("_i").sort_index()
 for z in q.columns:df[z]=q[z]
 return df
b=attach(b,h,"canonical_jockey_id","jockey","current_jockey_id");b=attach(b,h,"canonical_trainer_id","trainer","current_trainer_id")
rates=["jockey_prior_starts","jockey_prior_win_rate","jockey_prior_top3_rate","trainer_prior_starts","trainer_prior_win_rate","trainer_prior_top3_rate"]
ranks=[]
for x in rates:
 y=x+"_race_rank_pct";b[y]=b.groupby("_race")[x].rank(pct=True,method="average");ranks.append(y)
bar=["barrier_position_pct"]
tests={"BARRIER_CHAMP":base+bar,"PLUS_CONN_RATES":base+bar+rates,"PLUS_CONN_RANKS":base+bar+ranks,"PLUS_CONN_FULL":base+bar+rates+ranks}
def met(z):
 z=z.copy();z["p"]=z.groupby("_race").raw.transform(lambda x:x/x.sum());z["rk"]=z.groupby("_race").raw.rank(ascending=False,method="first");w=z[z.y==1];return len(w),(w.rk==1).mean(),(w.rk<=2).mean(),(w.rk<=3).mean(),(1/w.rk).mean(),-np.log(w.p.clip(1e-12)).mean()
print("D40_FULL_UNIVERSE_CONNECTION_REPLICATION");print("ROWS",len(b),"RACES",b._race.nunique(),"JOCKEY_RATE_COVERAGE",b.jockey_prior_win_rate.notna().mean(),"TRAINER_RATE_COVERAGE",b.trainer_prior_win_rate.notna().mean())
for yr in [2022,2023,2024]:
 tr=b[b._year<yr];te=b[b._year==yr]
 for name,fs in tests.items():
  m=make_pipeline(SimpleImputer(strategy="median",add_indicator=True),HistGradientBoostingClassifier(max_iter=350,learning_rate=.035,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=10,random_state=24582));m.fit(tr[fs],tr.y);z=te[["_race","y"]].copy();z["raw"]=m.predict_proba(te[fs])[:,1]
  print("RESULT",yr,name,*[f"{v:.6f}" if isinstance(v,float) else v for v in met(z)])
