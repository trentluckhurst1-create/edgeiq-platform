"""Issue23: exact numeric horse-code normalization; reject collisions, no name fallback."""
from pathlib import Path
from decimal import Decimal,InvalidOperation
import pandas as pd
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
L=P/"outputs/research/live_acquisition_v1/october_graphql_field_identities.csv"
C=P/"outputs/research/model_lab_075e/proven_horse_code_to_lab026_identity_075eb.csv"
O=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\issue23_live_identity")
def norm(v):
 if pd.isna(v):return None
 s=str(v).strip()
 try:
  d=Decimal(s)
  if not d.is_finite() or d!=d.to_integral_value() or d<0:return None
  return str(int(d))
 except (InvalidOperation,ValueError):return None
live=pd.read_csv(L,dtype="string")
cross=pd.read_csv(C,dtype="string")
live["code_normalized"]=live.horse_code.map(norm)
cross["code_normalized"]=cross.horse_code.map(norm)
valid=cross.dropna(subset=["code_normalized","canonical_horse_id"])
groups=valid.groupby("code_normalized").canonical_horse_id.agg(lambda s:sorted(set(s)))
collisions=groups[groups.map(len)>1]
unique=groups[groups.map(len)==1].map(lambda a:a[0])
live["canonical_horse_id"]=live.code_normalized.map(unique)
live["match_status"]="NOT_IN_HISTORICAL_CROSSWALK"
live.loc[live.code_normalized.isna(),"match_status"]="INVALID_CODE"
live.loc[live.code_normalized.isin(collisions.index),"match_status"]="CONFLICTING_NORMALIZED_CODE"
live.loc[live.canonical_horse_id.notna(),"match_status"]="UNIQUE_NORMALIZED_CODE"
dup=live.duplicated(["race_date","race_id","race_entry_id"],keep=False)
live.loc[dup,"match_status"]="DUPLICATE_RACE_ENTRY"
live.loc[dup,"canonical_horse_id"]=pd.NA
O.mkdir(parents=True,exist_ok=True)
out=O/"ISSUE23_NORMALIZED_CODE_AUDIT.csv"
if out.exists():raise RuntimeError("STOP output exists")
live.to_csv(out,index=False)
print("ISSUE23 NORMALIZED HORSE-CODE CROSSWALK")
print("LIVE_ROWS",len(live),"HISTORICAL_UNIQUE_CODES",len(unique),"COLLISIONS",len(collisions))
print(live.match_status.value_counts().to_string())
print("MATCHED_RACES",live.loc[live.match_status.eq("UNIQUE_NORMALIZED_CODE"),["race_date","race_id"]].drop_duplicates().shape[0])
print("OUTPUT",out)
print("RESEARCH_IDENTITY_CANDIDATES_ONLY; NO_SCORING; NO_OUTCOMES")
