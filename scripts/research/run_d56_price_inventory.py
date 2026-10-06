from pathlib import Path
import os,csv
roots=[Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research"),Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research")]
keys=("market","price","odds","bsp","sp_","starting")
seen=set();hits=[]
for root in roots:
 if not root.exists():continue
 for p in root.rglob("*.csv"):
  ps=str(p).lower()
  if not any(k in ps for k in keys):continue
  try:
   size=p.stat().st_size
   with p.open("r",encoding="utf-8-sig",errors="ignore",newline="") as f: hdr=next(csv.reader(f),[])
   cols="|".join(hdr).lower()
   score=sum(k in cols for k in ["price","odds","bsp","starting","sp","race_date","date"])
   if score>=2 or "market" in ps:
    key=(p.name,size,tuple(hdr))
    if key not in seen:seen.add(key);hits.append((score,size,str(p),hdr))
  except Exception:pass
hits=sorted(hits,key=lambda x:(-x[0],-x[1]))[:80]
print("D56_PRICE_INVENTORY_COUNT",len(hits))
for score,size,p,hdr in hits:print("FILE",score,size,p,"COLS",hdr[:40])
print("D56_PRICE_INVENTORY_COMPLETE")
