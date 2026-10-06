from pathlib import Path
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_price_diagnostics\lab231\run_lab231_performance_representation_search.py")
s=P.read_text(encoding="utf-8",errors="replace").splitlines()
for lo,hi in [(1,120),(140,260),(285,375)]:
 print(f"\n===== LINES {lo}-{hi} =====")
 for i in range(lo-1,min(hi,len(s))): print(f"{i+1}: {s[i]}")
