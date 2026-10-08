from pathlib import Path
import re
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
print("V2_STAGE024_CONTRACT EPI_ORIGINAL_BUILDER_RECOVERY NO_MODEL NO_MARKET_USE 2025_2026_SEALED")
roots=[ROOT/"scripts",ROOT/"docs",ROOT/"outputs"/"research"]
name_terms=("026","epi","performance_rating","flat_walk_forward")
content_terms=("edgeiq_certified_flat_walk_forward_epi_026","epi_value_026","LAB026","model_lab_026")
cands=[]
for base in roots:
 if not base.exists():continue
 for p in base.rglob("*"):
  if not p.is_file():continue
  s=str(p).lower()
  if any(t in p.name.lower() for t in name_terms):
   cands.append(p)
print("V2_STAGE024_FILENAME_CANDIDATES",len(cands))
for p in cands[:300]: print("V2_STAGE024_FILE",str(p))
# Source-like files only; search for definitions/writes rather than mere references.
hits=[]
for base in roots[:2]:
 if not base.exists():continue
 for p in base.rglob("*"):
  if not p.is_file() or p.suffix.lower() not in {".py",".md",".txt",".json",".yml",".yaml",".ps1"}:continue
  try:
   txt=p.read_text(encoding="utf-8",errors="ignore")
  except Exception:continue
  if any(t.lower() in txt.lower() for t in content_terms):
   lines=txt.splitlines()
   for i,line in enumerate(lines):
    lo=line.lower()
    if any(t.lower() in lo for t in content_terms):
     ctx=" || ".join(lines[max(0,i-3):min(len(lines),i+4)])
     score=sum(k in ctx.lower() for k in ["to_csv","epi_value_026 =","epi_value_026=","standard_time","lengths","performance_rating","walk_forward"])
     hits.append((score,p,i+1,ctx[:1800]))
hits.sort(key=lambda x:(-x[0],str(x[1]),x[2]))
print("V2_STAGE024_CONTENT_HITS",len(hits))
for score,p,line,ctx in hits[:250]:
 print("V2_STAGE024_HIT","SCORE",score,"FILE",str(p),"LINE",line,"CTX",ctx.replace("\n"," "))
print("V2_STAGE024_COMPLETE")
