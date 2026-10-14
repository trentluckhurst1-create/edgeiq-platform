"""Read-only inventory of historical identity evidence for 98 Racing.com horses."""
from pathlib import Path
import argparse
import pandas as pd

def main():
 a=argparse.ArgumentParser()
 a.add_argument("--form",default=r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\caulfield_browser_form.csv")
 a.add_argument("--stage006",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage006\V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv")
 a.add_argument("--bridge",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv")
 x=a.parse_args()
 f=pd.read_csv(x.form,dtype=str)
 names=set(f.horse_name.dropna().str.strip().str.casefold())
 print("LIVE_UNIQUE_NAMES",len(names),"LIVE_UNIQUE_CODES",f.horse_code.nunique())
 for label,path in [("STAGE006",x.stage006),("LAB245B_BRIDGE",x.bridge)]:
  if not Path(path).exists():
   print(label,"MISSING",path);continue
  cols=pd.read_csv(path,nrows=0).columns.tolist()
  candidates=[v for v in cols if any(k in v.casefold() for k in ("horse","name","source","race","date","track","venue","trainer","jockey"))]
  print("\nSOURCE",label,"CANDIDATE_COLUMNS",candidates)
  possible=[v for v in candidates if "name" in v.casefold() and "horse" in v.casefold()]
  if possible:
   d=pd.read_csv(path,usecols=possible,dtype=str)
   for v in possible:
    overlap=d[v].dropna().str.strip().str.casefold().isin(names)
    print("NAME_COLUMN",v,"OVERLAP_ROWS",int(overlap.sum()),"OVERLAP_UNIQUE_NAMES",int(d.loc[overlap,v].str.casefold().nunique()))
  else:print("NO_HORSE_NAME_COLUMN; cannot derive EIQ mapping from name")
 print("\nRESEARCH_ONLY: NAME OVERLAP IS DISCOVERY, NOT CERTIFIED IDENTITY")
if __name__=="__main__":main()
