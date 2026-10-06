from pathlib import Path
p=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_031\build_certified_current_context_031.py")
print("D32_LAB031_BARRIER_CONTRACT_AUDIT")
print("PATH",p,"EXISTS",p.exists())
if not p.exists(): raise SystemExit(2)
lines=p.read_text(encoding="utf-8",errors="replace").splitlines()
keys=("barrier","derived_field_size","current_barrier","barrier_position_pct","finish_position","target","race_rows","groupby")
for i,line in enumerate(lines,1):
 if any(k.lower() in line.lower() for k in keys):
  lo=max(1,i-3);hi=min(len(lines),i+3)
  print(f"--- LINES {lo}-{hi} ---")
  for j in range(lo,hi+1): print(f"{j}: {lines[j-1]}")
