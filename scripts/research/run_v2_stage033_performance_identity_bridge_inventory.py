from pathlib import Path
import pandas as pd
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
print("V2_STAGE033_CONTRACT PERFORMANCE_RATING_IDENTITY_BRIDGE_INVENTORY NO_MODEL NO_FUZZY NO_MARKET 2025_2026_SEALED")
# Search only CSV headers for a bridge containing both canonical horse identity and horse name.
roots=[P/"outputs"/"research",P/"public"/"data",P/"docs"/"performance-intelligence"]
hits=[]
for root in roots:
 if not root.exists(): continue
 for f in root.rglob("*.csv"):
  try:
   h=pd.read_csv(f,nrows=0).columns.tolist()
  except Exception: continue
  low={c.lower() for c in h}
  hascanon=any(c in low for c in ["canonical_horse_id","_horse"])
  hasname=any(c in low for c in ["horse","horse_name","horsename","runner_name"])
  if hascanon and hasname:
   hits.append((str(f),h))
print("V2_STAGE033_HITS",len(hits))
for f,h in hits[:120]:
 print("V2_STAGE033_FILE",f)
 print("V2_STAGE033_COLS","|".join(h))
print("V2_STAGE033_COMPLETE")
