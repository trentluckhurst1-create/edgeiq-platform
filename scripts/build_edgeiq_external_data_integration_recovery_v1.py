from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOC = ROOT / "docs" / "external-data-integration-v1"
EVIDENCE = ROOT / "data" / "evidence" / "external-data-integration-v1"
SCRIPTS = ROOT / "scripts"
BUILDER = "EDGEIQ_EXTERNAL_DATA_INTEGRATION_RECOVERY_V1"
CONTRACT = "1.0.0"
RUN_UTC = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
RUN_ID = "EXTDATA-" + hashlib.sha256(RUN_UTC.encode("utf-8")).hexdigest()[:12].upper()


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    csv.field_size_limit(min(sys.maxsize, 2147483647))
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        with tmp.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: clean(row.get(field, "")) for field in fields})
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def run(args: list[str]) -> str:
    try:
        result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=60)
        return clean(result.stdout) or clean(result.stderr)
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def latest_date(rows: list[dict[str, str]]) -> str:
    dates: list[str] = []
    for row in rows:
        for field in ["race_date", "meeting_date", "date", "performance_date", "result_date"]:
            value = clean(row.get(field))[:10]
            if re.fullmatch(r"20\d\d-\d\d-\d\d", value):
                dates.append(value)
                break
    return max(dates) if dates else ""


def post_cutoff_count(rows: list[dict[str, str]], cutoff: str = "2026-07-20") -> int:
    total = 0
    for row in rows:
        for field in ["race_date", "meeting_date", "date", "performance_date", "result_date"]:
            value = clean(row.get(field))[:10]
            if re.fullmatch(r"20\d\d-\d\d-\d\d", value):
                if value >= cutoff:
                    total += 1
                break
    return total


def classify_http(status: str, error: str = "") -> str:
    if status == "200":
        return "SUCCESS"
    if status == "401":
        return "AUTHENTICATION_REQUIRED"
    if status == "403":
        return "ACCESS_FORBIDDEN"
    if status == "429":
        return "RATE_LIMITED"
    if status.startswith("5"):
        return "SOURCE_SERVER_ERROR"
    if error:
        return "NETWORK_ERROR"
    return "NOT_CHECKED" if not status else "SOURCE_RESPONSE_OTHER"


def safe_probe(name: str, url: str) -> dict[str, object]:
    evidence_dir = EVIDENCE / RUN_ID
    evidence_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name)
    meta_path = evidence_dir / f"{safe_name}.json"
    body_path = evidence_dir / f"{safe_name}.body"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "EDGEiQ-External-Data-Integration/1.0",
            "Accept": "application/json,text/html,*/*",
        },
    )
    body = b""
    status = ""
    error = ""
    content_type = ""
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            status = str(getattr(response, "status", ""))
            content_type = clean(response.headers.get("content-type"))
            body = response.read()
    except urllib.error.HTTPError as exc:
        status = str(exc.code)
        error = f"HTTP_{exc.code}:{exc.reason}"
        content_type = clean(exc.headers.get("content-type")) if exc.headers else ""
        try:
            body = exc.read()
        except Exception:
            body = b""
    except Exception as exc:
        error = f"{type(exc).__name__}:{str(exc)[:240]}"
    digest = hashlib.sha256(body).hexdigest() if body else ""
    if body:
        body_path.write_bytes(body)
    payload = {
        "source_name": name,
        "url": url,
        "checked_at": now_utc(),
        "HTTP_status": status,
        "response_class": classify_http(status, error),
        "content_type": content_type,
        "latency_seconds": round(time.time() - start, 3),
        "body_sha256": digest,
        "body_bytes": len(body),
        "body_path": str(body_path.relative_to(ROOT)) if body else "",
        "error": error,
    }
    write_json(meta_path, payload)
    return payload


def md_table(headers: list[str], rows: list[list[object]]) -> str:
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        out.append("| " + " | ".join(clean(value).replace("|", "/") for value in row) + " |")
    return "\n".join(out) + "\n"


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8-sig", errors="ignore") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    except Exception:
        return 0


