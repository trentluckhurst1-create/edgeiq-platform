"""Read-only inventory of candidate field-size sources; never impute field sizes.
The historical warehouse field_size is empty for current linked horses.
"""
import argparse
from pathlib import Path
import pandas as pd

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--warehouse",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_WAREHOUSE_RUNNER_LVS.csv")
 ap.add_argument("--live-form",default=r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\caulfield_browser_form.csv")
 ap.add_argument("--stage006",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage006\V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv")
 a=ap.parse_args()
 for name,path in [("WAREHOUSE",a.warehouse),("LIVE_FORM",a.live_form),("STAGE006",a.stage006)]:
  f=Path(path)
  if not f.is_file():
   print(name,"MISSING_FILE",f)
   continue
  cols=pd.read_csv(f,nrows=0).columns.tolist()
  candidates=[c for c in cols if any(k in c.casefold() for k in ["field","runner","race","horse","date","margin"])]
  print("\nSOURCE",name,"ROWS_COLUMNS",len(cols))
  print("CANDIDATE_COLUMNS",candidates)
  use=[c for c in candidates if any(k in c.casefold() for k in ["field_size","represented_field_size","runner_count","number_of_runners","runners"])]
  if not use:
   print("NO_DIRECT_FIELD_SIZE_COLUMN")
   continue
  df=pd.read_csv(f,usecols=use,low_memory=False)
  for c in use:
   v=pd.to_numeric(df[c],errors="coerce")
   print("FIELD",c,"NON_NULL",int(df[c].notna().sum()),"POSITIVE_NUMERIC",int(v.gt(0).sum()),"UNIQUE_POSITIVE",int(v[v.gt(0)].nunique()))
 print("\nNO_FIELD_SIZE_VALUES_IMPUTED; inspect source identity and Stage011 denominator before joins")
if __name__=="__main__":main()
