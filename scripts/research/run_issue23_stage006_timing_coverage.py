from pathlib import Path
import csv
from collections import Counter,defaultdict

P=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage006\V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv")
print("ISSUE23 — STAGE006 HISTORICAL TIMING COVERAGE")
print("READ_ONLY; 2025_2026_ROWS_EXCLUDED_BEFORE_METRIC_ACCESS; NO_MODEL_FIT")
if not P.exists():raise SystemExit("MISSING "+str(P))
with P.open(encoding="utf-8-sig",newline="") as f:
 reader=csv.DictReader(f)
 cols=reader.fieldnames or []
 timing=[c for c in cols if c.startswith("timing_") or c=="has_prior_timing_signal"]
 keys=["_race","_horse","race_date","year","date"]
 print("TIMING_COLUMNS="+repr(timing))
 print("KEY_COLUMNS="+repr([k for k in keys if k in cols]))
 totals=Counter();present=Counter();unique_races=defaultdict(set);dupes=Counter();seen=set()
 for row in reader:
  date=(row.get("race_date") or row.get("date") or "")[:10]
  year=date[:4] if len(date)>=4 else str(row.get("year") or "")
  if year not in {"2021","2022","2023","2024"}:continue
  totals[year]+=1
  race=row.get("_race","")
  if race:unique_races[year].add(race)
  key=(race,row.get("_horse",""))
  if key in seen:dupes[year]+=1
  seen.add(key)
  for col in timing:
   value=(row.get(col) or "").strip()
   if value and value.lower() not in {"nan","none","null"}:
    try:
     if col in {"has_prior_timing_signal","timing_authority_present"} and float(value)==0:continue
    except ValueError:pass
    present[(year,col)]+=1
 for year in sorted(totals):
  print(f"YEAR={year} RUNNERS={totals[year]} RACES={len(unique_races[year])} DUPLICATE_RACE_HORSE={dupes[year]}")
  for col in timing:
   n=present[(year,col)]
   print(f"  {col}: {n}/{totals[year]} ({100*n/totals[year]:.2f}%)")
print("NEXT=VERIFY_PIT_PROVENANCE_AND_STAGE011_OVERLAP_BEFORE_ANY_TRAINING")
