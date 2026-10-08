from pathlib import Path
R=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
p=R/"scripts"/"build_edgeiq_historical_performance_rating_v1.py"
print("V2_STAGE027A_CONTRACT PERFORMANCE_RATING_PATH_TRACE NO_MODEL 2025_2026_SEALED")
print("V2_STAGE027A_EXISTS",p.exists())
s=p.read_text(encoding="utf-8",errors="replace")
for i,line in enumerate(s.splitlines(),1):
 if any(k in line for k in ["ROOT =","DATA =","SRC =","OUT =","AUDIT ="]):
  print("V2_STAGE027A_LINE",i,line)
print("V2_STAGE027A_COMPLETE")
