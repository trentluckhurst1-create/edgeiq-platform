from pathlib import Path
import pandas as pd
roots=[Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH"),Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")]
targets=["racingcom_sectional_warehouse_v2.csv","edgeiq_runner_dna_v6_3_historical_replay_v1.csv","edgeiq_horse_archetype_engine_v1.csv"]
print("D79_CONTRACT ORTHOGONAL_SOURCE_INVENTORY NO_MODEL")
for root in roots:
 for n in targets:
  hits=list(root.rglob(n))
  for p in hits:
   print("D79_FILE",n,str(p),"BYTES",p.stat().st_size)
   try:
    h=pd.read_csv(p,nrows=0);print("D79_COLUMNS",n,list(h.columns))
    d=pd.read_csv(p,nrows=200000,low_memory=False)
    for dc in ["meeting_date","race_date","date"]:
     if dc in d:
      q=pd.to_datetime(d[dc],errors="coerce");print("D79_DATES",n,dc,str(q.min()),str(q.max()),"COVERAGE",float(q.notna().mean()));break
    print("D79_ROWS_SAMPLE",n,len(d))
    for c in d.columns:
     lc=c.lower()
     if any(k in lc for k in ["section","split","speed","position","settle","tempo","horse_key","race_key","current_score","archetype","development","freshness"]):
      print("D79_FIELD",n,c,"COV",float(d[c].notna().mean()),"NU",int(d[c].nunique(dropna=True)),"SAMPLE",d[c].dropna().astype(str).head(3).tolist())
   except Exception as e:print("D79_ERROR",n,repr(e))
print("D79_COMPLETE")
