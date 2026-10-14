"""EDGEiQ: inspect existing market archive metadata for 2022-2024 coverage.

Read-only. No historical outcomes, no sealed-year data, no price substitution.
"""
from pathlib import Path
import pandas as pd
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research")
SOURCES=[
 ROOT/"model_lab_080"/"LAB081E_CANONICAL_MARKET_SOURCE_AUDIT.csv",
 ROOT/"model_lab_123"/"LAB123_PRICE_SOURCE_INVENTORY.csv",
 ROOT/"model_lab_080"/"LAB081D2_TARGETED_MARKET_ARCHIVE_INVENTORY.csv",
]
def main():
 print("EDGEIQ HISTORICAL PRICE ARCHIVE — 2022-2024 SOURCE CHECK")
 for f in SOURCES:
  print("\nSOURCE",f,"EXISTS",f.exists())
  if not f.exists():continue
  d=pd.read_csv(f,dtype="string",low_memory=False).fillna("")
  print("ROWS",len(d),"COLUMNS",",".join(d.columns))
  if f.name=="LAB081E_CANONICAL_MARKET_SOURCE_AUDIT.csv":
   print(d.to_string(index=False,max_colwidth=80))
  elif f.name=="LAB123_PRICE_SOURCE_INVENTORY.csv":
   cols=[c for c in ["source","date_min","date_max","rows","runner_coverage","race_coverage","historical_snapshot","back_or_lay","provenance_level"] if c in d]
   print(d[cols].to_string(index=False,max_colwidth=60))
  else:
   cols=[c for c in ["file","rows","role","identity_score","price_cols","timestamp_cols","race_time_cols"] if c in d]
   if cols:
    ranked=d.copy()
    if "identity_score" in ranked:ranked["_score"]=pd.to_numeric(ranked.identity_score,errors="coerce").fillna(-1)
    else:ranked["_score"]=0
    ranked=ranked.sort_values("_score",ascending=False)
    print(ranked[cols].head(20).to_string(index=False,max_colwidth=65))
 print("\nNO_PRICE_ROWS_OR_OUTCOMES_READ; NO_2025_2026_EVALUATION")
if __name__=="__main__":main()
