from pathlib import Path
import pandas as pd, numpy as np
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv"
W=R/"outputs"/"research"/"model_v2"/"stage006"/"V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv"
print("V2_STAGE020A_CONTRACT D99_VS_STAGE011_EXACT_FEATURE_GAP_LEDGER NO_MODEL NO_MARKET 2025_2026_SEALED")
d=pd.read_csv(D,nrows=5000);w=pd.read_csv(W,nrows=5000)
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"}
num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])]
ctx={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"}
d99base=[c for c in num if c not in ctx]
d99_clean=[c for c in d99base if c not in ["finishpos_mean5","finishpos_mean5_rel","last_finish","last_won","last_top3"]]
# Stage011 explicit core before clean placing; context discovered from D45 by exact naming rule.
stage011core=["current_distance","hist_runs","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_std5","margin_worst5","margin_last1","margin_last2","last_distance","margin_change_l1_l2","margin_per_runner_last1","margin_per_runner_last2","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best","represented_field_size"]
stage011ctx=[c for c in d.columns if any(k in c.lower() for k in ["barrier","jockey_prior","trainer_prior"]) and pd.api.types.is_numeric_dtype(d[c])]
stage011=set([c for c in stage011core+stage011ctx if c in set(d.columns)|set(w.columns)])
gap=[c for c in d99_clean if c not in stage011]
print("V2_STAGE020A_D99_CLEAN_N",len(d99_clean))
print("V2_STAGE020A_STAGE011_D45_EQUIV_N",len(stage011))
print("V2_STAGE020A_GAP_N",len(gap))
for c in gap:
 q=pd.to_numeric(d[c],errors="coerce")
 print("V2_STAGE020A_GAP",c,"COVER",repr(float(q.notna().mean())),"UNIQUE",int(q.nunique(dropna=True)),"MIN",repr(float(q.min())) if q.notna().any() else "NA","MAX",repr(float(q.max())) if q.notna().any() else "NA")
print("V2_STAGE020A_STAGE011_EQUIV","|".join(sorted(stage011)))
print("V2_STAGE020A_GAPS","|".join(gap))
print("V2_STAGE020A_COMPLETE")
