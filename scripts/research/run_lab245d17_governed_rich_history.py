from pathlib import Path
import pandas as pd
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
P=ROOT/"outputs/research/model_lab_026/edgeiq_certified_flat_walk_forward_epi_026.csv"
print("PERF026_EXISTS",P.exists(),"SIZE",P.stat().st_size if P.exists() else None)
if P.exists():
 d=pd.read_csv(P,nrows=5,low_memory=False); print("PERF026_COLS",list(d.columns)); print(d.to_string(index=False))
Q=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_price_diagnostics\lab231\run_lab231_performance_representation_search.py")
s=Q.read_text(encoding="utf-8",errors="replace").splitlines()
for i in range(150,185): print(f"{i+1}: {s[i]}")
