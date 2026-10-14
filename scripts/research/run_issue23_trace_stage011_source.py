from pathlib import Path
import re
ROOTS=[Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH"),Path(r"C:\EDGEIQ_ISSUE23")]
TOKENS=("STAGE011_REPRODUCTION_REPORT","STAGE011_RUNNER_PROBABILITIES","clean_finish_hist_n","barrier_position_pct")
print("ISSUE23 — TRACE STAGE011 REPRODUCTION SOURCE")
print("READ_ONLY PYTHON SOURCE SCAN; NO MODEL FIT; NO SEALED OUTCOMES")
count=0;hits=[]
for root in ROOTS:
 if not root.exists():continue
 for p in root.rglob("*.py"):
  if any(part in {".git",".venv","venv","node_modules","__pycache__"} for part in p.parts):continue
  count+=1
  try:
   if p.stat().st_size>2_000_000:continue
   lines=p.read_text(encoding="utf-8-sig",errors="replace").splitlines()
  except OSError:continue
  matches=[(i+1,s.strip()[:220]) for i,s in enumerate(lines) if any(t in s for t in TOKENS)]
  if matches:hits.append((p,matches))
for p,matches in sorted(hits,key=lambda z:("stage011" not in str(z[0]).lower(),str(z[0])))[:45]:
 print("SOURCE="+str(p))
 for line,s in matches[:16]:print(f"  L{line}: {s}")
print(f"PYTHON_FILES_SCANNED={count} SOURCE_MATCHES={len(hits)}")
if not hits:print("STOP: REPRODUCTION_SOURCE_NOT_FOUND")
else:print("NEXT=INSPECT_REPRODUCTION_SCRIPT_AND_EXACT_UPSTREAM_INPUT_PATHS")
