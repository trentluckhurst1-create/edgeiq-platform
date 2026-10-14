"""Issue23: audit live source freshness and identity bridge before feature engineering."""
from pathlib import Path
import ast
import pandas as pd
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
script=R/"scripts/research/edgeiq_live_identity_audit.py"
src=script.read_text(encoding="utf-8-sig")
print("LIVE_IDENTITY_SOURCE_BEGIN")
for i,line in enumerate(src.splitlines(),1):
 print(f"{i:03d} {line[:240]}")
print("LIVE_IDENTITY_SOURCE_END")
print("LIVE_ACQUISITION_INVENTORY")
for root in [R/"outputs/research/live_acquisition_v1",P/"outputs/research/live_acquisition_v1"]:
 print("ROOT="+str(root)+" EXISTS="+str(root.exists()))
 if root.exists():
  for p in sorted(root.glob("*"))[:30]:
   if p.is_file():print(f"FILE={p.name} BYTES={p.stat().st_size} MTIME_UTC={pd.Timestamp(p.stat().st_mtime,unit='s',tz='UTC')}")
print("NO_LIVE_SCORE; NO_OUTCOMES_READ")
