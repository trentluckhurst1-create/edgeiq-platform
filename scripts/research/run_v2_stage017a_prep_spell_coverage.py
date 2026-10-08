from pathlib import Path
import pandas as pd

U=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage004\V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv")
A=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_089\LAB089D_E_F_CERTIFIED_TODAY_CONTEXT_FEATURE_MATRIX.csv")
print("V2_STAGE017A_CONTRACT EXACT_PREP_SPELL_AUTHORITY_COVERAGE NO_MODEL NO_MARKET 2025_2026_SEALED")
u=pd.read_csv(U); a=pd.read_csv(A)
print("V2_STAGE017A_U",len(u),"A",len(a))
print("V2_STAGE017A_ACOLS","|".join(a.columns))
uk=["canonical_race_id","canonical_horse_id","race_date"]
if "canonical_race_id" not in u.columns and "_race" in u.columns:u["canonical_race_id"]=u["_race"]
if "canonical_horse_id" not in u.columns and "_horse" in u.columns:u["canonical_horse_id"]=u["_horse"]
for d in (u,a): d["race_date"]=pd.to_datetime(d["race_date"],errors="coerce").dt.strftime("%Y-%m-%d")
missing=[c for c in uk if c not in a.columns]
print("V2_STAGE017A_MISSING_KEYS","|".join(missing) if missing else "NONE")
if missing: raise SystemExit("LAB089 authority lacks exact V2 keys")
print("V2_STAGE017A_AUTH_DUP_KEYS",int(a.duplicated(uk).sum()))
fields=["lab089_prep_days_since_second_last_run","lab089_prep_spell_length","lab089_going_prior_same_condition_days_since"]
present=[c for c in fields if c in a.columns]
print("V2_STAGE017A_PRESENT_FIELDS","|".join(present))
m=u.merge(a[uk+present].drop_duplicates(uk),on=uk,how="left",indicator=True)
m["year"]=pd.to_datetime(m["race_date"]).dt.year
print("V2_STAGE017A_MATCH",int((m["_merge"]=="both").sum()),"RATE",float((m["_merge"]=="both").mean()))
for y,g in m.groupby("year"):
 print("V2_STAGE017A_YEAR",y,"N",len(g),"MATCH",int((g["_merge"]=="both").sum()),"RATE",float((g["_merge"]=="both").mean()))
 for c in present: print("V2_STAGE017A_COVER",y,c,int(g[c].notna().sum()),float(g[c].notna().mean()))
print("V2_STAGE017A_COMPLETE")
