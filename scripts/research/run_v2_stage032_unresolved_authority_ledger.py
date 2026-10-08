from pathlib import Path
import pandas as pd
print("V2_STAGE032_CONTRACT UNRESOLVED_AUTHORITY_LEDGER NO_MODEL NO_MARKET 2025_2026_SEALED")
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
checks=[
("PERFORMANCE_RATING",P/"public/data/edgeiq_historical_performance_rating_v1.csv"),
("PERFORMANCE_BRIDGE",R/"outputs/research/profitability_program/lab245b/LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"),
("TIMING_H4B",P/"outputs/research/model_lab_090/LAB090F5B_STRICT_PRIOR_TIMING_H4B_MATRIX.csv"),
("PACE",P/"outputs/research/model_lab_087/LAB087G_PACE_H4B_IDENTITY_BRIDGE.csv"),
("FIRST_STARTER",P/"outputs/research/model_lab_075f2/canonical_strict_date_first_starter_universe_075f2.csv"),
("FORM_LINE",P/"outputs/research/model_lab_120/LAB120E_DYNAMIC_FORM_LINE_FEATURES.csv"),
("LAB089",P/"outputs/research/model_lab_089/LAB089D_E_F_CERTIFIED_TODAY_CONTEXT_FEATURE_MATRIX.csv"),
("LAB031",P/"outputs/research/model_lab_031/certified_current_race_context_031.csv"),
]
for name,p in checks:
 print("V2_STAGE032_SOURCE",name,"EXISTS",p.exists(),"PATH",str(p))
 if not p.exists():continue
 try:
  d=pd.read_csv(p,nrows=5)
  cols=list(d.columns)
  ids=[c for c in cols if any(k in c.lower() for k in ["horse","race_id","race_date","market","odds","price","rating","class","age","sex","weight","track","going","condition"])]
  print("V2_STAGE032_SCHEMA",name,"|".join(ids[:80]))
 except Exception as e: print("V2_STAGE032_READ_ERROR",name,type(e).__name__,str(e))
print("V2_STAGE032_COMPLETE")
