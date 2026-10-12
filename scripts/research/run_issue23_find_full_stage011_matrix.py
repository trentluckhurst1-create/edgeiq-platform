from pathlib import Path
import csv,json
ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
report=ROOT/"outputs"/"research"/"model_v2"/"stage011_reproduction"/"STAGE011_REPRODUCTION_REPORT.json"
features=json.loads(report.read_text(encoding="utf-8-sig"))["features"]
need=set(features)
print("ISSUE23 — FIND EXACT 35-FEATURE TRAINING MATRIX")
print("READ_ONLY; HEADER SCAN ONLY; NO SEALED OUTCOMES")
print("REQUIRED_FEATURES="+repr(features))
roots=[ROOT/"outputs"/"research",ROOT/"edgeiq-platform"/"edgeiq-platform"/"outputs"/"research"]
hits=[];scanned=0
for base in roots:
 if not base.exists():continue
 for p in base.rglob("*.csv"):
  if p.stat().st_size>800_000_000:continue
  scanned+=1
  try:
   with p.open(encoding="utf-8-sig",errors="replace",newline="") as f:cols=next(csv.reader(f))
  except (OSError,StopIteration,csv.Error):continue
  overlap=need.intersection(cols)
  if len(overlap)>=25:
   hits.append((len(overlap),p,cols))
for n,p,cols in sorted(hits,key=lambda x:(-x[0],str(x[1])))[:50]:
 print("MATCH="+str(n)+"/"+str(len(features))+" FILE="+str(p)+" BYTES="+str(p.stat().st_size))
 print("MISSING="+repr(sorted(need-set(cols))))
 print("KEYS="+repr([x for x in ("_race","_horse","race_date","y","year","date") if x in cols]))
print(f"SCANNED={scanned} MATCHES_25_PLUS={len(hits)} FULL_MATCHES={sum(n==len(features) for n,_,_ in hits)}")
if not any(n==len(features) for n,_,_ in hits):print("STOP: NO COMPLETE_FEATURE_MATRIX — NEED REPRODUCTION SOURCE PATH OR REBUILD")
else:print("NEXT: VERIFY EXACT TRAINING ROW COUNTS, DATE CUTS, PIT CONTRACT, AND JOIN BEFORE FIT")
