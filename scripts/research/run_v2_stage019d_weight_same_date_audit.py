from pathlib import Path
import pandas as pd
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
A=P/"outputs"/"research"/"model_lab_045a"/"weight_features_045a.csv"
U=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage004\V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv")
print("V2_STAGE019D_CONTRACT LAB045A_SAME_DATE_PIT_AUDIT NO_MODEL 2025_2026_SEALED")
a=pd.read_csv(A,usecols=["canonical_race_id","canonical_horse_id","race_date","previous_start_weight","prior_recent_weight_average","change_from_recent_average"])
a["race_date"]=pd.to_datetime(a.race_date,errors="coerce").dt.strftime("%Y-%m-%d")
cnt=a.groupby(["canonical_horse_id","race_date"]).size()
bad=cnt[cnt>1]
print("V2_STAGE019D_SAME_DATE_HORSE_DATES",len(bad),"ROWS",int(bad.sum()),"MAX",int(bad.max()) if len(bad) else 0)
u=pd.read_csv(U)
if "canonical_race_id" not in u and "_race" in u:u["canonical_race_id"]=u["_race"]
if "canonical_horse_id" not in u and "_horse" in u:u["canonical_horse_id"]=u["_horse"]
u["race_date"]=pd.to_datetime(u.race_date,errors="coerce").dt.strftime("%Y-%m-%d")
k=a.merge(u[["canonical_race_id","canonical_horse_id","race_date"]],on=["canonical_race_id","canonical_horse_id","race_date"],how="inner")
kc=k.groupby(["canonical_horse_id","race_date"]).size()
kb=kc[kc>1]
print("V2_STAGE019D_V2_SAME_DATE_HORSE_DATES",len(kb),"ROWS",int(kb.sum()),"MAX",int(kb.max()) if len(kb) else 0)
print("V2_STAGE019D_COMPLETE")
