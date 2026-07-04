import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
IN_BOARD = DATA / 'edgeiq_live_runner_board_governed_v7_2g2_FRESH_CURRENT_EVIDENCE_MERGED.csv'
FACTOR = DATA / 'edgeiq_live_runner_factor_scorecard_v2.csv'
OUT = DATA / 'edgeiq_command_enrichment_feed_v2_FRESH_CURRENT.csv'
SUMMARY = DATA / 'edgeiq_command_enrichment_feed_v2_fresh_current_v1_summary.csv'
AUDIT = DATA / 'edgeiq_command_enrichment_feed_v2_fresh_current_v1_audit.csv'
REPORT = DATA / 'edgeiq_command_enrichment_feed_v2_fresh_current_v1_report.txt'
EXPECTED_ROWS = 383
EXPECTED_RACES = 25

def read_csv(path):
    if not path.exists():
        return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        r = csv.DictReader(f)
        return list(r), list(r.fieldnames or [])

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader(); w.writerows(rows)

def clean(v):
    return ' '.join(str(v or '').strip().upper().replace('\u00a0', ' ').split())

def clean_horse(v):
    return ''.join(ch for ch in clean(v) if ch.isalnum())

def race_no(v):
    s = clean(v).replace('RACE ', '').replace('R', '')
    return s.lstrip('0') or s

def key(row):
    return (clean(row.get('race_date') or row.get('current_race_date')), clean(row.get('track')), race_no(row.get('race_no')), clean_horse(row.get('horse') or row.get('horse_key')))

def rkey(row):
    return (clean(row.get('race_date') or row.get('current_race_date')), clean(row.get('track')), race_no(row.get('race_no')))

def yes(v):
    return clean(v) in {'YES', 'TRUE', '1', 'Y'}

def to_float(v):
    try:
        s = str(v or '').strip().replace('$', '').replace(',', '')
        if not s:
            return None
        return float(s)
    except Exception:
        return None

def first_value(row, names):
    for n in names:
        if n in row and str(row.get(n) or '').strip() != '':
            return row.get(n)
    return ''

def format_score(v):
    n = to_float(v)
    if n is None:
        return ''
    # Treat blank-derived zeroes as missing unless the source is a true factor score row.
    if abs(n) < 0.000001:
        return ''
    if abs(n - round(n)) < 0.000001:
        return str(int(round(n)))
    return f'{n:.2f}'.rstrip('0').rstrip('.')

def price(row):
    return first_value(row, ['edgeiq_active_display_fair_price_shadow','edgeiq_active_display_fair_price','edgeiq_v7_2g2_guarded_display_fair_price','display_fair_price','ui_fair_price','fair_price'])

def market_summary(row):
    existing = row.get('edgeiq_market_signal_summary', '')
    if existing:
        return existing
    bits = []
    for name in ['display_source','display_decision','market_state','market_source_status','live_price','display_fair_price']:
        val = row.get(name, '')
        if val:
            bits.append(f'{name}={val}')
    return '; '.join(bits) if bits else 'Market price context loaded.'

def score_from_factor_map(fmap, factor_names):
    for f in factor_names:
        row = fmap.get(f)
        if row:
            val = format_score(row.get('factor_score'))
            if val:
                return val, f'{f}:FACTOR_SCORECARD_V2'
    return '', f'{"/".join(factor_names)}:MISSING'

board, board_fields = read_csv(IN_BOARD)
factor_rows, _ = read_csv(FACTOR)
factors_by_runner = defaultdict(dict)
for fr in factor_rows:
    factors_by_runner[key(fr)][clean(fr.get('factor'))] = fr

race_rows = defaultdict(list)
for r in board:
    race_rows[rkey(r)].append(r)

