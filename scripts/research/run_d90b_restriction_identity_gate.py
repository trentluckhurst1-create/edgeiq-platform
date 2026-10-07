from pathlib import Path
import pandas as pd,re
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM");D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv";P=ROOT/"outputs"/"research"/"model_lab_026"/"edgeiq_certified_flat_walk_forward_epi_026.csv";H=ROOT/"public"/"data"/"edgeiq_historical_performance_rating_v6_1_research.csv"
def n(s):return s.astype(str).str.upper().str.strip().str.replace(r"\s+"," ",regex=True)
d=pd.read_csv(D,usecols=["_race","_horse","race_date"]);d["date"]=pd.to_datetime(d.race_date)
p=pd.read_csv(P,usecols=["canonical_horse_id","race_date","canonical_horse_name","canonical_track_id","distance_metres"]);p["date"]=pd.to_datetime(p.race_date);p=p.drop_duplicates(["canonical_horse_id","date"])
x=d.merge(p,left_on=["_horse","date"],right_on=["canonical_horse_id","date"],how="left")
h=pd.read_csv(H,usecols=["horse","race_date","track","distance","race_type_recovered","age_restriction_recovered","sex_restriction_recovered"]);h["date"]=pd.to_datetime(h.race_date);h["hk"]=n(h.horse);h["tk"]=n(h.track);h["dk"]=pd.to_numeric(h.distance,errors="coerce").round()
x["hk"]=n(x.canonical_horse_name);x["tk"]=n(x.canonical_track_id);x["dk"]=pd.to_numeric(x.distance_metres,errors="coerce").round()
keys=["hk","date","tk","dk"];amb=(h.groupby(keys,dropna=False).size()>1);print("D90B_CONTRACT EXACT_NAME_DATE_TRACK_DISTANCE_IDENTITY_GATE NO_MODEL");print("D90B_AUTH_ROWS",len(h),"AMBIG_KEYS",int(amb.sum()))
m=x.merge(h[keys+["race_type_recovered","age_restriction_recovered","sex_restriction_recovered"]].drop_duplicates(keys),on=keys,how="left")
for y in [2022,2023,2024]:
 q=m[m.date.dt.year.eq(y)];print("D90B_YEAR",y,"RUNNERS",len(q),"PERF026_ID",float(q.canonical_horse_name.notna().mean()))
 for c in ["race_type_recovered","age_restriction_recovered","sex_restriction_recovered"]:print("D90B_FIELD",y,c,"COV",float(q[c].notna().mean()),"UNIQUE",int(q[c].nunique(dropna=True)),"TOP",q[c].value_counts(dropna=False).head(10).to_dict())
print("D90B_COMPLETE")
