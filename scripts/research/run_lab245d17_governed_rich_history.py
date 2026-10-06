from pathlib import Path
import pandas as pd,numpy as np,math
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
BR=ROOT/"outputs"/"research"/"profitability_program"/"lab245b"/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
if not BR.exists(): BR=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\profitability_program\lab245b\LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv")
CTX=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_031\certified_current_race_context_031.csv")
b=pd.read_csv(BR);b=b[pd.to_numeric(b.target_finish_position,errors="coerce").notna()].copy();b["y"]=(pd.to_numeric(b.target_finish_position)==1).astype(int)
base0=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_std5","margin_worst5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]
base=base0.copy()
for x in base0:
 med=b.groupby("_race")[x].transform("median");b[x+"_rel"]=b[x]-med;base.append(x+"_rel")
base.append("target_field_size")
cols=["canonical_race_id","canonical_horse_id","current_barrier","barrier_position_pct","distance_change_metres","abs_distance_change_metres","prior_same_class_starts","jockey_changed_from_last_start","prior_same_jockey_starts","trainer_changed_from_last_start","prior_same_trainer_starts","prior_exact_distance_starts_031"]
ctx=pd.read_csv(CTX,usecols=cols).rename(columns={"canonical_race_id":"_race","canonical_horse_id":"_horse"}).drop_duplicates(["_race","_horse"])
b=b.merge(ctx,on=["_race","_horse"],how="left")
def met(z):
 q=z.copy();q["p"]=q.groupby("_race").raw.transform(lambda x:x/x.sum() if x.sum()>0 else np.repeat(1/len(x),len(x)));q["rk"]=q.groupby("_race").raw.rank(ascending=False,method="first");w=q[q.y==1];n=w._race.nunique()
 return n,(w.rk==1).mean(),(w.rk<=2).mean(),(w.rk<=3).mean(),(1/w.rk).mean(),-np.mean(np.log(np.clip(w.p,1e-12,1)))
bar=["barrier_position_pct"]
dist=["distance_change_metres","abs_distance_change_metres","prior_exact_distance_starts_031"]
cl=["prior_same_class_starts"]
conn=["jockey_changed_from_last_start","prior_same_jockey_starts","trainer_changed_from_last_start","prior_same_trainer_starts"]
tests={"BASE17":base,"BARRIER_CHAMP":base+bar,"BARRIER_DIST":base+bar+dist,"BARRIER_CLASSDEPTH":base+bar+cl,"BARRIER_CONNECTION":base+bar+conn,"BARRIER_DIST_CLASS":base+bar+dist+cl,"BARRIER_ALL_CONTEXT":base+bar+dist+cl+conn}
print("D35_BARRIER_CHAMPION_ADDITIVE_TOURNAMENT");print("FEATURE_ROWS",len(b),"RACES",b._race.nunique())
for yr in [2022,2023,2024]:
 tr=b[b._year<yr];te=b[b._year==yr]
 for name,fs in tests.items():
  m=make_pipeline(SimpleImputer(strategy="median",add_indicator=True),HistGradientBoostingClassifier(max_iter=350,learning_rate=.035,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=10,random_state=24582))
  m.fit(tr[fs],tr.y);z=te[["_race","y"]].copy();z["raw"]=m.predict_proba(te[fs])[:,1]
  n,t1,t2,t3,mrr,ll=met(z);print("RESULT",yr,name,n,f"{t1:.6f}",f"{t2:.6f}",f"{t3:.6f}",f"{mrr:.6f}",f"{ll:.6f}")
