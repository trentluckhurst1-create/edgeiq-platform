from pathlib import Path
import pandas as pd
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\public\data\edgeiq_historical_replay_settled_v1.csv")
print("D83_CONTRACT SETTLED_REPLAY_COMPONENT_INVENTORY NO_MODEL")
d=pd.read_csv(P,low_memory=False);dt=pd.to_datetime(d["meeting_date"],errors="coerce")
print("D83_ROWS",len(d),"DATES",str(dt.min()),str(dt.max()),"COLS",list(d.columns))
for c in ["projected_rating_v5_2","sectional_strength_rating","strength_adjusted_rating_v6","confidence_adjusted_rating_v6","trainer_score","jockey_score","connection_score","runner_score"]:
 if c not in d.columns: continue
 v=pd.to_numeric(d[c],errors="coerce");print("D83_FIELD",c,"COV",float(v.notna().mean()),"N",int(v.notna().sum()),"NU",int(v.nunique(dropna=True)))
 for y in [2021,2022,2023,2024]:
  m=dt.dt.year.eq(y);print("D83_YEAR",c,y,"ROWS",int(m.sum()),"NONNULL",int(v[m].notna().sum()))
print("D83_COMPLETE")
