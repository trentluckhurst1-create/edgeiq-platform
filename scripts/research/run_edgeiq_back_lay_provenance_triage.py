"""EDGEiQ price provenance triage, using existing historical audit registries.

Reads only source-inventory and provenance-audit metadata; does not load
historical outcomes, prices or 2025/26 sealed evaluation rows.
"""
from pathlib import Path
import pandas as pd
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_123")
FILES=["LAB123_PRICE_SOURCE_INVENTORY.csv","LAB123_PRICE_PROVENANCE_AUDIT.csv"]
def main():
 print("EDGEIQ BACK/LAY PRICE PROVENANCE TRIAGE")
 for filename in FILES:
  path=ROOT/filename
  print("\nSOURCE",path,"EXISTS",path.exists())
  if not path.exists():continue
  df=pd.read_csv(path,dtype="string").fillna("")
  print("ROWS",len(df),"COLUMNS",",".join(df.columns))
  cols=[c for c in ["source","provider","path","price_type","bookmaker_or_exchange","back_or_lay","historical_snapshot","potentially_executable","commission_known","deductions_known","provenance_level","timestamp_semantics","usable_for_lab123_returns","limitations","notes"] if c in df]
  if not cols:continue
  view=df[cols]
  terms="betfair|exchange|lay|back|timestamp|executable"
  matched=view.astype(str).apply(lambda s:s.str.contains(terms,case=False,regex=True)).any(axis=1)
  print("RELEVANT_ROWS",int(matched.sum()))
  print(view[matched].head(35).to_string(index=False,max_colwidth=65))
  if "back_or_lay" in df:print("SIDE_COUNTS",df.back_or_lay.value_counts(dropna=False).to_dict())
  if "potentially_executable" in df:print("EXECUTABILITY_COUNTS",df.potentially_executable.value_counts(dropna=False).to_dict())
 print("\nMETADATA_ONLY; NO_HISTORICAL_OUTCOMES; NO_2025_2026_EVALUATION; NO_BETTING")
if __name__=="__main__":main()
