from pathlib import Path
import pandas as pd
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")/"public"/"data"
r=pd.read_csv(P/"edgeiq_historical_performance_rating_v1.csv",low_memory=False)
m=pd.read_csv(P/"edgeiq_official_runs_master_v1.csv",low_memory=False)
print("V2_STAGE039_CONTRACT HISTORICAL_RATING_PROVENANCE_NO_MODEL_NO_MARKET_SEALED_2025_2026")
def norm(s):return s.fillna("").astype(str).str.upper().str.replace(r"[^A-Z0-9]","",regex=True)
for d in (r,m):
 d["_date"]=pd.to_datetime(d["race_date"],errors="coerce").dt.normalize()
 d.drop(d[d["_date"].dt.year.gt(2024)].index,inplace=True)
 d["_name"]=norm(d["horse"])
 d.drop(d[d["_date"].isna()|d["_name"].eq("")].index,inplace=True)
k=["_name","_date"]
z=r.merge(m[k+["horse_key","official_run_flag","trial_flag","jumpout_flag","finish_pos","margin"]],on=k,how="left",validate="one_to_one")
for flag in ["official_run_flag","trial_flag","jumpout_flag"]:
 print("V2_STAGE039_FLAG",flag,z[flag].astype(str).str.upper().value_counts(dropna=False).to_dict())
rating=pd.to_numeric(z["performance_rating_v1"],errors="coerce")
finish=pd.to_numeric(z["finish_position"],errors="coerce")
margin=pd.to_numeric(z["margin_x"],errors="coerce")
field=pd.to_numeric(z["field_size"],errors="coerce")
winner=(finish==1)
expected=70+winner.astype(float)*14+((finish>1)&(finish<=3)).astype(float)*6+(finish<=__import__("numpy").ceil(field/2)).astype(float)*3+__import__("numpy").maximum(0,(field-finish)/__import__("numpy").maximum(field-1,1))*16+__import__("numpy").select([margin<=.5,margin<=1,margin<=2,margin<=3],[6.,4.,2.5,1.],default=0.)-__import__("numpy").minimum(55,margin*3.75)
expected=__import__("numpy").round(__import__("numpy").clip(expected,0,110),2)
bad=int((~__import__("numpy").isclose(rating,expected,atol=.011,rtol=0)).sum())
print("V2_STAGE039_COUNTS",len(z),"RATING_NONNUMERIC",int(rating.isna().sum()),"FORMULA_MISMATCH",bad,"RATING_MIN",float(rating.min()),"RATING_MAX",float(rating.max()))
print("V2_STAGE039_HORSE_KEYS",z["horse_key"].nunique(),"HISTORICAL_DATES",z["_date"].nunique())
print("V2_STAGE039_DECISION","PASS_HISTORICAL_OBSERVATION_ONLY" if bad==0 and rating.notna().all() else "STOP_FORMULA_MISMATCH")
print("V2_STAGE039_COMPLETE")
