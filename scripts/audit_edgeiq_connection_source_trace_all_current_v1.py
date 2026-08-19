import csv, json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
GOV = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
SOURCES = [
    DATA / 'edgeiq_connection_intelligence_v2_1.csv',
    DATA / 'edgeiq_connection_intelligence_v2.csv',
    DATA / 'edgeiq_connection_intelligence_v1.csv',
    DATA / 'edgeiq_current_intelligence_evidence_fix_candidate_v1.csv',
    DATA / 'edgeiq_current_intelligence_evidence_fix_candidate_FRESH_v1.csv',
    DATA / 'edgeiq_live_runner_factor_scorecard_v2.csv',
    DATA / 'edgeiq_runner_dna_drawer_feed_v2.csv',
    DATA / 'edgeiq_explainability_terminal_feed_v1_2.csv',
    DATA / 'edgeiq_live_terminal_feed_v1.csv',
]
OUT = DATA / 'edgeiq_connection_source_trace_all_current_v1.csv'
SUMMARY = DATA / 'edgeiq_connection_source_trace_all_current_v1_summary.csv'
REPORT = DATA / 'edgeiq_connection_source_trace_all_current_v1_report.txt'

def read_csv(path):
    if not path.exists(): return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        r = csv.DictReader(f); return list(r), list(r.fieldnames or [])

def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)

def clean(v): return ' '.join(str(v or '').strip().upper().replace('\u00a0',' ').split())
def clean_horse(v): return ''.join(ch for ch in clean(v) if ch.isalnum())
def clean_person(v): return ''.join(ch for ch in clean(v).replace('&','AND') if ch.isalnum())
def race_no(v):
    s = clean(v).replace('RACE ', '').replace('R','')
    return s.lstrip('0') or s
def key(row): return (clean(row.get('race_date') or row.get('current_race_date') or row.get('_date')), clean(row.get('track') or row.get('_track')), race_no(row.get('race_no') or row.get('_race')), clean_horse(row.get('horse') or row.get('horse_key') or row.get('_horse')))
def race_key(row): return key(row)[:3]
def combo_key(row): return (clean_person(row.get('trainer') or row.get('trainer_name')), clean_person(row.get('jockey') or row.get('jockey_name')))
def to_float(v):
    try:
        s = str(v or '').strip().replace('%','').replace('$','').replace(',','')
        if not s: return None
        return float(s)
    except Exception: return None
def yes(v): return clean(v) in {'YES','TRUE','1','Y','AVAILABLE','MATERIAL','POSITIVE','STRONG','ELITE'}
def text_any(row, cols):
    vals=[]
    for c in cols:
        if c in row and str(row.get(c) or '').strip(): vals.append(str(row.get(c)).strip())
    return ' | '.join(vals)
def has_meaningful_text(v):
    s = clean(v)
    return bool(s and s not in {'NO','FALSE','NONE','NOT APPLICABLE TODAY','NO_CONNECTION','NO_EVIDENCE','LIMITED_CONNECTION'})
def score_angle(score):
    return score is not None and (score >= 60 or score <= 40)

gov, _ = read_csv(GOV)
current_keys = {key(r) for r in gov}
source_indexes = {}
source_meta = []
for path in SOURCES:
    rows, fields = read_csv(path)
    idx = defaultdict(list)
    combo_idx = defaultdict(list)
    for r in rows:
        k = key(r)
        if k[0] and k[1] and k[2] and k[3]: idx[k].append(r)
        ck = combo_key(r)
        if ck[0] or ck[1]: combo_idx[ck].append(r)
    source_indexes[path.name] = {'fields': fields, 'by_key': idx, 'by_combo': combo_idx, 'rows': len(rows)}
    source_meta.append({'file': path.name, 'rows': len(rows), 'fields': len(fields), 'has_trainer': 'YES' if any('trainer' in f.lower() for f in fields) else 'NO', 'has_jockey': 'YES' if any('jockey' in f.lower() for f in fields) else 'NO', 'has_connection': 'YES' if any('connection' in f.lower() or 'combo' in f.lower() for f in fields) else 'NO'})

