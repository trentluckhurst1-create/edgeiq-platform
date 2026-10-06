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
use=["race_date","canonical_horse_id","canonical_jockey_id","canonical_trainer_id","canonical_track_id","distance_metres","barrier","field_size","finish_position","epi_status_026"]
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
# D43 strict-PIT relationship histories. Current horse is bridge identity; current J/T from LAB031.
b["current_horse_id"]=b["_horse"]
def attach_combo(df,h,keys,prefix,current_cols):
 hh=h[keys+["date","win","top3"]].dropna(subset=keys+["date"]).copy()
 for k in keys:hh[k]=hh[k].astype(str)
 d=hh.groupby(keys+["date"]).agg(starts=("win","size"),wins=("win","sum"),top3=("top3","sum")).reset_index().sort_values(keys+["date"])
 for z in ["starts","wins","top3"]:d[z]=d.groupby(keys)[z].cumsum()
 cols=[prefix+"_prior_starts",prefix+"_prior_win_rate",prefix+"_prior_top3_rate"]
 d[cols[0]]=d.starts;d[cols[1]]=(d.wins+1)/(d.starts+10);d[cols[2]]=(d.top3+3)/(d.starts+10)
 left=df.reset_index().rename(columns={"index":"_i"})
 for src,k in zip(current_cols,keys):left[k]=left[src].astype(str)
 parts=[]
 for kval,g in left.groupby(keys,sort=False):
  kval=kval if isinstance(kval,tuple) else (kval,)
  mask=np.ones(len(d),dtype=bool)
  for k,v in zip(keys,kval):mask &= d[k].eq(v).to_numpy()
  r=d.loc[mask]
  if r.empty:
   q=g[["_i"]].copy()
   for z in cols:q[z]=np.nan
  else:q=pd.merge_asof(g.sort_values("date"),r[["date"]+cols].sort_values("date"),on="date",direction="backward",allow_exact_matches=False)[["_i"]+cols]
  parts.append(q)
 q=pd.concat(parts).set_index("_i").sort_index()
 for z in cols:df[z]=q[z]
 return df
b=attach_combo(b,h,["canonical_jockey_id","canonical_trainer_id"],"jt_combo",["current_jockey_id","current_trainer_id"])
b=attach_combo(b,h,["canonical_horse_id","canonical_jockey_id"],"horse_jockey",["current_horse_id","current_jockey_id"])
b=attach_combo(b,h,["canonical_horse_id","canonical_trainer_id"],"horse_trainer",["current_horse_id","current_trainer_id"])
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
# D44 strict-PIT track-distance-barrier mechanism.
h["distance_band_200"]=(pd.to_numeric(h["distance_metres"],errors="coerce")/200).round()*200
hb=pd.to_numeric(h["barrier"],errors="coerce");hf=pd.to_numeric(h["field_size"],errors="coerce")
h["hist_barrier_pct"]=(hb-1)/(hf-1);h.loc[hf<=1,"hist_barrier_pct"]=np.nan
h["barrier_zone"]=pd.cut(h["hist_barrier_pct"],[-np.inf,1/3,2/3,np.inf],labels=["INNER","MID","OUTER"]).astype(str)
b["distance_band_200"]=(pd.to_numeric(b["current_distance"],errors="coerce")/200).round()*200
bp=pd.to_numeric(b["barrier_position_pct"],errors="coerce")
b["barrier_zone"]=pd.cut(bp,[-np.inf,1/3,2/3,np.inf],labels=["INNER","MID","OUTER"]).astype(str)
# target track id from PERF026 race identity, joined without results.
race_track=h[["date","canonical_track_id"]].copy()
# map race via separate PERF race metadata
rm=pd.read_csv(PERF,usecols=["canonical_race_id","canonical_track_id"]).drop_duplicates("canonical_race_id").rename(columns={"canonical_race_id":"_race","canonical_track_id":"current_track_id"})
b=b.merge(rm,on="_race",how="left")
b=attach_combo(b,h,["canonical_track_id","distance_band_200","barrier_zone"],"tdb_mech",["current_track_id","distance_band_200","barrier_zone"])
b=attach_combo(b,h,["canonical_track_id","barrier_zone"],"tb_mech",["current_track_id","barrier_zone"])
b=attach_combo(b,h,["distance_band_200","barrier_zone"],"db_mech",["distance_band_200","barrier_zone"])
tdb=["tdb_mech_prior_starts","tdb_mech_prior_win_rate","tdb_mech_prior_top3_rate"]
tb=["tb_mech_prior_starts","tb_mech_prior_win_rate","tb_mech_prior_top3_rate"]
db=["db_mech_prior_starts","db_mech_prior_win_rate","db_mech_prior_top3_rate"]
champ=base+bar+rates
tests={"PBC_BASE":champ,"PLUS_TRACK_BARRIER":champ+tb,"PLUS_DIST_BARRIER":champ+db,"PLUS_TRACK_DIST_BARRIER":champ+tdb,"PLUS_ALL_BARRIER_MECH":champ+tb+db+tdb}
mech_cols=tb+db+tdb
print("D44B_MECHANISM_FEATURE_AUDIT")
for c in mech_cols:
    v=pd.to_numeric(b[c],errors="coerce")
    print("FEATURE",c,"COVERAGE",float(v.notna().mean()),"NUNIQUE",int(v.nunique(dropna=True)),"STD",float(v.std(skipna=True)) if v.notna().any() else np.nan,"MIN",float(v.min(skipna=True)) if v.notna().any() else np.nan,"MAX",float(v.max(skipna=True)) if v.notna().any() else np.nan)
print("TRACK_COVERAGE",float(b["current_track_id"].notna().mean()),"TRACK_NUNIQUE",int(b["current_track_id"].nunique(dropna=True)),"DISTBAND_NUNIQUE",int(b["distance_band_200"].nunique(dropna=True)),"ZONE_COUNTS",b["barrier_zone"].value_counts(dropna=False).to_dict())

print("D44B_LIGHTWEIGHT_AUDIT_COMPLETE")
raise SystemExit(0)
