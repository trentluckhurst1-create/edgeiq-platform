from pathlib import Path
import pandas as pd
U=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage004\V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv")
A=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_089\LAB089D_E_F_CERTIFIED_TODAY_CONTEXT_FEATURE_MATRIX.csv")
print("V2_STAGE017B_CONTRACT LAB089_IDENTITY_CERTIFICATION NO_MODEL NO_FUZZY NO_MARKET 2025_2026_SEALED")
u=pd.read_csv(U);a=pd.read_csv(A)
if "canonical_race_id" not in u.columns and "_race" in u.columns:u["canonical_race_id"]=u["_race"]
if "canonical_horse_id" not in u.columns and "_horse" in u.columns:u["canonical_horse_id"]=u["_horse"]
for d in (u,a):d["race_date"]=pd.to_datetime(d["race_date"],errors="coerce").dt.strftime("%Y-%m-%d")
for d,c in [(u,"canonical_race_id"),(u,"canonical_horse_id"),(a,"canonical_race_id"),(a,"horse_id")]:d[c]=d[c].astype(str).str.strip()
# Exact identity hypothesis only: LAB089 horse_id == V2 canonical_horse_id on same race/date.
ak=["canonical_race_id","horse_id","race_date"]
print("V2_STAGE017B_AUTH_DUP",int(a.duplicated(ak).sum()))
left=u[["canonical_race_id","canonical_horse_id","race_date"]].copy()
right=a[ak].drop_duplicates().rename(columns={"horse_id":"canonical_horse_id"})
m=left.merge(right,on=["canonical_race_id","canonical_horse_id","race_date"],how="left",indicator=True)
m["year"]=pd.to_datetime(m["race_date"]).dt.year
print("V2_STAGE017B_EXACT_MATCH",int((m["_merge"]=="both").sum()),"N",len(m),"RATE",float((m["_merge"]=="both").mean()))
for y,g in m.groupby("year"):print("V2_STAGE017B_YEAR",y,"MATCH",int((g["_merge"]=="both").sum()),"N",len(g),"RATE",float((g["_merge"]=="both").mean()))
# Race/date overlap tells whether missing horse matches are identity mismatch vs population absence.
races=left[["canonical_race_id","race_date"]].drop_duplicates().merge(a[["canonical_race_id","race_date"]].drop_duplicates(),on=["canonical_race_id","race_date"],how="left",indicator=True)
print("V2_STAGE017B_RACE_DATE_MATCH",int((races["_merge"]=="both").sum()),"N",len(races),"RATE",float((races["_merge"]=="both").mean()))
print("V2_STAGE017B_COMPLETE")
