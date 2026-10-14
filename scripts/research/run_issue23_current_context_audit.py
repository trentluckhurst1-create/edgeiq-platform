"""Issue23: inspect certified current race context schema and temporal readiness without using outcomes."""
from pathlib import Path
import pandas as pd
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_031\certified_current_race_context_031.csv")
print("ISSUE23 CURRENT CONTEXT SCHEMA AUDIT")
if not P.is_file():raise RuntimeError("STOP current context absent")
d=pd.read_csv(P,nrows=500,low_memory=False)
print("SAMPLE_ROWS="+str(len(d)))
print("COLUMNS="+repr(list(d.columns)))
for col in d.columns:
 if any(k in col.lower() for k in ("date","time","race","horse","runner","scratch","distance","jockey","trainer","barrier","status")):
  vals=d[col].dropna().astype(str).head(4).tolist()
  print(f"FIELD={col} NON_NULL={int(d[col].notna().sum())} EXAMPLES={vals}")
need=["current_distance","hist_runs","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_std5","margin_worst5","margin_last1","margin_last2","last_distance","margin_change_l1_l2","margin_per_runner_last1","margin_per_runner_last2","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best","represented_field_size","barrier_position_pct","jockey_prior_starts","jockey_prior_win_rate","jockey_prior_top3_rate","trainer_prior_starts","trainer_prior_win_rate","trainer_prior_top3_rate","clean_finish_mean5","clean_last_finish","clean_last_won","clean_last_top3","clean_finish_hist_n"]
present=[x for x in need if x in d];missing=[x for x in need if x not in d]
print("DIRECT_FEATURES_PRESENT="+str(len(present))+" MISSING="+str(len(missing)))
print("PRESENT="+repr(present));print("MISSING="+repr(missing))
print("READINESS=INSPECTION_ONLY NO_PREDICTIONS NO_OUTCOMES")
