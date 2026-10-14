from pathlib import Path
import ast
ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
names=["run_v2_stage011_reproduction_artifact.py","build_d45_frozen_pit_feature_matrix.py","run_v2_stage011_clean_placing.py"]
for name in names:
 p=ROOT/"scripts"/"research"/name
 print("\n"+"="*95+"\nSOURCE="+str(p))
 if not p.exists():print("MISSING");continue
 lines=p.read_text(encoding="utf-8-sig",errors="replace").splitlines()
 for i,line in enumerate(lines[:250],1):print(f"{i:03d} {line}")
print("\nSTOP: SOURCE INSPECTION ONLY")
