"""Inspect Stage006/D45 build contracts and live source suitability without loading outcome tables."""
from pathlib import Path
ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\scripts\research")
names=["run_v2_stage006_feature_warehouse.py","build_d45_frozen_pit_feature_matrix.py","fit_stage011_research_2024.py","edgeiq_live_identity_audit.py"]
terms=("read_csv","read_parquet","to_csv","def ","SOURCE","ROOT","Path(","canonical","race_date","shift(","merge(","sort_values","FEATURE","output","argparse")
for name in names:
 p=ROOT/name
 print("\n"+"="*88+"\nFILE="+str(p)+" EXISTS="+str(p.exists()))
 if not p.exists():continue
 lines=p.read_text(encoding="utf-8-sig",errors="replace").splitlines()
 print("TOTAL_LINES="+str(len(lines)))
 for i,line in enumerate(lines,1):
  if any(k in line for k in terms):
   print(f"{i:04d} {line[:220]}")
print("\nREAD_ONLY_SOURCE_INSPECTION_COMPLETE")
