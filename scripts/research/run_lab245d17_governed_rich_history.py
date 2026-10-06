from pathlib import Path
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_price_diagnostics\lab231\run_lab187_strict_elo_revalidation.py")
print("EXISTS",P.exists(),P)
if P.exists():
 s=P.read_text(encoding="utf-8-sig",errors="replace").splitlines()
 for i,line in enumerate(s):
  if "def load_source_features" in line:
   lo=max(0,i-20); hi=min(len(s),i+150)
   for j in range(lo,hi): print(f"{j+1}: {s[j]}")
