from pathlib import Path
import csv
from collections import Counter, defaultdict

P=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage006\V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv")
print("ISSUE23 — TIMING MISSINGNESS AND WINNER ASSOCIATION")
print("DIAGNOSTIC ONLY; 2021-24 ONLY; NO MODEL FIT; NO MARKET; NO PROMOTION")
if not P.exists():raise SystemExit("MISSING_STAGE006")
tot=defaultdict(Counter)
race=defaultdict(list)
with P.open(encoding="utf-8-sig",newline="") as f:
 r=csv.DictReader(f)
 required={"race_date","_race","_horse","y","hist_runs","represented_field_size","has_prior_timing_signal"}
 if not required.issubset(set(r.fieldnames or [])):raise SystemExit("MISSING_COLUMNS="+repr(required-set(r.fieldnames or [])))
 for row in r:
  year=(row["race_date"] or "")[:4]
  if year not in {"2021","2022","2023","2024"}:continue
  try:
   win=int(float(row["y"]))
   hist=float(row["hist_runs"])
   field=float(row["represented_field_size"])
   timed=int(float(row["has_prior_timing_signal"])>0)
  except (TypeError,ValueError):continue
  if win not in (0,1):continue
  h="0" if hist==0 else "1-2" if 0<hist<=2 else "3-5" if 2<hist<=5 else "6-10" if 5<hist<=10 else "11+" if hist>10 else "unknown"
  fs="13+" if field>=13 else "<=12"
  for group in [(year,"ALL","ALL"),(year,"HIST",h),(year,"FIELD",fs),(year,"HIST_FIELD",h+"|"+fs)]:
   k=(group,timed);tot[k]["runners"]+=1;tot[k]["wins"]+=win
  race[(year,row["_race"])].append((win,timed))
for (year,axis,band),_ in sorted(set((g,0) for g,t in tot)|set((g,1) for g,t in tot)):
 a=tot[((year,axis,band),0)];b=tot[((year,axis,band),1)]
 if a["runners"]<100 or b["runners"]<100:continue
 ar=100*a["wins"]/a["runners"];br=100*b["wins"]/b["runners"]
 print(f"YEAR={year} AXIS={axis} BAND={band} UNT_N={a['runners']} UNT_WIN={ar:.3f}% TIM_N={b['runners']} TIM_WIN={br:.3f}% GAP_PP={br-ar:+.3f}")
for year in ("2021","2022","2023","2024"):
 eligible=[rows for (y,_),rows in race.items() if y==year and sum(w for w,t in rows)==1 and any(t for w,t in rows) and any(not t for w,t in rows)]
 if not eligible:continue
 winners_timed=sum(next(t for w,t in rows if w) for rows in eligible)
 expected=sum(sum(t for w,t in rows)/len(rows) for rows in eligible)
 print(f"YEAR={year} MIXED_RACES={len(eligible)} WINNERS_TIMED={winners_timed} EXPECTED_IF_RANDOM_WITHIN_RACE={expected:.2f} DIFFERENCE={winners_timed-expected:+.2f}")
print("INTERPRETATION=DESCRIPTIVE_ASSOCIATION_ONLY; CONFUNDING_BY_HORSE_EXPERIENCE_REMAINS")
