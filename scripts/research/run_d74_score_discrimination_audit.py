from pathlib import Path
import pandas as pd
R=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM");P=R/"outputs"/"research"/"model_lab_026"/"edgeiq_certified_flat_walk_forward_epi_026.csv"
print("D84_CONTRACT CONTEXTUAL_CONNECTION_SOURCE_GATE NO_MODEL")
cols=list(pd.read_csv(P,nrows=0).columns);print("D84_COLUMNS",[c for c in cols if any(k in c.lower() for k in ["jockey","trainer","track","distance","condition","class","barrier","finish"])])
need=["race_date","canonical_jockey_id","canonical_trainer_id","canonical_track_id","distance_metres","barrier","finish_position"]
opt=[c for c in ["track_condition_group","race_class","race_class_group","class_group","race_classification"] if c in cols]
d=pd.read_csv(P,usecols=need+opt,low_memory=False);dt=pd.to_datetime(d.race_date,errors="coerce")
for c in need[1:]+opt: print("D84_COVERAGE",c,float(d[c].notna().mean()))
for y in [2020,2021,2022,2023,2024]: print("D84_YEAR",y,"ROWS",int(dt.dt.year.eq(y).sum()))
print("D84_COMPLETE")
