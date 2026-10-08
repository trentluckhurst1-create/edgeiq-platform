from pathlib import Path
import pandas as pd
U=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage004\V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv")
A=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_037\prior_jockey_trainer_intelligence_037.csv")
print("V2_STAGE018B_CONTRACT LAB037_CONNECTION_AUTHORITY_CERTIFICATION NO_MODEL NO_MARKET 2025_2026_SEALED")
u=pd.read_csv(U);a=pd.read_csv(A,nrows=0)
print("V2_STAGE018B_ACOLS","|".join(a.columns))
# Full load only after schema print; selected columns keep memory bounded.
cols=list(a.columns)
keys=[c for c in ["canonical_race_id","canonical_horse_id","horse_id","race_date"] if c in cols]
features=[c for c in cols if any(t in c.lower() for t in ["jockey","trainer"]) and c not in keys]
print("V2_STAGE018B_KEYS","|".join(keys));print("V2_STAGE018B_CANDIDATES","|".join(features))
use=list(dict.fromkeys(keys+features));a=pd.read_csv(A,usecols=use)
if "canonical_race_id" not in u.columns and "_race" in u.columns:u["canonical_race_id"]=u["_race"]
if "canonical_horse_id" not in u.columns and "_horse" in u.columns:u["canonical_horse_id"]=u["_horse"]
hid="canonical_horse_id" if "canonical_horse_id" in a.columns else ("horse_id" if "horse_id" in a.columns else None)
if not {"canonical_race_id","race_date"}.issubset(a.columns) or hid is None:raise SystemExit("LAB037 lacks exact race/horse/date keys")
a=a.rename(columns={hid:"canonical_horse_id"})
for d in (u,a):d["race_date"]=pd.to_datetime(d["race_date"],errors="coerce").dt.strftime("%Y-%m-%d")
k=["canonical_race_id","canonical_horse_id","race_date"]
for d in (u,a):
 for c in ["canonical_race_id","canonical_horse_id"]:d[c]=d[c].astype(str).str.strip()
print("V2_STAGE018B_AUTH_ROWS",len(a),"DUP_KEYS",int(a.duplicated(k).sum()))
m=u.merge(a[k+features].drop_duplicates(k),on=k,how="left",indicator=True)
m["year"]=pd.to_datetime(m.race_date).dt.year
print("V2_STAGE018B_MATCH",int((m["_merge"]=="both").sum()),"N",len(m),"RATE",float((m["_merge"]=="both").mean()))
for y,g in m.groupby("year"):
 print("V2_STAGE018B_YEAR",y,"MATCH",int((g["_merge"]=="both").sum()),"N",len(g),"RATE",float((g["_merge"]=="both").mean()))
for c in features:print("V2_STAGE018B_COVER",c,int(m[c].notna().sum()),float(m[c].notna().mean()))
print("V2_STAGE018B_COMPLETE")
