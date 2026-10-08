from pathlib import Path
import pandas as pd
U=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage004\V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv")
A=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_075f2\canonical_strict_date_first_starter_universe_075f2.csv")
print("V2_STAGE030_CONTRACT FIRST_STARTER_RACE_ID_DISAMBIGUATION NO_MODEL NO_FUZZY NO_MARKET 2025_2026_SEALED")
u=pd.read_csv(U,low_memory=False);a=pd.read_csv(A,low_memory=False)
if "canonical_horse_id" not in u.columns and "_horse" in u.columns:u["canonical_horse_id"]=u["_horse"]
if "canonical_race_id" not in u.columns and "_race" in u.columns:u["canonical_race_id"]=u["_race"]
for d in (u,a):d["race_date"]=pd.to_datetime(d["race_date"],errors="coerce").dt.strftime("%Y-%m-%d")
a=a[a["canonical_horse_id_075f2"].notna() & a["lab026_canonical_race_id"].notna()].copy()
a["canonical_horse_id"]=a["canonical_horse_id_075f2"].astype(str).str.strip()
a["canonical_race_id"]=a["lab026_canonical_race_id"].astype(str).str.strip()
u["canonical_horse_id"]=u["canonical_horse_id"].astype(str).str.strip();u["canonical_race_id"]=u["canonical_race_id"].astype(str).str.strip()
keys=["canonical_race_id","canonical_horse_id","race_date"]
print("V2_STAGE030_RESOLVED_ROWS",len(a),"DUP_EXACT_KEYS",int(a.duplicated(keys).sum()))
fields=["trainer_prior_first_starters","trainer_prior_first_starter_wins","trainer_prior_first_starter_places","jockey_prior_first_starters","jockey_prior_first_starter_wins","jockey_prior_first_starter_places","combo_prior_first_starters","combo_prior_first_starter_wins","combo_prior_first_starter_places"]
r=a[keys+fields].drop_duplicates(keys)
m=u.merge(r,on=keys,how="left",indicator=True)
m["year"]=pd.to_datetime(m["race_date"]).dt.year
print("V2_STAGE030_MATCH",int((m["_merge"]=="both").sum()),"N",len(m),"RATE",float((m["_merge"]=="both").mean()))
for y,g in m.groupby("year"):print("V2_STAGE030_YEAR",y,"MATCH",int((g["_merge"]=="both").sum()),"N",len(g),"RATE",float((g["_merge"]=="both").mean()))
for c in fields:print("V2_STAGE030_FIELD",c,"NONNULL_MATCHED",int(m.loc[m["_merge"]=="both",c].notna().sum()))
print("V2_STAGE030_COMPLETE")
