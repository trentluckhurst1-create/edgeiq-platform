from pathlib import Path
import pandas as pd
U=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage004\V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv")
sources={
"LAB037":Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_037\prior_jockey_trainer_intelligence_037.csv"),
"LAB045A":Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_045a\weight_features_045a.csv")}
print("V2_STAGE018B_CONTRACT DENSE_AUTHORITY_SCHEMA_COVERAGE NO_MODEL NO_MARKET 2025_2026_SEALED")
u=pd.read_csv(U)
if "canonical_race_id" not in u and "_race" in u:u["canonical_race_id"]=u["_race"]
if "canonical_horse_id" not in u and "_horse" in u:u["canonical_horse_id"]=u["_horse"]
u["race_date"]=pd.to_datetime(u.race_date,errors="coerce").dt.strftime("%Y-%m-%d")
for name,p in sources.items():
 a=pd.read_csv(p)
 print("V2_STAGE018B_SOURCE",name,"ROWS",len(a))
 print("V2_STAGE018B_COLS",name,"|".join(a.columns))
 # determine exact horse key only from explicit candidates, never fuzzy
 hk=next((c for c in ["canonical_horse_id","horse_id"] if c in a.columns),None)
 rk=next((c for c in ["canonical_race_id","race_id"] if c in a.columns),None)
 dk="race_date" if "race_date" in a.columns else None
 print("V2_STAGE018B_KEYS",name,rk,hk,dk)
 if not all([rk,hk,dk]):continue
 a[dk]=pd.to_datetime(a[dk],errors="coerce").dt.strftime("%Y-%m-%d")
 left=u[["canonical_race_id","canonical_horse_id","race_date"]].copy()
 right=a[[rk,hk,dk]].copy();right.columns=["canonical_race_id","canonical_horse_id","race_date"]
 for d in (left,right):
  d["canonical_race_id"]=d["canonical_race_id"].astype(str).str.strip();d["canonical_horse_id"]=d["canonical_horse_id"].astype(str).str.strip()
 print("V2_STAGE018B_DUP",name,int(right.duplicated(["canonical_race_id","canonical_horse_id","race_date"]).sum()))
 m=left.merge(right.drop_duplicates(),on=["canonical_race_id","canonical_horse_id","race_date"],how="left",indicator=True)
 m["year"]=pd.to_datetime(m.race_date).dt.year
 print("V2_STAGE018B_MATCH",name,int((m._merge=="both").sum()),len(m),float((m._merge=="both").mean()))
 for y,g in m.groupby("year"):print("V2_STAGE018B_YEAR",name,y,int((g._merge=="both").sum()),len(g),float((g._merge=="both").mean()))
print("V2_STAGE018B_COMPLETE")
