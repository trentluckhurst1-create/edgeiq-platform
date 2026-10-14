"""Find current-form timing/LVS source coverage without contaminating sealed outcomes.

Read-only inventory. Never constructs guessed LVS or joins by name.
"""
from pathlib import Path
import argparse
import pandas as pd
TOKENS=("time","timing","standard","benchmark","lvs","performance","result","warehouse")
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--root",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research")
 p.add_argument("--live",default=r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\caulfield_browser_form.csv")
 p.add_argument("--cutoff",default="2026-10-14")
 a=p.parse_args()
 root=Path(a.root)
 if not root.exists():raise RuntimeError("STOP research root missing")
 live=pd.read_csv(a.live,dtype="string")
 live=live[pd.to_datetime(live.race_date,errors="coerce").lt(pd.Timestamp(a.cutoff))]
 print("LIVE_FORM_ROWS",len(live),"HORSES",live.horse_code.nunique(),"DATE_MIN",live.race_date.min(),"DATE_MAX",live.race_date.max())
 print("LIVE_FORM_YEAR_COUNTS",pd.to_datetime(live.race_date,errors="coerce").dt.year.value_counts().sort_index().to_dict())
 paths=[]
 for f in root.rglob("*"):
  if f.is_file() and f.suffix.lower() in (".csv",".parquet") and any(t in f.name.casefold() for t in TOKENS):paths.append(f)
 print("CANDIDATE_SOURCE_FILES",len(paths))
 for f in sorted(paths,key=lambda z:str(z))[:250]:
  try:
   if f.suffix.lower()==".csv":
    sample=pd.read_csv(f,nrows=100,dtype="string")
   else:sample=pd.read_parquet(f).head(100)
   cols=sample.columns.tolist()
   datecols=[c for c in cols if "date" in c.casefold()]
   timecols=[c for c in cols if any(t in c.casefold() for t in ("time","standard","benchmark","lvs","length"))]
   if not datecols and not timecols:continue
   print("SOURCE",f)
   print("  DATES",datecols[:12],"PERFORMANCE",timecols[:18])
   for c in datecols[:2]:
    dt=pd.to_datetime(sample[c],errors="coerce")
    if dt.notna().any():print("  SAMPLE_DATE_RANGE",c,str(dt.min().date()),str(dt.max().date()))
  except Exception as e:print("UNREADABLE",f,type(e).__name__,str(e)[:100])
 print("INVENTORY_ONLY; NO SEALED OUTCOME READOUT, NO MODEL OR BETS")
if __name__=="__main__":main()
