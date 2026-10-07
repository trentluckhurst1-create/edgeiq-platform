from pathlib import Path
import pandas as pd,numpy as np
D=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\d45\D45_FROZEN_PIT_FEATURE_MATRIX.csv");B=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv")
d=pd.read_csv(D);b=pd.read_csv(B);z=d.merge(b[["_race","_horse","last_distance","last_finish","last_won","last_top3"]],on=["_race","_horse"],how="left");z["distance_change"]=z.current_distance-z.last_distance;z["abs_distance_change"]=z.distance_change.abs();z["yr"]=pd.to_datetime(z.race_date).dt.year
meta={"_race","_horse","race_date","y","target_finish_position","current_track_id","barrier_zone","year","yr"};num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])];ctx={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"};F=list(dict.fromkeys([c for c in num if c not in ctx]+["days_since_last","distance_change","abs_distance_change","last_finish","last_won","last_top3"]))
print("D96_CONTRACT PREP47_TEMPORAL_REGIME_DIAGNOSTIC NO_MODEL_SELECTION NO_MARKET")
for y in [2021,2022,2023,2024]:
 q=z[z.yr.eq(y)];fs=q.groupby("_race").size();print("D96_YEAR",y,"RUNNERS",len(q),"RACES",q._race.nunique(),"FIELD_MED",float(fs.median()),"FIELD_MEAN",float(fs.mean()),"WIN_RATE",float(q.y.mean()))
for c in F:
 vals=[]
 for y in [2021,2022,2023,2024]:
  q=z[z.yr.eq(y)];v=pd.to_numeric(q[c],errors="coerce");w=pd.to_numeric(q.loc[q.y.eq(1),c],errors="coerce");vals.append((y,float(v.notna().mean()),float(v.median()) if v.notna().any() else np.nan,float(w.median()) if w.notna().any() else np.nan))
 if max(a[1] for a in vals)-min(a[1] for a in vals)>.05 or np.nanmax([a[2] for a in vals])-np.nanmin([a[2] for a in vals])>0:
  print("D96_FEATURE",c,vals)
print("D96_COMPLETE")
