from pathlib import Path
import pandas as pd
R=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
U=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage004\V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv")
cands=[
 R/"outputs"/"research"/"model_lab_075f2"/"canonical_strict_date_first_starter_universe_075f2.csv",
 R/"outputs"/"research"/"model_lab_075e",
 R/"outputs"/"research"/"model_lab_075f",
 R/"outputs"/"research"/"model_lab_075f2",
]
print("V2_STAGE028_CONTRACT FIRST_STARTER_IDENTITY_RECOVERY_INVENTORY NO_MODEL NO_FUZZY NO_MARKET 2025_2026_SEALED")
for p in cands:
 print("V2_STAGE028_PATH",p,"EXISTS",p.exists(),"DIR",p.is_dir() if p.exists() else False)
 if p.is_file():
  d=pd.read_csv(p,nrows=3,low_memory=False);print("V2_STAGE028_FILE_COLS",p.name,"|".join(d.columns))
 if p.is_dir():
  for f in sorted(p.glob("*.csv")):
   try:
    d=pd.read_csv(f,nrows=2,low_memory=False)
    cols="|".join(d.columns)
    if any(k in cols.lower() for k in ["canonical","horse_code","horse_id","identity","first"]):
     print("V2_STAGE028_CANDIDATE",f.name,"COLS",cols)
   except Exception as e:print("V2_STAGE028_READERR",f.name,type(e).__name__)
print("V2_STAGE028_COMPLETE")
