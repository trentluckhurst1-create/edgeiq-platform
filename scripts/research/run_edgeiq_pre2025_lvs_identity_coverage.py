"""Assess actual pre-2025 LVS warehouse linkage to Issue23 live horses.

Read-only. Identity must match canonical_horse_id exactly; name-only candidate
matches are excluded. No scoring or post-2024 outcome use.
"""
from pathlib import Path
import argparse
import pandas as pd
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--warehouse",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_WAREHOUSE_RUNNER_LVS.csv")
 p.add_argument("--linkage",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\issue23_live_features\ISSUE23_LAB245B_HISTORY_LINKAGE.csv")
 p.add_argument("--date",default="2026-10-14")
 p.add_argument("--venue",default="Caulfield")
 a=p.parse_args()
 w=pd.read_csv(a.warehouse,dtype="string",usecols=["canonical_race_id","canonical_horse_id","race_date","runner_lvs"])
 l=pd.read_csv(a.linkage,dtype="string")
 l=l[l.race_date.eq(a.date)&l.venue.str.casefold().eq(a.venue.casefold())].copy()
 w=w[pd.to_datetime(w.race_date,errors="coerce").lt(pd.Timestamp("2025-01-01"))].copy()
 w["runner_lvs_num"]=pd.to_numeric(w.runner_lvs,errors="coerce")
 w=w[w.runner_lvs_num.notna()]
 print("WAREHOUSE_PRE2025_VALID_LVS_ROWS",len(w),"HORSES",w.canonical_horse_id.nunique())
 if w.duplicated(["canonical_race_id","canonical_horse_id"]).any():raise RuntimeError("STOP warehouse duplicate race/horse keys")
 if l.duplicated(["race_no","horse_name"]).any():raise RuntimeError("STOP duplicate live identity")
 by=w.groupby("canonical_horse_id").agg(pre2025_lvs_runs=("runner_lvs_num","size"),last_pre2025_lvs_date=("race_date","max"))
 result=l.join(by,on="canonical_horse_id")
 print("LIVE_LINKAGE_ROWS",len(result),"WITH_PRE2025_LVS",int(result.pre2025_lvs_runs.notna().sum()))
 print("LINKAGE_STATUS_BREAKDOWN")
 for status,g in result.groupby("linkage_status",dropna=False):
  print(status,"total",len(g),"with_lvs",int(g.pre2025_lvs_runs.notna().sum()))
 print("HORSE_LEVEL")
 for r in result[["race_no","horse_name","linkage_status","pre2025_lvs_runs","last_pre2025_lvs_date"]].itertuples(index=False):
  print(r.race_no,r.horse_name,r.linkage_status,"LVS_RUNS",r.pre2025_lvs_runs,"LAST",r.last_pre2025_lvs_date)
 print("HISTORICAL COVERAGE IS NOT CURRENT FORM; NO FEATURES OR PROBABILITIES GENERATED")
if __name__=="__main__":main()
