from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
REPORT = DATA / 'edgeiq_v7_2_render_switch_build_v1_report.txt'
OUT = DATA / 'edgeiq_v7_2_render_switch_build_result_v1.csv'
SUM = DATA / 'edgeiq_v7_2_render_switch_build_result_v1_summary.csv'

def read_any(path):
    if not path.exists(): return ''
    raw = path.read_bytes()
    for enc in ['utf-8-sig','utf-16','utf-16-le','utf-16-be','cp1252']:
        try: return raw.decode(enc)
        except Exception: pass
    return raw.decode('utf-8', errors='replace')
text = read_any(REPORT); low = text.lower()
contains_built = 'built in' in low and 'vite' in low
contains_error = 'error ts' in low or 'failed to compile' in low or 'build failed' in low
status = 'BUILD_PASS' if contains_built and not contains_error else 'BUILD_FAIL'
row = {'build_report':str(REPORT.relative_to(BASE)),'report_exists':'YES' if REPORT.exists() else 'NO','contains_vite_built':'YES' if contains_built else 'NO','contains_typescript_error':'YES' if contains_error else 'NO','contains_chunk_warning':'YES' if 'some chunks are larger than 500 kb' in low else 'NO','status':status}
pd.DataFrame([row]).to_csv(OUT,index=False)
metrics={'built_at':datetime.now(timezone.utc).isoformat(), **row}
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False))
