from pathlib import Path
import pandas as pd
A=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_045a\weight_features_045a.csv")
print("V2_STAGE018C_CONTRACT LAB045A_WEIGHT_SCHEMA_ONLY NO_MODEL NO_MARKET 2025_2026_SEALED")
d=pd.read_csv(A,nrows=5)
print("V2_STAGE018C_COLS","|".join(d.columns))
for c in d.columns:
 print("V2_STAGE018C_SAMPLE",c,"|".join(map(str,d[c].tolist())))
print("V2_STAGE018C_COMPLETE")
