from pathlib import Path
import pandas as pd,re
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM");DATA=ROOT/"public"/"data"
print("D86_CONTRACT AGE_SEX_DEVELOPMENT_SOURCE_HUNT NO_MODEL")
names=["age","horse_age","runner_age","age_years","sex","gender","horse_sex","runner_sex","sex_code","foal_date","date_of_birth","dob"]
hits=[]
for p in DATA.glob("*.csv"):
 try:
  h=pd.read_csv(p,nrows=0);low={c.lower():c for c in h.columns};found=[low[n] for n in names if n in low]
  if not found: continue
  d=pd.read_csv(p,nrows=300000,low_memory=False);datecol=next((c for c in d.columns if c.lower() in ["race_date","meeting_date","date","run_date"]),None);horse=next((c for c in d.columns if c.lower() in ["horse","horse_name","runner","runner_name","canonical_horse_name"]),None)
  dt=pd.to_datetime(d[datecol],errors="coerce") if datecol else pd.Series(pd.NaT,index=d.index)
  rec={"file":p.name,"rows_sample":len(d),"fields":found,"datecol":datecol,"horse":horse,"min":str(dt.min()),"max":str(dt.max()),"y2021":int(dt.dt.year.eq(2021).sum()),"y2022":int(dt.dt.year.eq(2022).sum())}
  for c in found:rec[c+"_cov"]=float(d[c].notna().mean())
  hits.append(rec);print("D86_HIT",rec)
 except Exception as e: pass
print("D86_TOTAL",len(hits));print("D86_COMPLETE")
