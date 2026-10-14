"""Diagnose LAB123 timestamped price nonavailability by year/reason.

Reads price metadata only, no outcomes and no sealed evaluation.
"""
from pathlib import Path
import pandas as pd
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_123\LAB123_RULE2_TIMESTAMPED_PRICES.csv")
def main():
 cols=pd.read_csv(P,nrows=0).columns.tolist()
 wanted=["year","available","reason_unavailable","provider","price_type","decimal_price","price_timestamp","race_start","decision_timepoint","decision_cutoff","price_age_bucket"]
 d=pd.read_csv(P,usecols=[c for c in wanted if c in cols],dtype="string",low_memory=False)
 d=d.loc[d.year.isin(["2022","2023","2024"])].copy()
 print("EDGEIQ LAB123 PRICE FAILURE DIAGNOSTIC — 2022-2024 ONLY")
 print("ROWS",len(d))
 for c in ["reason_unavailable","price_age_bucket","decision_timepoint","price_type","provider","available"]:
  if c in d:print(c.upper(),d[c].fillna("<NULL>").value_counts().head(20).to_dict())
 for c in ["decimal_price","price_timestamp","race_start","decision_cutoff"]:
  if c in d:
   x=d[c].fillna("").str.strip()
   print("FIELD",c,"NONEMPTY",int(x.ne("").sum()),"EXAMPLES",x[x.ne("")].head(5).tolist())
 if "reason_unavailable" in d:
  print("YEAR_REASON_COUNTS")
  print(d.groupby(["year","reason_unavailable"],dropna=False).size().sort_values(ascending=False).head(30).to_string())
 print("NO_OUTCOME_COLUMNS_READ; NO_2025_2026; NO_EXECUTION_CLAIMS")
if __name__=="__main__":main()
