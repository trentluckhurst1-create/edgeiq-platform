from pathlib import Path
import pandas as pd
U=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage004\V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv")
A=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_075f2\canonical_strict_date_first_starter_universe_075f2.csv")
print("V2_STAGE029_CONTRACT FIRST_STARTER_CANONICAL_ID_CERT NO_MODEL NO_FUZZY NO_MARKET 2025_2026_SEALED")
u=pd.read_csv(U,low_memory=False);a=pd.read_csv(A,low_memory=False)
if "canonical_horse_id" not in u.columns and "_horse" in u.columns:u["canonical_horse_id"]=u["_horse"]
if "canonical_race_id" not in u.columns and "_race" in u.columns:u["canonical_race_id"]=u["_race"]
u["race_date"]=pd.to_datetime(u["race_date"],errors="coerce").dt.strftime("%Y-%m-%d")
a["race_date"]=pd.to_datetime(a["race_date"],errors="coerce").dt.strftime("%Y-%m-%d")
for d,c in [(u,"canonical_horse_id"),(a,"canonical_horse_id_075f2")]:d[c]=d[c].astype(str).str.strip()
print("V2_STAGE029_ROWS",len(a))
for c in ["identity_method_075f2","_chronology_status","resolved_id_in_lab026","canonical_horse_id_075f2"]:
 if c in a.columns:print("V2_STAGE029_VALUE_COUNTS",c,a[c].astype(str).value_counts(dropna=False).head(20).to_dict())
# exact target date + resolved canonical horse
right=a.rename(columns={"canonical_horse_id_075f2":"canonical_horse_id"})
keys=["race_date","canonical_horse_id"]
print("V2_STAGE029_DUP_KEYS",int(right.duplicated(keys).sum()))
m=u.merge(right[keys+["trainer_prior_first_starters","trainer_prior_first_starter_wins","trainer_prior_first_starter_places","jockey_prior_first_starters","jockey_prior_first_starter_wins","jockey_prior_first_starter_places","combo_prior_first_starters","combo_prior_first_starter_wins","combo_prior_first_starter_places","_chronology_status","identity_method_075f2"]].drop_duplicates(keys),on=keys,how="left",indicator=True)
m["year"]=pd.to_datetime(m["race_date"]).dt.year
print("V2_STAGE029_MATCH",int((m["_merge"]=="both").sum()),"N",len(m),"RATE",float((m["_merge"]=="both").mean()))
for y,g in m.groupby("year"):
 print("V2_STAGE029_YEAR",y,"MATCH",int((g["_merge"]=="both").sum()),"N",len(g),"RATE",float((g["_merge"]=="both").mean()))
print("V2_STAGE029_COMPLETE")
