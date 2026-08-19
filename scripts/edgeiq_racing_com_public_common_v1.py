
from __future__ import annotations
import csv, json, hashlib, os, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs'/'racing-com-public-data-v1'
FRONTEND=DOC/'frontend'; GRAPHQL=DOC/'graphql'; HAR=DOC/'har'; SECT=DOC/'sectionals'; AUDIT=DOC/'audit'; ACCEPT=DOC/'acceptance'
RAW=ROOT/'data'/'raw'/'racing-com-public-v1'
PROCESSED=ROOT/'data'/'processed'/'racing-com-public-v1'
PUB=ROOT/'public'/'data'
UA='EDGEiQ-public-data-discovery-v1 (research; contact: repository-owner)'
SYMBOLS=['getRacesForMeet','getNoCacheRacesForMeet','getRaceForm','useCDFSectionals','checkChampionDataForSectionals','cloudfrontUrl','downloadPdf','downloadCsv','graphQl.endpoint','Champion','sectionals','splits','FinalPosition','Saddlecloth','Sectional','Speed']
GRAPHQL_ENDPOINT='https://graphql.rmdprod.racing.com'
APPV2_MEETS='https://www.racing.com/services/appv2/GetMeetsByMonth/{year}/{month}'

def ensure():
    for p in [DOC,FRONTEND,GRAPHQL,GRAPHQL/'operation_documents',GRAPHQL/'response_samples_redacted',HAR,SECT,AUDIT,ACCEPT,PROCESSED]: p.mkdir(parents=True,exist_ok=True)
    for n in ['meeting','race','results','timing','sectionals','downloads']:(RAW/n).mkdir(parents=True,exist_ok=True)

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def sha_bytes(b:bytes): return hashlib.sha256(b).hexdigest()
def sha_file(p):
    p=Path(p)
    return sha_bytes(p.read_bytes()) if p.exists() else ''
def write_json(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8')
def write_text(path,text):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text,encoding='utf-8')
def write_csv(path,rows,fields=None):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    rows=list(rows)
    if fields is None:
        fields=[]
        for r in rows:
            for k in r.keys():
                if k not in fields: fields.append(k)
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def read_csv(path):
    path=Path(path)
    if not path.exists(): return []
    csv.field_size_limit(min(sys.maxsize,2147483647))
    with path.open('r',encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def first(row,names,default=''):
    for n in names:
        v=row.get(n)
        if v is not None and str(v).strip()!='': return str(v).strip()
    return default
def clean_track(s): return re.sub(r'[^A-Z0-9]','',(s or '').upper())
def safe_float(v):
    try:
        s=str(v).strip()
        return float(s) if s not in ('','None','nan') else None
    except Exception: return None
def parse_time_seconds(v):
    if v is None: return None
    s=str(v).strip()
    if not s: return None
    try:
        if ':' in s:
            parts=[float(x) for x in s.split(':')]
            total=0
            for x in parts: total=total*60+x
            return round(total,3)
        return round(float(s),3)
    except Exception: return None
def split_bounds(s):
    s=(s or '').upper().replace(' ', '')
    if '-' not in s: return ('','','')
    a,b=s.split('-',1)
    def d(x): return '0' if x=='FINISH' else re.sub(r'[^0-9]','',x)
    start,end=d(a),d(b)
    dist=''
    if start!='' and end!='':
        try: dist=str(abs(int(start)-int(end)))
        except Exception: dist=''
    return start,end,dist
def request_public(url,timeout=20):
    req=Request(url,headers={'User-Agent':UA,'Accept':'application/json,text/html,*/*'})
    try:
        with urlopen(req,timeout=timeout) as r:
            data=r.read(); return {'ok':True,'status':getattr(r,'status',200),'url':url,'body':data,'hash':sha_bytes(data),'error':''}
    except HTTPError as e:
        return {'ok':False,'status':e.code,'url':url,'body':b'','hash':'','error':str(e)}
    except URLError as e:
        return {'ok':False,'status':'URL_ERROR','url':url,'body':b'','hash':'','error':str(e.reason)}
def redact_text(s):
    s=re.sub(r'(?i)([A-Za-z0-9_]*(?:api[-_ ]?key|endpointkey|accesskey|clientsecret|authorization|token|cookie)[A-Za-z0-9_]*)\s*[:=]\s*["\']?[^"\'\s,;]+',r'\1=[REDACTED]',s)
    s=re.sub(r'(?i)(da2-[a-z0-9]{10,})','[REDACTED_DA2_KEY]',s)
    return s[:200000]
