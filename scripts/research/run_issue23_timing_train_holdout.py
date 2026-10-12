from pathlib import Path
import csv,math
from collections import defaultdict,Counter

ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2")
print("ISSUE23 — TIMING FLAG TRAIN-ONLY CHALLENGER")
print("EXPLORATORY; FIT 2022-23; EVALUATE 2024 ONCE; NO MARKET; NO 2025-26")
pit={}
with (ROOT/"stage006"/"V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv").open(encoding="utf-8-sig",newline="") as f:
 for r in csv.DictReader(f):
  if (r["race_date"] or "")[:4] not in {"2022","2023","2024"}:continue
  key=(r["_race"],r["_horse"])
  if key in pit:raise SystemExit("STOP: duplicate PIT key")
  v=(r.get("has_prior_timing_signal") or "").strip().lower()
  if v not in {"true","false","1","0","1.0","0.0",""}:raise SystemExit("STOP: unexpected timing flag")
  pit[key]=int(v in {"true","1","1.0"})
races={}
for year in (2022,2023,2024):
 rr=defaultdict(list);seen=set()
 path=ROOT/"stage011_reproduction"/f"STAGE011_RUNNER_PROBABILITIES_{year}.csv"
 with path.open(encoding="utf-8-sig",newline="") as f:
  for r in csv.DictReader(f):
   key=(r["_race"],r["_horse"])
   if key in seen or key not in pit:raise SystemExit("STOP: duplicate/unmatched Stage011 key")
   seen.add(key)
   if (r["race_date"] or "")[:4]!=str(year):raise SystemExit("STOP: year mismatch")
   y=int(float(r["y"]));p=float(r["p"])
   if y not in (0,1) or not math.isfinite(p) or p<0 or p>1:raise SystemExit("STOP: invalid y/p")
   rr[r["_race"]].append((r["_horse"],y,p,pit[key]))
 if len(seen)!={2022:7459,2023:30163,2024:31234}[year]:raise SystemExit("STOP: population drift")
 if any(sum(x[1] for x in rows)!=1 for rows in rr.values()):raise SystemExit("STOP: race without exactly one winner")
 races[year]=rr
 print(f"YEAR={year} RUNNERS={len(seen)} RACES={len(rr)}")
def race_probs(rows,beta):
 scores=[max(p,1e-12)*math.exp(beta*t) for _,_,p,t in rows]
 z=sum(scores)
 return [s/z for s in scores]
def loss(years,beta):
 ll=0;n=0
 for year in years:
  for rows in races[year].values():
   q=race_probs(rows,beta)
   ll-=math.log(max(next(v for v,row in zip(q,rows) if row[1]),1e-15))
   n+=1
 return ll/n
# One predeclared, coarse one-dimensional search; no 2024 access until selection.
grid=[-0.6,-0.4,-0.2,0.0,0.2,0.4,0.6]
training=[(b,loss((2022,2023),b)) for b in grid]
print("TRAIN_2022_2023="+repr([(b,round(ll,7)) for b,ll in training]))
best=min(training,key=lambda x:(x[1],abs(x[0])))[0]
print(f"FROZEN_BETA={best:+.3f} SELECTED_ON=2022_2023")
for year in (2022,2023,2024):
 baseline=challenger=improved=worsened=same=0
 for rows in races[year].values():
  a=max(range(len(rows)),key=lambda i:(rows[i][2],rows[i][0]))
  q=race_probs(rows,best)
  b=max(range(len(rows)),key=lambda i:(q[i],rows[i][0]))
  wa=rows[a][1];wb=rows[b][1]
  baseline+=wa;challenger+=wb
  improved+=int(wb==1 and wa==0);worsened+=int(wb==0 and wa==1);same+=int(a==b)
 n=len(races[year])
 print(f"YEAR={year} ROLE={'EVALUATION' if year==2024 else 'TRAIN'} RACES={n} BASELINE_HITS={baseline} CHALLENGER_HITS={challenger} DELTA_HITS={challenger-baseline:+d} DELTA_PP={100*(challenger-baseline)/n:+.4f} IMPROVED={improved} WORSENED={worsened} UNCHANGED_PICK={same} BASELINE_LL={loss((year,),0):.7f} CHALLENGER_LL={loss((year,),best):.7f}")
print("NO_PROMOTION: PIT PROVENANCE UNCERTIFIED; 2024 NOW USED FOR THIS SINGLE EVALUATION")
