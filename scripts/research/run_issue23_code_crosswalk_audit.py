"""Issue23: deterministic horse-code identity certification, no fuzzy-name fallback."""
from pathlib import Path
import pandas as pd
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
L=P/"outputs/research/live_acquisition_v1/october_graphql_field_identities.csv"
C=P/"outputs/research/model_lab_075e/proven_horse_code_to_lab026_identity_075eb.csv"
OUT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\issue23_live_identity")
if not L.exists() or not C.exists():raise RuntimeError("STOP missing GraphQL identities or certified crosswalk")
live=pd.read_csv(L,dtype={"horse_code":"string","eiq_horse_id":"string","race_id":"string","race_entry_id":"string"})
cross=pd.read_csv(C,dtype={"horse_code":"string","canonical_horse_id":"string"})
required_live={"race_date","race_id","race_entry_id","horse_code","eiq_horse_id"}
if not required_live.issubset(live):raise RuntimeError("STOP missing live columns")
if not {"horse_code","canonical_horse_id"}.issubset(cross):raise RuntimeError("STOP missing crosswalk columns")
for d in (live,cross):
 d["horse_code"]=d["horse_code"].str.strip()
cross=cross.dropna(subset=["horse_code","canonical_horse_id"])
cross=cross[cross.horse_code.ne("")]
grp=cross.groupby("horse_code").canonical_horse_id.agg(lambda x:sorted(set(x.dropna())))
conflicting=set(grp[grp.map(len)>1].index)
mapping=grp[grp.map(len)==1].map(lambda x:x[0]).to_dict()
live["canonical_horse_id"]=live.horse_code.map(mapping)
live["identity_status"]="CODE_NOT_IN_CROSSWALK"
live.loc[live.horse_code.isin(conflicting),"identity_status"]="CONFLICTING_CODE_MAPPING"
live.loc[live.canonical_horse_id.notna(),"identity_status"]="UNIQUE_CODE_CROSSWALK"
dup=live.duplicated(["race_date","race_id","race_entry_id"],keep=False)
live.loc[dup,"identity_status"]="DUPLICATE_RACE_ENTRY"
live.loc[dup,"canonical_horse_id"]=pd.NA
missing=live[["race_date","race_id","race_entry_id","horse_code","eiq_horse_id"]].isna().any(axis=1)
live.loc[missing,"identity_status"]="MISSING_LIVE_IDENTITY"
live.loc[missing,"canonical_horse_id"]=pd.NA
# A direct code crosswalk establishes candidate identity, not historical availability or PIT eligibility.
OUT.mkdir(parents=True,exist_ok=True)
target=OUT/"ISSUE23_GRAPHQL_CODE_IDENTITY_AUDIT.csv"
if target.exists():raise RuntimeError("STOP audit output exists; refusing overwrite")
live.to_csv(target,index=False)
print("ISSUE23 DETERMINISTIC CODE CROSSWALK")
print("LIVE_ROWS="+str(len(live))+" RACES="+str(live[["race_date","race_id"]].drop_duplicates().shape[0]))
print("CROSSWALK_CODES="+str(len(mapping))+" CONFLICTING_CODES="+str(len(conflicting)))
print(live.identity_status.value_counts().to_string())
print("DIRECT_CANDIDATES="+str(live.identity_status.eq("UNIQUE_CODE_CROSSWALK").sum()))
print("OUTPUT="+str(target))
print("NOT_CERTIFIED_FOR_SCORING; NO_FUZZY_MATCH; NO_OUTCOMES_READ")
