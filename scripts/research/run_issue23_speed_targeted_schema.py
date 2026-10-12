from pathlib import Path
import csv
import re

ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
BASE=ROOT / "edgeiq-platform" / "edgeiq-platform"
TARGETS=[
 BASE/"public/data/edgeiq_racingcom_performance_warehouse_v2.csv",
 BASE/"public/data/edgeiq_racingcom_canonical_runner_sectional_fact_v2_1.csv",
 BASE/"public/data/edgeiq_racingcom_canonical_runner_split_fact_v2_1.csv",
 BASE/"public/data/edgeiq_racingcom_canonical_runner_speed_fact_v2_1.csv",
 BASE/"src/data/edgeiq_live_sectional_intelligence_v1.csv",
 BASE/"src/data/edgeiq_race_shape_story_v1.csv",
 ROOT/"outputs/research/model_v2/stage006/V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv",
 ROOT/"outputs/research/issue10_pre2022_partition/ISSUE10_PRE2022_PIT_FEATURE_MATRIX.csv",
]
print("ISSUE23 TARGETED SPEED DATA SCHEMA / COVERAGE")
print("READ_ONLY; 2025_2026_ROWS_NOT_READ; NO MODEL TRAINING")
for path in TARGETS:
 print("\nFILE="+str(path))
 if not path.exists():
  print("STATUS=MISSING");continue
 try:
  with path.open("r",encoding="utf-8-sig",errors="replace",newline="") as f:
   reader=csv.reader(f)
   header=next(reader)
   print("SIZE_BYTES="+str(path.stat().st_size))
   print("COLUMNS="+repr(header))
   # Only inspect rows from public feature sources; never inspect any research matrices.
   if "outputs" in path.parts:
    print("ROW_SCAN=SKIPPED_RESEARCH_MATRIX")
    continue
   sample=[]
   for i,row in enumerate(reader):
    if len(row)!=len(header):continue
    if i>=10000:break
    if len(sample)<3:sample.append(row)
   print("ROWS_SCANNED_MAX=10000; SAMPLE_ROWS="+str(len(sample)))
   keys=[(j,h) for j,h in enumerate(header) if re.search(r"race.?date|meeting.?date|^date$|horse|runner|race.?id|meeting.?id|section|split|pace|speed|tempo|shape|^year$|source|status",h,re.I)]
   for row in sample:
    print("SAMPLE_KEYS="+repr({h:row[j][:65] for j,h in keys[:16]}))
 except Exception as e:
  print("ERROR="+repr(e))
print("\nNEXT=PROVENANCE_AND_JOIN_COVERAGE_AUDIT; DO_NOT_MODEL_YET")