factor_rows, _ = read_csv(DATA / 'edgeiq_live_runner_factor_scorecard_v2.csv')
factors = defaultdict(dict)
for fr in factor_rows:
    factors[key(fr)][clean(fr.get('factor'))] = fr

rows_out=[]
for r in gov:
    k = key(r); ck = combo_key(r); fmap = factors.get(k, {})
    trainer_factor = fmap.get('TRAINER', {})
    jockey_factor = fmap.get('JOCKEY', {})
    combo_factor = fmap.get('COMBO', {})
    trainer_score = to_float(trainer_factor.get('factor_score'))
    jockey_score = to_float(jockey_factor.get('factor_score'))
    combo_score = to_float(combo_factor.get('factor_score'))
    matched_sources=[]; summaries=[]; matched_by=[]
    source_detail=[]
    for name, ix in source_indexes.items():
        matches = []
        by_key = ix['by_key'].get(k, [])
        if by_key:
            matches.extend(('runner_key', m) for m in by_key[:3])
        elif name in {'edgeiq_live_runner_factor_scorecard_v2.csv','edgeiq_runner_dna_drawer_feed_v2.csv'}:
            # These files are runner-key based only; no combo fallback needed.
            pass
        else:
            by_combo = ix['by_combo'].get(ck, [])
            if by_combo:
                matches.extend(('trainer_jockey_combo', m) for m in by_combo[:3])
        if matches:
            matched_sources.append(name)
            matched_by.append(f'{name}:{matches[0][0]}')
            for how, m in matches[:1]:
                summary = text_any(m, ['connection_narrative','connection_summary_for_decision_engine','connection_angle_1','connection_angle_summary','edgeiq_connection_angle_summary','edgeiq_connection_angle_summary_v2','trainer_track_read','combo_read','factor_explanation','impact_explanation'])
                if summary: summaries.append(f'{name}: {summary}')
                source_detail.append(f'{name}={how}')
    factor_connection_summaries=[]
    for label, fr, sc in [('Trainer Pattern', trainer_factor, trainer_score), ('Jockey Pattern', jockey_factor, jockey_score), ('Partnership Pattern', combo_factor, combo_score)]:
        if fr and sc is not None and clean(fr.get('factor_band')) != 'NO_SCORE':
            factor_connection_summaries.append(f'{label}: {fr.get("factor_band", "")} {sc:g}. {fr.get("factor_explanation", "")}')
    if factor_connection_summaries and 'edgeiq_live_runner_factor_scorecard_v2.csv' not in matched_sources:
        matched_sources.append('edgeiq_live_runner_factor_scorecard_v2.csv')
        matched_by.append('edgeiq_live_runner_factor_scorecard_v2.csv:runner_key')
    if factor_connection_summaries:
        summaries = factor_connection_summaries + summaries
    connection_scores = [s for s in [trainer_score, jockey_score, combo_score] if s is not None]
    connection_score = round(sum(connection_scores)/len(connection_scores), 2) if connection_scores else None
    qualified = any(score_angle(s) for s in [trainer_score, jockey_score, combo_score]) or any(has_meaningful_text(s) and not any(bad in clean(s) for bad in ['NO QUALIFYING','NO CONNECTION','NO_EVIDENCE']) for s in summaries)
    source_matched = bool(matched_sources)
    if qualified:
        truth = 'QUALIFYING_CONNECTION_ANGLE'
    elif source_matched:
        truth = 'TRUE_ZERO_NO_QUALIFYING_ANGLE'
    else:
        truth = 'SOURCE_MISSING_OR_JOIN_FAILED'
    reason = truth if source_matched else 'No current-runner or trainer/jockey-combo match in scanned connection sources.'
    rows_out.append({
        'race_date': r.get('race_date',''), 'track': r.get('track',''), 'race_no': r.get('race_no',''), 'horse': r.get('horse',''),
        'trainer': r.get('trainer',''), 'jockey': r.get('jockey',''),
        'matched_sources': '|'.join(dict.fromkeys(matched_sources)),
        'matched_by': '|'.join(dict.fromkeys(matched_by)),
        'source_match_status': 'SOURCE_MATCH_WITH_ANGLE' if qualified else ('SOURCE_MATCH_WITH_NO_ANGLE' if source_matched else 'SOURCE_MISSING'),
        'trainer_score': '' if trainer_score is None else f'{trainer_score:g}',
        'jockey_score': '' if jockey_score is None else f'{jockey_score:g}',
        'combo_score': '' if combo_score is None else f'{combo_score:g}',
        'connection_score': '' if connection_score is None else f'{connection_score:g}',
        'connection_qualified_angle': 'YES' if qualified else 'NO',
        'connection_source_matched': 'YES' if source_matched else 'NO',
        'connection_summary_available': 'YES' if summaries else 'NO',
        'connection_summary': ' || '.join(summaries[:4]),
        'no_match_or_no_angle_reason': reason,
    })

