"""EDGEiQ historical back/lay readiness report from existing provenance registries.

Metadata only. Explicitly does not certify executable prices or calculate ROI.
"""
from pathlib import Path
import pandas as pd
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_123")
def yes(v):return str(v).strip().lower()=="true"
def main():
 a=pd.read_csv(ROOT/"LAB123_PRICE_SOURCE_INVENTORY.csv",dtype=str).fillna("")
 b=pd.read_csv(ROOT/"LAB123_PRICE_PROVENANCE_AUDIT.csv",dtype=str).fillna("")
 m=a.merge(b[["source","usable_for_lab123_returns","limitations"]],on="source",how="left",validate="one_to_one")
 print("EDGEIQ MODEL SELECTION — MARKET DATA READINESS")
 print("SOURCES",len(m))
 print("EXECUTABLE_CERTIFIED",0,"(LAB123 reports no LEVEL_4 source)")
 print("BETFAIR_LAY_SOURCES",sum(m["back_or_lay"].str.contains("lay",case=False,na=False)))
 print("LAB123_RETURN_ANALYSIS_USABLE",sum(m.usable_for_lab123_returns.map(yes)))
 for _,r in m.iterrows():
  side=r["back_or_lay"]
  is_lay="lay" in side.lower()
  usable=yes(r.usable_for_lab123_returns)
  if is_lay:status="LAY_PRICE_PRESENT_UNCERTIFIED"
  elif usable:status="HISTORICAL_BACK_DIAGNOSTIC_ONLY"
  elif yes(r.historical_snapshot):status="BACK_SNAPSHOT_NEEDS_IDENTITY_AND_EXECUTION_AUDIT"
  else:status="CLOSING_REFERENCE_ONLY"
  print("SOURCE",r["source"],"|",status,"|",r["provider"],"|",r["provenance_level"])
 print("NEXT_GATE: certify source-to-selection identity, actual quote side, time, availability, commission, and executable odds before profitability claims")
 print("NO_OUTCOME_ROWS_READ; NO_2025_2026_EVALUATION; NO_LIVE_BETTING")
if __name__=="__main__":main()
