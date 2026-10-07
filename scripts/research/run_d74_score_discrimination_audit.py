from pathlib import Path
import pandas as pd,os
roots=[Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH"),Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")]
names={"LAB231_HISTORICAL_PERFORMANCE_FEATURES.csv","LAB231_OOF_PREDICTIONS.csv","LAB229_OOF_PREDICTIONS_CORRECTED.csv"}
print("D77_CONTRACT LAB231_UNIQUE_INFORMATION_INVENTORY NO_MODEL NO_OUTCOME_INSPECTION")
for root in roots:
 for dp,dn,fn in os.walk(root):
  dn[:]=[x for x in dn if x.lower() not in {".git","node_modules","__pycache__"}]
  for n in fn:
   if n not in names:continue
   p=Path(dp)/n;print("D77_FILE",p,"BYTES",p.stat().st_size)
   try:
    h=pd.read_csv(p,nrows=0);print("D77_COLUMNS",n,list(h.columns))
    use=list(h.columns)[:120];d=pd.read_csv(p,usecols=use,nrows=200000,low_memory=False)
    for c in use:
     cov=float(d[c].notna().mean());nu=int(d[c].nunique(dropna=True))
     if cov>0:print("D77_FIELD",n,c,"COVERAGE_SAMPLE",cov,"NUNIQUE_SAMPLE",nu)
   except Exception as e:print("D77_ERROR",n,repr(e))
print("D77_COMPLETE")
