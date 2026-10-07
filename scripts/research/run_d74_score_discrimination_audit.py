from pathlib import Path
import pandas as pd,numpy as np
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_026\edgeiq_certified_flat_walk_forward_epi_026.csv")
print("D102_CONTRACT NONFINISH_CONTAMINATION_HISTORY_GATE NO_MODEL")
h=pd.read_csv(P,usecols=["race_date","canonical_horse_id","finish_position","finish_margin","epi_value_026"],low_memory=False);h["date"]=pd.to_datetime(h.race_date);h["fp"]=pd.to_numeric(h.finish_position,errors="coerce");h["margin"]=pd.to_numeric(h.finish_margin,errors="coerce");h["epi"]=pd.to_numeric(h.epi_value_026,errors="coerce");h["valid_finish"]=h.fp.between(1,99)
for y in [2020,2021,2022,2023,2024]:
 q=h[h.date.dt.year.eq(y)];bad=~q.valid_finish
 print("D102_YEAR",y,"ROWS",len(q),"INVALID_FINISH",int(bad.sum()),"RATE",float(bad.mean()),"BAD_MARGIN_NONNULL",int(q.loc[bad,"margin"].notna().sum()),"BAD_MARGIN_Q",q.loc[bad,"margin"].quantile([0,.5,.9,.99,1]).to_dict(),"BAD_EPI_NONNULL",int(q.loc[bad,"epi"].notna().sum()),"BAD_EPI_Q",q.loc[bad,"epi"].quantile([0,.5,.9,.99,1]).to_dict())
print("D102_COMPLETE")

# D102 fresh dispatch marker 20261008A

# D102 reconnect dispatch after label repair B
