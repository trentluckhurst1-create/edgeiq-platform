from pathlib import Path
import pandas as pd,numpy as np
U=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage004\V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv")
A=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_045a\weight_features_045a.csv")
print("V2_STAGE018D_CONTRACT LAB045A_WEIGHT_CERTIFICATION NO_MODEL NO_MARKET 2025_2026_SEALED")
u=pd.read_csv(U)
fields=["current_weight","relative_to_race_mean","relative_to_race_min","relative_to_race_max","weight_rank_in_full_field","weight_pct_in_full_field","full_field_weight_count","previous_start_weight","change_from_previous_start","prior_recent_weight_average","change_from_recent_average"]
use=["canonical_race_id","canonical_horse_id","race_date"]+fields
a=pd.read_csv(A,usecols=use)
if "_race" in u.columns:u["canonical_race_id"]=u["_race"]
if "_horse" in u.columns:u["canonical_horse_id"]=u["_horse"]
for d in (u,a):
 d["race_date"]=pd.to_datetime(d.race_date,errors="coerce").dt.strftime("%Y-%m-%d")
 for c in ["canonical_race_id","canonical_horse_id"]:d[c]=d[c].astype(str).str.strip()
k=["canonical_race_id","canonical_horse_id","race_date"]
print("V2_STAGE018D_AUTH_ROWS",len(a),"DUP",int(a.duplicated(k).sum()))
m=u.merge(a.drop_duplicates(k),on=k,how="left",indicator=True);m["year"]=pd.to_datetime(m.race_date).dt.year
print("V2_STAGE018D_MATCH",int((m["_merge"]=="both").sum()),"N",len(m),"RATE",float((m["_merge"]=="both").mean()))
for y,g in m.groupby("year"):print("V2_STAGE018D_YEAR",y,"MATCH",int((g["_merge"]=="both").sum()),"N",len(g),"RATE",float((g["_merge"]=="both").mean()))
for c in fields:
 s=pd.to_numeric(m[c],errors="coerce")
 q=s.quantile([0,.01,.5,.99,1]).tolist()
 print("V2_STAGE018D_FIELD",c,"COVER",int(s.notna().sum()),"RATE",float(s.notna().mean()),"Q","|".join(map(repr,q)))
print("V2_STAGE018D_COMPLETE")
