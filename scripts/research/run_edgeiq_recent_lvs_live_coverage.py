"""Read-only exact-ID prospective LVS coverage for Issue23 live runners.

Uses already-governed runner LVS; refuses ambiguous identity mappings.
Never trains, scores, or inspects race outcomes for model evaluation.
"""
import argparse
from pathlib import Path
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
 if l.duplicated(["race_no","horse_name"]).any():raise RuntimeError("STOP duplicate live identity")
 w["dt"]=pd.to_datetime(w.race_date,errors="coerce")
 w["lvs"]=pd.to_numeric(w.runner_lvs,errors="coerce")
 w=w[w.dt.notna()&w.dt.lt(pd.Timestamp(a.date))&w.lvs.notna()].copy()
 if w.duplicated(["canonical_race_id","canonical_horse_id"]).any():raise RuntimeError("STOP duplicate canonical race/horse")
 by=w.groupby("canonical_horse_id").agg(lvs_runs=("lvs","size"),last_lvs=("dt","max"),post2024_runs=("dt",lambda s:int((s>=pd.Timestamp("2025-01-01")).sum())))
 d=l.join(by,on="canonical_horse_id")
 print("EXACT_ID_LIVE_ROWS",len(d),"WITH_ANY_LVS",int(d.lvs_runs.notna().sum()),"WITH_2025_2026_LVS",int(d.post2024_runs.fillna(0).gt(0).sum()))
 print("LATEST_LVS_DATE",w.dt.max().date())
 for r in d[["race_no","horse_name","linkage_status","lvs_runs","post2024_runs","last_lvs"]].itertuples(index=False):
  print(r.race_no,r.horse_name,r.linkage_status,"RUNS",r.lvs_runs,"RECENT",r.post2024_runs,"LAST",r.last_lvs)
 print("EXACT-ID COVERAGE ONLY; NO PROBABILITIES, NO MODEL TRAINING, NO BETS")
if __name__=="__main__":main()