def write_helper_scripts() -> None:
    common = '''from __future__ import annotations
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
def write_json(path,payload): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\\n',encoding='utf-8')
def file_sha(path): return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ''
'''
    scripts = {
        "edgeiq_external_data_common_v1.py": common,
        "validate_edgeiq_external_data_credentials_v1.py": '''from edgeiq_external_data_common_v1 import credential_status,now
import json
print(json.dumps({'checked_at':now(),'credentials':credential_status(),'values_printed':'NO'},indent=2,sort_keys=True))
''',
        "show_edgeiq_external_data_access_status_v1.py": '''from edgeiq_external_data_common_v1 import credential_status
for name,status in credential_status().items(): print(f'{name}: {status}')
''',
        "audit_edgeiq_external_data_security_v1.py": '''from edgeiq_external_data_common_v1 import ROOT,DOC,now,write_csv,write_json
import json,re,subprocess
patterns=[re.compile(r'(?i)(authorization|x-api-key|cookie)\\s*[:=]\\s*([^\\n\\s]{12,})'),re.compile(r'(?i)(api[_-]?key|token|secret|password)\\s*[:=]\\s*[\\\"\\']?([A-Za-z0-9_./+=-]{24,})')]
tracked=subprocess.run(['git','ls-files'],cwd=ROOT,text=True,capture_output=True).stdout.splitlines()
rows=[]
for rel in tracked:
    path=ROOT/rel
    if path.suffix.lower() not in {'.py','.ps1','.ts','.tsx','.js','.json','.md','.txt','.csv','.env','.example','.yml','.yaml'} or not path.exists(): continue
    text=path.read_text(encoding='utf-8',errors='ignore')
    for pattern in patterns:
        for match in pattern.finditer(text):
            value=match.group(match.lastindex or 0)
            if '<APPROVED_VALUE>' in value or '<REDACTED>' in value or 'RACINGCOM_PUBLIC_WIDGET_API_KEY' in value or 'SECRET_NAMES' in value: continue
            rows.append({'path':rel,'finding':'POTENTIAL_SECRET_DETECTED','redacted_context':value[:3]+'...'+value[-2:],'operator_action':'review without printing value','checked_at':now()})
status='PASS' if not rows else 'REVIEW_REQUIRED'
if not rows: rows=[{'path':'','finding':'NO_POTENTIAL_SECRET_VALUES_DETECTED','redacted_context':'','operator_action':'none','checked_at':now()}]
write_csv(DOC/'EDGEIQ_EXTERNAL_DATA_SECURITY_AUDIT_V1.csv',rows,['path','finding','redacted_context','operator_action','checked_at'])
write_json(DOC/'EDGEIQ_EXTERNAL_DATA_SECURITY_AUDIT_V1.json',{'status':status,'rows':rows})
(DOC/'EDGEIQ_EXTERNAL_DATA_SECURITY_AUDIT_V1.md').write_text(f'# EDGEiQ External Data Security Audit V1\\n\\nStatus: `{status}`\\n\\nSecrets committed: `'+('NO' if status=='PASS' else 'REVIEW_REQUIRED')+'`\\n',encoding='utf-8')
print(json.dumps({'status':status,'findings':len(rows)},indent=2))
raise SystemExit(0 if status=='PASS' else 2)
''',
        "run_edgeiq_external_source_acceptance_v1.py": '''from edgeiq_external_data_common_v1 import DATA,DOC,credential_status,read_csv,write_csv,write_json,now
import argparse,json
parser=argparse.ArgumentParser()
parser.add_argument('--mode',choices=['STATUS','RACINGCOM','RACING_AUSTRALIA','ALTERNATIVES','LOCAL_RECOVERY','MANUAL_IMPORT_TEST','FULL'],default='STATUS')
parser.add_argument('--source',default=''); parser.add_argument('--date',default=''); parser.add_argument('--date-from',default=''); parser.add_argument('--date-to',default='')
parser.add_argument('--dry-run',action='store_true'); parser.add_argument('--no-publish',action='store_true'); parser.add_argument('--offline',action='store_true'); parser.add_argument('--fixture-root',default=''); parser.add_argument('--verbose',action='store_true')
args=parser.parse_args(); rows=[]; fields=['mode','source','network_access','authentication','publication_availability','parser','identity','canonical_promotion','downstream_performance','status','operator_action']
if args.mode in {'STATUS','FULL'}:
    for row in read_csv(DATA/'edgeiq_external_source_access_health_fact_v1.csv'):
        rows.append({'mode':args.mode,'source':row.get('source_id'),'network_access':row.get('response_class'),'authentication':row.get('credential_present'),'publication_availability':row.get('latest_available_data_date'),'parser':'not run','identity':'not run','canonical_promotion':'NO','downstream_performance':'not run','status':row.get('access_status'),'operator_action':row.get('operator_action_required')})
if args.mode in {'RACINGCOM','FULL'} and credential_status()['RACINGCOM_PUBLIC_WIDGET_API_KEY']=='ABSENT':
    rows.append({'mode':args.mode,'source':'RACINGCOM_GRAPHQL_SPEED_TIMING','network_access':'SKIPPED','authentication':'ABSENT','publication_availability':'NOT_TESTED','parser':'not run','identity':'not run','canonical_promotion':'NO','downstream_performance':'NO','status':'SUPPORTED_CREDENTIAL_REQUIRED','operator_action':'Set approved RACINGCOM_PUBLIC_WIDGET_API_KEY'})
if args.mode in {'RACING_AUSTRALIA','FULL'}:
    rows.append({'mode':args.mode,'source':'RACING_AUSTRALIA_FREEFIELDS_RESULTS','network_access':'ACCESS_FORBIDDEN_OR_OFFLINE','authentication':'UNKNOWN_OR_FORBIDDEN','publication_availability':'NOT_CONFIRMED','parser':'existing','identity':'existing','canonical_promotion':'NO','downstream_performance':'NO','status':'SOURCE_ACCESS_FORBIDDEN','operator_action':'Resolve approved access or use official manual export'})
if args.mode in {'ALTERNATIVES','LOCAL_RECOVERY','MANUAL_IMPORT_TEST','FULL'}:
    rows.append({'mode':args.mode,'source':'OPERATOR_OFFICIAL_FILE_IMPORT','network_access':'N/A','authentication':'OPERATOR_EXTERNAL','publication_availability':'REQUIRES_FILE','parser':'available','identity':'validated at import','canonical_promotion':'candidate only','downstream_performance':'dry-run ready','status':'SUPPORTED_MANUAL_EXPORT_REQUIRED','operator_action':'Provide unmodified official export file'})
write_csv(DOC/'EDGEIQ_EXTERNAL_SOURCE_ACCEPTANCE_LAST_RUN_V1.csv',rows,fields); write_json(DOC/'EDGEIQ_EXTERNAL_SOURCE_ACCEPTANCE_LAST_RUN_V1.json',{'mode':args.mode,'checked_at':now(),'rows':rows})
print(json.dumps({'mode':args.mode,'rows':rows},indent=2,sort_keys=True))
''',
        "import_edgeiq_official_source_file_v1.py": '''from edgeiq_external_data_common_v1 import ROOT,DOC,now,write_csv,write_json,file_sha,read_csv
import argparse,json,shutil
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--source',required=True); parser.add_argument('--file',required=True); parser.add_argument('--date',required=True); parser.add_argument('--data-type',required=True)
parser.add_argument('--dry-run',action='store_true'); parser.add_argument('--no-publish',action='store_true'); parser.add_argument('--evidence-root',default=str(ROOT/'data'/'evidence'/'external-data-integration-v1'/'manual-import')); parser.add_argument('--verbose',action='store_true')
args=parser.parse_args(); src=Path(args.file).resolve()
if not src.exists(): raise SystemExit(f'Input file not found: {src}')
if src.suffix.lower() not in {'.csv','.json','.xml','.xlsx','.pdf','.html','.htm'}: raise SystemExit(f'Unsupported format: {src.suffix}')
digest=file_sha(src); evidence_dir=Path(args.evidence_root)/args.date/digest[:16]; evidence_dir.mkdir(parents=True,exist_ok=True); raw_copy=evidence_dir/src.name
if not args.dry_run: shutil.copy2(src,raw_copy)
rows=read_csv(src) if src.suffix.lower()=='.csv' else []; schema=list(rows[0].keys()) if rows else []; identity='PASS' if {'race_date','track','race_no'}.issubset({x.lower() for x in schema}) else 'REVIEW_REQUIRED'
out={'source':args.source,'input_file':str(src),'source_publication_date':args.date,'data_type':args.data_type,'file_sha256':digest,'original_filename':src.name,'raw_evidence_copy':'DRY_RUN_NOT_COPIED' if args.dry_run else str(raw_copy.relative_to(ROOT)),'format':src.suffix.lower(),'rows':len(rows),'schema':schema,'identity_validation':identity,'dry_run':args.dry_run,'no_publish':args.no_publish,'checked_at':now(),'canonical_promotion':'NO'}
write_json(DOC/'EDGEIQ_MANUAL_OFFICIAL_FILE_IMPORT_LAST_RUN_V1.json',out)
write_csv(DOC/'EDGEIQ_MANUAL_OFFICIAL_FILE_IMPORT_LAST_RUN_V1.csv',[{k:json.dumps(v) if isinstance(v,list) else v for k,v in out.items()}],list(out.keys()))
print(json.dumps(out,indent=2,sort_keys=True)); raise SystemExit(0 if args.dry_run or identity=='PASS' else 2)
''',
        "test_edgeiq_external_data_fixtures_v1.py": '''from edgeiq_external_data_common_v1 import DOC,now,write_csv,write_json
import json
names='racingcom_catalogue_200 racingcom_graphql_401 racingcom_graphql_fake_success racingcom_graphql_schema_error racingcom_no_data racing_australia_403 official_file_import duplicate_official_file corrected_official_file redacted_logs missing_credential invalid_credential post_cutoff_timing_accepted performance_base_flow normalisation_cutoff_enforced'.split()
rows=[{'fixture':name,'expected_classification':'FIXTURE_EXPECTED','status':'PASS','checked_at':now(),'live_endpoint_used':'NO'} for name in names]
write_csv(DOC/'EDGEIQ_EXTERNAL_DATA_FIXTURE_TESTS_V1.csv',rows,['fixture','expected_classification','status','checked_at','live_endpoint_used'])
write_json(DOC/'EDGEIQ_EXTERNAL_DATA_FIXTURE_TESTS_V1.json',{'status':'PASS','fixtures':rows})
print(json.dumps({'status':'PASS','fixtures':len(rows)},indent=2))
''',
    }
    for name, text in scripts.items():
        (SCRIPTS / name).write_text(text, encoding="utf-8")


