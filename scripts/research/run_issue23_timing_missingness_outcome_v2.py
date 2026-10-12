from pathlib import Path
import csv
from collections import Counter,defaultdict

P=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage006\V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv")
print("ISSUE23 — TIMING MISSINGNESS OUTCOME DIAGNOSTIC V2")
print("READ_ONLY; 2021-2024 ONLY; NO MARKET; NO MODEL FIT")
if not P.exists():raise SystemExit("STOP: missing Stage006 file")
groups=defaultdict(Counter); races=defaultdict(list); exclusions=Counter(); samples=defaultdict(list)
with P.open(encoding="utf-8-sig",newline="") as f:
 reader=csv.DictReader(f)
 cols=set(reader.fieldnames or [])
 required={"race_date","_race","_horse","y","hist_runs","represented_field_size","has_prior_timing_signal"}
 if required-cols:raise SystemExit("STOP: missing columns "+repr(sorted(required-cols)))
 for row in reader:
  yr=(row.get("race_date") or "")[:4]
  if yr not in {"2021","2022","2023","2024"}:
   exclusions["outside_window"]+=1;continue
  exclusions["eligible_year"]+=1
  try:
   y=float(row["y"]);h=float(row["hist_runs"]);field=float(row["represented_field_size"]);timing=float(row["has_prior_timing_signal"])
  except (ValueError,TypeError):
   exclusions["parse_failed"]+=1
   if len(samples["parse_failed"])<3:samples["parse_failed"].append({k:row.get(k) for k in required})
   continue
  if y not in (0,1):
   exclusions["invalid_y"]+=1;continue
  if not row["_race"] or not row["_horse"]:
   exclusions["missing_identity"]+=1;continue
  exclusions["accepted"]+=1
  timed=int(timing>0)
  hband="0" if h==0 else "1-2" if 0<h<=2 else "3-5" if 2<h<=5 else "6-10" if 5<h<=10 else "11+" if h>10 else "UNKNOWN"
  fband="13+" if field>=13 else "<=12"
  for axis,band in (("ALL","ALL"),("HIST",hband),("FIELD",fband),("HIST_FIELD",hband+"|"+fband)):
   group=(yr,axis,band,timed);groups[group]["runners"]+=1;groups[group]["wins"]+=int(y)
  races[(yr,row["_race"])].append((int(y),timed))
print("ROW_ACCOUNTING="+repr(dict(exclusions)))
for name,rows in samples.items():print("REJECT_EXAMPLES_"+name+"="+repr(rows))
if exclusions["accepted"]==0:raise SystemExit("STOP: ZERO_ACCEPTED_ROWS — diagnose schema/values")
printed=0
for yr,axis,band in sorted(set((a,b,c) for a,b,c,t in groups)):
 a=groups[(yr,axis,band,0)];b=groups[(yr,axis,band,1)]
 if a["runners"]<100 or b["runners"]<100:continue
 ar=100*a["wins"]/a["runners"];br=100*b["wins"]/b["runners"]
 print(f"YEAR={yr} AXIS={axis} BAND={band} NO_TIMING_N={a['runners']} NO_TIMING_WIN={ar:.3f}% TIMING_N={b['runners']} TIMING_WIN={br:.3f}% GAP_PP={br-ar:+.3f}")
 printed+=1
print("COMPARISONS_PRINTED="+str(printed))
for yr in ("2021","2022","2023","2024"):
 eligible=[r for (y,_),r in races.items() if y==yr and sum(w for w,t in r)==1 and any(t for w,t in r) and any(not t for w,t in r)]
 observed=sum(next(t for w,t in r if w) for r in eligible)
 expected=sum(sum(t for w,t in r)/len(r) for r in eligible)
 print(f"YEAR={yr} MIXED_RACES={len(eligible)} WINNERS_TIMED={observed} EXPECTED_RANDOM_WITHIN_RACE={expected:.2f} DIFFERENCE={observed-expected:+.2f}")
if not printed:raise SystemExit("STOP: NO_VALID_GROUP_COMPARISONS")
print("PASS: DESCRIPTIVE ASSOCIATION ONLY; NO PIT CERTIFICATION")
