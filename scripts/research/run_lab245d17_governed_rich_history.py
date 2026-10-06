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
use=["race_date","canonical_horse_id","canonical_jockey_id","canonical_trainer_id","distance_metres","finish_position","epi_status_026"]
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
# PL002 preparation/recency port: strict prior-date horse history only.
prep=["runs_last_30d","runs_last_60d","runs_last_90d","prep_run_number_90d","first_up_90d","second_up_90d","third_up_90d","distance_change_from_last","abs_distance_change_from_last","last_finish_position","last_won","last_top3"]
for x in prep:b[x]=np.nan
hh=h[["canonical_horse_id","date","distance_metres","finish_position"]].dropna(subset=["canonical_horse_id","date"]).copy()
hh["canonical_horse_id"]=hh.canonical_horse_id.astype(str);hh["distance_metres"]=pd.to_numeric(hh.distance_metres,errors="coerce");hh["finish_position"]=pd.to_numeric(hh.finish_position,errors="coerce")
targets=b[["_horse","date","current_distance"]].copy();targets["_horse"]=targets._horse.astype(str)
for horse,idx in targets.groupby("_horse",sort=False).groups.items():
 hist=hh[hh.canonical_horse_id.eq(horse)].sort_values("date")
 if hist.empty:continue
 dates=hist.date.to_numpy(dtype="datetime64[ns]");dists=hist.distance_metres.to_numpy(float);fin=hist.finish_position.to_numpy(float)
 for i in idx:
  td=np.datetime64(targets.at[i,"date"]);pos=np.searchsorted(dates,td,side="left")
  if pos<=0:continue
  gaps=(td-dates[:pos]).astype("timedelta64[D]").astype(float)
  n30=float(np.sum(gaps<=30));n60=float(np.sum(gaps<=60));n90=float(np.sum(gaps<=90))
  b.at[i,"runs_last_30d"]=n30;b.at[i,"runs_last_60d"]=n60;b.at[i,"runs_last_90d"]=n90;b.at[i,"prep_run_number_90d"]=1+n90
  b.at[i,"first_up_90d"]=float(gaps[-1]>90);b.at[i,"second_up_90d"]=float(gaps[-1]<=90 and n90==1);b.at[i,"third_up_90d"]=float(gaps[-1]<=90 and n90==2)
  dc=pd.to_numeric(targets.at[i,"current_distance"],errors="coerce")-dists[pos-1];b.at[i,"distance_change_from_last"]=dc;b.at[i,"abs_distance_change_from_last"]=abs(dc)
  lf=fin[pos-1];b.at[i,"last_finish_position"]=lf;b.at[i,"last_won"]=float(lf==1);b.at[i,"last_top3"]=float(lf<=3)
prep_rank=[]
for x in ["days_since_last","prep_run_number_90d","distance_change_from_last"]:
 y=x+"_prep_race_rank_pct";b[y]=b.groupby("_race")[x].rank(pct=True,method="average");prep_rank.append(y)
rates=["jockey_prior_starts","jockey_prior_win_rate","jockey_prior_top3_rate","trainer_prior_starts","trainer_prior_win_rate","trainer_prior_top3_rate"]
ranks=[]
for x in rates:
 y=x+"_race_rank_pct";b[y]=b.groupby("_race")[x].rank(pct=True,method="average");ranks.append(y)
bar=["barrier_position_pct"]
conn=base+bar+rates
prep_counts=["runs_last_30d","runs_last_60d","runs_last_90d","prep_run_number_90d","first_up_90d","second_up_90d","third_up_90d"]
prep_last=["distance_change_from_last","abs_distance_change_from_last","last_finish_position","last_won","last_top3"]
tests={"PBC_BASE":conn,"PBC_PREP_COUNTS":conn+prep_counts,"PBC_PREP_LAST":conn+prep_last,"PBC_PREP_RANKS":conn+prep_rank,"PBC_PREP_ALL":conn+prep_counts+prep_last+prep_rank}
def met(z):
 z=z.copy();z["p"]=z.groupby("_race").raw.transform(lambda x:x/x.sum());z["rk"]=z.groupby("_race").raw.rank(ascending=False,method="first");w=z[z.y==1];return len(w),(w.rk==1).mean(),(w.rk<=2).mean(),(w.rk<=3).mean(),(1/w.rk).mean(),-np.log(w.p.clip(1e-12)).mean()
print("D42_FULL_UNIVERSE_PL002_PREP_ABLATION");print("ROWS",len(b),"RACES",b._race.nunique(),"JOCKEY_RATE_COVERAGE",b.jockey_prior_win_rate.notna().mean(),"TRAINER_RATE_COVERAGE",b.trainer_prior_win_rate.notna().mean(),"PREP_COVERAGE",b.runs_last_90d.notna().mean())
for yr in [2022,2023,2024]:
 tr=b[b._year<yr];te=b[b._year==yr]
 for name,fs in tests.items():
  m=make_pipeline(SimpleImputer(strategy="median",add_indicator=True),HistGradientBoostingClassifier(max_iter=350,learning_rate=.035,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=10,random_state=24582));m.fit(tr[fs],tr.y);z=te[["_race","y"]].copy();z["raw"]=m.predict_proba(te[fs])[:,1]
  print("RESULT",yr,name,*[f"{v:.6f}" if isinstance(v,float) else v for v in met(z)])
