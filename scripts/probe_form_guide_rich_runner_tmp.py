from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
path = ROOT/'public/data/edgeiq_form_guide_enriched_v2.json'
data = json.loads(path.read_text(encoding='utf-8'))
races = data.get('races') if isinstance(data, dict) else data
rows=[]
for race in races or []:
    runners = race.get('runners') or []
    for r in runners:
        full = r.get('fullForm') or []
        profiles = sum(1 for k in ['careerRecord','trackRecord','distanceRecord','trackDistanceRecord'] if r.get(k))
        profiles += len(r.get('conditionProfile') or []) + len(r.get('classProfile') or []) + len((r.get('jockeyProfile') or {}).values()) + len(r.get('preparationProfile') or []) + len(r.get('raceDayPattern') or [])
        sec=epi=eri=pir=0
        for run in full[:8]:
            if run.get('historicalEpi') or run.get('performanceRating'): epi += 1
            if run.get('raceRating'): eri += 1
            if any(run.get(k) for k in ['positionInRunning','position_in_running','inRunning','settlingPosition','settling_position']): pir += 1
            if run.get('sectionalIndices'): sec += 1
        score = len(full[:8])*10 + profiles*2 + epi + eri + pir + sec
        rows.append({'score':score,'meeting':race.get('meeting') or race.get('track') or race.get('trackName'),'date':race.get('date') or race.get('raceDate'),'raceNumber':race.get('raceNumber') or race.get('race_no') or race.get('raceNo'),'raceKey':race.get('raceKey') or race.get('race_id') or '', 'runnerName':r.get('runnerName') or r.get('horse') or r.get('name'),'runnerNumber':r.get('runnerNumber') or r.get('no'),'fullForm':len(full),'profiles':profiles,'epiRows':epi,'eriRows':eri,'pirRows':pir,'sectionalRows':sec})
rows.sort(key=lambda x: x['score'], reverse=True)
for row in rows[:30]: print(json.dumps(row, ensure_ascii=False))
