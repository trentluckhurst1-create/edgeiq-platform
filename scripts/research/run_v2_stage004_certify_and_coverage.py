from pathlib import Path
import pandas as pd,numpy as np,os
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv";OUT=R/"outputs"/"research"/"model_v2"/"stage004";OUT.mkdir(parents=True,exist_ok=True)
z=pd.read_csv(D,usecols=["_race","_horse","race_date","y","target_finish_position"]);z["date"]=pd.to_datetime(z.race_date);z["year"]=z.date.dt.year;z=z[z.year<=2024]
rs=z.groupby("_race").y.sum();good=set(rs.index[rs.eq(1)]);u=z[z._race.isin(good)].copy()
u.to_csv(OUT/"V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv",index=False)
print("V2_STAGE004_CONTRACT CERTIFY_SINGLE_WINNER_UNIVERSE_AND_AUTHORITY_COVERAGE NO_MODEL 2025_2026_SEALED")
print("V2_STAGE004_UNIVERSE","RUNNERS",len(u),"RACES",u._race.nunique(),"EXCLUDED_RACES",z._race.nunique()-u._race.nunique())
for yr,g in u.groupby("year"):print("V2_STAGE004_YEAR",yr,"RUNNERS",len(g),"RACES",g._race.nunique(),"WINS",int(g.y.sum()))
files=[
("PERFORMANCE_BRIDGE",R/"outputs"/"research"/"profitability_program"/"lab245b"/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"),
("TIMING_H4B",P/"outputs"/"research"/"model_lab_090"/"LAB090F5B_STRICT_PRIOR_TIMING_H4B_MATRIX.csv"),
("PACE",P/"outputs"/"research"/"model_lab_087"/"LAB087G_PACE_H4B_IDENTITY_BRIDGE.csv"),
("FIRST_STARTER",P/"outputs"/"research"/"model_lab_075f2"/"canonical_strict_date_first_starter_universe_075f2.csv"),
("FORM_LINE",P/"outputs"/"research"/"model_lab_120"/"LAB120E_DYNAMIC_FORM_LINE_FEATURES.csv"),
]
for name,p in files:
 if not p.exists():print("V2_AUTH",name,"MISSING",p);continue
 try:
  h=pd.read_csv(p,nrows=0);cols=list(h.columns)
  print("V2_AUTH",name,"BYTES",p.stat().st_size,"NCOLS",len(cols),"KEYS","|".join([c for c in cols if c.lower() in {"_race","_horse","canonical_race_id","canonical_horse_id","race_date","race_date_model","year","horse_id"}]),"COLS","|".join(cols[:35]))
 except Exception as e:print("V2_AUTH",name,"ERROR",str(e))
print("V2_STAGE004_COMPLETE",OUT)
