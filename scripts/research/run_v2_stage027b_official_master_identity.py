from pathlib import Path
import pandas as pd
R=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
p=R/"public"/"data"/"edgeiq_official_runs_master_v1.csv"
print("V2_STAGE027B_CONTRACT OFFICIAL_RUNS_MASTER_IDENTITY_SCHEMA NO_MODEL NO_MARKET 2025_2026_SEALED")
print("V2_STAGE027B_SOURCE",p,"EXISTS",p.exists())
if not p.exists():raise SystemExit("official runs master missing")
a=pd.read_csv(p,nrows=5,low_memory=False)
print("V2_STAGE027B_COLS","|".join(a.columns))
for c in ["canonical_horse_id","horse_id","horse","canonical_race_id","race_id","race_date","date","finish_position","finish_pos_raw","margin","margin_raw","field_size"]:
 print("V2_STAGE027B_FIELD",c,c in a.columns)
print("V2_STAGE027B_COMPLETE")
