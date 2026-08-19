from __future__ import annotations
import csv,hashlib,json,os,re,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'; DOC=ROOT/'docs'/'external-data-integration-v1'
def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def clean(v): return '' if v is None else str(v).strip()
def credential_status(): return {'RACINGCOM_PUBLIC_WIDGET_API_KEY':'PRESENT' if os.environ.get('RACINGCOM_PUBLIC_WIDGET_API_KEY') else 'ABSENT'}
def read_csv(path):
    if not path.exists(): return []
    csv.field_size_limit(min(sys.maxsize,2147483647))
    with path.open('r',encoding='utf-8-sig',newline='') as handle: return list(csv.DictReader(handle))
def write_csv(path,rows,fields):
    path.parent.mkdir(parents=True,exist_ok=True); fd,tmp_name=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent); os.close(fd); tmp=Path(tmp_name)
    with tmp.open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields,extrasaction='ignore'); writer.writeheader()
        for row in rows: writer.writerow({field:clean(row.get(field,'')) for field in fields})
    os.replace(tmp,path)
def write_json(path,payload): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def file_sha(path): return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ''
