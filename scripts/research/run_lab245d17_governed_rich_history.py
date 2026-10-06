from pathlib import Path
import pandas as pd,numpy as np,math
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH"); PROD=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
B=ROOT/"outputs/research/profitability_program/lab245b/LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
C=PROD/"outputs/research/model_lab_031/certified_current_race_context_031.csv"
P=PROD/"outputs/research/model_lab_026/edgeiq_certified_flat_walk_forward_epi_026.csv"
BASE=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_worst5","margin_std5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]
def norm(s): return s.astype(str).str.strip().str.lower()
b=pd.read_csv(B,low_memory=False); b=b[pd.to_numeric(b["_year"],errors="coerce").between(2021,2024)&b.target_lvs.notna()].copy()
c=pd.read_csv(C,usecols=["canonical_race_id","canonical_horse_id","current_class_group","current_condition_group"],low_memory=False)
b["_jr"]=norm(b["_race"]);b["_jh"]=norm(b["_horse"]);c["_jr"]=norm(c.canonical_race_id);c["_jh"]=norm(c.canonical_horse_id)
b=b.merge(c[["_jr","_jh","current_class_group","current_condition_group"]].drop_duplicates(["_jr","_jh"]),on=["_jr","_jh"],how="left")
use=["canonical_race_id","canonical_horse_id","race_date","distance_metres","race_class_group","track_condition_group","epi_value_026"]
h=pd.read_csv(P,usecols=use,low_memory=False); h["race_date"]=pd.to_datetime(h.race_date,errors="coerce");h=h[h.race_date.notna()].copy();h["_h"]=norm(h.canonical_horse_id)
for x in ["distance_metres","epi_value_026"]:h[x]=pd.to_numeric(h[x],errors="coerce")
h=h.sort_values(["_h","race_date","canonical_race_id"])
groups={k:g for k,g in h.groupby("_h",sort=False)}
cols=["epi_last10_median","epi_peak","epi_last1_minus_peak","epi_near_peak10","epi_dist200_mean","epi_dist200_best","epi_same_class_count","epi_same_class_mean","epi_same_class_best","epi_same_cond_count","epi_same_cond_mean"]
out={x:[] for x in cols}
for n,r in b.iterrows():
 g=groups.get(r["_jh"]); vals={x:np.nan for x in cols}
 if g is not None:
  td=pd.Timestamp(r.race_date); pr=g[g.race_date<td]; epi=pr.epi_value_026.to_numpy(float); epi=epi[np.isfinite(epi)]
  if len(epi):
   e10=epi[-10:];peak=np.nanmax(epi);vals["epi_last10_median"]=np.nanmedian(e10);vals["epi_peak"]=peak;vals["epi_last1_minus_peak"]=epi[-1]-peak;vals["epi_near_peak10"]=np.mean(e10>=peak-5)
   raw=pr.epi_value_026.to_numpy(float);dist=pr.distance_metres.to_numpy(float);dm=np.abs(dist-float(r.current_distance))<=200; de=raw[dm & np.isfinite(raw)]
   if len(de):vals["epi_dist200_mean"]=np.mean(de);vals["epi_dist200_best"]=np.max(de)
   cl=pr.race_class_group.astype(str).str.strip().eq(str(r.current_class_group).strip()).to_numpy();ce=raw[cl & np.isfinite(raw)]
   if len(ce):vals["epi_same_class_count"]=len(ce);vals["epi_same_class_mean"]=np.mean(ce);vals["epi_same_class_best"]=np.max(ce)
   co=pr.track_condition_group.astype(str).str.strip().eq(str(r.current_condition_group).strip()).to_numpy();qe=raw[co & np.isfinite(raw)]
   if len(qe):vals["epi_same_cond_count"]=len(qe);vals["epi_same_cond_mean"]=np.mean(qe)
 for x in cols:out[x].append(vals[x])
for x in cols:b[x]=out[x]
b["y"]=(pd.to_numeric(b.target_finish_position,errors="coerce")==1).astype(int);b["field_size"]=b.groupby("_race")["_horse"].transform("size")
for x in BASE:b[x]=pd.to_numeric(b[x],errors="coerce");b[x+"_relmed"]=b[x]-b[x].groupby(b._race).transform("median")
base=BASE+[x+"_relmed" for x in BASE]+["field_size"]
blocks={"BASE17":base,"CLASS":base+["epi_same_class_count","epi_same_class_mean","epi_same_class_best"],"CONDITION":base+["epi_same_cond_count","epi_same_cond_mean"],"FORM_DISTANCE":base+["epi_last10_median","epi_peak","epi_last1_minus_peak","epi_near_peak10","epi_dist200_mean","epi_dist200_best"],"COMBINED":base+cols}
def met(z):
 rr=[]
 for _,g in z.groupby("_race",sort=False):
  w=np.flatnonzero(g.y.to_numpy()==1)
  if len(w)!=1:continue
  rank=int(g.raw.rank(method="first",ascending=False).iloc[w[0]]);q=np.clip(g.raw.to_numpy(float),1e-12,None);q=q/q.sum();p=q[w[0]];rr.append((rank,-math.log(max(p,1e-12))))
 a=np.array(rr);return len(a),np.mean(a[:,0]<=1),np.mean(a[:,0]<=2),np.mean(a[:,0]<=3),np.mean(1/a[:,0]),np.mean(a[:,1])
print("FEATURE_ROWS",len(b),"RACES",b._race.nunique())
for yr in [2022,2023,2024]:
 tr=b[b._year<yr];te=b[b._year==yr]
 for name,fs in blocks.items():
  m=make_pipeline(SimpleImputer(strategy="median",add_indicator=True),HistGradientBoostingClassifier(max_iter=350,learning_rate=.035,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=10,random_state=24582))
  m.fit(tr[fs],tr.y);z=te[["_race","y"]].copy();z["raw"]=m.predict_proba(te[fs])[:,1]
  n,t1,t2,t3,mrr,ll=met(z);print("RESULT",yr,name,n,f"{t1:.6f}",f"{t2:.6f}",f"{t3:.6f}",f"{mrr:.6f}",f"{ll:.6f}")
