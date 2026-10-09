from pathlib import Path
import pandas as pd, re
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
R=P/"public"/"data"/"edgeiq_historical_performance_rating_v1.csv"
B=P/"docs"/"performance-intelligence"/"prototypes"/"phase1_4_1b"/"edgeiq_cross_provider_horse_identity_candidates_v0_1_20260716_063119.csv"
print("V2_STAGE034_CONTRACT GOVERNED_PERFORMANCE_IDENTITY_CERT NO_MODEL NO_FUZZY NO_MARKET 2025_2026_SEALED")
r=pd.read_csv(R,low_memory=False);b=pd.read_csv(B,low_memory=False)
print("V2_STAGE034_ROWS RATING",len(r),"BRIDGE",len(b))
print("V2_STAGE034_CLASS_COUNTS",b["classification"].astype(str).value_counts(dropna=False).to_dict())
print("V2_STAGE034_AUTO_COUNTS",b["automatic_merge_allowed"].astype(str).value_counts(dropna=False).to_dict())
def norm(s):
 return s.astype(str).str.upper().str.replace(r"[^A-Z0-9]","",regex=True)
# Governance requires explicit automatic merge permission + canonical ID.
allow=b["automatic_merge_allowed"].astype(str).str.upper().isin(["TRUE","YES","1","Y"])
g=b[allow & b["canonical_horse_id"].notna()].copy()
g["_name"]=norm(g["horse_name"])
# Reject any name mapping to >1 canonical ID.
amb=g.groupby("_name")["canonical_horse_id"].nunique()
safe=set(amb[amb==1].index)
g=g[g["_name"].isin(safe)][["_name","canonical_horse_id"]].drop_duplicates("_name")
r["_name"]=norm(r["horse"])
m=r.merge(g,on="_name",how="left")
print("V2_STAGE034_SAFE_BRIDGE_NAMES",len(g),"AMBIGUOUS_NAMES",int((amb>1).sum()))
print("V2_STAGE034_RATING_MATCH",int(m["canonical_horse_id"].notna().sum()),"N",len(m),"RATE",float(m["canonical_horse_id"].notna().mean()))
m["year"]=pd.to_datetime(m["race_date"],errors="coerce").dt.year
for y,z in m.groupby("year"):
 if y<=2024: print("V2_STAGE034_YEAR",int(y),"MATCH",int(z["canonical_horse_id"].notna().sum()),"N",len(z),"RATE",float(z["canonical_horse_id"].notna().mean()))
print("V2_STAGE034_COMPLETE")
