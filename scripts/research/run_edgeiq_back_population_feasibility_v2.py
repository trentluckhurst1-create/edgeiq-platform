"""EDGEiQ historical BACK price feasibility, read-only, with explicit year exclusions.

Only 2022-2024 records are eligible for reporting. Later, missing and malformed
years are counted but excluded. No outcome columns are read.
"""
from pathlib import Path
import argparse
import pandas as pd

DEFAULT_ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research")
LAB123=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_123")
ALLOWED_YEARS={2022,2023,2024}

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--root",type=Path,default=DEFAULT_ROOT)
 ap.add_argument("--max-candidates",type=int,default=12)
 args=ap.parse_args()
 path=LAB123/"LAB123_RULE2_TIMESTAMPED_PRICES.csv"
 if not path.exists():raise FileNotFoundError(path)
 header=pd.read_csv(path,nrows=0).columns.tolist()
 wanted=["selection_id","canonical_race_id","canonical_horse_id","year","price_timestamp","race_start","decimal_price","available","provider","price_type","decision_cutoff"]
 use=[c for c in wanted if c in header]
 if "year" not in use:raise ValueError("STOP: year column absent")
 d=pd.read_csv(path,usecols=use,dtype="string",low_memory=False)
 raw=d["year"].str.strip()
 numeric=pd.to_numeric(raw,errors="coerce")
 valid=numeric.isin(ALLOWED_YEARS)
 invalid_missing=raw.isna()|raw.eq("")
 invalid_other=(~valid)&(~invalid_missing)
 print("EDGEIQ BACK WIN — HISTORICAL PRICE FEASIBILITY (READ ONLY)")
 print("INPUT_ROWS",len(d))
 print("YEAR_COUNTS",raw.fillna("<missing>").value_counts().head(20).to_dict())
 print("ELIGIBLE_2022_2024",int(valid.sum()))
 print("EXCLUDED_MISSING_YEAR",int(invalid_missing.sum()))
 print("EXCLUDED_OTHER_YEAR_OR_INVALID",int(invalid_other.sum()))
 d=d.loc[valid].copy()
 if d.empty:
  print("STOP: ZERO ELIGIBLE ROWS; NO POPULATION TO ANALYZE")
  return
 print("ELIGIBLE_BY_YEAR",numeric.loc[valid].astype(int).value_counts().sort_index().to_dict())
 for c in ["price_type","provider","available"]:
  if c in d:print(c.upper(),d[c].fillna("<missing>").value_counts().head(12).to_dict())
 for c in ["price_timestamp","race_start","decision_cutoff"]:
  if c in d:
   ts=pd.to_datetime(d[c],errors="coerce",utc=True)
   print(c.upper()+"_PARSEABLE",int(ts.notna().sum()))
 if {"price_timestamp","race_start","decimal_price"}.issubset(d.columns):
  ts=pd.to_datetime(d.price_timestamp,errors="coerce",utc=True)
  start=pd.to_datetime(d.race_start,errors="coerce",utc=True)
  price=pd.to_numeric(d.decimal_price,errors="coerce")
  print("PREJUMP_POSITIVE_PRICE_ROWS",int((ts.notna()&start.notna()&(ts<start)&price.gt(1)).sum()))
 for c in ["canonical_race_id","canonical_horse_id","selection_id"]:
  if c in d:print("IDENTITY",c,"NONNULL",int(d[c].notna().sum()),"UNIQUE",int(d[c].nunique()))
 files=sorted(args.root.rglob("*OOF*PREDICTIONS*.csv")) if args.root.exists() else []
 print("OOF_CANDIDATE_FILES",len(files))
 for f in files[:args.max_candidates]:
  h=pd.read_csv(f,nrows=0).columns.tolist()
  print("OOF",str(f),"BYTES",f.stat().st_size,"KEY_COLUMNS",[x for x in h if x in ("_race","_horse","_year","p","p_model","raw","model_name","architecture","algorithm")])
 print("NO_OUTCOME_COLUMNS_READ; NO_JOIN_CERTIFICATION; NO_RETURNS; NO_2025_2026_EVALUATION")
if __name__=="__main__":main()
