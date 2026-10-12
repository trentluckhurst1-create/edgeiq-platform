"""EDGEiQ: inventory historical price data for separate BACK/LAY research.

Read-only inventory. Does not open result data or 2025/26 outcomes.
Lists candidate CSV/Parquet sources and CSV header columns for eligibility review.
"""
from pathlib import Path
import csv, argparse
ROOTS=[Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research"),Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research")]
TERMS=("market","price","odds","betfair","exchange","bsp","sp_","snapshot","tick")
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--max-files",type=int,default=300)
 args=p.parse_args()
 found=[]
 for root in ROOTS:
  if not root.exists():continue
  for f in root.rglob("*"):
   if not f.is_file() or f.suffix.lower() not in (".csv",".parquet"):continue
   if not any(t in str(f).lower() for t in TERMS):continue
   found.append(f)
 found=sorted(set(found),key=lambda f:str(f).lower())
 print("EDGEIQ PRICE SOURCE INVENTORY — READ ONLY")
 print("CANDIDATE_FILES",len(found))
 for f in found[:args.max_files]:
  print("\nFILE",f)
  print("BYTES",f.stat().st_size)
  if f.suffix.lower()==".csv":
   try:
    with f.open("r",encoding="utf-8-sig",newline="") as h:cols=next(csv.reader(h))
    print("COLUMNS",",".join(cols[:90]))
   except (OSError,UnicodeError,StopIteration) as e:print("HEADER_ERROR",type(e).__name__,str(e)[:150])
  else:print("PARQUET_SCHEMA_NOT_READ")
 print("\nFILES_SHOWN",min(len(found),args.max_files))
 print("NO_OUTCOME_ROWS_READ; NO_STRATEGY_TESTING; NO_SEALED_2025_2026_EVALUATION")
if __name__=="__main__":main()
