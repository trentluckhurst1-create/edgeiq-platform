"""Find existing governed horse crosswalk files and test live-to-canonical coverage.

Read-only. Does not certify matches from string equality or invent IDs.
"""
from pathlib import Path
import argparse
import pandas as pd
ROOTS=[Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research"),Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research")]
LIVE=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\october_graphql_field_identities.csv")
TOKENS=("crosswalk","identity","horse_map","horse_code","canonical_horse","match_bridge")
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--date",default="2026-10-14")
 p.add_argument("--venue",default="Caulfield")
 p.add_argument("--max-candidates",type=int,default=120)
 a=p.parse_args()
 live=pd.read_csv(LIVE,dtype="string")
 live=live[live.race_date.eq(a.date)&live.venue.str.casefold().eq(a.venue.casefold())]
 print("LIVE_RUNNERS",len(live),"HORSE_CODE",live.horse_code.nunique(),"EIQ_HORSE_ID",live.eiq_horse_id.nunique())
 candidates=[]
 for root in ROOTS:
  if not root.exists():continue
  for f in root.rglob("*.csv"):
   if any(token in f.name.lower() for token in TOKENS):candidates.append(f)
 candidates=sorted(set(candidates),key=lambda f:(-f.stat().st_mtime,str(f)))
 print("CANDIDATE_FILES",len(candidates),"CHECKING",min(len(candidates),a.max_candidates))
 for f in candidates[:a.max_candidates]:
  try:cols=pd.read_csv(f,nrows=0).columns.tolist()
  except Exception as e:
   print("UNREADABLE",str(f),str(e));continue
  id_cols=[c for c in cols if any(x in c.lower() for x in ("horse","canonical","code","match_status","source"))]
  if not id_cols:continue
  print("CANDIDATE",f,"BYTES",f.stat().st_size,"IDENTITY_COLUMNS",",".join(id_cols[:25]))
  if f.stat().st_size>100_000_000:continue
  try:
   d=pd.read_csv(f,usecols=id_cols,dtype="string",low_memory=False)
   for target in ("horse_code","eiq_horse_id"):
    for col in id_cols:
     if col not in d or target not in live:continue
     vals=set(d[col].dropna().str.strip().str.upper())
     n=int(live[target].dropna().str.strip().str.upper().isin(vals).sum())
     if n:print("POSSIBLE_COVERAGE_UNCERTIFIED",target,"->",col,n,"OF",len(live))
  except Exception as e:print("READ_ERROR",str(f),type(e).__name__,str(e)[:120])
 print("NO_IDENTITIES_CERTIFIED; REQUIRE_EXACT_GOVERNED_CROSSWALK_WITH_LINEAGE")
if __name__=="__main__":main()
