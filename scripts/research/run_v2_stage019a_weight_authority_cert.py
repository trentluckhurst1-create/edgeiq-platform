from pathlib import Path
import pandas as pd
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
U=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage004\V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv")
A=P/"outputs"/"research"/"model_lab_045a"/"weight_features_045a.csv"
print("V2_STAGE019A_CONTRACT LAB045A_WEIGHT_AUTHORITY_CERTIFICATION NO_MODEL NO_MARKET NO_EPI 2025_2026_SEALED")
u=pd.read_csv(U);a=pd.read_csv(A)
print("V2_STAGE019A_ACOLS","|".join(a.columns))
for d in (u,a):d["race_date"]=pd.to_datetime(d["race_date"],errors="coerce").dt.strftime("%Y-%m-%d")
if "canonical_race_id" not in u.columns and "_race" in u:u["canonical_race_id"]=u["_race"]
if "canonical_horse_id" not in u.columns and "_horse" in u:u["canonical_horse_id"]=u["_horse"]
# exact identity only; accept authority horse_id only if it equals canonical horse id.
horsecol="canonical_horse_id" if "canonical_horse_id" in a.columns else ("horse_id" if "horse_id" in a.columns else None)
print("V2_STAGE019A_HORSE_KEY",horsecol)
if horsecol is None:raise SystemExit("NO_HORSE_KEY")
for d,c in [(u,"canonical_race_id"),(u,"canonical_horse_id"),(a,"canonical_race_id"),(a,horsecol)]:d[c]=d[c].astype(str).str.strip()
if horsecol!="canonical_horse_id":a=a.rename(columns={horsecol:"canonical_horse_id"})
keys=["canonical_race_id","canonical_horse_id","race_date"]
print("V2_STAGE019A_DUP_KEYS",int(a.duplicated(keys).sum()))
fields=["weight_rank_in_full_field","weight_pct_in_full_field","full_field_weight_count","previous_start_weight","prior_recent_weight_average","change_from_recent_average"]
present=[c for c in fields if c in a]
print("V2_STAGE019A_FIELDS","|".join(present))
m=u.merge(a[keys+present].drop_duplicates(keys),on=keys,how="left",indicator=True);m["year"]=pd.to_datetime(m.race_date).dt.year
print("V2_STAGE019A_MATCH",int((m._merge=="both").sum()),"N",len(m),"RATE",float((m._merge=="both").mean()))
for y,g in m.groupby("year"):
 print("V2_STAGE019A_YEAR",y,"MATCH",int((g._merge=="both").sum()),"N",len(g),"RATE",float((g._merge=="both").mean()))
 for c in present:print("V2_STAGE019A_COVER",y,c,int(g[c].notna().sum()),float(g[c].notna().mean()))
# schema-level prohibited lineage gate
bad=[c for c in a.columns if any(t in c.lower() for t in ["market","odds","bsp","starting_price","epi"])]
print("V2_STAGE019A_PROHIBITED_COLUMNS","|".join(bad) if bad else "NONE")
print("V2_STAGE019A_COMPLETE")
