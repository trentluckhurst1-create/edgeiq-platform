from pathlib import Path
import csv
from collections import Counter
from datetime import datetime
import re

ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
BASE=ROOT/"edgeiq-platform"/"edgeiq-platform"
FILES=[
 BASE/"public/data/edgeiq_racingcom_performance_warehouse_v2.csv",
 BASE/"public/data/edgeiq_racingcom_canonical_runner_sectional_fact_v2_1.csv",
 BASE/"public/data/edgeiq_racingcom_canonical_runner_split_fact_v2_1.csv",
 BASE/"public/data/edgeiq_racingcom_canonical_runner_speed_fact_v2_1.csv",
 BASE/"src/data/edgeiq_live_sectional_intelligence_v1.csv",
 BASE/"src/data/edgeiq_race_shape_story_v1.csv",
]
DATE_FIELDS=("race_date","meeting_date","date")
METRICS=("early_speed","mid_speed","late_speed","peak_speed","avg_speed","early_speed_source","mid_speed_source","late_speed_source","average_speed_source","segment_time_seconds","position_at_marker","position_at_split_end","tempo")
print("ISSUE23 HISTORICAL SECTIONAL DATE COVERAGE — READ ONLY")
print("NO_OUTCOMES_OR_PRICES_ACCESSED; NO_MODEL_FIT")
for path in FILES:
 print("\nSOURCE="+str(path))
 if not path.exists():
  print("MISSING");continue
 with path.open(encoding="utf-8-sig",errors="replace",newline="") as f:
  reader=csv.DictReader(f)
  fields=reader.fieldnames or []
  dcol=next((x for x in DATE_FIELDS if x in fields),None)
  if not dcol:
   print("DATE_COLUMN_MISSING");continue
  counts=Counter(); unique=Counter(); filled=Counter(); bad=0; total=0
  keycol=next((x for x in ("runner_key","warehouse_record_id","horse_key","horse_name","horse") if x in fields),None)
  for row in reader:
   total+=1
   date=(row.get(dcol) or "")[:10]
   if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",date):
    bad+=1;continue
   year=date[:4]
   counts[year]+=1
   if keycol and row.get(keycol):
    unique[year]+=1
   for metric in METRICS:
    if metric in fields and (row.get(metric) or "").strip():
     filled[(year,metric)]+=1
  print("TOTAL_ROWS="+str(total)+"; BAD_DATES="+str(bad))
  print("YEAR_COUNTS="+str(dict(sorted(counts.items()))))
  print("AVAILABLE_METRICS="+repr([m for m in METRICS if m in fields]))
  for year in sorted(counts):
   if year not in {"2021","2022","2023","2024"}:continue
   print(f"YEAR={year} ROWS={counts[year]} NONEMPTY_METRIC_COUNTS="+repr({m:filled[(year,m)] for m in METRICS if m in fields}))
print("\nVERDICT_RULE=IF_2022_2024_ZERO_DO_NOT_TRAIN_ON_THESE_SOURCES")
