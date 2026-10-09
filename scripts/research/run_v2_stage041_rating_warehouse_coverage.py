from pathlib import Path
import pandas as pd
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
w=R/"outputs"/"research"/"model_v2"/"stage006"/"V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv"
a=P/"public"/"data"/"edgeiq_historical_performance_rating_v1.csv"
m=P/"public"/"data"/"edgeiq_official_runs_master_v1.csv"
print("V2_STAGE041_CONTRACT PRE2025_V2_RATING_JOIN_FEASIBILITY NO_MODEL NO_MARKET NO_FUZZY SEALED")
wh=pd.read_csv(w,nrows=0); rh=pd.read_csv(a,nrows=0);mh=pd.read_csv(m,nrows=0)
print("V2_STAGE041_WAREHOUSE_COLUMNS","|".join(wh.columns))
print("V2_STAGE041_RATING_COLUMNS","|".join(rh.columns))
print("V2_STAGE041_MASTER_COLUMNS","|".join(mh.columns))
wcols=[c for c in wh.columns if any(s in c.lower() for s in ("horse","name","date","race","year"))]
print("V2_STAGE041_IDENTITY_CANDIDATES","|".join(wcols))
x=pd.read_csv(w,usecols=wcols,low_memory=False)
if "race_date" not in x.columns:
 print("V2_STAGE041_DECISION STOP_NO_RACE_DATE");raise SystemExit(0)
x["date"]=pd.to_datetime(x["race_date"],errors="coerce").dt.normalize()
x=x[x.date.dt.year.le(2024)].copy()
print("V2_STAGE041_PRE2025_ROWS",len(x),"DATE_MIN",str(x.date.min()),"DATE_MAX",str(x.date.max()))
namecols=[c for c in wcols if c.lower() in ("horse","horse_name","runner_name","name")]
print("V2_STAGE041_EXACT_NAME_FIELDS","|".join(namecols))
if not namecols:
 print("V2_STAGE041_DECISION STOP_NO_EXACT_NAME_FIELD_IN_WAREHOUSE");raise SystemExit(0)
name=namecols[0]
r=pd.read_csv(a,usecols=["horse","race_date","performance_rating_v1"],low_memory=False)
r["date"]=pd.to_datetime(r.race_date,errors="coerce").dt.normalize();r=r[r.date.dt.year.le(2024)].copy()
def norm(s):return s.fillna("").astype(str).str.upper().str.replace(r"[^A-Z0-9]","",regex=True)
r["name"]=norm(r.horse);x["name"]=norm(x[name])
r=r[r.name.ne("") & r.date.notna()]
x=x[x.name.ne("") & x.date.notna()]
hist={k:g.date.sort_values().to_numpy(dtype="datetime64[ns]") for k,g in r.groupby("name")}
import numpy as np
counts=[]
for k,g in x.groupby("name"):
 h=hist.get(k)
 if h is None:counts.extend([0]*len(g))
 else:counts.extend(np.searchsorted(h,g.date.to_numpy(dtype="datetime64[ns]"),side="left").tolist())
print("V2_STAGE041_NAME_MATCHED_RUNNERS",int(x.name.isin(r.name).sum()),"ELIGIBLE_RUNNERS",len(x))
print("V2_STAGE041_WITH_STRICT_PRIOR",sum(n>0 for n in counts),"COVERAGE",sum(n>0 for n in counts)/len(x) if len(x) else 0)
print("V2_STAGE041_DECISION PASS_COVERAGE_DIAGNOSTIC_ONLY")
print("V2_STAGE041_COMPLETE")
