"""Locate Stage011 historical feature source files without changing model data.

Prints candidate files and schemas, then verifies whether horse identifiers
could support a governed live-to-history bridge. Does not auto-join identities.
"""
from pathlib import Path
import argparse
import pandas as pd

PATTERNS=("*LAB245B*","*STAGE011*","*CROSSWALK*","*HORSE*IDENT*","*PERFORMANCE*BRIDGE*","*WAREHOUSE*LVS*")
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--root",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research")
 p.add_argument("--live",default=r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\october_graphql_field_identities.csv")
 a=p.parse_args()
 root=Path(a.root)
 if not root.is_dir():raise RuntimeError("STOP missing research root")
 paths={}
 for pat in PATTERNS:
  for x in root.rglob(pat):
   if x.is_file() and x.suffix.lower() in {".csv",".parquet",".json"}:paths[str(x)]=x
 print("STAGE011 SOURCE RECOVERY candidates",len(paths))
 for x in sorted(paths.values(),key=lambda p:str(p).lower())[:150]:
  print("FILE",x)
  if x.suffix.lower()==".csv":
   try:print(" COLUMNS",pd.read_csv(x,nrows=0).columns.tolist()[:90])
   except Exception as e:print(" READ_ERROR",type(e).__name__,str(e)[:160])
 live=Path(a.live)
 if live.exists():
  d=pd.read_csv(live,dtype="string")
  print("LIVE_COLUMNS",d.columns.tolist())
  if "horse_code" in d:print("LIVE_UNIQUE_HORSE_CODES",d.horse_code.nunique())
 print("READ_ONLY; NO JOIN, NO MODEL SCORES, NO BETS")
if __name__=="__main__":main()
