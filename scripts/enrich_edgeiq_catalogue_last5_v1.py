from __future__ import annotations
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; P=ROOT/'public/data/edgeiq_three_day_product_catalog_v1.json'
def deep_arrays(o,keys,d=0):
 if d>8:return None
 if isinstance(o,dict):
  for k in keys:
   if isinstance(o.get(k),list) and o[k]:return o[k]
  for v in o.values():
   x=deep_arrays(v,keys,d+1)
   if x:return x
 elif isinstance(o,list):
  for v in o:
   x=deep_arrays(v,keys,d+1)
   if x:return x
 return None
def pos(run):
 if not isinstance(run,dict):return str(run or '').strip()
 for k in ('finishPosition','finish_position','finishingPosition','position','placing','place','finish','result'):
  v=run.get(k)
  if v not in (None,''):
   m=re.search(r'\d+',str(v));return m.group(0) if m else str(v).strip()
 return ''
def main():
 d=json.loads(P.read_text(encoding='utf-8-sig'));filled=0
 for m in d.get('meetings') or []:
  for race in m.get('races') or []:
   for r in race.get('runners') or []:
    if r.get('lastFive') or r.get('last5'):continue
    runs=deep_arrays(r,('pastEvents','past_events','historicalRuns','historical_runs','formRuns','form_runs','previousRuns','previous_runs'))
    if runs:
     vals=[pos(x) for x in runs];vals=[x for x in vals if x][:5]
     if vals:r['lastFive']=vals;filled+=1
 P.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 print(f'LAST5_ENRICHED runners={filled}')
if __name__=='__main__':main()
