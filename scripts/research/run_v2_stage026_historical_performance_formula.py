from pathlib import Path
p=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\scripts\build_edgeiq_historical_performance_rating_v1.py")
lines=p.read_text(encoding="utf-8",errors="ignore").splitlines()
print("V2_STAGE026_CONTRACT HISTORICAL_PERFORMANCE_FORMULA_FORENSIC NO_MODEL 2025_2026_SEALED")
for i,line in enumerate(lines):
 lo=line.lower()
 if "market" in lo or "price" in lo or 115<=i+1<=145 or "read_csv" in lo:
  print("V2_STAGE026_LINE",i+1,line)
print("V2_STAGE026_COMPLETE")
