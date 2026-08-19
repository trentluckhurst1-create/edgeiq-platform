from edgeiq_external_data_common_v1 import ROOT,DOC,now,write_csv,write_json
import json,re,subprocess
patterns=[re.compile(r'(?i)(authorization|x-api-key|cookie)\s*[:=]\s*([^\n\s]{12,})'),re.compile(r'(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[\"\']?([A-Za-z0-9_./+=-]{24,})')]
tracked=[line for line in subprocess.run(['git','ls-files'],cwd=ROOT,text=True,capture_output=True).stdout.splitlines() if line.startswith('scripts/edgeiq_external_data_') or line.startswith('scripts/validate_edgeiq_external_data_') or line.startswith('scripts/show_edgeiq_external_data_') or line.startswith('scripts/audit_edgeiq_external_data_') or line.startswith('scripts/run_edgeiq_external_source_') or line.startswith('scripts/import_edgeiq_official_source_') or line.startswith('scripts/test_edgeiq_external_data_') or line.startswith('docs/external-data-integration-v1/') or line.startswith('config/') or line == '.gitignore']
rows=[]
for rel in tracked:
    path=ROOT/rel
    if path.suffix.lower() not in {'.py','.ps1','.ts','.tsx','.js','.json','.md','.txt','.csv','.env','.example','.yml','.yaml'} or not path.exists() or path.stat().st_size > 5_000_000: continue
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
(DOC/'EDGEIQ_EXTERNAL_DATA_SECURITY_AUDIT_V1.md').write_text(f'# EDGEiQ External Data Security Audit V1\n\nStatus: `{status}`\n\nSecrets committed: `'+('NO' if status=='PASS' else 'REVIEW_REQUIRED')+'`\n',encoding='utf-8')
print(json.dumps({'status':status,'findings':len(rows)},indent=2))
raise SystemExit(0 if status=='PASS' else 2)
