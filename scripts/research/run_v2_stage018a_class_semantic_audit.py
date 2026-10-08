from pathlib import Path
import pandas as pd
U=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage004\V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv")
A=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_031\certified_current_race_context_031.csv")
print("V2_STAGE018A_CONTRACT CLASS_LABEL_SEMANTIC_AUDIT NO_MODEL NO_MARKET 2025_2026_SEALED")
u=pd.read_csv(U);a=pd.read_csv(A,usecols=["canonical_race_id","canonical_horse_id","race_date","current_class_group"])
if "canonical_race_id" not in u.columns and "_race" in u.columns:u["canonical_race_id"]=u["_race"]
if "canonical_horse_id" not in u.columns and "_horse" in u.columns:u["canonical_horse_id"]=u["_horse"]
for d in (u,a):d["race_date"]=pd.to_datetime(d["race_date"],errors="coerce").dt.strftime("%Y-%m-%d")
m=u.merge(a,on=["canonical_race_id","canonical_horse_id","race_date"],how="left",validate="one_to_one")
m["year"]=pd.to_datetime(m.race_date).dt.year
print("V2_STAGE018A_ROWS",len(m),"COVER",int(m.current_class_group.notna().sum()),"RATE",float(m.current_class_group.notna().mean()))
for y,g in m.groupby("year"):
 s=g.current_class_group.dropna().astype(str).str.strip()
 print("V2_STAGE018A_YEAR",y,"N",len(g),"COVER",len(s),"UNIQUE",s.nunique())
 print("V2_STAGE018A_TOP",y,"|".join(f"{k}:{v}" for k,v in s.value_counts().head(25).items()))
# vocabulary overlap, using 2021 as first training vocabulary then cumulative prior-year vocab.
for y in [2022,2023,2024]:
 prior=set(m.loc[m.year<y,"current_class_group"].dropna().astype(str).str.strip())
 cur=m.loc[m.year==y,"current_class_group"].dropna().astype(str).str.strip()
 unseen=~cur.isin(prior)
 print("V2_STAGE018A_UNSEEN",y,int(unseen.sum()),len(cur),float(unseen.mean()) if len(cur) else 0.0,"UNSEEN_LABELS","|".join(sorted(cur[unseen].unique())[:50]))
print("V2_STAGE018A_COMPLETE")
