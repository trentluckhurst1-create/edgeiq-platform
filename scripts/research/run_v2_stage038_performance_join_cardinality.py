from pathlib import Path
import pandas as pd
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")/"public"/"data"
r=pd.read_csv(P/"edgeiq_historical_performance_rating_v1.csv",low_memory=False)
m=pd.read_csv(P/"edgeiq_official_runs_master_v1.csv",low_memory=False)
print("V2_STAGE038_CONTRACT EXACT_JOIN_CARDINALITY NO_MODEL NO_FUZZY NO_MARKET 2025_2026_SEALED")
def norm(s):return s.fillna("").astype(str).str.upper().str.replace(r"[^A-Z0-9]","",regex=True)
for d in (r,m):
 d["_date"]=pd.to_datetime(d["race_date"],errors="coerce").dt.normalize()
 d.drop(d[d["_date"].dt.year.gt(2024)].index,inplace=True)
 d["_name"]=norm(d["horse"])
 d.drop(d[d["_name"].eq("")|d["_date"].isna()].index,inplace=True)
k=["_name","_date"]
a=r.groupby(k).size().rename("rating_n")
b=m.groupby(k).agg(master_n=("horse_key","size"),horse_keys=("horse_key","nunique"))
j=a.to_frame().join(b,how="left").fillna(0)
print("V2_STAGE038_COUNTS RATING_ROWS",len(r),"RATING_KEYS",len(a),"MASTER_ROWS",len(m),"MATCHED_RATING_ROWS",int(j.loc[j.master_n.gt(0),"rating_n"].sum()))
print("V2_STAGE038_RATING_DUP_KEYS",int(a.gt(1).sum()),"RATING_DUP_ROWS",int(a[a.gt(1)].sum()))
print("V2_STAGE038_MASTER_DUP_KEYS",int(b.master_n.gt(1).sum()),"MASTER_MULTI_HORSE_KEY_KEYS",int(b.horse_keys.gt(1).sum()))
print("V2_STAGE038_MATCHED_AMBIGUOUS_RATING_ROWS",int(j.loc[j.master_n.gt(1),"rating_n"].sum()),"MATCHED_MULTI_HORSE_KEY_RATING_ROWS",int(j.loc[j.horse_keys.gt(1),"rating_n"].sum()))
print("V2_STAGE038_RATING_COLUMNS","|".join(r.columns))
print("V2_STAGE038_DECISION", "PASS_CARDINALITY_ONLY" if j.master_n.eq(1).all() and a.eq(1).all() and j.horse_keys.eq(1).all() else "STOP_AMBIGUOUS_JOIN")
print("V2_STAGE038_COMPLETE")
