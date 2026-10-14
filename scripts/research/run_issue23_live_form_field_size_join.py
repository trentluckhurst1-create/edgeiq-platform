"""Research-only exact race/date/horse linkage of Racing.com field sizes.
Never match horse names alone; never write to model feature matrices.
"""
import argparse
from pathlib import Path
import pandas as pd

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--form",default=r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\caulfield_browser_form.csv")
 ap.add_argument("--warehouse",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_WAREHOUSE_RUNNER_LVS.csv")
 ap.add_argument("--out",default=r"C:\EDGEIQ_ISSUE23\outputs\research\ISSUE23_RACINGCOM_FIELD_SIZE_EXACT_JOIN_V1.csv")
 a=ap.parse_args()
 f=pd.read_csv(a.form,dtype="string")
 w=pd.read_csv(a.warehouse,dtype="string")
 required_f={"horse_code","race_date","race_code","field_size","finish","margin"}
 required_w={"canonical_horse_id","canonical_race_id","race_date","finish_position","finish_margin"}
 if not required_f.issubset(f.columns) or not required_w.issubset(w.columns):raise RuntimeError("STOP source schema changed")
 for c in ("horse_code","race_code","race_date"):f[c]=f[c].str.strip()
 for c in ("canonical_horse_id","canonical_race_id","race_date"):w[c]=w[c].str.strip()
 f["field_num"]=pd.to_numeric(f.field_size,errors="coerce")
 f["finish_num"]=pd.to_numeric(f.finish,errors="coerce")
 f["margin_num"]=pd.to_numeric(f.margin,errors="coerce")
 w["finish_num"]=pd.to_numeric(w.finish_position,errors="coerce")
 w["margin_num"]=pd.to_numeric(w.finish_margin,errors="coerce")
 print("FORM_ROWS",len(f),"WAREHOUSE_ROWS",len(w))
 print("FORM_HORSE_CODE_PREFIXES",f.horse_code.dropna().str.extract(r"^([^_]+)")[0].value_counts().head(10).to_dict())
 print("WAREHOUSE_HORSE_ID_PREFIXES",w.canonical_horse_id.dropna().str.extract(r"^([^_]+)")[0].value_counts().head(10).to_dict())
 print("FORM_RACE_CODE_EXAMPLES",f.race_code.dropna().head(3).tolist())
 print("WAREHOUSE_RACE_ID_EXAMPLES",w.canonical_race_id.dropna().head(3).tolist())
 # Exact namespace equality is a necessary condition, not a sufficient one.
 candidates=f.merge(w,left_on=["horse_code","race_code","race_date"],right_on=["canonical_horse_id","canonical_race_id","race_date"],how="inner",suffixes=("_form","_warehouse"))
 print("EXACT_THREE_KEY_MATCHES",len(candidates))
 if candidates.empty:
  print("STOP NO_EXACT_IDENTITY_MATCH; requires independently certified crosswalk, not name matching")
  return
 if candidates.duplicated(["horse_code","race_code","race_date"]).any() or candidates.duplicated(["canonical_horse_id","canonical_race_id","race_date"]).any():
  raise RuntimeError("STOP ambiguous race identity")
 candidates=candidates[candidates.field_num.gt(0)&candidates.finish_num_form.eq(candidates.finish_num_warehouse)].copy()
 candidates["margin_agrees"]=((candidates.margin_num_form-candidates.margin_num_warehouse).abs()<1e-6)
 print("FINISH_CONFIRMED_AND_FIELD_SIZE_VALID",len(candidates))
 print("MARGIN_AGREEMENT",int(candidates.margin_agrees.sum()))
 if not candidates.margin_agrees.all():raise RuntimeError("STOP source margin disagreement; no output")
 if candidates.empty:raise RuntimeError("STOP no verified race outcomes")
 candidates["margin_per_runner"]=candidates.margin_num_warehouse/candidates.field_num.sub(1).clip(lower=1)
 target=Path(a.out)
 if target.exists():raise RuntimeError("STOP immutable output exists")
 target.parent.mkdir(parents=True,exist_ok=True)
 candidates[["canonical_horse_id","canonical_race_id","race_date","field_num","margin_per_runner"]].to_csv(target,index=False)
 print("OUTPUT",target,"ROWS",len(candidates),"RESEARCH_ONLY_DO_NOT_SCORE")
if __name__=="__main__":main()
