from pathlib import Path
import csv
from collections import defaultdict,Counter
ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2")
PIT=ROOT/"stage006"/"V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv"
print("ISSUE23 — STAGE011 TOP1 MISSED WINNER PAIRWISE GAP PROFILE")
print("READ_ONLY; 2022-2024; NO MARKET; NO FIT; NO 2025-26")
features=["hist_runs","days_since_last","dist200_runs","lvs_last1","lvs_mean3","lvs_mean5","margin_mean5","margin_last1","last_distance","current_distance"]
pit={}
with PIT.open(encoding="utf-8-sig",newline="") as f:
 reader=csv.DictReader(f)
 missing=set(features)-set(reader.fieldnames or [])
 if missing:raise SystemExit("STOP: missing "+repr(sorted(missing)))
 for r in reader:
  if (r.get("race_date") or "")[:4] not in {"2022","2023","2024"}:continue
  k=(r["_race"],r["_horse"])
  if k in pit:raise SystemExit("STOP: duplicate PIT key")
  pit[k]=r
for year in (2022,2023,2024):
 path=ROOT/"stage011_reproduction"/f"STAGE011_RUNNER_PROBABILITIES_{year}.csv"
 races=defaultdict(list);n=0
 with path.open(encoding="utf-8-sig",newline="") as f:
  for r in csv.DictReader(f):
   k=(r["_race"],r["_horse"])
   if k not in pit:raise SystemExit("STOP: unmatched "+repr(k))
   if (r["race_date"] or "")[:4]!=str(year):raise SystemExit("STOP: year mismatch")
   races[r["_race"]].append((r["_horse"],int(float(r["y"])),float(r["p"]),pit[k]))
   n+=1
 profile=defaultdict(Counter);gaps=defaultdict(list);counts=Counter()
 for rk,rows in races.items():
  if sum(x[1] for x in rows)!=1:raise SystemExit("STOP: invalid winner count")
  ranked=sorted(rows,key=lambda x:(-x[2],x[0]))
  top=ranked[0];win=next(x for x in rows if x[1])
  if top[1]:continue
  counts["missed"]+=1
  rank=next(i+1 for i,x in enumerate(ranked) if x[1])
  band="R2" if rank==2 else "R3" if rank==3 else "R4+"
  gap=top[2]-win[2]
  gapband="<.02" if gap<.02 else ".02-.05" if gap<.05 else ".05-.10" if gap<.10 else ">=.10"
  counts[(band,gapband)]+=1
  for feature in features:
   try:a=float(win[3][feature]);b=float(top[3][feature])
   except (TypeError,ValueError):continue
   if not all(map(__import__("math").isfinite,(a,b))):continue
   c=profile[(band,feature)];c["n"]+=1;c["winner_higher"]+=a>b;c["winner_lower"]+=a<b;c["tie"]+=a==b
   gaps[(band,feature)].append(a-b)
 print(f"YEAR={year} RUNNERS={n} RACES={len(races)} MISSED_TOP1={counts['missed']}")
 for band in ("R2","R3","R4+"):
  print(f"YEAR={year} BAND={band} GAP_COUNTS="+repr({g:counts[(band,g)] for g in ("<.02",".02-.05",".05-.10",">=.10")}))
  for feature in features:
   c=profile[(band,feature)]
   if c["n"]<30:continue
   values=sorted(gaps[(band,feature)])
   med=values[len(values)//2]
   print(f"YEAR={year} BAND={band} FEATURE={feature} PAIRS={c['n']} WINNER_HIGHER={c['winner_higher']/c['n']:.3f} WINNER_LOWER={c['winner_lower']/c['n']:.3f} MEDIAN_WINNER_MINUS_TOP={med:.4f}")
print("DESCRIPTIVE_ONLY; SELECT_NEXT_EXPERIMENT_USING_PREDECLARED_MECHANISM_NOT_BEST_LOOKING_SLICE")
