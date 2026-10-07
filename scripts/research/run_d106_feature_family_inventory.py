from pathlib import Path
import pandas as pd,numpy as np
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv"
d=pd.read_csv(D,nrows=0);cols=list(d.columns)
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"};num=[c for c in cols if c not in meta];ctx={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"};base=[c for c in num if c not in ctx]
print("D106_CONTRACT D99_FEATURE_FAMILY_INVENTORY NO_MODEL NO_SEARCH")
families={}
for c in base:
 k=("CONNECTION" if c.startswith(("jockey_","trainer_")) else "BARRIER" if "barrier" in c else "LVS_EPI" if ("lvs" in c or "epi" in c) else "MARGIN" if "margin" in c else "PLACE" if ("finish" in c or "top3" in c or "won" in c) else "DISTANCE" if ("dist" in c or "distance" in c) else "HISTORY" if ("hist" in c or "runs" in c) else "OTHER")
 families.setdefault(k,[]).append(c)
for k,v in families.items():print("D106_FAMILY",k,len(v),v)
print("D106_COMPLETE")
