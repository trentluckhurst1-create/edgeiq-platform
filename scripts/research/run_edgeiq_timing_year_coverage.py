"""Read-only temporal coverage of original timing benchmark and runner LVS.

This is source readiness only. Never builds model features, joins live
horse identities, evaluates sealed outcomes or scores bets.
"""
from pathlib import Path
import argparse
import pandas as pd
def inspect(path,cols,cutoff):
 d=pd.read_csv(path,usecols=cols,dtype="string")
 dt=pd.to_datetime(d.race_date,errors="coerce")
 d=d.loc[dt.notna() & dt.lt(pd.Timestamp(cutoff))].copy()
 d["year"]=pd.to_datetime(d.race_date).dt.year
 print("FILE",path,"ROWS",len(d))
 for y,g in d.groupby("year",sort=True):
  metrics=[]
  for c in cols:
   if c=="race_date":continue
   v=pd.to_numeric(g[c],errors="coerce")
   metrics.append(f"{c}={int(v.notna().sum())}/{len(g)}")
  print("YEAR",y,"ROWS",len(g)," ".join(metrics))
 return d
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--root",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b")
 p.add_argument("--cutoff",default="2026-10-14")
 a=p.parse_args()
 root=Path(a.root)
 b=inspect(root/"LAB245B_STRICT_PIT_RACE_BENCHMARK_CHECKPOINT.csv",["race_date","official_race_time_seconds","standard_time_seconds","benchmark_n"],a.cutoff)
 w=inspect(root/"LAB245B_WAREHOUSE_RUNNER_LVS.csv",["race_date","runner_lvs","race_lvs","standard_time_seconds","seconds_per_length","benchmark_n"],a.cutoff)
 print("BENCHMARK_LATEST",b.race_date.max(),"RUNNER_LVS_LATEST",w.race_date.max())
 print("NO CURRENT-FORM LVS INFERRED; NO SEALED EVALUATION OR MODEL SCORES")
if __name__=="__main__":main()
