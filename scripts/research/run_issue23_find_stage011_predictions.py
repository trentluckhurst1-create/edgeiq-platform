from pathlib import Path
import csv
import re

ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
print("ISSUE23 — LOCATE FROZEN STAGE011 PREDICTIONS FOR INCREMENTAL TEST")
print("READ_ONLY HEADERS; NO OUTCOMES READ; NO MARKET")
roots=[ROOT/"outputs"/"research",ROOT/"edgeiq-platform"/"edgeiq-platform"/"outputs"/"research"]
found=[]
for base in roots:
 if not base.exists():continue
 for path in base.rglob("*.csv"):
  if not re.search(r"stage.?011|stage011|winner.rank|top.?1|champion",str(path),re.I):continue
  if path.stat().st_size>250_000_000:continue
  try:
   with path.open(encoding="utf-8-sig",errors="replace",newline="") as f:
    fields=next(csv.reader(f))
   lower=[x.lower() for x in fields]
   if any(x in lower for x in ("_race","race_key","race_id")) and any(x in lower for x in ("_horse","horse_key","runner_key")):
    found.append((str(path),path.stat().st_size,fields))
  except (OSError,StopIteration,UnicodeError):continue
for path,size,fields in sorted(found)[:40]:
 print("FILE="+path)
 print("BYTES="+str(size))
 print("COLUMNS="+repr(fields))
print("CANDIDATE_FILES="+str(len(found)))
if not found:print("STOP: NO_MATCHING_STAGE011_PREDICTION_CSV; NEED_EXPLICIT_BASELINE_PATH")
print("NEXT=STRICT_JOIN_AND_PAIRED_TOP1_TEST_ONLY_AFTER_BASELINE_IDENTIFIED")
