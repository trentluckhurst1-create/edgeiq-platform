"""Test Stage006 margin-per-runner denominator hypotheses, read-only.
Never fills or scores live features. Report evidence before choosing a formula.
"""
import argparse
import numpy as np
import pandas as pd

def main():
 a=argparse.ArgumentParser()
 a.add_argument("--stage006",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage006\V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv")
 a=a.parse_args()
 cols=["represented_field_size","margin_last1","margin_last2","margin_per_runner_last1","margin_per_runner_last2"]
 d=pd.read_csv(a.stage006,usecols=cols,low_memory=False)
 for c in cols:d[c]=pd.to_numeric(d[c],errors="coerce")
 print("STAGE006_ROWS",len(d))
 print("FIELD_SIZE_NON_NULL",int(d.represented_field_size.notna().sum()))
 for i in (1,2):
  margin=d[f"margin_last{i}"]
  actual=d[f"margin_per_runner_last{i}"]
  print("\nLAST",i,"MARGIN_AVAILABLE",int(margin.notna().sum()),"TARGET_AVAILABLE",int(actual.notna().sum()))
  for denom_name,denom in [("CURRENT_FIELD_SIZE",d.represented_field_size),("CURRENT_FIELD_SIZE_MINUS_ONE",d.represented_field_size-1)]:
   valid=margin.notna()&actual.notna()&denom.gt(0)
   if not valid.any():
    print(denom_name,"NO_COMPARABLE_ROWS")
    continue
   err=np.abs((margin[valid]/denom[valid]).to_numpy()-actual[valid].to_numpy())
   print(denom_name,"N",int(valid.sum()),"EXACT_1E9",int((err<1e-9).sum()),"MAX_ERROR",float(err.max()),"MEAN_ERROR",float(err.mean()))
 print("\nNO_FORMULA_CERTIFIED_WITHOUT_FULL_PARITY; historical field size may refer to current rather than prior race")
if __name__=="__main__":main()
