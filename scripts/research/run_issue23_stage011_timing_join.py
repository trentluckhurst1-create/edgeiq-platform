from pathlib import Path
import csv
from collections import Counter,defaultdict
from math import sqrt

ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2")
PIT=ROOT/"stage006"/"V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv"
PRED=ROOT/"stage011_reproduction"
print("ISSUE23 STAGE011 STRICT JOIN + TIMING ASSOCIATION")
print("READ_ONLY; 2022-24; NO MARKET; NO MODEL FIT; NO ADJUSTMENT")
flags={};dup=0
with PIT.open(encoding="utf-8-sig",newline="") as f:
 r=csv.DictReader(f)
 for x in r:
  yr=(x.get("race_date") or "")[:4]
  if yr not in {"2022","2023","2024"}:continue
  k=(x["_race"],x["_horse"])
  if k in flags:dup+=1
  raw=(x.get("has_prior_timing_signal") or "").strip().lower()
  if raw not in ("true","false","1","0","1.0","0.0",""):raise SystemExit("STOP: unknown timing flag")
  flags[k]=raw in ("true","1","1.0")
if dup:raise SystemExit(f"STOP: duplicate PIT keys {dup}")
print("PIT_KEYS="+str(len(flags)))
for year in ("2022","2023","2024"):
 path=PRED/f"STAGE011_RUNNER_PROBABILITIES_{year}.csv"
 if not path.exists():raise SystemExit("STOP: missing "+str(path))
 races=defaultdict(list);stats=Counter();seen=set()
 with path.open(encoding="utf-8-sig",newline="") as f:
  for x in csv.DictReader(f):
   if (x.get("race_date") or "")[:4]!=year:raise SystemExit("STOP: year mismatch")
   k=(x["_race"],x["_horse"])
   if k in seen:raise SystemExit("STOP: duplicate prediction key")
   seen.add(k)
   if k not in flags:
    stats["unmatched"]+=1;continue
   try:y=int(float(x["y"]));p=float(x["p"])
   except (ValueError,TypeError):raise SystemExit("STOP: invalid y/p")
   if y not in (0,1) or not 0<=p<=1:raise SystemExit("STOP: invalid probability/outcome")
   races[x["_race"]].append((x["_horse"],y,p,flags[k]))
   stats["matched"]+=1
 print(f"YEAR={year} MATCHED={stats['matched']} UNMATCHED={stats['unmatched']} MATCH_RATE={stats['matched']/(stats['matched']+stats['unmatched']):.5f}")
 if stats["unmatched"]:raise SystemExit("STOP: incomplete join")
 valid=0;top1=0;top1_timed=0;top1_untimed=0;wins_timed=0;wins_untimed=0;errors_timed=0;errors_untimed=0
 rank=defaultdict(Counter)
 for race,rows in races.items():
  if sum(y for _,y,_,_ in rows)!=1:continue
  valid+=1
  ranked=sorted(rows,key=lambda t:(-t[2],t[0]))
  chosen=ranked[0]
  top1+=chosen[1]
  if chosen[3]:
   top1_timed+=1;wins_timed+=chosen[1];errors_timed+=1-chosen[1]
  else:
   top1_untimed+=1;wins_untimed+=chosen[1];errors_untimed+=1-chosen[1]
  for i,(_,y,p,t) in enumerate(ranked):
   if y:rank["WINNER_RANK"][str(min(i+1,4))]+=1
 print(f"YEAR={year} VALID_RACES={valid} STAGE011_TOP1_CORRECT={top1} HIT_RATE={top1/valid:.5f}")
 print(f"YEAR={year} TOP1_TIMED={top1_timed} TIMED_CORRECT={wins_timed} TIMED_HIT_RATE={wins_timed/top1_timed if top1_timed else 0:.5f}")
 print(f"YEAR={year} TOP1_UNTIMED={top1_untimed} UNTIMED_CORRECT={wins_untimed} UNTIMED_HIT_RATE={wins_untimed/top1_untimed if top1_untimed else 0:.5f}")
 print(f"YEAR={year} WINNER_RANK_COUNTS="+repr(dict(rank["WINNER_RANK"])))
print("NEXT=PREDECLARE_TRAIN_ONLY_TIMING_ADJUSTMENT_AND_HOLDOUT_PAIRED_TEST")
