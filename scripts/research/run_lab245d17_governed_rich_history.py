from pathlib import Path
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
P=ROOT/"outputs/research/model_lab_031/build_certified_current_context_031.py"
print("FILE",P,"EXISTS",P.exists())
if P.exists():
 s=P.read_text(encoding="utf-8-sig",errors="replace").splitlines()
 for i,line in enumerate(s):
  if any(k in line for k in ["read_csv","to_csv","race_class","track_condition","canonical_race_id","canonical_horse_id","OUTPUT","OUT","MODEL","merge("]):
   print(f"{i+1}: {line}")