race_counts=[]
byrace=defaultdict(list)
for ro in rows_out: byrace[(ro['race_date'], clean(ro['track']), race_no(ro['race_no']))].append(ro)
for rk, rs in sorted(byrace.items()):
    race_counts.append({
        'race_date': rk[0], 'track': rk[1], 'race_no': rk[2], 'field_size': len(rs),
        'connection_any_source_count': sum(1 for x in rs if x['connection_source_matched']=='YES'),
        'connection_qualified_angle_count': sum(1 for x in rs if x['connection_qualified_angle']=='YES'),
        'connection_score_available_count': sum(1 for x in rs if x['connection_score']!=''),
        'connection_summary_available_count': sum(1 for x in rs if x['connection_summary_available']=='YES'),
    })
missing = sum(1 for x in rows_out if x['connection_source_matched'] != 'YES')
qualified = sum(1 for x in rows_out if x['connection_qualified_angle'] == 'YES')
source_matched = sum(1 for x in rows_out if x['connection_source_matched'] == 'YES')
if source_matched == 0:
    status='CONNECTION_SOURCES_MISSING'
elif missing > 0:
    status='CONNECTION_JOIN_FAILURE_FOUND'
else:
    status='CONNECTION_TRACE_COMPLETE'
summary={
    'status': status, 'generated_at': datetime.now().isoformat(timespec='seconds'),
    'rows': len(rows_out), 'races': len(byrace), 'connection_source_matched_rows': source_matched,
    'connection_qualified_angle_rows': qualified, 'connection_true_zero_rows': sum(1 for x in rows_out if x['source_match_status']=='SOURCE_MATCH_WITH_NO_ANGLE'),
    'connection_source_missing_rows': missing,
    'caulfield_r7_source_matched': sum(1 for x in rows_out if x['track'].upper()=='CAULFIELD' and str(x['race_no'])=='7' and x['connection_source_matched']=='YES'),
    'caulfield_r7_qualified': sum(1 for x in rows_out if x['track'].upper()=='CAULFIELD' and str(x['race_no'])=='7' and x['connection_qualified_angle']=='YES'),
    'sources_scanned': len(SOURCES),
}
fields=list(rows_out[0].keys()) if rows_out else ['status']
write_csv(OUT, rows_out, fields)
write_csv(SUMMARY, [summary], list(summary.keys()))
REPORT.write_text('\n'.join([
    'EDGEiQ Connection Source Trace All Current V1','='*50,
    f'Status: {status}', f'Rows/races: {summary["rows"]}/{summary["races"]}',
    f'Source matched rows: {source_matched}', f'Qualified angle rows: {qualified}',
    f'True zero rows: {summary["connection_true_zero_rows"]}', f'Source missing rows: {missing}',
    f'CAULFIELD R7 source matched/qualified: {summary["caulfield_r7_source_matched"]}/{summary["caulfield_r7_qualified"]}',
    '', 'Race-level counts:',
] + [json.dumps(x, ensure_ascii=False) for x in race_counts] + ['', 'Sources scanned:'] + [json.dumps(x, ensure_ascii=False) for x in source_meta]) + '\n', encoding='utf-8')
print(status)
