"""Read-only candidate novelty/PIT lineage audit. Never runs experiment scripts."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
TOKENS=["prior_same_jockey_starts","prior_same_trainer_starts","jockey_prior_residual_mean_shrunk_037","trainer_prior_residual_mean_shrunk_037"]
print("CONTRACT CONNECTION_NOVELTY SOURCE_INSPECTION_ONLY NO_FIT NO_MARKET")
for token in TOKENS:
 print("FEATURE",token)
 matches=[]
 for p in (ROOT/"research").glob("*.py"):
  if p.name==Path(__file__).name:continue
  try:s=p.read_text(encoding="utf-8")
  except (OSError,UnicodeError):continue
  if token in s:
   lines=s.splitlines()
   for n,line in enumerate(lines,1):
    if token in line:matches.append((p.name,n,line.strip()[:200]))
 print("SCRIPT_OCCURRENCES",len(matches))
 for f,n,line in matches[:30]:print("HIT",f,n,line)
 print("STATUS UNVERIFIED — indirect inclusion through inherited feature lists requires manual review")
print("NOTE A source column present in earlier scripts is not proof of a fitted model; absence of text is not proof of novelty.")
print("PIT_CERTIFICATION NOT_ESTABLISHED")
