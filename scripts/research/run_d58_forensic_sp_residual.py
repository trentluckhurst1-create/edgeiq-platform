from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
D45=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\d45\D45_FROZEN_PIT_FEATURE_MATRIX.csv")
PB=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245C3C_LAB146_PRICE_BRIDGE.csv")
d=pd.read_csv(D45);p=pd.read_csv(PB)
d["date"]=pd.to_datetime(d.race_date);d["year_eval"]=d.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"}
num=[c for c in d if c not in meta and pd.api.types.is_numeric_dtype(d[c])]
context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"}
F=[c for c in num if c not in context]
print("D58_START D45",len(d),"PRICE_BRIDGE",len(p),"FEATURES",len(F))
print("PRICE_COLS",list(p.columns))
# exact existing bridge identity only
need=["_race","_horse","_sp"]
pp=p[need].copy();pp["_sp"]=pd.to_numeric(pp["_sp"],errors="coerce")
pp=pp[pp._sp.gt(1)].drop_duplicates(["_race","_horse"],keep=False)
x=d.merge(pp,on=["_race","_horse"],how="left",validate="one_to_one")
print("D58_PRICE_JOIN","COVERAGE",float(x._sp.notna().mean()),"ROWS",int(x._sp.notna().sum()),"RACES",int(x.loc[x._sp.notna(),"_race"].nunique()))
for yr in [2022,2023]:
 tr=x.year_eval<yr;te=x.year_eval.eq(yr)&x._sp.notna()
 m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42))
 m.fit(x.loc[tr,F],x.loc[tr,"y"])
 q=x.loc[te,["_race","_horse","y","_sp","target_field_size"]].copy()
 q["s"]=m.decision_function(x.loc[te,F])
 q["p"]=q.groupby("_race").s.transform(lambda z:np.exp(z-z.max())/np.exp(z-z.max()).sum())
 q["rawq"]=1/q._sp
 q["q"]=q.rawq/q.groupby("_race").rawq.transform("sum")
 q["resid"]=q.p-q.q
 q["profit"]=np.where(q.y.eq(1),q._sp-1,-1.0)
 q["odds_band"]=pd.cut(q._sp,[1,2,4,8,16,np.inf],right=False,labels=["1-2","2-4","4-8","8-16","16+"])
 q["field_band"]=pd.cut(q.target_field_size,[0,9,13,np.inf],right=False,labels=["<9","9-12","13+"])
 print("YEAR",yr,"RUNNERS",len(q),"RACES",q._race.nunique(),"MARKET_LL",float(-np.log(q.loc[q.y.eq(1),"q"].clip(1e-12,1)).mean()),"MODEL_LL",float(-np.log(q.loc[q.y.eq(1),"p"].clip(1e-12,1)).mean()),"MEAN_ABS_RESID",float(q.resid.abs().mean()))
 for band,g in q.groupby("odds_band",observed=True):
  print("ODDS",yr,str(band),"N",len(g),"WINS",int(g.y.sum()),"MEAN_P_MINUS_Q",float(g.resid.mean()),"ALL_RUNNER_SP_POT",float(g.profit.sum()/len(g)))
 for band,g in q.groupby("field_band",observed=True):
  print("FIELD",yr,str(band),"N",len(g),"MEAN_P_MINUS_Q",float(g.resid.mean()),"ALL_RUNNER_SP_POT",float(g.profit.sum()/len(g)))
print("D58_FORENSIC_SP_COMPLETE NOTE_FINAL_SP_NOT_EXECUTABLE")

# D59 deterministic LAB146 namespace audit
H=Path(r"C:\\Users\\trent\\OneDrive\\Documents\\EDGEIQ_PLATFORM\\outputs\\research\\model_price_diagnostics\\forward_validation\\LAB146_COMPLETE_HISTORICAL_E264_MATRIX.csv")
h=pd.read_csv(H,usecols=["_race","_horse","race_date_model","starting_price_decimal"])
a=d[["_race","_horse"]].copy(); a["_race"]=a["_race"].astype(str); a["_horse"]=a["_horse"].astype(str)
b=h[["_race","_horse"]].copy(); b["_race"]=b["_race"].astype(str); b["_horse"]=b["_horse"].astype(str)
j=a.merge(b.drop_duplicates(),on=["_race","_horse"],how="inner")
print("D59_LAB146_ROWS",len(h),"RACES",h["_race"].nunique())
print("D59_EXACT_NAMESPACE_ROWS",len(j),"RACES",j["_race"].nunique())
h["date"]=pd.to_datetime(h["race_date_model"],errors="coerce")
for yy in [2021,2022,2023,2024]:
 z=h[h["date"].dt.year.eq(yy)]; print("D59_YEAR",yy,"ROWS",len(z),"RACES",z["_race"].nunique(),"VALID_SP",pd.to_numeric(z["starting_price_decimal"],errors="coerce").gt(1).sum())
print("D59_COMPLETE")
