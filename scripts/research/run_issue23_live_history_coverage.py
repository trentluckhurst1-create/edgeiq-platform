"""Issue23: certify identity and historical coverage for complete live race fields.

No model scoring, no results or market columns read.
"""
from pathlib import Path
import pandas as pd
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
AUD=R/"outputs/research/model_v2/issue23_live_identity/ISSUE23_NORMALIZED_CODE_AUDIT.csv"
H=R/"outputs/research/profitability_program/lab245b/LAB245B_WAREHOUSE_RUNNER_LVS.csv"
OUT=R/"outputs/research/model_v2/issue23_live_identity"
if not AUD.exists() or not H.exists():raise RuntimeError("STOP missing audit or history")
live=pd.read_csv(AUD,dtype={"canonical_horse_id":"string","horse_code":"string","race_id":"string"})
live["race_date"]=pd.to_datetime(live.race_date,errors="raise")
if live.duplicated(["race_date","race_id","race_entry_id"]).any():raise RuntimeError("STOP duplicate live race entries")
hist=pd.read_csv(H,usecols=["canonical_horse_id","race_date"],dtype={"canonical_horse_id":"string"})
hist["race_date"]=pd.to_datetime(hist.race_date,errors="coerce")
hist=hist.dropna(subset=["canonical_horse_id","race_date"]).drop_duplicates()
# Historical source may include 2025-26 outcomes: NEVER inspect or use those rows.
hist=hist[hist.race_date.dt.year<=2024]
last=hist.groupby("canonical_horse_id").race_date.agg(["count","max"]).rename(columns={"count":"historical_rows_through_2024","max":"latest_history_through_2024"})
live=live.join(last,on="canonical_horse_id")
live["historical_rows_through_2024"]=live.historical_rows_through_2024.fillna(0).astype(int)
live["coverage_status"]="UNMATCHED_IDENTITY"
ok=live.match_status.eq("UNIQUE_NORMALIZED_CODE")
live.loc[ok,"coverage_status"]="MATCHED_NO_PRE2025_HISTORY"
live.loc[ok & live.historical_rows_through_2024.gt(0),"coverage_status"]="MATCHED_WITH_PRE2025_HISTORY"
live.loc[live.race_date.dt.year<=2024,"coverage_status"]="STOP_NOT_PROSPECTIVE"
g=live.groupby(["race_date","race_id"],dropna=False)
race=g.agg(runners=("race_entry_id","size"),identified=("match_status",lambda x:int(x.eq("UNIQUE_NORMALIZED_CODE").sum())),with_history=("coverage_status",lambda x:int(x.eq("MATCHED_WITH_PRE2025_HISTORY").sum())),venue=("venue","first"),race_no=("race_no","first")).reset_index()
race["complete_identity"]=race.runners.eq(race.identified)
race["complete_pre2025_history"]=race.runners.eq(race.with_history)
out1=OUT/"ISSUE23_LIVE_HISTORY_COVERAGE.csv";out2=OUT/"ISSUE23_RACE_COMPLETENESS.csv"
if out1.exists() or out2.exists():raise RuntimeError("STOP outputs exist")
live.to_csv(out1,index=False);race.to_csv(out2,index=False)
print("LIVE_ROWS",len(live),"RACES",len(race))
print(live.coverage_status.value_counts().to_string())
print("FULL_IDENTITY_RACES",int(race.complete_identity.sum()),"FULL_PRE2025_HISTORY_RACES",int(race.complete_pre2025_history.sum()))
print(race[["race_date","venue","race_no","runners","identified","with_history","complete_identity"]].to_string(index=False))
print("OUTPUTS",out1,out2)
print("READ_ONLY_SOURCE; RESEARCH_ONLY; 2025_2026_HISTORY_EXCLUDED; NO_SCORING")
