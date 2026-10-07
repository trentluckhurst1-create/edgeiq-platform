from pathlib import Path
import pandas as pd
R=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
print("D81_CONTRACT PRE2023_SECTIONAL_PARENT_TRACE NO_MODEL")
cand=list(R.rglob("edgeiq_sectional_race_identity_v28_unresolved.csv"))
if not cand: raise SystemExit("NO_UNRESOLVED")
u=pd.read_csv(cand[0],low_memory=False)
u["race_date"]=pd.to_datetime(u["race_date"],errors="coerce")
q=u[u["race_date"]<pd.Timestamp("2023-01-01")]
print("D81_UNRESOLVED_PRE2023","ROWS",len(q),"DATES",str(q["race_date"].min()),str(q["race_date"].max()))
for c in ["source","parent_source_file","source_lineage","v25_reason","v26_diagnostic_reason"]:
 if c in q.columns: print("D81_TOP",c,q[c].astype(str).value_counts().head(20).to_dict())
parents=q["parent_source_file"].dropna().astype(str).unique().tolist() if "parent_source_file" in q.columns else []
print("D81_PARENT_COUNT",len(parents))
for raw in parents[:100]:
 p=Path(raw);hits=[p] if p.exists() else list(R.rglob(p.name))[:5]
 print("D81_PARENT",raw,"HITS",[str(x) for x in hits])
 for h in hits[:2]:
  if h.suffix.lower()!=".csv": continue
  try:
   cols=list(pd.read_csv(h,nrows=0).columns);print("D81_PARENT_COLS",h.name,cols)
   d=pd.read_csv(h,nrows=2000,low_memory=False)
   for c in cols:
    lc=c.lower()
    if any(k in lc for k in ["section","split","speed","time","last200","last400","last600","distance","position"]):
     print("D81_MEASURE_FIELD",h.name,c,"COV",float(d[c].notna().mean()),"NU",int(d[c].nunique(dropna=True)),"SAMPLE",d[c].dropna().astype(str).head(3).tolist())
  except Exception as e: print("D81_ERROR",str(h),repr(e))
print("D81_COMPLETE")
