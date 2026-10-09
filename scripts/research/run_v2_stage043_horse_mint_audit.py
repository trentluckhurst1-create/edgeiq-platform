from pathlib import Path
import re, subprocess
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
print("V2_STAGE043_CONTRACT BOUNDED_SOURCE_MINT_AUDIT NO_MODEL NO_FUZZY NO_MARKET SEALED")
roots=[R/"scripts",P/"scripts"]
pattern=re.compile(r"EIQ_HORSE_|_horse\s*=|\[\s*['\"]_horse['\"]\s*\]\s*=|canonical_horse_id.*hash|hash.*canonical_horse_id",re.I)
hits=[]
for root in roots:
 if not root.exists():continue
 for p in root.rglob("*.py"):
  if any(s in str(p).lower() for s in ("node_modules",".venv","site-packages")):continue
  try:
   for i,line in enumerate(p.read_text(encoding="utf-8-sig",errors="replace").splitlines(),1):
    if pattern.search(line):
     hits.append((str(p),i,line.strip()[:250]))
  except OSError:continue
print("V2_STAGE043_SOURCE_HITS",len(hits))
for path,n,line in hits[:120]:print("V2_STAGE043_HIT",path,"LINE",n,"TEXT",line)
print("V2_STAGE043_WAREHOUSE_SCHEMA _horse EIQ_HORSE_HASH_NAMESPACE")
print("V2_STAGE043_OFFICIAL_SCHEMA horse_key NORMALIZED_NAME_NAMESPACE")
print("V2_STAGE043_DECISION STOP_NO_CERTIFIED_PURE_MINT_YET")
print("V2_STAGE043_NOTE This is source-level discovery only; any discovered expression requires independent purity proof before a join")
print("V2_STAGE043_COMPLETE")
