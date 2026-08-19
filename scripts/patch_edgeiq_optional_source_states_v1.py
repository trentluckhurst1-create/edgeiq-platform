
from __future__ import annotations
import csv, json, shutil
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'/'operations-readiness'/'final-acceptance'
DATA=ROOT/'public'/'data'
RESULTS=ROOT/'src'/'edgeiq-os'/'race'/'components'/'ResultsWorkspace.tsx'
DOCS.mkdir(parents=True,exist_ok=True)
cp=RESULTS.with_name(f'{RESULTS.stem}_CHECKPOINT_PRE_OPTIONAL_SOURCE_STATES_V1{RESULTS.suffix}')
if RESULTS.exists() and not cp.exists(): shutil.copy2(RESULTS,cp)
text=RESULTS.read_text(encoding='utf-8') if RESULTS.exists() else ''
if 'Stewards report unavailable from the current governed source.' not in text and 'SectionalsBoundary' in text:
    text=text.replace('</p>\n      <dl>', '</p>\n      <p>Stewards report unavailable from the current governed source.</p>\n      <dl>', 1)
    RESULTS.write_text(text,encoding='utf-8')
weather='WEATHER_UNAVAILABLE'
for q in [DATA/'edgeiq_on_track_weather_governed_v1_2.csv', DATA/'edgeiq_weather_engineering_current_v1.csv']:
    if q.exists() and q.stat().st_size>80: weather='WEATHER_TIMESTAMP_UNKNOWN'
market='MARKET_SNAPSHOT' if (DATA/'edgeiq_market_terminal_feed_v1.csv').exists() else 'MARKET_UNAVAILABLE'
sectionals='SECTIONALS_HISTORICAL_ONLY' if any((DATA/n).exists() for n in ['edgeiq_form_sectional_terminal_feed_v1.csv','racingcom_sectional_warehouse_v2.csv']) else 'SECTIONALS_UNAVAILABLE'
stewards='STEWARDS_UNAVAILABLE'
rows=[{'source':'weather','state':weather,'evidence':'current governed weather file absent or timestamp limited'}, {'source':'live market','state':market,'evidence':'edgeiq_market_terminal_feed_v1 carries snapshot disclosure metadata'}, {'source':'sectionals','state':sectionals,'evidence':'historical sectional warehouses exist; current official sectionals not guaranteed'}, {'source':'stewards','state':stewards,'evidence':'no governed current stewards provider; Results copy states unavailable'}]
with (DOCS/'edgeiq_optional_source_states_v1.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
(DOCS/'edgeiq_optional_source_states_audit_v1.json').write_text(json.dumps({'generated_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),'states':rows,'status':'PASS'},indent=2)+'\n',encoding='utf-8')
print('optional source states PASS')
