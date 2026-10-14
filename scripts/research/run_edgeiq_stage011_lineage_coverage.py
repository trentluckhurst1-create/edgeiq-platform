"""Read-only Stage011 source lineage and target identity coverage.

This diagnoses exact historical bridge availability; it never scores or certifies.
"""
from pathlib import Path
import argparse,json
import pandas as pd
ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
LIVE=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1")
SOURCES={
 "lab245b_compact":ROOT/"outputs/research/profitability_program/lab245b/LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv",
 "lab245b_runner_lvs":ROOT/"outputs/research/profitability_program/lab245b/LAB245B_WAREHOUSE_RUNNER_LVS.csv",
 "certified_context":ROOT/"outputs/research/model_lab_031/certified_current_race_context_031.csv",
 "perf026":ROOT/"outputs/research/model_lab_026/edgeiq_certified_flat_walk_forward_epi_026.csv",
}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--date",default="2026-10-14")
 p.add_argument("--venue",default="Caulfield")
 a=p.parse_args()
 d=pd.read_csv(LIVE/"october_graphql_field_identities.csv",dtype="string")
 d=d[d.race_date.eq(a.date)&d.venue.str.casefold().eq(a.venue.casefold())].copy()
 print("EDGEIQ HISTORICAL LINEAGE CHECK",a.date,a.venue,"TARGET_RUNNERS",len(d))
 print("LIVE_IDENTITY_COLUMNS",",".join(d.columns))
 for label,path in SOURCES.items():
  print("SOURCE",label,"EXISTS",path.exists(),"PATH",path)
  if not path.exists():continue
  cols=pd.read_csv(path,nrows=0).columns.tolist()
  print("SOURCE_COLUMNS",label,",".join(cols))
  keys=[x for x in ["canonical_horse_id","horse_code","race_date","runner_lvs","canonical_jockey_id","canonical_trainer_id","finish_position","finish_margin"] if x in cols]
  print("RELEVANT_FIELDS",label,",".join(keys))
  if "canonical_horse_id" not in cols:continue
  # Chunked scan: avoid loading multi-million row files into RAM.
  matches=set()
  observed=set()
  target_codes=set(d.horse_code.dropna().astype(str).str.strip().str.upper())
  for chunk in pd.read_csv(path,usecols=["canonical_horse_id"],dtype="string",chunksize=250000):
   vals=set(chunk.canonical_horse_id.dropna().str.strip().str.upper())
   matches.update(vals & target_codes)
   if len(matches)==len(target_codes):break
  print("DIRECT_HORSE_CODE_MATCHES_UNVALIDATED",len(matches),"OF",len(target_codes))
  print("NOTE direct string equality is NOT a certified canonical identity crosswalk")
 print("NEXT_REQUIREMENT exact canonical horse/jockey/trainer crosswalk and strict pre-target-date joins")
 print("NO_OUTCOMES_EXPORTED; NO_MODEL_SCORING; NO_CERTIFICATION; NO_BETTING")
if __name__=="__main__":main()
