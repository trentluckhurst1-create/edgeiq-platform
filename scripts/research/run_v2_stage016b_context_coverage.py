from pathlib import Path
import pandas as pd
U=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage004\V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv")
A=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_031\certified_current_race_context_031.csv")
print("V2_STAGE016B_CONTRACT EXACT_CONTEXT_AUTHORITY_COVERAGE NO_MODEL NO_MARKET 2025_2026_SEALED")
u=pd.read_csv(U); a=pd.read_csv(A)
print("V2_STAGE016B_U",len(u),"A",len(a))
print("V2_STAGE016B_UCOLS","|".join(u.columns));print("V2_STAGE016B_ACOLS","|".join(a.columns))
# normalize keys
uk=["canonical_race_id","canonical_horse_id","race_date"]
if "canonical_race_id" not in u.columns and "_race" in u.columns:u["canonical_race_id"]=u["_race"]
if "canonical_horse_id" not in u.columns and "_horse" in u.columns:u["canonical_horse_id"]=u["_horse"]
for d in (u,a): d["race_date"]=pd.to_datetime(d["race_date"],errors="coerce").dt.strftime("%Y-%m-%d")
print("V2_STAGE016B_AUTH_DUP_KEYS",int(a.duplicated(uk).sum()))
fields=["current_weight_kg","weight_change_kg","current_distance_metres","distance_change_metres","abs_distance_change_metres","current_class_group","prior_same_class_starts","prior_exact_distance_starts_031"]
keep=uk+[c for c in fields if c in a.columns]
m=u.merge(a[keep].drop_duplicates(uk),on=uk,how="left",indicator=True)
print("V2_STAGE016B_MATCH",int((m["_merge"]=="both").sum()),"RATE",float((m["_merge"]=="both").mean()))
m["year"]=pd.to_datetime(m["race_date"]).dt.year
for y,g in m.groupby("year"):
 print("V2_STAGE016B_YEAR",y,"N",len(g),"MATCH",int((g["_merge"]=="both").sum()),"RATE",float((g["_merge"]=="both").mean()))
 for c in fields:
  if c in g.columns: print("V2_STAGE016B_COVER",y,c,int(g[c].notna().sum()),float(g[c].notna().mean()))
print("V2_STAGE016B_COMPLETE")
