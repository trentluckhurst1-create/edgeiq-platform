"""Read-only assessment of the existing Issue23 historical linkage.

No rescoring, inferred joins, outcome access, or production changes.
"""
from pathlib import Path
import argparse
import pandas as pd

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--linkage",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\issue23_live_features\ISSUE23_LAB245B_HISTORY_LINKAGE.csv")
 p.add_argument("--candidates",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\live_identity_audit\LIVE_HORSE_IDENTITY_CANDIDATES.csv")
 p.add_argument("--manifest",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\issue23_prospective_artifacts\ISSUE23_MODEL_ARTIFACT_MANIFEST.json")
 p.add_argument("--date",default="2026-10-14")
 p.add_argument("--venue",default="Caulfield")
 a=p.parse_args()
 import json
 m=json.loads(Path(a.manifest).read_text(encoding="utf-8"))
 features=m["features"]
 d=pd.read_csv(a.linkage,dtype="string")
 for k in ["race_date","venue","race_no","horse_name","canonical_horse_id","linkage_status"]:
  if k not in d:raise RuntimeError("STOP missing "+k)
 d=d[d.race_date.eq(a.date)&d.venue.str.casefold().eq(a.venue.casefold())].copy()
 print("ISSUE23 EXISTING LINKAGE","rows",len(d),"races",d.race_no.nunique())
 for col in ["linkage_status","feature_status","status","active_status_confirmed","scratch_status"]:
  if col in d:print(col,d[col].fillna("<MISSING>").value_counts(dropna=False).to_dict())
 print("CANONICAL_IDS",d.canonical_horse_id.notna().sum(),"UNIQUE",d.canonical_horse_id.nunique())
 if d.duplicated(["race_no","horse_name"]).any():raise RuntimeError("STOP duplicate race/horse identity")
 print("FEATURE COVERAGE")
 complete=pd.Series(True,index=d.index)
 for f in features:
  v=pd.to_numeric(d[f],errors="coerce") if f in d else pd.Series(float("nan"),index=d.index)
  complete &= v.notna()
  print(f,"populated",int(v.notna().sum()),"/",len(d))
 print("COMPLETE_FEATURE_ROWS",int(complete.sum()),"/",len(d))
 c=pd.read_csv(a.candidates,dtype="string")
 c=c[c.race_date.eq(a.date)&c.venue.str.casefold().eq(a.venue.casefold())]
 print("IDENTITY_CANDIDATES",len(c))
 if "match_status" in c:print("MATCH_STATUS",c.match_status.fillna("<MISSING>").value_counts().to_dict())
 print("UNLINKED_LIVE_HORSES")
 for r in d[d.canonical_horse_id.isna()][["race_no","horse_name","linkage_status"]].itertuples(index=False):
  print(r.race_no,r.horse_name,r.linkage_status)
 print("READ ONLY; NO PROBABILITIES OR BETS")
if __name__=="__main__":main()
