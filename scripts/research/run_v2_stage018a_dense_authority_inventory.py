from pathlib import Path
import os,re
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research")
print("V2_STAGE018A_CONTRACT DENSE_UNUSED_AUTHORITY_INVENTORY NO_MODEL NO_MARKET 2025_2026_SEALED")
terms=re.compile(r"(gear|age|sex|gender|class|weight|track.?condition|going|barrier|jockey|trainer|spell|prep)",re.I)
exclude=re.compile(r"(market|price|bsp|odds)",re.I)
hits=[]
for p in ROOT.rglob("*.csv"):
 s=str(p)
 if exclude.search(s): continue
 if terms.search(p.name):
  try:
   size=p.stat().st_size
   if size>1000:hits.append((size,s))
  except:pass
for size,s in sorted(hits,reverse=True)[:160]:
 print("V2_STAGE018A_FILE",size,s)
print("V2_STAGE018A_COUNT",len(hits))
print("V2_STAGE018A_COMPLETE")
