from pathlib import Path
import pandas as pd
U=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage004\V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv")
A=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_076p\eligible_runner_classification_076p.csv")
print("V2_STAGE022B_CONTRACT LAB076P_ABSOLUTE_CLASS_COVERAGE_IDENTITY NO_MODEL NO_MARKET 2025_2026_SEALED")
u=pd.read_csv(U);a=pd.read_csv(A)
print("V2_STAGE022B_ACOLS","|".join(a.columns),"A_N",len(a))
if "canonical_race_id" not in u.columns and "_race" in u.columns:u["canonical_race_id"]=u["_race"]
if "canonical_horse_id" not in u.columns and "_horse" in u.columns:u["canonical_horse_id"]=u["_horse"]
for d in (u,a):d["race_date"]=pd.to_datetime(d["race_date"],errors="coerce").dt.strftime("%Y-%m-%d")
# Determine strongest exact key supported by authority without inventing identity.
keys=["canonical_horse_id","race_date"]
print("V2_STAGE022B_DUP_KEYS",int(a.duplicated(keys).sum()))
m=u.merge(a[keys+["race_class"]].drop_duplicates(keys),on=keys,how="left",indicator=True)
m["year"]=pd.to_datetime(m["race_date"]).dt.year
print("V2_STAGE022B_MATCH",int((m["_merge"]=="both").sum()),"N",len(m),"RATE",float((m["_merge"]=="both").mean()))
for y,g in m.groupby("year"):
 print("V2_STAGE022B_YEAR",y,"MATCH",int((g["_merge"]=="both").sum()),"N",len(g),"RATE",float((g["_merge"]=="both").mean()),"CLASS_COVER",float(g["race_class"].notna().mean()),"CLASS_UNIQUE",int(g["race_class"].nunique(dropna=True)))
print("V2_STAGE022B_CLASS_SAMPLE","|".join(map(str,a["race_class"].dropna().astype(str).value_counts().head(25).index.tolist())))
print("V2_STAGE022B_COMPLETE")
