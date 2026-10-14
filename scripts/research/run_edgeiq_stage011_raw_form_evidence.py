"""Inspect prior-form evidence against the frozen Stage011 feature contract.

Read-only. Never substitutes form fields for Stage011 features or scores runners.
"""
import argparse,json
from pathlib import Path
import pandas as pd
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1")
ART=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\issue23_prospective_artifacts\ISSUE23_MODEL_ARTIFACT_MANIFEST.json")
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--date",default="2026-10-14")
 p.add_argument("--venue",default="Caulfield")
 a=p.parse_args()
 ids=pd.read_csv(ROOT/"october_graphql_field_identities.csv",dtype="string")
 ids=ids[ids.race_date.eq(a.date)&ids.venue.str.casefold().eq(a.venue.casefold())]
 manifest=json.loads(ART.read_text(encoding="utf-8-sig"))
 features=manifest["features"]
 print("EDGEIQ STAGE011 RAW FORM EVIDENCE — READ ONLY")
 print("TARGET",a.date,a.venue,"RUNNERS",len(ids),"RACES",ids.race_id.nunique(),"REQUIRED_FEATURES",len(features))
 print("MANIFEST_FEATURES",",".join(features))
 for name in ["caulfield_browser_form.csv","caulfield_browser_form_raw.json"]:
  path=ROOT/name
  print("SOURCE",name,"EXISTS",path.exists())
  if not path.exists():continue
  if path.suffix==".csv":
   frame=pd.read_csv(path,dtype="string",low_memory=False)
   print("FORM_CSV_ROWS",len(frame),"COLUMNS",",".join(frame.columns))
   print("DIRECT_FEATURE_COLUMN_OVERLAP",sorted(set(frame.columns)&set(features)))
   for c in ["horse_code","horse_name","race_date","date","isTrial","isJumpOut","margin","finish","raceDistance","raceCode"]:
    if c in frame:print("FORM_CSV_FIELD",c,"NONEMPTY",int(frame[c].notna().sum()),"UNIQUE",int(frame[c].nunique()))
  else:
   data=json.loads(path.read_text(encoding="utf-8-sig"))
   print("RAW_TYPE",type(data).__name__,"HORSES",len(data) if isinstance(data,dict) else "N/A")
   if isinstance(data,dict):
    samples=[(k,v) for k,v in data.items() if isinstance(v,list)]
    print("RAW_LIST_HORSES",len(samples),"TOTAL_FORM_ENTRIES",sum(len(v) for _,v in samples))
    entries=[e for _,v in samples for e in v if isinstance(e,dict)]
    print("RAW_ENTRY_KEYS",sorted({k for e in entries for k in e.keys()}))
    print("RAW_NESTED_RACE_KEYS",sorted({k for e in entries if isinstance(e.get("race"),dict) for k in e["race"]}))
    for c in ["isTrial","isJumpOut","finish","margin","raceDate","raceDistance","horseCode","raceCode","time"]:
     print("RAW_FIELD",c,"PRESENT",sum(e.get(c) is not None for e in entries))
    print("RAW_NONTRIAL_ENTRIES",sum(not e.get("isTrial") and not e.get("isJumpOut") for e in entries))
 print("BLOCKER: Stage011 LVS is a governed historical time-standard measure; raw finishing margins cannot replace it.")
 print("BLOCKER: Stage011 jockey/trainer prior rates, clean-finish fields, race timing and scratch governance need exact point-in-time reconstruction.")
 print("NO_FEATURE_CERTIFICATION; NO_SCORING; NO_OUTCOMES_READ; NO_BETTING")
if __name__=="__main__":main()
