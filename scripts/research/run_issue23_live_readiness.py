"""Issue23: inspect prospective feature readiness without reading sealed outcomes."""
from pathlib import Path
import json
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
paths={
 "STAGE011_REPRODUCTION_SOURCE":R/"scripts/research/run_v2_stage011_reproduction_artifact.py",
 "STAGE011_LIVE_SCORER":R/"scripts/research/edgeiq_stage011_live_scorer.py",
 "ISSUE23_FULL_PAIRWISE":Path(__file__).with_name("run_issue23_full_feature_pairwise.py"),
 "STAGE006_WAREHOUSE":R/"outputs/research/model_v2/stage006/V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv",
 "D45_MATRIX":R/"outputs/research/profitability_program/d45/D45_FROZEN_PIT_FEATURE_MATRIX.csv",
 "PERF026":P/"outputs/research/model_lab_026/edgeiq_certified_flat_walk_forward_epi_026.csv",
 "CURRENT_CONTEXT":P/"outputs/research/model_lab_031/certified_current_race_context_031.csv",
}
print("ISSUE23 — PROSPECTIVE READINESS INVENTORY")
for name,path in paths.items():
 print(f"{name} EXISTS={path.is_file()} PATH={path}")
 if path.is_file() and path.suffix==".py" and name in {"STAGE011_LIVE_SCORER"}:
  print("SOURCE_BEGIN")
  for i,line in enumerate(path.read_text(encoding="utf-8-sig",errors="replace").splitlines()[:220],1):print(f"{i:03d} {line}")
  print("SOURCE_END")
print("NO FIT; NO OUTCOME READ; NO PRODUCTION CHANGE")
