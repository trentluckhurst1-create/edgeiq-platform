"""Read-only first-meeting source check, replacing interrupted Codex investigation.

No outcomes read, no market quotes certified, no betting.
"""
from pathlib import Path
import argparse, json
import pandas as pd

ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1")
ART=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\issue23_prospective_artifacts")
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--meeting-date",default="2026-10-14")
 p.add_argument("--venue",default="Caulfield")
 a=p.parse_args()
 print("EDGEIQ FIRST MEETING SOURCE CHECK — READ ONLY")
 print("MEETING",a.meeting_date,a.venue)
 paths={"field_identities":ROOT/"october_graphql_field_identities.csv",
        "browser_prior_form":ROOT/"caulfield_browser_form.csv",
        "raw_prior_form":ROOT/"caulfield_browser_form_raw.json",
        "artifact_manifest":ART/"ISSUE23_MODEL_ARTIFACT_MANIFEST.json",
        "stage011_artifact":ART/"ISSUE23_STAGE011_TRAIN_THROUGH_2024.joblib"}
 for label,f in paths.items():
  print("SOURCE",label,"EXISTS",f.exists(),"BYTES",f.stat().st_size if f.exists() else 0)
 f=paths["field_identities"]
 if f.exists():
  d=pd.read_csv(f,dtype="string",low_memory=False)
  needed={"race_date","venue","race_no","race_id","horse_code","horse_name"}
  if not needed.issubset(d.columns):print("BLOCKER IDENTITY_COLUMNS_MISSING",sorted(needed-set(d.columns)))
  else:
   m=d.loc[d.race_date.eq(a.meeting_date)&d.venue.str.casefold().eq(a.venue.casefold())]
   print("MATCHED_RUNNER_IDENTITIES",len(m),"RACES",m.race_id.nunique(),"BY_RACE",m.groupby("race_no").size().to_dict())
   for col in ["horse_code","race_id","race_entry_id","jockey_code","trainer_code","barrier"]:
    if col in m:print("FIELD",col,"NONEMPTY",int(m[col].notna().sum()),"UNIQUE",int(m[col].nunique()))
   if m.empty:print("BLOCKER NO_MEETING_IDENTITIES")
 if paths["artifact_manifest"].exists():
  data=json.loads(paths["artifact_manifest"].read_text(encoding="utf-8-sig"))
  print("MANIFEST_KEYS",sorted(data.keys()))
 print("BLOCKER NO_CERTIFIED_35_FEATURE_STAGE011_MATRIX_UNLESS_INDEPENDENTLY_VERIFIED")
 print("BLOCKER NO_CERTIFIED_EXECUTABLE_QUOTE_DEPTH_UNLESS_INDEPENDENTLY_VERIFIED")
 print("NO_SCORING; NO_OUTCOMES; NO_EXECUTION; NO_PROFITABILITY_CLAIM")
if __name__=="__main__":main()
