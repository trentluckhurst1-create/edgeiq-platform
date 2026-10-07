from pathlib import Path
import os,re,pandas as pd
roots=[Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH"),Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")]
rx=re.compile(r"(sectional|split.*tim|speed.*warehouse|warehouse.*speed)",re.I)
seen=set();print("D80_CONTRACT HISTORICAL_SECTIONAL_SOURCE_DISCOVERY NO_MODEL")
for root in roots:
 for dp,dn,fn in os.walk(root):
  dn[:]=[x for x in dn if x.lower() not in {".git","node_modules","__pycache__"}]
  for n in fn:
   if not rx.search(n) or not n.lower().endswith((".csv",".parquet",".json")):continue
   p=Path(dp)/n
   try:key=(n,p.stat().st_size)
   except:continue
   if key in seen:continue
   seen.add(key);print("D80_FILE",str(p),"BYTES",p.stat().st_size)
   if n.lower().endswith(".csv"):
    try:
     h=pd.read_csv(p,nrows=0);cols=list(h.columns);print("D80_COLS",n,cols)
     datecols=[c for c in cols if "date" in c.lower()]
     if datecols:
      use=[datecols[0]];d=pd.read_csv(p,usecols=use,low_memory=False);q=pd.to_datetime(d[use[0]],errors="coerce");print("D80_RANGE",n,str(q.min()),str(q.max()),"ROWS",len(d))
    except Exception as e:print("D80_ERROR",n,repr(e))
print("D80_COMPLETE")
