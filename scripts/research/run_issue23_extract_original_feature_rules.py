"""Issue23: extract original Stage011 feature lineage and barrier rules from local source.

Read-only inspection of source code, not a scoring or data audit.
"""
from pathlib import Path
import ast
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
E=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
FILES=[
 R/"scripts/research/run_v2_stage011_reproduction_artifact.py",
 R/"scripts/research/run_v2_stage006_feature_warehouse.py",
 R/"scripts/research/build_d45_frozen_pit_feature_matrix.py",
 E/"scripts/research/run_v2_stage006_feature_warehouse.py",
 E/"scripts/research/build_d45_frozen_pit_feature_matrix.py",
]
TERMS=("barrier_position_pct","represented_field_size","current_distance","hist_runs","jockey_prior","trainer_prior","clean_finish","lvs_mean3","margin_mean5","dist200_runs")
def main():
 seen=set()
 for p in FILES:
  if p in seen or not p.exists():continue
  seen.add(p)
  print("\n"+"="*90+"\nSOURCE "+str(p))
  lines=p.read_text(encoding="utf-8-sig").splitlines()
  try:ast.parse("\n".join(lines))
  except SyntaxError as ex:print("WARNING source syntax:",ex)
  matches=[i for i,line in enumerate(lines) if any(t in line for t in TERMS)]
  if not matches:
   print("NO_FEATURE_REFERENCES");continue
  intervals=[]
  for i in matches:
   lo=max(0,i-5);hi=min(len(lines),i+7)
   if intervals and lo<=intervals[-1][1]:intervals[-1]=(intervals[-1][0],max(hi,intervals[-1][1]))
   else:intervals.append((lo,hi))
  for lo,hi in intervals:
   print("--- lines",lo+1,"to",hi)
   for i in range(lo,hi):print(f"{i+1:04d}: {lines[i]}")
 if not seen:raise RuntimeError("STOP no original builder source files found")
 print("\nSOURCE_INSPECTION_COMPLETE; NO_DATA_READ; NO_SCORING")
if __name__=="__main__":main()
