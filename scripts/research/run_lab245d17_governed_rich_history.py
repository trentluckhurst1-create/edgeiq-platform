from pathlib import Path
import pandas as pd
p=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv")
if not p.exists(): p=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\profitability_program\lab245b\LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv")
x=pd.read_csv(p,nrows=3)
print("D40B_BRIDGE_SCHEMA",list(x.columns))
print(x.to_string(index=False))
