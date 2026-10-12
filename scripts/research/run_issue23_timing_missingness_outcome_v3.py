from pathlib import Path
import csv
from collections import Counter,defaultdict

P=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage006\V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv")
print("ISSUE23 — TIMING MISSINGNESS OUTCOME V3")
print("READ_ONLY; 2021-24 ONLY; NO MARKET; NO MODEL FIT")
if not P.exists():raise SystemExit("STOP: missing Stage006")
def timing_flag(raw):
 s=(raw or "").strip().lower()
 if s in ("true","1","1.0"):return 1
 if s in ("false","0","0.0",""):return 0
 raise ValueError("unexpected timing flag: "+repr(raw))
groups=defaultdict(Counter);races=defaultdict(list);account=Counter();errors=[]
with P.open(encoding="utf-8-sig",newline="") as f:
 r=csv.DictReader(f)
 needed={"race_date","_race","_horse","y","hist_runs","represented_field_size","has_prior_timing_signal"}
 if needed-set(r.fieldnames or []):raise SystemExit("STOP: missing "+repr(sorted(needed-set(r.fieldnames or []))))
 for row in r:
  year=(row.get("race_date") or "")[:4]
  if year not in {"2021","2022","2023","2024"}:continue
  account["eligible"]+=1
  try:
   y=float(row["y"]);h=float(row["hist_runs"]);field=float(row["represented_field_size"])
   timed=timing_flag(row["has_prior_timing_signal"])
  except (TypeError,ValueError) as e:
   account["parse_failed"]+=1
   if len(errors)<5:errors.append((str(e),{k:row.get(k) for k in needed}))
   continue
  if y not in (0,1) or not row["_race"] or not row["_horse"]:
   account["invalid_outcome_or_key"]+=1;continue
  account["accepted"]+=1
  hband="0" if h==0 else "1-2" if 0<h<=2 else "3-5" if 2<h<=5 else "6-10" if 5<h<=10 else "11+" if h>10 else "UNKNOWN"
  fband="13+" if field>=13 else "<=12"
  for axis,band in (("ALL","ALL"),("HIST",hband),("FIELD",fband),("HIST_FIELD",hband+"|"+fband)):
   k=(year,axis,band,timed);groups[k]["runners"]+=1;groups[k]["wins"]+=int(y)
  races[(year,row["_race"])].append((int(y),timed))
print("ACCOUNT="+repr(dict(account)))
print("PARSE_EXAMPLES="+repr(errors))
if account["accepted"]==0 or account["parse_failed"]:raise SystemExit("STOP: invalid row accounting")
nprinted=0
for year,axis,band in sorted(set((yr,a,b) for yr,a,b,t in groups)):
 a=groups[(year,axis,band,0)];b=groups[(year,axis,band,1)]
 if a["runners"]<100 or b["runners"]<100:continue
 p0=100*a["wins"]/a["runners"];p1=100*b["wins"]/b["runners"]
 print(f"YEAR={year} AXIS={axis} BAND={band} NO_TIMING_N={a['runners']} NO_TIMING_WIN={p0:.3f}% TIMING_N={b['runners']} TIMING_WIN={p1:.3f}% GAP_PP={p1-p0:+.3f}")
 nprinted+=1
print("COMPARISONS="+str(nprinted))
for year in ("2021","2022","2023","2024"):
 eligible=[rows for (yr,_),rows in races.items() if yr==year and sum(w for w,t in rows)==1 and any(t for w,t in rows) and any(not t for w,t in rows)]
 observed=sum(next(t for w,t in rows if w) for rows in eligible)
 expected=sum(sum(t for w,t in rows)/len(rows) for rows in eligible)
 print(f"YEAR={year} MIXED_RACES={len(eligible)} TIMED_WINNERS={observed} RANDOM_EXPECTATION={expected:.2f} DIFFERENCE={observed-expected:+.2f}")
if not nprinted:raise SystemExit("STOP: no group comparisons")
print("PASS: ASSOCIATION_ONLY; NOT_PIT_CERTIFIED; NOT_A_MODEL_RESULT")
