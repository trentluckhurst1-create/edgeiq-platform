from pathlib import Path
import pandas as pd,json,os
roots=[Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH"),Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")]
tokens=("research","warehouse","historical","performance","result","form","timing","sectional","rating","jockey","trainer","race")
seen=set();rows=[]
print("V2_001_CONTRACT CERTIFIED_DATA_ESTATE_INVENTORY NO_MODEL NO_2025_2026_OUTCOME_INSPECTION")
for root in roots:
 for base in [root/"outputs"/"research",root/"docs"/"performance-intelligence"]:
  if not base.exists():continue
  for p in base.rglob("*"):
   if not p.is_file() or p.suffix.lower() not in {".csv",".parquet"}:continue
   ps=str(p).lower()
   if not any(t in ps for t in tokens):continue
   key=str(p.resolve()).lower()
   if key in seen:continue
   seen.add(key)
   try:
    size=p.stat().st_size
    if p.suffix.lower()==".csv":
     x=pd.read_csv(p,nrows=5,low_memory=False);cols=list(x.columns)
     # Header/sample only: no sealed-year outcome analysis.
     datecols=[c for c in cols if "date" in c.lower()]
     ids=[c for c in cols if any(t in c.lower() for t in ["race","horse","jockey","trainer"])][:20]
     rows.append({"path":str(p),"bytes":size,"columns":len(cols),"date_columns":"|".join(datecols[:10]),"id_columns":"|".join(ids),"sample_columns":"|".join(cols[:40])})
    else:
     rows.append({"path":str(p),"bytes":size,"columns":None,"date_columns":"","id_columns":"","sample_columns":"PARQUET_HEADER_NOT_OPENED"})
   except Exception as e:rows.append({"path":str(p),"bytes":p.stat().st_size,"columns":None,"date_columns":"","id_columns":"","sample_columns":"ERROR:"+str(e)[:120]})
out=pd.DataFrame(rows).sort_values("bytes",ascending=False);dest=roots[0]/"outputs"/"research"/"profitability_program"/"v2";dest.mkdir(parents=True,exist_ok=True);out.to_csv(dest/"V2_001_DATA_ESTATE_INVENTORY.csv",index=False)
print("V2_001_FILES",len(out),"TOTAL_BYTES",int(out.bytes.sum()))
for _,r in out.head(60).iterrows():print("V2_001_FILE","BYTES",int(r.bytes),"COLS",r["columns"],"PATH",r.path,"IDS",r.id_columns,"DATES",r.date_columns)
print("V2_001_COMPLETE NO_MODEL 2025_2026_SEALED")
