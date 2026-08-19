import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"

FORM = DATA / "edgeiq_form_guide_enriched_v2.json"
HIST = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"

OUT = ROOT / "docs" / "full-product-implementation" / "FORM_GUIDE_UNMATCHED_FORENSIC_AUDIT.txt"

def clean(v):
    return "" if v is None else str(v).strip()

def norm(v):
    return re.sub(r"[^A-Z0-9]+","",clean(v).upper())

def dist(v):
    t=clean(v)
    if not t:
        return ""
    try:
        f=float(t)
        return str(int(f)) if f.is_integer() else str(f)
    except:
        return t

def horse(v):
    x=norm(v)
    for s in ("AUS","NZ","GB","IRE","USA","FR","JPN"):
        if x.endswith(s) and len(x)>len(s)+2:
            x=x[:-len(s)]
    return x

with open(FORM,encoding="utf-8") as f:
    form=json.load(f)

hist_rows=list(csv.DictReader(open(HIST,encoding="utf-8-sig")))

full={}
nodist={}
notrack={}
nodate={}
nameonly={}

for r in hist_rows:

    h=horse(r["horse"])
    d=clean(r["race_date"])
    t=norm(r["track"])
    di=dist(r["distance"])

    full[(h,d,t,di)]=1
    nodist[(h,d,t)]=1
    notrack[(h,d,di)]=1
    nodate[(h,t,di)]=1
    nameonly[h]=1

counts=Counter()

examples=[]

for race in form["races"]:
    for runner in race["runners"]:

        h=horse(runner["runnerName"])

        for run in runner["fullForm"]:

            d=clean(run.get("date"))
            t=norm(run.get("track"))
            di=dist(run.get("distance"))

            if (h,d,t,di) in full:
                counts["FULL_MATCH"]+=1

            elif (h,d,t) in nodist:
                counts["DISTANCE_ONLY"]+=1
                if len(examples)<30:
                    examples.append(("DISTANCE",runner["runnerName"],d,t,di))

            elif (h,d,di) in notrack:
                counts["TRACK_ONLY"]+=1
                if len(examples)<30:
                    examples.append(("TRACK",runner["runnerName"],d,t,di))

            elif (h,t,di) in nodate:
                counts["DATE_ONLY"]+=1
                if len(examples)<30:
                    examples.append(("DATE",runner["runnerName"],d,t,di))

            elif h in nameonly:
                counts["NAME_ONLY"]+=1
                if len(examples)<30:
                    examples.append(("NAME",runner["runnerName"],d,t,di))

            else:
                counts["HORSE_NOT_PRESENT"]+=1
                if len(examples)<30:
                    examples.append(("NONE",runner["runnerName"],d,t,di))

lines=[]

lines.append("EDGEIQ FORM GUIDE UNMATCHED FORENSIC AUDIT")
lines.append("="*80)
lines.append("")

for k,v in counts.items():
    lines.append(f"{k}: {v}")

lines.append("")
lines.append("EXAMPLES")
lines.append("-"*80)

for e in examples:
    lines.append(str(e))

OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text("\n".join(lines),encoding="utf-8")

print("\n".join(lines))
print()
print(f"WROTE={OUT}")
print("EDGEIQ_FORM_GUIDE_UNMATCHED_FORENSIC_AUDIT_PASS")
