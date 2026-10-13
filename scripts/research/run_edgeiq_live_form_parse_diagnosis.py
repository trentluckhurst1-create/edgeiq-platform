"""Diagnose actual live form value formats and feature loss, without scoring.

Read-only on sources; reports parsed margins, finish, distance and field sizes,
plus exact failing raw examples. Does not alter model or invent missing features.
"""
import argparse,json,re
from pathlib import Path
import pandas as pd
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--form",default=r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\caulfield_browser_form.csv")
 p.add_argument("--date",default="2026-10-14")
 p.add_argument("--output",default="outputs/research/selection_gate_v2/CAULFIELD_FORM_PARSING_DIAGNOSIS.json")
 a=p.parse_args()
 d=pd.read_csv(a.form,dtype="string",keep_default_na=False)
 fields=["horse_code","race_date","margin","finish","distance","field_size"]
 missing=[c for c in fields if c not in d.columns]
 if missing:raise RuntimeError("STOP missing form columns: "+",".join(missing))
 d=d[pd.to_datetime(d.race_date,errors="coerce").lt(pd.Timestamp(a.date))].copy()
 report={"rows":len(d),"columns":d.columns.tolist(),"fields":{}}
 for col in ["margin","finish","distance","field_size"]:
  raw=d[col].astype("string").str.strip()
  direct=pd.to_numeric(raw,errors="coerce")
  invalid=raw.ne("")&direct.isna()
  examples=raw[invalid].value_counts().head(25)
  report["fields"][col]={"nonblank":int(raw.ne("").sum()),"direct_numeric":int(direct.notna().sum()),"invalid_nonblank":int(invalid.sum()),"invalid_examples":[{"raw":str(k),"count":int(v)} for k,v in examples.items()],"valid_examples":raw[direct.notna()].head(8).tolist()}
 print("LIVE FORM PARSING DIAGNOSIS rows",len(d))
 for k,v in report["fields"].items():
  print(k,"nonblank",v["nonblank"],"numeric",v["direct_numeric"],"invalid",v["invalid_nonblank"])
  print(" INVALID_EXAMPLES",v["invalid_examples"][:12])
 out=Path(a.output)
 if out.exists():raise RuntimeError("STOP immutable output exists; use --output new path")
 out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("OUTPUT",out)
 print("READ_ONLY DIAGNOSTIC; NO MODEL SCORES")
if __name__=="__main__":main()
