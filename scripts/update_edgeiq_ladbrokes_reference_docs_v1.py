from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'/'market-intelligence'/'ladbrokes'
json_path=DOCS/'edgeiq_ladbrokes_reference_inspection_v1.json'
md_path=DOCS/'edgeiq_ladbrokes_reference_inspection_v1.md'
if json_path.exists():
    payload=json.loads(json_path.read_text(encoding='utf-8'))
    contract=payload.setdefault('reference_auth_contract',{})
    contract['edgeiq_runtime_env_preferred']=['EDGEIQ_LADBROKES_FROM','EDGEIQ_LADBROKES_X_PARTNER']
    contract['edgeiq_runtime_env_legacy_fallback']=['EDGEIQ_LADBROKES_EMAIL','EDGEIQ_LADBROKES_PARTNER_NAME']
    contract['edgeiq_runtime_env']=['EDGEIQ_LADBROKES_FROM','EDGEIQ_LADBROKES_X_PARTNER','EDGEIQ_LADBROKES_EMAIL','EDGEIQ_LADBROKES_PARTNER_NAME']
    json_path.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
if md_path.exists():
    text=md_path.read_text(encoding='utf-8')
    if 'Preferred EDGEiQ env' not in text:
        text += '\n## EDGEiQ Env Compatibility\n\nPreferred EDGEiQ env: `EDGEIQ_LADBROKES_FROM`, `EDGEIQ_LADBROKES_X_PARTNER`. Legacy fallback remains supported: `EDGEIQ_LADBROKES_EMAIL`, `EDGEIQ_LADBROKES_PARTNER_NAME`.\n'
    md_path.write_text(text,encoding='utf-8')
print('EDGEIQ_LADBROKES_REFERENCE_DOCS_UPDATED')
