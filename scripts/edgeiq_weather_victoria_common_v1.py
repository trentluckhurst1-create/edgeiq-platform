from __future__ import annotations
import csv,json,re,sys
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(2147483647)
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
DOCS_BOM=ROOT/'docs'/'weather-intelligence'/'bom'; DOCS_OBS=DOCS_BOM/'observations'; DOCS_LIVE=ROOT/'docs'/'weather-intelligence'/'live'; PUBLIC=ROOT/'public'/'data'
for p in (DOCS_BOM,DOCS_OBS,DOCS_LIVE,PUBLIC): p.mkdir(parents=True,exist_ok=True)
DIRECT={'FLEMINGTON':('Flemington','VRC'),'CAULFIELD':('Caulfield','MRC'),'CAULFIELD_HEATH':('Caulfield Heath','MRC'),'SANDOWN_HILLSIDE':('Sandown Hillside','MRC'),'SANDOWN_LAKESIDE':('Sandown Lakeside','MRC'),'MORNINGTON':('Mornington','MRC')}
NAMES='Alexandra|Ararat|Avoca|Bairnsdale|Ballarat|Ballarat Synthetic|Balnarring|Benalla|Bendigo|Buchan|Burrumbeet|Camperdown|Casterton|Colac|Coleraine|Cranbourne|Dederang|Donald|Drouin|Dunkeld|Echuca|Edenhope|Geelong|Geelong Synthetic|Great Western|Gunbower|Hamilton|Hanging Rock|Healesville|Hinnomunjie|Horsham|Kerang|Kilmore|Kyneton|Manangatang|Mansfield|Merton|Mildura|Moe|Moonee Valley|Mortlake|Murtoa|Nhill|Tynong|Tynong Synthetic|Penshurst|Sale|Seymour|St Arnaud|Stawell|Stony Creek|Swan Hill|Swifts Creek|Tatura|Terang|Towong|Traralgon|Wangaratta|Warracknabeal|Warrnambool|Werribee|Wodonga|Woolamai|Wycheproof|Yarra Valley|Yea'.split('|')
def cid(name:str)->str: return re.sub(r'[^A-Z0-9]+','_',name.upper()).strip('_')
IN_SCOPE=[(cid(n),n,'SYNTHETIC' if 'Synthetic' in n else 'TURF','SYNTHETIC' if 'Synthetic' in n else 'TURF') for n in NAMES]
SPONSORS=['Ladbrokes','Sportsbet','bet365','Apiam','Southside','TAB','Picklebet Park']
SPECIAL={'PAKENHAM':('TYNONG','Tynong','TURF','TURF'),'PAKENHAM SYNTHETIC':('TYNONG_SYNTHETIC','Tynong Synthetic','SYNTHETIC','SYNTHETIC'),'SOUTHSIDE PAKENHAM':('TYNONG','Tynong','TURF','TURF'),'SOUTHSIDE PAKENHAM SYNTHETIC':('TYNONG_SYNTHETIC','Tynong Synthetic','SYNTHETIC','SYNTHETIC'),'SOUTHSIDE CRANBOURNE':('CRANBOURNE','Cranbourne','TURF','TURF')}
def utc(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def norm(v:Any)->str: return re.sub(r'[^A-Z0-9]+',' ',str(v or '').upper()).strip()
def clean(v:Any)->str:
 t=norm(v); 
 if t in SPECIAL: return SPECIAL[t][1]
 for s in SPONSORS: t=re.sub(rf'^\s*{re.escape(s.upper())}\s+','',t).strip()
 if t in SPECIAL: return SPECIAL[t][1]
 m={norm(n):n for _,n,_,_ in IN_SCOPE}; m.update({norm(n):n for _,(n,_) in DIRECT.items()})
 return m.get(t,str(v or '').strip())
def write_csv(p:Path,rows:list[dict[str,Any]],fields:list[str]):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def read_csv(p:Path)->list[dict[str,str]]:
 if not p.exists() or p.stat().st_size==0: return []
 with p.open('r',encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def write_json(p:Path,o:Any): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def canonical(track:str):
 venue=clean(track)
 for c,n,s,l in IN_SCOPE:
  if norm(n)==norm(venue): return c,n,s,l
 for c,(n,prov) in DIRECT.items():
  if norm(n)==norm(venue) or (c.startswith('SANDOWN') and 'SANDOWN' in norm(venue)): return c,n,'TURF','TURF'
 return cid(venue),venue,'',''
