from pathlib import Path
import pandas as pd,re
R=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM");P=R/"public"/"data"/"sectionals.csv";D=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\d45\D45_FROZEN_PIT_FEATURE_MATRIX.csv")
print("D82_CONTRACT SECTIONALS_CSV_VALUE_AND_D45_OVERLAP NO_MODEL")
s=pd.read_csv(P,low_memory=False);s["race_date"]=pd.to_datetime(s.race_date,errors="coerce");s["run_date"]=pd.to_datetime(s.run_date,errors="coerce")
print("D82_ROWS",len(s),"RACE_RANGE",str(s.race_date.min()),str(s.race_date.max()),"RUN_RANGE",str(s.run_date.min()),str(s.run_date.max()))
cols=["last_600","last_400","last_200","last_600_rank","last_400_rank","last_200_rank","closing_speed_pct","midrace_speed_pct","sectional_score"]
for c in cols:
 v=pd.to_numeric(s[c],errors="coerce");print("D82_FIELD",c,"COV",float(v.notna().mean()),"N",int(v.notna().sum()),"MIN",float(v.min()) if v.notna().any() else None,"MAX",float(v.max()) if v.notna().any() else None)
for y,g in s.groupby(s.race_date.dt.year):
 print("D82_YEAR",int(y),"ROWS",len(g),**{c:int(pd.to_numeric(g[c],errors="coerce").notna().sum()) for c in cols[:6]})
d=pd.read_csv(D,usecols=["_race","_horse","race_date"]);d["race_date"]=pd.to_datetime(d.race_date,errors="coerce")
canon=lambda x:x.astype(str).str.upper().str.replace(r"[^A-Z0-9]","",regex=True)
d["hk"]=canon(d["_horse"]);s["hk"]=canon(s["horse"])
for y in [2021,2022,2023,2024]:
 a=d[d.race_date.dt.year.eq(y)];hist=s[(s.run_date<s.race_date)&s.run_date.notna()]
 horses=set(hist.loc[hist.run_date<pd.Timestamp(f"{y}-12-31"),"hk"])
 print("D82_D45_YEAR",y,"RUNNERS",len(a),"HORSE_HAS_ANY_SECTIONAL_HISTORY",int(a.hk.isin(horses).sum()))
print("D82_COMPLETE")
