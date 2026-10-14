"""Issue23: populate only independently verifiable declaration features.

This is a guarded intermediate builder, not an authority to score.
Reads only live field identities and scaffold, never outcome/market files.
"""
from pathlib import Path
import pandas as pd
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
BASE=R/"outputs/research/model_v2/issue23_live_features/ISSUE23_FIVE_RACE_FEATURE_SCAFFOLD.csv"
LIVE=P/"outputs/research/live_acquisition_v1/october_graphql_field_identities.csv"
OUT=R/"outputs/research/model_v2/issue23_live_features/ISSUE23_DECLARATION_FEATURES_V1.csv"
def main():
 a=pd.read_csv(BASE,dtype={"race_id":"string","runner_id":"string"})
 b=pd.read_csv(LIVE,usecols=["race_date","race_id","race_entry_id","barrier","scratched","emergency"],dtype={"race_id":"string","race_entry_id":"string"})
 if a.empty or a.duplicated(["race_date","race_id","runner_id"]).any():raise RuntimeError("STOP scaffold identities")
 if b.duplicated(["race_date","race_id","race_entry_id"]).any():raise RuntimeError("STOP duplicate live entries")
 b=b.rename(columns={"race_entry_id":"runner_id"})
 d=a.merge(b,on=["race_date","race_id","runner_id"],how="left",validate="one_to_one",indicator=True)
 if not d._merge.eq("both").all():raise RuntimeError("STOP incomplete declaration join")
 for col in ("scratched","emergency"):
  values=d[col].astype("string").str.lower()
  if not values.isin(["true","false","0","1"]).all():raise RuntimeError("STOP unknown "+col+" status")
  d[col]=values.isin(["true","1"])
 # All declared runners retained for field-size denominator; do not silently
 # remove scratched/emergency runners without a certified effective-field rule.
 d["declared_runner_count"]=d.groupby(["race_date","race_id"]).runner_id.transform("size")
 d["barrier_numeric"]=pd.to_numeric(d.barrier,errors="coerce")
 if (d.barrier_numeric.dropna()<=0).any():raise RuntimeError("STOP invalid barrier")
 d["active_status_confirmed"]=(~d.scratched)&(~d.emergency)
 # No race-distance source yet; current_distance remains unavailable.
 # No governed barrier percentile convention; preserve raw barrier only.
 d["feature_status"]="DECLARATION_JOIN_ONLY_DO_NOT_SCORE"
 d=d.drop(columns=["_merge"])
 OUT.parent.mkdir(parents=True,exist_ok=True)
 if OUT.exists():raise RuntimeError("STOP immutable output exists")
 d.to_csv(OUT,index=False)
 print("ISSUE23 DECLARATION JOIN")
 print("ROWS",len(d),"RACES",d[["race_date","race_id"]].drop_duplicates().shape[0])
 print("ACTIVE_NONEMERGENCY",int(d.active_status_confirmed.sum()),"SCRATCHED",int(d.scratched.sum()),"EMERGENCY",int(d.emergency.sum()))
 print("BARRIER_PRESENT",int(d.barrier_numeric.notna().sum()))
 print("CERTIFIED_STAGE011_FEATURES",0)
 print("OUTPUT",OUT)
 print("NO_OUTCOMES; NO_MARKET; NOT_SCOREABLE")
if __name__=="__main__":main()
