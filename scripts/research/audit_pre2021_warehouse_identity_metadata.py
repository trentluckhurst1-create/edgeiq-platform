"""Grok-approved single-file, identity/date-only archive audit. No outcomes."""
import argparse,csv,collections,datetime,pathlib,sys
p=argparse.ArgumentParser()
p.add_argument("--warehouse",required=True,help="EXACT path to the single results-warehouse CSV")
p.add_argument("--race-id",required=True,help="Exact header for race identifier")
p.add_argument("--runner-id",required=True,help="Exact header for runner identifier")
p.add_argument("--race-date",required=True,help="Exact header for race date")
a=p.parse_args()
f=pathlib.Path(a.warehouse)
if not f.is_file() or f.suffix.lower()!=".csv":sys.exit("STOP: exact warehouse CSV missing")
names=[a.race_id,a.runner_id,a.race_date]
if len(set(names))!=3:sys.exit("STOP: identifiers and date must be distinct columns")
counts=collections.defaultdict(lambda:[set(),0,0])
excluded=0
print("CONTRACT ONE_WAREHOUSE_CSV THREE_COLUMNS_ONLY NO_OUTCOMES NO_FIT NO_JOIN")
with f.open(encoding="utf-8-sig",newline="") as h:
 reader=csv.reader(h)
 try:header=next(reader)
 except StopIteration:sys.exit("STOP: empty file")
 missing=[n for n in names if n not in header]
 if missing:sys.exit("STOP: required column absent: "+repr(missing))
 idx=[header.index(n) for n in names]
 for lineno,row in enumerate(reader,2):
  if len(row)<=max(idx):sys.exit(f"STOP: malformed row at line {lineno}")
  rid,hid,raw=(row[i].strip() for i in idx)
  try:
   d=datetime.date.fromisoformat(raw[:10])
  except ValueError:sys.exit(f"STOP: unparseable date at line {lineno}; no further reads")
  if d.year>2020:
   excluded+=1
   continue
  s=counts[d.year]
  s[1]+=1
  if rid and hid:
   s[2]+=1
   s[0].add(rid)
print("YEAR RACES ROWS ROWS_WITH_BOTH_IDENTIFIERS BOTH_ID_RATE")
for year in sorted(counts):
 races,rows,both=counts[year]
 print(year,len(races),rows,both,f"{both/rows:.6f}" if rows else "NA")
print("POST_2020_EXCLUDED_ROWS",excluded)
print("TOTAL_PRE2021_UNIQUE_YEAR_RACE_PAIRS",sum(len(v[0]) for v in counts.values()))
print("STATUS METADATA_ONLY_EXPOSURE_REVIEW_REQUIRED; NO_FIT_AUTHORISED")
