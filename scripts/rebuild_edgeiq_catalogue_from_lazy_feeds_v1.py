from __future__ import annotations
import json, os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.environ.get('EDGEIQ_DATA_DIR',str(ROOT/'public'/'data')))
SUMMARY=DATA/'edgeiq_meetings_summary_feed_v1.json'
MEETINGS=DATA/'meetings'
OUT=DATA/'edgeiq_three_day_product_catalog_v1.json'

def main():
    if not SUMMARY.exists(): raise SystemExit(f'missing summary feed: {SUMMARY}')
    summary=json.loads(SUMMARY.read_text(encoding='utf-8-sig'))
    meetings=[]
    missing=[]
    for day in summary.get('days',[]) or []:
        for sm in day.get('meetings',[]) or []:
            key=str(sm.get('meetingKey','')).strip()
            date=str(sm.get('date') or day.get('date') or '').strip()[:10]
            matched=None
            for p in MEETINGS.glob(f'{date}_*.json'):
                try:
                    payload=json.loads(p.read_text(encoding='utf-8-sig'))
                except Exception:
                    continue
                meeting=payload.get('meeting') if isinstance(payload,dict) else None
                if isinstance(meeting,dict) and str(meeting.get('meetingKey','')).strip()==key:
                    matched=meeting;break
            if matched is None: missing.append(f'{date}|{key}')
            else: meetings.append(matched)
    if missing: raise SystemExit('missing lazy meeting detail feeds: '+', '.join(missing[:10]))
    payload={'schemaVersion':'edgeiq_three_day_catalog_rebuilt_from_lazy_v1','generatedAt':summary.get('generatedAt',''),'dates':[str(d.get('date','')) for d in summary.get('days',[]) or []],'dayLabels':{str(d.get('date','')):str(d.get('key','')) for d in summary.get('days',[]) or []},'meetings':meetings}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    runners=sum(len(r.get('runners',[]) or []) for m in meetings for r in m.get('races',[]) or [])
    print(f'REBUILT_CATALOG meetings={len(meetings)} runners={runners} output={OUT}')
if __name__=='__main__':main()
