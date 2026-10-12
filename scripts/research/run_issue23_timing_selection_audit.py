from pathlib import Path
import csv
from collections import Counter,defaultdict

P=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage006\V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv")
print("ISSUE23 TIMING AVAILABILITY SELECTION AUDIT")
print("READ_ONLY; 2025-26 EXCLUDED; DIAGNOSTIC ONLY; NO MODEL FIT")
if not P.exists():raise SystemExit("MISSING_SOURCE")
with P.open(encoding="utf-8-sig",newline="") as f:
 reader=csv.DictReader(f)
 needed={"race_date","_race","_horse","hist_runs","has_prior_timing_signal","current_distance","represented_field_size"}
 missing=needed-set(reader.fieldnames or [])
 if missing:raise SystemExit("MISSING_COLUMNS="+repr(sorted(missing)))
 groups=defaultdict(lambda:Counter())
 raceflags=defaultdict(lambda:[0,0])
 for row in reader:
  year=(row.get("race_date") or "")[:4]
  if year not in {"2021","2022","2023","2024"}:continue
  try:hist=float(row["hist_runs"])
  except (ValueError,TypeError):hist=-1
  try:field=float(row["represented_field_size"])
  except (ValueError,TypeError):field=-1
  try:dist=float(row["current_distance"])
  except (ValueError,TypeError):dist=-1
  present=str(row["has_prior_timing_signal"]).strip().lower() in {"1","1.0","true"}
  hband="0" if hist==0 else "1-2" if 0<hist<=2 else "3-5" if hist<=5 and hist>0 else "6-10" if hist<=10 and hist>0 else "11+" if hist>10 else "UNKNOWN"
  fband="<=8" if 0<field<=8 else "9-12" if 8<field<=12 else "13+" if field>12 else "UNKNOWN"
  dband="<1200" if 0<dist<1200 else "1200-1599" if 1200<=dist<1600 else "1600-1999" if 1600<=dist<2000 else "2000+" if dist>=2000 else "UNKNOWN"
  for axis,band in [("ALL","ALL"),("HIST_RUNS",hband),("FIELD",fband),("DISTANCE",dband)]:
   k=(year,axis,band);groups[k]["total"]+=1;groups[k]["present"]+=int(present)
  rk=(year,row["_race"])
  raceflags[rk][0]+=1;raceflags[rk][1]+=int(present)
 for (year,axis,band),v in sorted(groups.items()):
  n=v["total"];k=v["present"]
  print(f"YEAR={year} AXIS={axis} BAND={band} N={n} TIMED={k} COVERAGE={100*k/n:.2f}%")
 for year in ("2021","2022","2023","2024"):
  r=[v for (y,_),v in raceflags.items() if y==year]
  anytimed=sum(t>0 for n,t in r)
  half=sum(2*t>=n for n,t in r)
  full=sum(t==n for n,t in r)
  print(f"YEAR={year} RACES={len(r)} ANY_TIMED={anytimed} HALF_OR_MORE={half} FULL_TIMED={full}")
print("CAUTION=AVAILABILITY_BIAS_IS_NOT_CAUSAL_EVIDENCE; PROVENANCE_NOT_YET_CERTIFIED")
