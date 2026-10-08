from pathlib import Path
import pandas as pd,numpy as np
D=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\d45\D45_FROZEN_PIT_FEATURE_MATRIX.csv")
print("V2_STAGE020B_CONTRACT D99_RELATIVE_TRANSFORM_SEMANTIC_CERT NO_MODEL NO_MARKET 2025_2026_SEALED")
d=pd.read_csv(D)
pairs=[("hist_runs","hist_runs_rel"),("lvs_last1","lvs_last1_rel"),("lvs_mean3","lvs_mean3_rel"),("lvs_mean5","lvs_mean5_rel"),("lvs_median5","lvs_median5_rel"),("lvs_std5","lvs_std5_rel"),("lvs_peak","lvs_peak_rel"),("lvs_worst5","lvs_worst5_rel"),("margin_mean5","margin_mean5_rel"),("margin_std5","margin_std5_rel"),("margin_worst5","margin_worst5_rel"),("days_since_last","days_since_last_rel"),("dist200_runs","dist200_runs_rel"),("dist200_lvs_mean","dist200_lvs_mean_rel"),("dist200_lvs_best","dist200_lvs_best_rel")]
ok=True
for raw,rel in pairs:
 calc=pd.to_numeric(d[raw],errors="coerce")-d.groupby("_race")[raw].transform("median")
 obs=pd.to_numeric(d[rel],errors="coerce")
 mask=calc.notna()&obs.notna()
 diff=(calc[mask]-obs[mask]).abs()
 maxd=float(diff.max()) if len(diff) else np.nan
 mismatch=int((diff>1e-9).sum()) if len(diff) else 0
 cov=float(obs.notna().mean())
 print("V2_STAGE020B_PAIR",raw,rel,"COVER",repr(cov),"N",int(mask.sum()),"MISMATCH",mismatch,"MAX_ABS_DIFF",repr(maxd))
 if mismatch:ok=False
print("V2_STAGE020B_PASS",ok)
print("V2_STAGE020B_COMPLETE")
