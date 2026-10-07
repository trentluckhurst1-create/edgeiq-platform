from pathlib import Path
import pandas as pd,numpy as np
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_026\edgeiq_certified_flat_walk_forward_epi_026.csv")
print("D100_CONTRACT STATUS109_LAST_ACTUAL_START_CONTAMINATION_AUDIT NO_MODEL")
d=pd.read_csv(P,usecols=["canonical_horse_id","race_date","finish_position"],low_memory=False);d["date"]=pd.to_datetime(d.race_date);d["pos"]=pd.to_numeric(d.finish_position,errors="coerce");d=d.dropna(subset=["canonical_horse_id","date"]).sort_values(["canonical_horse_id","date"])
d["prev_pos"]=d.groupby("canonical_horse_id").pos.shift();d["prev_date"]=d.groupby("canonical_horse_id").date.shift()
for y in [2021,2022,2023,2024]:
 q=d[d.date.dt.year.eq(y)];print("D100_YEAR",y,"ROWS",len(q),"CURRENT109",int(q.pos.eq(109).sum()),"PREV109",int(q.prev_pos.eq(109).sum()),"PREV109_RATE",float(q.prev_pos.eq(109).mean()))
print("D100_TOTAL_PREV109",int(d.prev_pos.eq(109).sum()))
print("D100_COMPLETE")
