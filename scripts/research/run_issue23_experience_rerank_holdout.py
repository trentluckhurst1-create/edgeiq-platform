from pathlib import Path
import csv,math
from collections import defaultdict
ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2")
print("ISSUE23 — EXPERIENCE-AWARE STAGE011 RERANK TEST")
print("EXPLORATORY; TRAIN 2022-23; EVALUATE 2024; NO MARKET; NO 2025-26")
pit={}
with (ROOT/"stage006"/"V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv").open(encoding="utf-8-sig",newline="") as f:
 for r in csv.DictReader(f):
  if (r.get("race_date") or "")[:4] not in {"2022","2023","2024"}:continue
  key=(r["_race"],r["_horse"])
  if key in pit:raise SystemExit("STOP duplicate PIT")
  pit[key]=r
races={}
for year,expected in ((2022,7459),(2023,30163),(2024,31234)):
 rr=defaultdict(list);seen=set()
 with (ROOT/"stage011_reproduction"/f"STAGE011_RUNNER_PROBABILITIES_{year}.csv").open(encoding="utf-8-sig",newline="") as f:
  for r in csv.DictReader(f):
   key=(r["_race"],r["_horse"])
   if key in seen or key not in pit:raise SystemExit("STOP key mismatch")
   seen.add(key)
   if (r["race_date"] or "")[:4]!=str(year):raise SystemExit("STOP year mismatch")
   x=pit[key]
   try:
    y=int(float(r["y"]));p=float(r["p"])
    hist=float(x["hist_runs"]);dist=float(x["dist200_runs"])
   except (ValueError,TypeError):raise SystemExit("STOP invalid numeric")
   if y not in (0,1) or not 0<=p<=1 or not all(math.isfinite(v) for v in (p,hist,dist)):raise SystemExit("STOP invalid value")
   # Bounded, monotonic, prior-history-only adjustment. Two predeclared families.
   features={"hist":math.log1p(max(0,hist)),"distance":math.log1p(max(0,dist))}
   rr[r["_race"]].append((r["_horse"],y,p,features))
 if len(seen)!=expected or any(sum(row[1] for row in rows)!=1 for rows in rr.values()):raise SystemExit("STOP population mismatch")
 races[year]=rr
 print(f"YEAR={year} RUNNERS={len(seen)} RACES={len(rr)}")
def probs(rows,family,beta):
 logits=[math.log(max(row[2],1e-12))+beta*row[3][family] for row in rows]
 m=max(logits);ex=[math.exp(z-m) for z in logits];s=sum(ex)
 return [v/s for v in ex]
def logloss(years,family,beta):
 total=0;n=0
 for year in years:
  for rows in races[year].values():
   q=probs(rows,family,beta)
   total-=math.log(max(next(v for v,row in zip(q,rows) if row[1]),1e-15));n+=1
 return total/n
# All candidates fixed in advance. Selection uses 2022-23 ONLY.
candidates=[("hist",b) for b in (-0.3,-0.15,0.0,0.15,0.3)]+[("distance",b) for b in (-0.3,-0.15,0.15,0.3)]
train=[(fam,b,logloss((2022,2023),fam,b)) for fam,b in candidates]
for fam,b,ll in train:print(f"TRAIN FAMILY={fam} BETA={b:+.2f} LOGLOSS={ll:.7f}")
family,beta,_=min(train,key=lambda x:(x[2],abs(x[1]),x[0]))
print(f"FROZEN_CHALLENGER={family} BETA={beta:+.2f}")
for year in (2022,2023,2024):
 base=challenger=up=down=changed=0
 for rows in races[year].values():
  a=max(range(len(rows)),key=lambda i:(rows[i][2],rows[i][0]))
  q=probs(rows,family,beta)
  b=max(range(len(rows)),key=lambda i:(q[i],rows[i][0]))
  base+=rows[a][1];challenger+=rows[b][1]
  changed+=a!=b;up+=rows[a][1]==0 and rows[b][1]==1
  down+=rows[a][1]==1 and rows[b][1]==0
 n=len(races[year])
 print(f"YEAR={year} ROLE={'EVALUATION' if year==2024 else 'TRAIN'} RACES={n} BASE_HITS={base} CHALLENGER_HITS={challenger} DELTA_HITS={challenger-base:+d} DELTA_PP={100*(challenger-base)/n:+.4f} CHANGED={changed} CORRECTED={up} LOST={down} BASE_LL={logloss((year,),family,0):.7f} CHALLENGER_LL={logloss((year,),family,beta):.7f}")
print("NO_PROMOTION: RESEARCH YEARS ALREADY EXPLORED; NO UNTOUCHED FINAL VALIDATION")
