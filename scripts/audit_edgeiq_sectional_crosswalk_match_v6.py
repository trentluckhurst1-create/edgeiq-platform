from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
TARGETS = [
    DATA / "edgeiq_sectional_payload_reconstruction_v1.csv",
    DATA / "sectionals.csv",
]
REFERENCE = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
OUT_SUMMARY = DATA / "edgeiq_sectional_crosswalk_match_v6_summary.csv"
OUT_MATCHES = DATA / "edgeiq_sectional_crosswalk_match_v6_matches.csv"
OUT_AMBIG = DATA / "edgeiq_sectional_crosswalk_match_v6_ambiguous.csv"

MISSING={"","-","nan","none","null","undefined","n/a"}
ALIASES={
 "date":("race_date","date","meeting_date","run_date"),
 "track":("track","venue","meeting","track_name"),
 "horse":("horse_name","horse","runner_name","runner","name"),
 "horse_id":("canonical_horse_id","horse_id","horse_key","runner_id","runner_key"),
 "distance":("distance","race_distance","dist","race_distance_metres"),
 "race_no":("race_no","race_number","race"),
 "race_id":("canonical_race_id","race_id","racingcom_race_id","raceid"),
}

def clean(v):
 s=str(v or "").strip(); return "" if s.lower() in MISSING else s

def nk(s): return re.sub(r"[^a-z0-9]+","",clean(s).lower())
def nt(s): return " ".join(clean(s).upper().replace("_"," ").split())
def nh(s): return re.sub(r"[^A-Z0-9]","",clean(s).upper())
def nd(s):
 x=re.sub(r"[^0-9.]","",clean(s));
 if not x:return ""
 try:return str(int(round(float(x))))
 except:return ""
def nr(s):
 x=re.sub(r"[^0-9]","",clean(s)); return str(int(x)) if x else ""
def date_norm(s):
 s=clean(s)[:10]
 for f in ("%Y-%m-%d","%d/%m/%Y","%Y/%m/%d","%d-%m-%Y"):
  try:return datetime.strptime(s,f).strftime("%Y-%m-%d")
  except:pass
 return s

def find(fields, aliases):
 d={nk(x):x for x in fields}
 for a in aliases:
  if nk(a) in d:return d[nk(a)]
 return ""
def cmap(fields):return {k:find(fields,v) for k,v in ALIASES.items()}
def g(r,c,k):return clean(r.get(c.get(k,""))) if c.get(k) else ""

def main():
 if not REFERENCE.exists(): raise SystemExit(f"Missing reference: {REFERENCE}")
 # Exact historical reference indexes. No fuzzy matching.
 indexes={"DTHD":defaultdict(set),"DTH":defaultdict(set),"DHD":defaultdict(set)}
 ref_rows=0; ref_valid=0
 with REFERENCE.open("r",newline="",encoding="utf-8-sig") as h:
  rd=csv.DictReader(h); c=cmap(list(rd.fieldnames or []))
  print("REFERENCE_COLUMNS",c)
  for r in rd:
   ref_rows+=1
   d=date_norm(g(r,c,"date")); t=nt(g(r,c,"track")); hname=nh(g(r,c,"horse") or g(r,c,"horse_id")); dist=nd(g(r,c,"distance")); rn=nr(g(r,c,"race_no")); rid=g(r,c,"race_id")
   if not (d and t and hname and rn):continue
   ref_valid+=1; val=(rn,rid)
   if dist:indexes["DTHD"][(d,t,hname,dist)].add(val)
   indexes["DTH"][(d,t,hname)].add(val)
   if dist:indexes["DHD"][(d,hname,dist)].add((t,rn,rid))

 counts=Counter(); matches=[]; amb=[]
 for path in TARGETS:
  if not path.exists():continue
  with path.open("r",newline="",encoding="utf-8-sig") as h:
   rd=csv.DictReader(h); c=cmap(list(rd.fieldnames or [])); print("TARGET_COLUMNS",path.name,c)
   for rowno,r in enumerate(rd,2):
    counts["target_rows"]+=1
    existing=nr(g(r,c,"race_no"))
    if existing: counts["already_has_race_no"]+=1; continue
    counts["target_missing_race_no"]+=1
    d=date_norm(g(r,c,"date")); t=nt(g(r,c,"track")); horse=nh(g(r,c,"horse") or g(r,c,"horse_id")); dist=nd(g(r,c,"distance"))
    method=""; vals=set()
    if d and t and horse and dist:
     vals=indexes["DTHD"].get((d,t,horse,dist),set()); method="EXACT_DATE_TRACK_HORSE_DISTANCE"
    if not vals and d and t and horse:
     vals=indexes["DTH"].get((d,t,horse),set()); method="EXACT_DATE_TRACK_HORSE"
    # Track recovery is allowed only if date+horse+distance maps to exactly one track/race.
    if not vals and d and horse and dist and not t:
     x=indexes["DHD"].get((d,horse,dist),set())
     if len(x)==1:
      tr,rn,rid=next(iter(x)); vals={(rn,rid)}; t=tr; method="EXACT_DATE_HORSE_DISTANCE_UNIQUE_TRACK"
     elif len(x)>1:
      counts["ambiguous_unique_track"]+=1
    if len(vals)==1:
     rn,rid=next(iter(vals)); counts["exact_unique_matches"]+=1; counts[method]+=1
     if len(matches)<5000: matches.append({"source_file":str(path.relative_to(ROOT)),"row_no":rowno,"race_date":d,"track":t,"horse_key":horse,"distance":dist,"recovered_race_no":rn,"recovered_race_id":rid,"identity_method":method})
    elif len(vals)>1:
     counts["ambiguous_matches"]+=1
     if len(amb)<1000: amb.append({"source_file":str(path.relative_to(ROOT)),"row_no":rowno,"race_date":d,"track":t,"horse_key":horse,"distance":dist,"candidate_count":len(vals),"candidates":"|".join(sorted(f"{a}:{b}" for a,b in vals))})
    else: counts["unmatched"]+=1

 with OUT_SUMMARY.open("w",newline="",encoding="utf-8") as h:
  w=csv.writer(h); w.writerow(["metric","value"]); w.writerow(["reference_rows",ref_rows]); w.writerow(["reference_valid_rows",ref_valid]);
  for k,v in counts.items():w.writerow([k,v])
 def write(path,rows,fields):
  with path.open("w",newline="",encoding="utf-8") as h:
   w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(rows)
 write(OUT_MATCHES,matches,["source_file","row_no","race_date","track","horse_key","distance","recovered_race_no","recovered_race_id","identity_method"])
 write(OUT_AMBIG,amb,["source_file","row_no","race_date","track","horse_key","distance","candidate_count","candidates"])
 print("="*90);print("EDGEIQ SECTIONAL HISTORICAL CROSSWALK MATCH AUDIT V6");print("="*90)
 print("reference_rows:",ref_rows);print("reference_valid_rows:",ref_valid)
 for k,v in counts.items():print(f"{k}: {v}")
 print("SUMMARY:",OUT_SUMMARY);print("MATCHES:",OUT_MATCHES);print("AMBIGUOUS:",OUT_AMBIG)

if __name__=="__main__":main()
