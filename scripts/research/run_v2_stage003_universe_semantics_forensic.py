from pathlib import Path
import pandas as pd,numpy as np
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv"
z=pd.read_csv(D,usecols=["_race","_horse","race_date","y","target_finish_position","target_field_size"]);z["date"]=pd.to_datetime(z.race_date);z["year"]=z.date.dt.year;z=z[z.year<=2024]
print("V2_STAGE003_CONTRACT UNIVERSE_SEMANTICS_FORENSIC NO_MODEL 2025_2026_SEALED")
for yr,g in z.groupby("year"):
 rg=g.groupby("_race").agg(n=("_horse","size"),wins=("y","sum"),f1=("target_finish_position",lambda s:(pd.to_numeric(s,errors="coerce")==1).sum()),fs_nunique=("target_field_size","nunique"),fs_min=("target_field_size","min"),fs_max=("target_field_size","max"))
 bad=rg[rg.wins.ne(1)]
 print("V2_STAGE003_YEAR",yr,"RACES",len(rg),"MULTI_OR_ZERO_WINNER",len(bad),"FINISH1_MISMATCH_RACES",int((rg.wins!=rg.f1).sum()),"FIELD_NUNIQUE_MEDIAN",float(rg.fs_nunique.median()),"FIELD_MIN_MEDIAN",float(rg.fs_min.median()),"FIELD_MAX_MEDIAN",float(rg.fs_max.median()))
 for race,row in bad.iterrows():
  q=g[g._race.eq(race)][["_horse","y","target_finish_position","target_field_size"]]
  print("V2_STAGE003_BADWIN",yr,race,"N",len(q),"YSUM",int(q.y.sum()),"F1",int((pd.to_numeric(q.target_finish_position,errors="coerce")==1).sum()),"WINNERS","|".join(q.loc[q.y.eq(1),"_horse"].astype(str).tolist()))
# Determine whether target_field_size equals race size for any runner and distribution of gaps
z["race_n"]=z.groupby("_race")["_horse"].transform("size");z["fs"]=pd.to_numeric(z.target_field_size,errors="coerce");z["fs_gap"]=z.fs-z.race_n
print("V2_STAGE003_FIELD_EXACT_RUNNER_RATE",float(z.fs.eq(z.race_n).mean()),"GAP_MEDIAN",float(z.fs_gap.median()),"GAP_MIN",float(z.fs_gap.min()),"GAP_MAX",float(z.fs_gap.max()))
print("V2_STAGE003_COMPLETE")
