from pathlib import Path
import os,csv,json
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
RROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
OUT=RROOT/"outputs"/"research"/"model_v2"/"stage001";OUT.mkdir(parents=True,exist_ok=True)
terms=("epi","performance","timing","section","form","race_field","result","jockey","trainer","barrier","weight","class","speed","pace","first_start","market")
rows=[]
seen=set()
for base in [ROOT/"outputs"/"research",ROOT/"docs"/"performance-intelligence",RROOT/"outputs"/"research"]:
 if not base.exists(): continue
 for dp,dn,fn in os.walk(base):
  # avoid runaway duplicate/cache internals
  dn[:]=[d for d in dn if d not in {".git","node_modules","__pycache__"}]
  for name in fn:
   low=name.lower()
   if not low.endswith((".csv",".parquet",".json")) or not any(t in low for t in terms): continue
   p=Path(dp)/name
   key=str(p).lower()
   if key in seen:continue
   seen.add(key)
   try:size=p.stat().st_size
   except:continue
   rows.append({"path":str(p),"name":name,"bytes":size,"ext":p.suffix.lower()})
rows=sorted(rows,key=lambda x:x["bytes"],reverse=True)
# inspect CSV headers only: zero modelling and avoids loading large authorities
for r in rows:
 r["columns"]=""
 if r["ext"]==".csv":
  try:
   with open(r["path"],"r",encoding="utf-8-sig",errors="replace",newline="") as f:r["columns"]="|".join(next(csv.reader(f)))
  except Exception as e:r["columns"]="ERROR:"+str(e)[:120]
import pandas as pd
df=pd.DataFrame(rows)
df.to_csv(OUT/"V2_STAGE001_DATA_ESTATE_INVENTORY.csv",index=False)
print("V2_STAGE001_CONTRACT DATA_ESTATE_INVENTORY_ONLY NO_MODEL NO_2025_2026_OUTCOME_INSPECTION")
print("V2_STAGE001_FILES",len(df))
for _,r in df.head(80).iterrows():
 print("V2_FILE",r["bytes"],r["path"],"COLS",str(r["columns"])[:500])
print("V2_STAGE001_COMPLETE",OUT/"V2_STAGE001_DATA_ESTATE_INVENTORY.csv")