base_rows = []
for r in board:
    fmap = factors_by_runner.get(key(r), {})
    distance_score, distance_src = score_from_factor_map(fmap, ['DISTANCE'])
    condition_score, condition_src = score_from_factor_map(fmap, ['TRACK', 'CONDITION'])
    class_score, class_src = score_from_factor_map(fmap, ['CLASS'])
    campaign_score, campaign_src = score_from_factor_map(fmap, ['CAMPAIGN'])
    pace_score, pace_src = score_from_factor_map(fmap, ['PACE', 'SPEED'])
    confidence_score, confidence_src = score_from_factor_map(fmap, ['CONFIDENCE'])
    # Connections and market are evidence cards; give a neutral evidence baseline only when evidence exists.
    connection_score = '50' if yes(r.get('edgeiq_connection_evidence_available')) else ''
    market_score = '50' if yes(r.get('edgeiq_market_evidence_available')) else ''
    overall = format_score(first_value(r, ['total_rating_points','runner_score_v3','runner_score_v2','runner_dna_v6_2_score']))
    if not overall:
        dna = to_float(r.get('runner_dna_v6_2_score'))
        if dna and dna > 0:
            overall = format_score(dna)
    score_sources = [
        f'OVERALL:{"LIVE_RATING_INPUT" if overall else "MISSING"}', distance_src, condition_src, class_src,
        campaign_src, pace_src,
        f'CONNECTIONS:{"EVIDENCE_AVAILABLE_BASELINE" if connection_score else "MISSING"}',
        f'MARKET:{"EVIDENCE_AVAILABLE_BASELINE" if market_score else "MISSING"}', confidence_src
    ]
    edge = to_float(r.get('display_edge_pct') or r.get('ui_edge_pct') or r.get('edge_pct'))
    market_role = 'MARKET_WATCH' if yes(r.get('edgeiq_market_evidence_available')) else ''
    if edge is not None and edge >= 5:
        market_role = 'VALUE_EDGE'
    elif edge is not None and edge <= -15:
        market_role = 'OVERBET_RISK'
    review = []
    if yes(r.get('edgeiq_connection_evidence_available')): review.append('CONNECTION')
    if yes(r.get('edgeiq_market_evidence_available')): review.append('MARKET')
    if yes(r.get('edgeiq_hidden_gem_evidence_available')): review.append('HIDDEN_GEM')
    if any([overall, distance_score, condition_score, class_score, campaign_score, pace_score, connection_score, market_score, confidence_score]): review.append('SCORE')
    base_rows.append({
        'race_date': r.get('race_date',''),
        'track': r.get('track',''),
        'race_no': r.get('race_no',''),
        'horse': r.get('horse',''),
        'edgeiq_active_display_fair_price': price(r),
        'edgeiq_v7_2g2_guarded_display_fair_price': first_value(r, ['edgeiq_v7_2g2_guarded_display_fair_price','edgeiq_v7_2g2_active_display_fair_price_shadow','edgeiq_active_display_fair_price_shadow']),
        'edgeiq_connection_evidence_available_v2': 'YES' if yes(r.get('edgeiq_connection_evidence_available')) else 'NO',
        'edgeiq_connection_angle_summary_v2': r.get('edgeiq_connection_angle_summary',''),
        'edgeiq_market_evidence_available_v2': 'YES' if yes(r.get('edgeiq_market_evidence_available')) else 'NO',
        'edgeiq_market_signal_summary_v2': market_summary(r) if yes(r.get('edgeiq_market_evidence_available')) else '',
        'edgeiq_hidden_gem_evidence_available_v2': 'YES' if yes(r.get('edgeiq_hidden_gem_evidence_available')) else 'NO',
        'edgeiq_hidden_gem_summary_v2': r.get('edgeiq_hidden_gem_summary',''),
        'edgeiq_score_overall_v2': overall,
        'edgeiq_score_distance_v2': distance_score,
        'edgeiq_score_condition_v2': condition_score,
        'edgeiq_score_class_v2': class_score,
        'edgeiq_score_campaign_v2': campaign_score,
        'edgeiq_score_pace_v2': pace_score,
        'edgeiq_score_connections_v2': connection_score,
        'edgeiq_score_market_v2': market_score,
        'edgeiq_score_confidence_v2': confidence_score,
        'edgeiq_score_source_v2': '|'.join(score_sources),
        'command_market_role_v2': market_role,
        'command_connection_role_v2': 'CONNECTION_ANGLE' if yes(r.get('edgeiq_connection_evidence_available')) else '',
        'command_review_flag_v2': '|'.join(dict.fromkeys(review)),
        '_race_key': rkey(r),
    })

