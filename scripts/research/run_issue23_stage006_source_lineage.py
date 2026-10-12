"""Issue23: read-only Stage006 lineage and source schema inspection for PIT feature port.

Never loads result rows, 2025/26 outcomes, market columns, or model artifacts.
"""
from pathlib import Path
import ast
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
E=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
CANDIDATES=[
 R/"scripts/research/run_v2_stage006_feature_warehouse.py",
 E/"scripts/research/run_v2_stage006_feature_warehouse.py",
 R/"scripts/research/build_d45_frozen_pit_feature_matrix.py",
]
TOKENS=("read_csv","merge(","to_csv","LAB245","LAB090","LAB120","STAGE004","feature","source","current_distance","hist_runs")
def main():
 for p in CANDIDATES:
  if not p.exists():continue
  print("\nSOURCE",p)
  lines=p.read_text(encoding="utf-8-sig").splitlines()
  tree=ast.parse("\n".join(lines))
  print("LINES",len(lines),"IMPORTS",len([n for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))]))
  print("PATH_DECLARATIONS_AND_IO")
  for i,line in enumerate(lines,1):
   if any(t in line for t in TOKENS):
    print(f"{i:04d}: {line[:400]}")
 print("\nINSPECTION_COMPLETE; SOURCE_TEXT_ONLY; NO_OUTCOMES_READ; NO_SCORING")
if __name__=="__main__":main()