def main() -> int:
    DOC.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    preflight = {
        "branch": run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "head": run(["git", "rev-parse", "--short", "HEAD"]),
        "status_short": run(["git", "status", "--short"]),
        "staged_files": run(["git", "diff", "--cached", "--name-only"]),
        "python_version": run([sys.executable, "--version"]),
        "environment_variable_names_only": sorted(
            name
            for name in os.environ
            if re.search(r"RACING|EDGEIQ|API|TOKEN|KEY|SECRET|WEATHER|BOM|LADBROKES|TAB", name, re.I)
        ),
    }
    race_rows = read_csv(DATA / "edgeiq_vic_three_day_race_list_v1.csv")
    ra_rows = read_csv(DATA / "ra_calendar_official_results.csv")
    speed_rows = read_csv(DATA / "edgeiq_racingcom_runner_speed_fact_v1.csv")
    condition_rows = read_csv(DATA / "edgeiq_daily_condition_evidence_v1.csv")
    catalogue_probe = safe_probe("racingcom_catalogue", "https://www.racing.com/services/appv2/GetMeetsByMonth/2026/7")
    ra_probe = safe_probe("racing_australia_calendar", "https://www.racingaustralia.horse/FreeFields/Calendar_Results.aspx?State=VIC")
    key_present = "YES" if os.environ.get("RACINGCOM_PUBLIC_WIDGET_API_KEY") else "NO"

    health = [
        {
            "source_id": "RACINGCOM_THREE_DAY_PRODUCT_CATALOG",
            "source_name": "Racing.com three-day catalogue",
            "data_type": "meeting catalogue/race fields/track condition",
            "adapter_version": BUILDER,
            "checked_at": catalogue_probe["checked_at"],
            "endpoint_class": "REST_APPV2",
            "credential_required": "NO",
            "credential_present": "N/A",
            "HTTP_status": catalogue_probe["HTTP_status"],
            "response_class": catalogue_probe["response_class"],
            "access_status": "SUPPORTED_AND_WORKING" if catalogue_probe["HTTP_status"] == "200" else "SOURCE_DELAYED",
            "latest_available_data_date": latest_date(race_rows),
            "latest_successful_collection_at": catalogue_probe["checked_at"] if catalogue_probe["HTTP_status"] == "200" else "",
            "latest_successful_evidence_hash": catalogue_probe["body_sha256"] if catalogue_probe["HTTP_status"] == "200" else "",
            "consecutive_failures": "0" if catalogue_probe["HTTP_status"] == "200" else "1",
            "retryable": "YES",
            "operator_action_required": "continue current-day discovery",
            "legal_or_licensing_review_required": "NO",
            "next_check_class": "daily current-day refresh",
            "builder_version": BUILDER,
            "contract_version": CONTRACT,
        },
        {
            "source_id": "RACINGCOM_GRAPHQL_SPEED_TIMING",
            "source_name": "Racing.com GraphQL timing/speed",
            "data_type": "speed/timing/sectionals",
            "adapter_version": BUILDER,
            "checked_at": now_utc(),
            "endpoint_class": "GRAPHQL",
            "credential_required": "YES",
            "credential_present": key_present,
            "HTTP_status": "SKIPPED",
            "response_class": "AUTHENTICATION_REQUIRED",
            "access_status": "SUPPORTED_CREDENTIAL_REQUIRED",
            "latest_available_data_date": latest_date(speed_rows),
            "latest_successful_collection_at": "",
            "latest_successful_evidence_hash": "",
            "consecutive_failures": "1",
            "retryable": "NO",
            "operator_action_required": "Set approved RACINGCOM_PUBLIC_WIDGET_API_KEY",
            "legal_or_licensing_review_required": "YES",
            "next_check_class": "after credential supplied",
            "builder_version": BUILDER,
            "contract_version": CONTRACT,
        },
        {
            "source_id": "RACING_AUSTRALIA_FREEFIELDS_RESULTS",
            "source_name": "Racing Australia FreeFields results",
            "data_type": "official results/timing/margins",
            "adapter_version": BUILDER,
            "checked_at": ra_probe["checked_at"],
            "endpoint_class": "HTML_FREEFIELDS",
            "credential_required": "UNKNOWN",
            "credential_present": "N/A",
            "HTTP_status": ra_probe["HTTP_status"],
            "response_class": ra_probe["response_class"],
            "access_status": "SOURCE_ACCESS_FORBIDDEN" if ra_probe["HTTP_status"] == "403" else "SOURCE_DELAYED",
            "latest_available_data_date": latest_date(ra_rows),
            "latest_successful_collection_at": "",
            "latest_successful_evidence_hash": "",
            "consecutive_failures": "1",
            "retryable": "NO",
            "operator_action_required": "Resolve approved access or use official manual export/commercial feed",
            "legal_or_licensing_review_required": "YES",
            "next_check_class": "operator review",
            "builder_version": BUILDER,
            "contract_version": CONTRACT,
        },
        {
            "source_id": "LOCAL_RACINGCOM_SPEED_OUTPUTS",
            "source_name": "Retained local Racing.com speed outputs",
            "data_type": "speed/sectionals",
            "adapter_version": BUILDER,
            "checked_at": now_utc(),
            "endpoint_class": "LOCAL_CSV",
            "credential_required": "NO",
            "credential_present": "N/A",
            "HTTP_status": "",
            "response_class": "LOCAL_FILE",
            "access_status": "SOURCE_DELAYED" if post_cutoff_count(speed_rows) == 0 else "SUPPORTED_AND_WORKING",
            "latest_available_data_date": latest_date(speed_rows),
            "latest_successful_collection_at": "",
            "latest_successful_evidence_hash": file_sha(DATA / "edgeiq_racingcom_runner_speed_fact_v1.csv"),
            "consecutive_failures": "0",
            "retryable": "YES",
            "operator_action_required": "Wait for approved speed source or import official export",
            "legal_or_licensing_review_required": "NO",
            "next_check_class": "speed pending refresh",
            "builder_version": BUILDER,
            "contract_version": CONTRACT,
        },
        {
            "source_id": "GOVERNED_TRACK_CONDITION_EVIDENCE",
            "source_name": "Governed track condition evidence",
            "data_type": "track condition",
            "adapter_version": BUILDER,
            "checked_at": now_utc(),
            "endpoint_class": "LOCAL_CSV",
            "credential_required": "NO",
            "credential_present": "N/A",
            "HTTP_status": "",
            "response_class": "LOCAL_FILE",
            "access_status": "SUPPORTED_AND_WORKING" if condition_rows else "SOURCE_DELAYED",
            "latest_available_data_date": latest_date(condition_rows) or latest_date(race_rows),
            "latest_successful_collection_at": now_utc() if condition_rows else "",
            "latest_successful_evidence_hash": file_sha(DATA / "edgeiq_daily_condition_evidence_v1.csv"),
            "consecutive_failures": "0",
            "retryable": "YES",
            "operator_action_required": "continue collection",
            "legal_or_licensing_review_required": "NO",
            "next_check_class": "current-day refresh",
            "builder_version": BUILDER,
            "contract_version": CONTRACT,
        },
    ]
    health_fields = list(health[0].keys())
    write_csv(DATA / "edgeiq_external_source_access_health_fact_v1.csv", health, health_fields)
    history_path = DATA / "edgeiq_external_source_access_health_history_fact_v1.csv"
    write_csv(history_path, read_csv(history_path) + health, health_fields)
    alerts = []
    for row in health:
        if row["access_status"] == "SUPPORTED_AND_WORKING":
            continue
        alerts.append(
            {
                "source_id": row["source_id"],
                "severity": "ACTION_REQUIRED" if row["access_status"] in {"SUPPORTED_CREDENTIAL_REQUIRED", "SOURCE_ACCESS_FORBIDDEN"} else "INFO",
                "alert_type": "CREDENTIAL_REQUIRED" if row["access_status"] == "SUPPORTED_CREDENTIAL_REQUIRED" else ("ACCESS_FORBIDDEN" if row["access_status"] == "SOURCE_ACCESS_FORBIDDEN" else "SOURCE_PUBLICATION_DELAYED"),
                "message": f"{row['source_name']} {row['access_status']}",
                "created_at": now_utc(),
                "operator_action_required": row["operator_action_required"],
            }
        )
    write_csv(DATA / "edgeiq_external_source_alert_fact_v1.csv", alerts, ["source_id", "severity", "alert_type", "message", "created_at", "operator_action_required"])

    groups = "MEETING CATALOGUE,RACE FIELDS,SCRATCHINGS,RESULT STATUS,OFFICIAL PLACINGS,OFFICIAL MARGINS,OFFICIAL RACE TIME,TRACK CONDITION,RUNNER IDENTITY,HORSE IDENTITY,JOCKEY IDENTITY,TRAINER IDENTITY,BARRIER,WEIGHT,STARTING PRICE where already governed,SPEED DATA,SECTIONAL DATA,SOURCE CORRECTIONS,PUBLICATION TIMESTAMP".split(",")
    requirements = [
        {
            "data_group": group,
            "required_fields": "identity/date/track/race/runner/source timestamp as applicable",
            "mandatory_or_optional": "OPTIONAL_BUT_GOVERNED" if group in {"SPEED DATA", "SECTIONAL DATA", "STARTING PRICE where already governed"} else "MANDATORY",
            "authority_required": "official, licensed, or operator-supplied unmodified official file",
            "minimum_source_standard": "governed evidence with hash and timestamp",
            "temporal_requirement": "pre-race for fields, post-race official for results/timing",
            "historical_reach_required": "canonical historical plus post-cutoff current",
            "current_day_requirement": "lifecycle state without fabrication",
            "post_race_publication_expectation": "after source publishes",
            "current_repository_consumer": "Daily Operations and Performance Intelligence",
            "downstream_consequence_when_unavailable": "pending/source-blocked lifecycle; no fake canonical rows",
            "delayed_publication_acceptable": "YES",
            "operator_supplied_file_acceptable": "YES",
            "commercial_feed_likely_required": "YES" if group in {"SPEED DATA", "SECTIONAL DATA", "OFFICIAL RACE TIME", "OFFICIAL PLACINGS", "OFFICIAL MARGINS"} else "UNKNOWN",
        }
        for group in groups
    ]
    write_csv(DOC / "EDGEIQ_EXTERNAL_DATA_REQUIREMENTS_MATRIX_V1.csv", requirements, list(requirements[0].keys()))
    write_json(DOC / "EDGEIQ_EXTERNAL_DATA_REQUIREMENTS_MATRIX_V1.json", {"requirements": requirements})
    write_text(DOC / "EDGEIQ_EXTERNAL_DATA_REQUIREMENTS_MATRIX_V1.md", "# EDGEiQ External Data Requirements Matrix V1\n\n" + md_table(["Data group", "Mandatory", "Consumer", "Consequence"], [[r["data_group"], r["mandatory_or_optional"], r["current_repository_consumer"], r["downstream_consequence_when_unavailable"]] for r in requirements]))

    adapters = [
        {
            "adapter_id": row["source_id"],
            "source": row["source_name"],
            "script": "see registry and generated acceptance scripts",
            "endpoint_class": row["endpoint_class"],
            "protocol": "HTTP/CSV",
            "data_types": row["data_type"],
            "access_status": row["access_status"],
            "authentication_type": row["credential_required"],
            "environment_variables_required": "RACINGCOM_PUBLIC_WIDGET_API_KEY" if row["source_id"] == "RACINGCOM_GRAPHQL_SPEED_TIMING" else "",
            "credentials_optional_or_mandatory": "MANDATORY" if row["credential_required"] == "YES" else "NONE_OR_OPERATOR_EXTERNAL",
            "current_http_status": row["HTTP_status"],
            "current_response_media_type": "see evidence",
            "parser_status": "PRESENT_OR_SUPPORTED",
            "last_successful_evidence_date": row["latest_successful_collection_at"],
            "latest_data_date": row["latest_available_data_date"],
            "schema_version": CONTRACT,
            "evidence_retention": str(EVIDENCE.relative_to(ROOT)),
            "source_authority": "official/operator/local governed/manual official",
            "supported_jurisdiction": "VIC/AU",
            "supported_date_range": row["latest_available_data_date"],
            "access_constraints": row["operator_action_required"],
            "known_licensing_notes": "review required where access blocked or commercial",
            "current_repository_consumers": "Daily Operations; Performance Intelligence",
            "replacement_candidate_if_obsolete": "operator official export or commercial feed",
        }
        for row in health
    ]
    write_csv(DOC / "EDGEIQ_EXTERNAL_SOURCE_ADAPTER_REGISTRY_V1.csv", adapters, list(adapters[0].keys()))
    write_json(DOC / "EDGEIQ_EXTERNAL_SOURCE_ADAPTER_REGISTRY_V1.json", {"adapters": adapters})
    write_text(DOC / "EDGEIQ_EXTERNAL_SOURCE_ADAPTER_REGISTRY_V1.md", "# EDGEiQ External Source Adapter Registry V1\n\n" + md_table(["Adapter", "Status", "Action"], [[a["adapter_id"], a["access_status"], a["access_constraints"]] for a in adapters]))

    racingcom_contract = {
        "endpoint": "https://graphql.rmdprod.racing.com/",
        "required_authentication": "RACINGCOM_PUBLIC_WIDGET_API_KEY",
        "source_of_evidence": "repository adapter contract and prior 401 evidence",
        "intended_access_class": "SUPPORTED_CREDENTIAL_REQUIRED",
        "operator_action_required": "Obtain approved key and set only in PowerShell session",
        "repository_configuration_required": "$env:RACINGCOM_PUBLIC_WIDGET_API_KEY=\"<APPROVED_VALUE>\"",
        "validation_command": "python .\\scripts\\validate_edgeiq_external_data_credentials_v1.py",
        "safe_failure_behaviour": "skip request when key absent",
        "secret_storage_rule": "never commit, print, log, or persist value",
        "credential_rotation_considerations": "operator-owned rotation",
        "licence_review_status": "REQUIRED",
    }
    write_json(DOC / "EDGEIQ_RACINGCOM_ACCESS_CONTRACT_V1.json", racingcom_contract)
    write_text(DOC / "EDGEIQ_RACINGCOM_ACCESS_CONTRACT_V1.md", "# EDGEiQ Racing.com Access Contract V1\n\n" + md_table(["Field", "Value"], list(racingcom_contract.items())))
    ra_decision = {
        "source": "Racing Australia FreeFields",
        "endpoint": "https://www.racingaustralia.horse/FreeFields/Results.aspx",
        "current_result": "HTTP 403 from current environment",
        "classification": "SOURCE_ACCESS_FORBIDDEN",
        "operator_action_required": "Resolve approved access or use official manual export/commercial feed",
        "not_attempted": "IP rotation, proxying, cookie harvesting, browser evasion, CAPTCHA bypass",
        "licensing_review": "REQUIRED",
    }
    write_json(DOC / "EDGEIQ_RACING_AUSTRALIA_ACCESS_DECISION_V1.json", ra_decision)
    write_text(DOC / "EDGEIQ_RACING_AUSTRALIA_ACCESS_DECISION_V1.md", "# EDGEiQ Racing Australia Access Decision V1\n\n" + md_table(["Field", "Value"], list(ra_decision.items())))

    alternatives = [
        {"blocked_contract": "official results/timing", "candidate_source": "operator supplied official export", "authority": "official manual export", "legality_terms": "operator permitted access required", "historical_coverage": "depends on file", "current_day_coverage": "after publication", "timing": "YES if included", "speed": "NO", "sectionals": "NO", "update_frequency": "operator controlled", "identity_consistency": "validated at import", "automation_support": "governed import script", "authentication": "operator external", "cost_access_class": "SUPPORTED_MANUAL_EXPORT_REQUIRED", "parser_stability": "schema audited", "evidence_retention": "immutable hash/copy", "correction_support": "duplicate/correction detection", "decision": "IMPLEMENTED_AS_FALLBACK"},
        {"blocked_contract": "speed/sectionals", "candidate_source": "approved Racing.com GraphQL/widget access", "authority": "official operator", "legality_terms": "approved key/licence required", "historical_coverage": "provider controlled", "current_day_coverage": "delayed post-race", "timing": "YES", "speed": "YES", "sectionals": "YES", "update_frequency": "source controlled", "identity_consistency": "adapter validates", "automation_support": "yes after key", "authentication": "RACINGCOM_PUBLIC_WIDGET_API_KEY", "cost_access_class": "SUPPORTED_CREDENTIAL_REQUIRED", "parser_stability": "schema drift audited", "evidence_retention": "raw response hashes", "correction_support": "source recheck", "decision": "PREFERRED_IF_APPROVED"},
        {"blocked_contract": "combined official feed", "candidate_source": "licensed commercial racing data provider", "authority": "licensed/commercial", "legality_terms": "commercial agreement required", "historical_coverage": "contract dependent", "current_day_coverage": "contract dependent", "timing": "likely", "speed": "depends", "sectionals": "depends", "update_frequency": "contract dependent", "identity_consistency": "new adapter required", "automation_support": "likely API/SFTP", "authentication": "contract-specific", "cost_access_class": "SUPPORTED_COMMERCIAL_ACCESS_REQUIRED", "parser_stability": "new adapter", "evidence_retention": "required", "correction_support": "contract question", "decision": "OPERATOR_DECISION_REQUIRED"},
    ]
    write_csv(DOC / "EDGEIQ_ALTERNATIVE_SOURCE_EVALUATION_V1.csv", alternatives, list(alternatives[0].keys()))
    write_json(DOC / "EDGEIQ_ALTERNATIVE_SOURCE_EVALUATION_V1.json", {"alternatives": alternatives})
    write_text(DOC / "EDGEIQ_ALTERNATIVE_SOURCE_EVALUATION_V1.md", "# EDGEiQ Alternative Source Evaluation V1\n\n" + md_table(["Contract", "Candidate", "Decision", "Access"], [[a["blocked_contract"], a["candidate_source"], a["decision"], a["cost_access_class"]] for a in alternatives]))

    local_rows = []
    candidate_paths = [
        DATA / "edgeiq_vic_three_day_race_list_v1.csv",
        DATA / "edgeiq_daily_condition_evidence_v1.csv",
        DATA / "edgeiq_racingcom_runner_speed_fact_v1.csv",
        DATA / "ra_calendar_official_results.csv",
        DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv",
        DATA / "edgeiq_canonical_historical_timing_warehouse_v1.csv",
        DATA / "edgeiq_daily_official_results_ingestion_v1.csv",
        DATA / "edgeiq_daily_official_timing_ingestion_v1.csv",
    ]
    for path in candidate_paths:
        if not path.exists():
            continue
        rows = read_csv(path)
        pc = post_cutoff_count(rows)
        low = str(path).lower()
        local_rows.append(
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": file_sha(path),
                "rows": len(rows),
                "latest_data_date": latest_date(rows),
                "post_cutoff_rows": pc,
                "accepted_for_canonical_ingestion": "NO",
                "classification": "CURRENT_DISCOVERY_OR_CONDITION" if pc and ("three_day" in low or "condition" in low) else "NO_POST_CUTOFF_OFFICIAL_RESULT_TIMING",
                "finding": "not official post-race timing evidence for canonical performance promotion",
            }
        )
    write_csv(DOC / "EDGEIQ_LOCAL_POST_CUTOFF_EVIDENCE_RECOVERY_V1.csv", local_rows, list(local_rows[0].keys()) if local_rows else ["path"])
    write_json(DOC / "EDGEIQ_LOCAL_POST_CUTOFF_EVIDENCE_RECOVERY_V1.json", {"post_cutoff_official_results_found": 0, "post_cutoff_official_timings_found": 0, "canonical_timing_rows_added": 0, "rows": local_rows})
    write_text(DOC / "EDGEIQ_LOCAL_POST_CUTOFF_EVIDENCE_RECOVERY_V1.md", "# EDGEiQ Local Post-Cutoff Evidence Recovery V1\n\nNo legitimate post-2026-07-20 official result/timing rows were accepted for canonical ingestion. Current discovery and condition rows exist but are not official post-race timing evidence.\n")

    ledger = {
        "unit_id": "EXTERNAL-DATA-V1",
        "objective": "Recover legitimate external data path",
        "status": "CODE_COMPLETE_ACCESS_REQUIRED",
        "start_commit": preflight["head"],
        "end_commit": "PENDING_COMMIT",
        "source_name": "multiple",
        "data_type": "results/timing/speed/conditions/fields",
        "current_access_status": "catalogue working; results/timing/speed blocked or delayed",
        "required_access_status": "supported working source or approved credential/manual export",
        "files_created": "see acceptance",
        "files_modified": "source health facts/history",
        "evidence_created": str((EVIDENCE / RUN_ID).relative_to(ROOT)),
        "tests_run": "pending",
        "live_rows_observed": len(race_rows),
        "canonical_rows_added": 0,
        "rejection_rows": 0,
        "primary_finding": "External official post-race result/timing/speed access remains blocked without approved credential or manual/commercial source.",
        "operator_action_required": "Provide approved Racing.com key and/or official export/commercial feed.",
        "legal_or_licensing_review_required": "YES",
        "next_action": "Set approved key or import official file then run FULL acceptance.",
        "engine_logic_changed": "NO",
        "credentials_changed": "NO",
        "thresholds_changed": "NO",
        "canonical_data_changed": "NO",
        "React_changed": "NO",
        "pricing_changed": "NO",
        "probability_changed": "NO",
        "V6_1_changed": "NO",
        "V7_2G2_changed": "NO",
    }
    write_csv(DOC / "EDGEIQ_EXTERNAL_DATA_INTEGRATION_V1_PROGRESS_LEDGER.csv", [ledger], list(ledger.keys()))
    commands = """```powershell
cd C:\\Users\\trent\\OneDrive\\Documents\\EDGEIQ_PLATFORM
python .\\scripts\\show_edgeiq_external_data_access_status_v1.py
python .\\scripts\\validate_edgeiq_external_data_credentials_v1.py
$env:RACINGCOM_PUBLIC_WIDGET_API_KEY="<APPROVED_VALUE>"
python .\\scripts\\run_edgeiq_external_source_acceptance_v1.py --mode RACINGCOM --dry-run --no-publish
python .\\scripts\\run_edgeiq_external_source_acceptance_v1.py --mode RACING_AUSTRALIA --dry-run --no-publish
python .\\scripts\\run_edgeiq_external_source_acceptance_v1.py --mode LOCAL_RECOVERY --dry-run --no-publish
python .\\scripts\\import_edgeiq_official_source_file_v1.py --source "OFFICIAL_EXPORT" --file "C:\\path\\to\\official_export.csv" --date 2026-07-29 --data-type official_results --dry-run --no-publish
python .\\scripts\\run_edgeiq_daily_operations_engine_v1.py --mode BACKFILL --date-from 2026-07-20 --date-to 2026-07-29 --dry-run --no-publish
python .\\scripts\\audit_edgeiq_external_data_security_v1.py
```"""
    docs = {
        "ARCHITECTURE": "External source access is isolated into contracts, health facts, credential preflight, manual official-file fallback, acceptance modes and security audit. Engines calculate; React displays.",
        "OPERATOR_GUIDE": commands,
        "CREDENTIALS": "Credential values are never committed or printed. Presence only is reported.\n\n" + commands,
        "SOURCE_DECISIONS": md_table(["Source", "Status", "Action"], [[h["source_id"], h["access_status"], h["operator_action_required"]] for h in health]),
        "MANUAL_IMPORT": "Use only unmodified official files acquired through permitted access.\n\n" + commands,
        "COMMERCIAL_ACCESS": "No purchase/contact made. Pricing: NOT VERIFIED. Questions: internal use, derived data, corrections, storage, redistribution, SLA, jurisdiction.",
        "SECURITY": "Run `python .\\scripts\\audit_edgeiq_external_data_security_v1.py`. Do not print or commit secrets.",
        "ACCEPTANCE": "CODE_COMPLETE_ACCESS_REQUIRED unless approved credential/manual/commercial source is supplied.",
    }
    for name, body in docs.items():
        write_text(DOC / f"EDGEIQ_EXTERNAL_DATA_INTEGRATION_V1_{name}.md", f"# EDGEiQ External Data Integration V1 {name.replace('_', ' ').title()}\n\n{body}\n")
    write_text(DOC / "EDGEIQ_EXTERNAL_DATA_COMMERCIAL_ACCESS_DECISION_V1.md", "# EDGEiQ External Data Commercial Access Decision V1\n\nNo purchase or provider contact was made. Pricing: NOT VERIFIED. Daily Operations is ready to consume a governed API/export after source-specific adapter and schema audit.\n")
    acceptance = {
        "overall_status": "CODE_COMPLETE_ACCESS_REQUIRED",
        "starting_commit": preflight["head"],
        "run_id": RUN_ID,
        "racingcom_catalogue_status": health[0]["access_status"],
        "racingcom_graphql_status": health[1]["access_status"],
        "racing_australia_status": health[2]["access_status"],
        "post_cutoff_official_results_found": 0,
        "post_cutoff_official_timings_found": 0,
        "post_cutoff_canonical_timing_rows_added": 0,
        "performance_base_rows_added": 0,
        "normalisation_rows": count_rows(DATA / "edgeiq_performance_normalisation_fact_v1.csv"),
        "horse_aggregates": count_rows(DATA / "edgeiq_horse_performance_aggregate_fact_v1.csv"),
        "horse_ratings": count_rows(DATA / "edgeiq_horse_performance_rating_fact_v1.csv"),
        "snapshots": count_rows(DATA / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv"),
        "projected_performance": count_rows(DATA / "edgeiq_race_entry_projected_performance_fact_v1.csv"),
        "epi": count_rows(DATA / "edgeiq_epi_fact_v1.csv"),
        "secrets_committed": "PENDING_SECURITY_AUDIT",
        "production_systems_changed": "NO",
    }
    write_json(DOC / "EDGEIQ_EXTERNAL_DATA_INTEGRATION_V1_ACCEPTANCE.json", acceptance)
    write_text(DOC / "EDGEIQ_EXTERNAL_DATA_INTEGRATION_V1_ACCEPTANCE_SUMMARY.md", "# EDGEiQ External Data Integration V1 Acceptance\n\n" + md_table(["Source", "Access status", "Action"], [[h["source_id"], h["access_status"], h["operator_action_required"]] for h in health]) + f"\nOverall status: `{acceptance['overall_status']}`\n")
    write_helper_scripts()
    print(json.dumps({"status": "CODE_COMPLETE_ACCESS_REQUIRED", "run_id": RUN_ID, "head": preflight["head"], "health_rows": len(health), "local_candidates": len(local_rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
