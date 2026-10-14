"""EDGEiQ: read-only candidate population coverage for BACK WIN research.

Uses pre-existing 2022-2024 Stage011 predictions and LAB123 timestamped
price diagnostics. No joining by guesswork; no sealed 2025/26 rows.
Does not claim executable prices, or optimize thresholds.
"""
from pathlib import Path
import argparse
import pandas as pd
DEFAULT_ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research")
LAB123=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_123")
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--root",type=Path,default=DEFAULT_ROOT)
 ap.add_argument("--max-candidates",type=int,default=12)
 a=ap.parse_args()
 print("EDGEIQ BACK WIN — POPULATION FEASIBILITY (READ ONLY)")
 price=LAB123/"LAB123_RULE2_TIMESTAMPED_PRICES.csv"
 if not price.exists():raise FileNotFoundError(price)
 cols=["selection_id","canonical_race_id","canonical_horse_id","year","price_timestamp","race_start","decimal_price","available","provider","price_type","decision_cutoff","p_model","outcome"]
 header=pd.read_csv(price,nrows=0).columns.tolist()
 use=[c for c in cols if c in header]
 d=pd.read_csv(price,usecols=use)
 d["year"]=pd.to_numeric(d.year,errors="coerce")
 if d.year.isna().any() or (~d.year.isin([2022,2023,2024])).any():raise ValueError("STOP: unexpected years in LAB123 price rows")
 print("LAB123_ROWS",len(d),"YEARS",d.year.value_counts().sort_index().to_dict())
 print("PRICE_TYPE",d.price_type.astype(str).value_counts().head(12).to_dict())
 print("PROVIDERS",d.provider.astype(str).value_counts().head(12).to_dict())
 print("AVAILABLE",d.available.astype(str).value_counts().to_dict())
 for col in ["price_timestamp","race_start","decision_cutoff"]:
  if col in d:
   parsed=pd.to_datetime(d[col],errors="coerce",utc=True)
   print(col+"_PARSEABLE",int(parsed.notna().sum()))
 if {"price_timestamp","race_start","decimal_price"}.issubset(d):
  ts=pd.to_datetime(d.price_timestamp,errors="coerce",utc=True)
  start=pd.to_datetime(d.race_start,errors="coerce",utc=True)
  price_num=pd.to_numeric(d.decimal_price,errors="coerce")
  print("PREJUMP_POSITIVE_PRICE_ROWS",int((ts.notna()&start.notna()&(ts<start)&price_num.gt(1)).sum()))
 print("IDENTITY_KEYS",[(c,int(d[c].notna().sum()),int(d[c].nunique())) for c in ["canonical_race_id","canonical_horse_id","selection_id"] if c in d])
 # Discovery only: metadata of existing OOF prediction files, not target/outcome values.
 files=sorted(a.root.rglob("*OOF*PREDICTIONS*.csv"))
 print("OOF_CANDIDATE_FILES",len(files))
 for f in files[:a.max_candidates]:
  h=pd.read_csv(f,nrows=0).columns.tolist()
  print("OOF",str(f),"BYTES",f.stat().st_size,"KEY_COLUMNS",[x for x in h if x in ("_race","_horse","_year","p","p_model","raw","model_name","architecture","algorithm")])
 print("NO_JOIN_CERTIFICATION; NO_RETURNS; NO_STRATEGY_PROMOTION; NO_2025_2026_OUTCOMES")
if __name__=="__main__":main()
