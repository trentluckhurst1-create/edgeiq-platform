"""Issue23: trace existing feature construction and candidate live input coverage; no outcome access."""
from pathlib import Path
import ast
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
targets=[
 R/"scripts/research/run_v2_stage011_reproduction_artifact.py",
 R/"scripts/research/edgeiq_stage011_live_scorer.py",
 Path(__file__).with_name("run_issue23_full_feature_pairwise.py"),
]
terms=("def ","read_csv","merge(","FEATURES","feature","warehouse","canonical_horse_id","clean_finish","jockey_prior","trainer_prior")
for p in targets:
 print("\nSOURCE="+str(p)+" EXISTS="+str(p.is_file()))
 if not p.is_file():continue
 lines=p.read_text(encoding="utf-8-sig",errors="replace").splitlines()
 print("LINES="+str(len(lines)))
 for i,line in enumerate(lines,1):
  if any(t in line for t in terms):
   print(f"{i:04d}: {line[:230]}")
print("\nPOTENTIAL PIPELINE FILES")
for root in [R/"scripts/research",P/"scripts/research"]:
 if not root.is_dir():continue
 matches=[p for p in root.glob("*.py") if any(k in p.name.lower() for k in ("stage006","d45","stage011","live","pit_feature","feature_warehouse"))]
 for p in sorted(matches)[:70]:print(str(p))
print("AUDIT_ONLY=TRUE; NO_OUTCOMES_READ")
