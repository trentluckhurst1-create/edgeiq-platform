from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
D=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\d45\D45_FROZEN_PIT_FEATURE_MATRIX.csv")
B=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv")
H=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_price_diagnostics\forward_validation\LAB146_COMPLETE_HISTORICAL_E264_MATRIX.csv")
d=pd.read_csv(D); b=pd.read_csv(B)
bridge_prep=["last_distance","last_finish","last_won","last_top3"]
z=d.merge(b[["_race","_horse"]+bridge_prep],on=["_race","_horse"],how="left",validate="one_to_one")
z["distance_change"]=z["current_distance"]-z["last_distance"]; z["abs_distance_change"]=z["distance_change"].abs()
prep=["days_since_last","distance_change","abs_distance_change","last_finish","last_won","last_top3"]
z["date"]=pd.to_datetime(z.race_date); z["year_eval"]=z.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"}
num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])]
context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"}
base=[c for c in num if c not in context]
h=pd.read_csv(H,usecols=["_race","_horse","starting_price_decimal"])
for q in (z,h):
 q["_race"]=q["_race"].astype(str); q["_horse"]=q["_horse"].astype(str)
h["_sp"]=pd.to_numeric(h["starting_price_decimal"],errors="coerce")
h=h[h["_sp"].gt(1)].drop_duplicates(["_race","_horse"],keep=False)
z=z.merge(h[["_race","_horse","_sp"]],on=["_race","_horse"],how="left",validate="one_to_one")
# Complete field means every D45 runner in the race has a valid LAB146 SP and exactly one winner.
race_ok=z.groupby("_race").agg(n=("y","size"),priced=("_sp",lambda x:x.notna().sum()),wins=("y","sum"))
complete=set(race_ok.index[(race_ok.n==race_ok.priced)&(race_ok.wins==1)])
print("D64_CONTRACT COMPLETE_FIELD_FINAL_SP_FORENSIC BASE42_VS_PROMOTED_PREP48")
print("D64_COMPLETE_FIELD_RACES",len(complete))
for yr in [2022,2023,2024]:
 tr=z.year_eval<yr
 te=z.year_eval.eq(yr)&z["_race"].isin(complete)
 out={}
 for name,F in [("BASE",base),("PREP",base+prep)]:
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42))
  m.fit(z.loc[tr,F],z.loc[tr,"y"])
  q=z.loc[te,["_race","_horse","y","_sp"]].copy()
  q["s"]=m.decision_function(z.loc[te,F]); q["p"]=q.groupby("_race").s.transform(lambda x:np.exp(x-x.max())/np.exp(x-x.max()).sum())
  q["rawq"]=1/q["_sp"]; q["mq"]=q.rawq/q.groupby("_race").rawq.transform("sum"); q["resid"]=q.p-q.mq
  w=q[q.y.eq(1)]
  print("D64_RESULT",yr,name,"RUNNERS",len(q),"RACES",q._race.nunique(),"MODEL_LL",float(-np.log(w.p.clip(1e-12,1)).mean()),"MARKET_LL",float(-np.log(w.mq.clip(1e-12,1)).mean()),"ABS_RESID",float(q.resid.abs().mean()))
  q["band"]=pd.cut(q["_sp"],[1,2,4,8,16,np.inf],right=False,labels=["1-2","2-4","4-8","8-16","16+"])
  for band,g in q.groupby("band",observed=True):
   print("D64_BAND",yr,name,str(band),"N",len(g),"MEAN_P_MINUS_MARKET",float(g.resid.mean()))
print("D64_COMPLETE FINAL_SP_FORENSIC_ONLY 2025_2026_SEALED")