counts = {}
for rk, rows in race_rows.items():
    members = [br for br in base_rows if br['_race_key'] == rk]
    counts[rk] = {
        'race_field_size_v2': str(len(rows)),
        'race_connection_count_v2': str(sum(1 for m in members if m['edgeiq_connection_evidence_available_v2'] == 'YES')),
        'race_market_count_v2': str(sum(1 for m in members if m['edgeiq_market_evidence_available_v2'] == 'YES')),
        'race_hidden_gem_count_v2': str(sum(1 for m in members if m['edgeiq_hidden_gem_evidence_available_v2'] == 'YES')),
        'race_score_breakdown_count_v2': str(sum(1 for m in members if any(m.get(c) for c in ['edgeiq_score_overall_v2','edgeiq_score_distance_v2','edgeiq_score_condition_v2','edgeiq_score_class_v2','edgeiq_score_campaign_v2','edgeiq_score_pace_v2','edgeiq_score_connections_v2','edgeiq_score_market_v2','edgeiq_score_confidence_v2']))),
    }
for br in base_rows:
    br.update(counts[br['_race_key']])
    del br['_race_key']

fields = ['race_date','track','race_no','horse','edgeiq_active_display_fair_price','edgeiq_v7_2g2_guarded_display_fair_price','edgeiq_connection_evidence_available_v2','edgeiq_connection_angle_summary_v2','edgeiq_market_evidence_available_v2','edgeiq_market_signal_summary_v2','edgeiq_hidden_gem_evidence_available_v2','edgeiq_hidden_gem_summary_v2','edgeiq_score_overall_v2','edgeiq_score_distance_v2','edgeiq_score_condition_v2','edgeiq_score_class_v2','edgeiq_score_campaign_v2','edgeiq_score_pace_v2','edgeiq_score_connections_v2','edgeiq_score_market_v2','edgeiq_score_confidence_v2','edgeiq_score_source_v2','command_market_role_v2','command_connection_role_v2','command_review_flag_v2','race_field_size_v2','race_connection_count_v2','race_market_count_v2','race_hidden_gem_count_v2','race_score_breakdown_count_v2']

races = set(rkey(r) for r in board)
caulfield_r7 = [r for r in base_rows if clean(r.get('race_date')) == '2026-06-27' and clean(r.get('track')) == 'CAULFIELD' and race_no(r.get('race_no')) == '7']
dupe = len([key(r) for r in board]) - len(set(key(r) for r in board))
status = 'COMMAND_ENRICHMENT_V2_FRESH_CURRENT_BUILT'
if len(base_rows) != EXPECTED_ROWS or len(races) != EXPECTED_RACES or len(caulfield_r7) != 19 or dupe:
    status = 'BLOCKED'
summary = {
    'status': status,
    'generated_at': datetime.now().isoformat(timespec='seconds'),
    'rows': len(base_rows),
    'races': len(races),
    'duplicate_runner_keys': dupe,
    'caulfield_r7_rows': len(caulfield_r7),
    'market_available_rows': sum(1 for r in base_rows if r['edgeiq_market_evidence_available_v2'] == 'YES'),
    'connection_available_rows': sum(1 for r in base_rows if r['edgeiq_connection_evidence_available_v2'] == 'YES'),
    'hidden_gem_available_rows': sum(1 for r in base_rows if r['edgeiq_hidden_gem_evidence_available_v2'] == 'YES'),
    'score_rows': sum(1 for r in base_rows if r['race_score_breakdown_count_v2'] != '0'),
    'production_changed': 'NO',
}
audit_rows = []
for rk, vals in sorted(counts.items()):
    audit_rows.append({'race_date': rk[0], 'track': rk[1], 'race_no': rk[2], **vals})
write_csv(OUT, base_rows, fields)
write_csv(SUMMARY, [summary], list(summary.keys()))
write_csv(AUDIT, audit_rows, list(audit_rows[0].keys()) if audit_rows else ['status'])
REPORT.write_text('\n'.join([
    'EDGEiQ Command Enrichment Feed V2 Fresh Current V1',
    '=' * 55,
    f'Status: {status}',
    f'Rows: {summary["rows"]}',
    f'Races: {summary["races"]}',
    f'CAULFIELD R7 rows: {summary["caulfield_r7_rows"]}',
    f'Market available rows: {summary["market_available_rows"]}',
    f'Connection available rows: {summary["connection_available_rows"]}',
    f'Hidden gem available rows: {summary["hidden_gem_available_rows"]}',
    f'Score rows: {summary["score_rows"]}',
    'Zero/missing score policy: missing, blank, and blank-derived zero scores are emitted blank for UI NOT LOADED handling.',
    'Production changed: NO',
]) + '\n', encoding='utf-8')
print(status)
