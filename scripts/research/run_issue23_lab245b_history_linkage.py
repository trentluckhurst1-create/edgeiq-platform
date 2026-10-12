"""Issue23: join current identities to historical LAB245B runner records through 2024.

The historical feature rows describe THEIR historical target races, not today's
race. They are lineage evidence only and are never copied into live features.
"""
from pathlib import Path
import pandas as pd
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
SRC=R/"outputs/research/model_v2/issue23_live_features/ISSUE23_BARRIER_DENOMINATOR_COMPARISON.csv"
BR=R/"outputs/research/profitability_program/lab245b/LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
OUT=R/"outputs/research/model_v2/issue23_live_features/ISSUE23_LAB245B_HISTORY_LINKAGE.csv"
def main():
 d=pd.read_csv(SRC,dtype={"canonical_horse_id":"string","race_id":"string","runner_id":"string"})
 if d.empty or d.duplicated(["race_date","race_id","runner_id"]).any():raise RuntimeError("STOP invalid live identities")
 # Only identity and date. No target outcome, SP, or 2025/26 historical feature rows loaded.
 h=pd.read_csv(BR,usecols=["_horse","_race","race_date"],dtype="string")
 h["race_date"]=pd.to_datetime(h.race_date,errors="coerce")
 h=h[h.race_date.dt.year.le(2024)].dropna(subset=["_horse","_race","race_date"])
 h=h[h._horse.isin(d.canonical_horse_id)]
 h=h.drop_duplicates(["_horse","_race"])
 stats=h.groupby("_horse").race_date.agg(historical_bridge_rows="size",last_bridge_date="max")
 d=d.join(stats,on="canonical_horse_id")
 d["historical_bridge_rows"]=d.historical_bridge_rows.fillna(0).astype(int)
 d["linkage_status"]=d.historical_bridge_rows.gt(0).map({True:"HISTORICAL_BRIDGE_LINKED",False:"NO_PRE2025_BRIDGE"})
 d["feature_status"]="HISTORY_LINKAGE_ONLY_DO_NOT_SCORE"
 if OUT.exists():raise RuntimeError("STOP immutable output exists")
 OUT.parent.mkdir(parents=True,exist_ok=True)
 d.to_csv(OUT,index=False)
 print("ISSUE23 LAB245B HISTORICAL LINKAGE")
 print("LIVE_RUNNERS",len(d),"RACES",d[['race_date','race_id']].drop_duplicates().shape[0])
 print(d.linkage_status.value_counts().to_string())
 print("HISTORICAL_BRIDGE_ROWS",len(h))
 print("OUTPUT",OUT)
 print("NO_HISTORICAL_TARGET_FEATURES_COPIED; NO_OUTCOMES; NO_MARKET; NOT_SCOREABLE")
if __name__=="__main__":main()
