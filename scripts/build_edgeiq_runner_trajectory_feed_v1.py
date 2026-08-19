import csv, math, re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
GOV = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
FULL_FORM = DATA / 'full_career_form.csv'
RUNNER_HISTORY = DATA / 'runner_form_history.csv'
FORM_INTEL = DATA / 'edgeiq_form_intelligence_v2.csv'
OUT = DATA / 'edgeiq_runner_trajectory_feed_v1.csv'
SUMMARY = DATA / 'edgeiq_runner_trajectory_feed_v1_summary.csv'
AUDIT = DATA / 'edgeiq_runner_trajectory_feed_v1_audit.csv'
REPORT = DATA / 'edgeiq_runner_trajectory_feed_v1_report.txt'
COVERAGE = DATA / 'edgeiq_runner_trajectory_command_coverage_audit_v1.csv'
COVERAGE_SUMMARY = DATA / 'edgeiq_runner_trajectory_command_coverage_audit_v1_summary.csv'
COVERAGE_REPORT = DATA / 'edgeiq_runner_trajectory_command_coverage_audit_v1_report.txt'

def read_csv(path):
    if not path.exists():
        return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader(); writer.writerows(rows)

def clean(v):
    return ' '.join(str(v or '').strip().upper().replace('\u00a0', ' ').split())

def clean_horse(v):
    s = clean(v)
    s = re.sub(r'\([^)]*\)', '', s)
    return ''.join(ch for ch in s if ch.isalnum())

def race_no(v):
    s = clean(v).replace('RACE ', '').replace('R', '')
    return s.lstrip('0') or s

def key(row):
    return (clean(row.get('race_date') or row.get('current_race_date')), clean(row.get('track')), race_no(row.get('race_no')), clean_horse(row.get('horse') or row.get('horse_key')))

def rkey(row):
    return key(row)[:3]

def to_float(v):
    try:
        s = str(v or '').strip().replace('$', '').replace(',', '').replace('L', '').replace('l', '')
        if s in {'', '-', '--'}:
            return None
        return float(s)
    except Exception:
        return None

def parse_pos(v):
    s = str(v or '').strip().upper()
    if not s:
        return None
    m = re.search(r'(\d+)', s)
    return int(m.group(1)) if m else None

def parse_date(v):
    s = str(v or '').strip()
    if not s:
        return ''
    return s[:10]

def fmt(v, dp=2):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ''
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f'{v:.{dp}f}'.rstrip('0').rstrip('.')

def avg(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None

def slope(vals):
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return None
    # vals are oldest -> newest; positive means improving for ratings/SP? caller interprets.
    n = len(vals)
    xs = list(range(n))
    xbar = sum(xs) / n
    ybar = sum(vals) / n
    den = sum((x - xbar) ** 2 for x in xs)
    if den == 0:
        return None
    return sum((x - xbar) * (y - ybar) for x, y in zip(xs, vals)) / den

def band_from_score(score, evidence):
    if evidence == 'NO_HISTORY':
        return 'NO_HISTORY'
    if score >= 70:
        return 'IMPROVING'
    if score >= 56:
        return 'POSITIVE'
    if score >= 44:
        return 'STABLE'
    if score >= 30:
        return 'DECLINING'
    return 'SHARP_DECLINE'

def classify_component(value, positive_good=True):
    if value is None:
        return 'MISSING'
    val = value if positive_good else -value
    if val > 1.5: return 'IMPROVING'
    if val > 0.25: return 'SLIGHT_UP'
    if val >= -0.25: return 'STABLE'
    if val >= -1.5: return 'SLIGHT_DOWN'
    return 'DECLINING'

gov, gov_fields = read_csv(GOV)
full_form, full_fields = read_csv(FULL_FORM)
runner_history, hist_fields = read_csv(RUNNER_HISTORY)
form_intel, form_fields = read_csv(FORM_INTEL)

form_by_horse = defaultdict(list)
for row in full_form:
    h = clean_horse(row.get('horse') or row.get('horse_key'))
    if not h:
        continue
    rec = dict(row)
    rec['_date'] = parse_date(row.get('run_date') or row.get('run_date_iso'))
    rec['_rating'] = to_float(row.get('run_rating') or row.get('rating_display') or row.get('rating'))
    rec['_sp'] = to_float(row.get('starting_price') or row.get('sp') or row.get('SP') or row.get('sp_text'))
    rec['_finish'] = parse_pos(row.get('finish_pos') or row.get('finishing_position') or row.get('position'))
    rec['_margin'] = to_float(row.get('margin') or row.get('beaten_margin'))
    if rec['_date'] or rec['_rating'] is not None or rec['_finish'] is not None:
        form_by_horse[h].append(rec)
for h in list(form_by_horse.keys()):
    form_by_horse[h].sort(key=lambda r: r.get('_date') or '', reverse=True)

hist_by_key = {clean_horse(r.get('horse') or r.get('horse_key')): r for r in runner_history}
form_intel_by_key = {key(r): r for r in form_intel}

rows_out = []
audit_rows = []
for gr in gov:
    h = clean_horse(gr.get('horse') or gr.get('horse_key'))
    starts = form_by_horse.get(h, [])[:5]
    oldest_to_newest = list(reversed(starts))
    ratings = [r.get('_rating') for r in oldest_to_newest]
    finishes = [r.get('_finish') for r in oldest_to_newest]
    sps = [r.get('_sp') for r in oldest_to_newest]
    margins = [r.get('_margin') for r in oldest_to_newest]
    rating_slope = slope(ratings)
    finish_slope_raw = slope(finishes)
    # Lower finish position is better, so invert slope for positive-good movement.
    finish_movement = -finish_slope_raw if finish_slope_raw is not None else None
    sp_slope_raw = slope(sps)
    # Shortening SP is a positive market movement, so invert.
    sp_movement = -sp_slope_raw if sp_slope_raw is not None else None
    margin_slope_raw = slope(margins)
    margin_movement = -margin_slope_raw if margin_slope_raw is not None else None
    recent_rating = ratings[-1] if ratings else None
    prior_rating = ratings[-2] if len(ratings) >= 2 else None
    rating_delta = recent_rating - prior_rating if recent_rating is not None and prior_rating is not None else None
    recent_finish = finishes[-1] if finishes else None
    prior_finish = finishes[-2] if len(finishes) >= 2 else None
    finish_delta = prior_finish - recent_finish if recent_finish is not None and prior_finish is not None else None
    recent_sp = sps[-1] if sps else None
    prior_sp = sps[-2] if len(sps) >= 2 else None
    sp_delta = prior_sp - recent_sp if recent_sp is not None and prior_sp is not None else None
    form_row = form_intel_by_key.get(key(gr), {})
    epf = to_float(form_row.get('EPF') or form_row.get('EPF_value'))
    # Score is descriptive only; no pricing/model maths.
    score = 50.0
    components = []
    if rating_slope is not None:
        score += max(-18, min(18, rating_slope * 3.0)); components.append('RATING_MOVEMENT')
    if finish_movement is not None:
        score += max(-14, min(14, finish_movement * 2.0)); components.append('FINISH_POSITION_MOVEMENT')
    if sp_movement is not None:
        score += max(-10, min(10, sp_movement * 0.7)); components.append('SP_MOVEMENT')
    if margin_movement is not None:
        score += max(-8, min(8, margin_movement * 1.2)); components.append('MARGIN_MOVEMENT')
    if epf is not None:
        score += max(-8, min(8, (epf - 50) / 8 if epf > 20 else (epf - 3) * 1.2)); components.append('EPF_CONTEXT')
    score = max(0, min(100, score))
    evidence = 'NO_HISTORY'
    if len(starts) >= 3:
        evidence = 'STRONG_HISTORY'
    elif len(starts) >= 1:
        evidence = 'LIMITED_HISTORY'
    elif form_row:
        evidence = 'FORM_INTELLIGENCE_ONLY'
    band = band_from_score(score, evidence)
    rating_component = classify_component(rating_slope, True)
    finish_component = classify_component(finish_movement, True)
    sp_component = classify_component(sp_movement, True)
    margin_component = classify_component(margin_movement, True)
    trend_bits = []
    if rating_component != 'MISSING': trend_bits.append(f'rating {rating_component.lower().replace("_", " ")}')
    if finish_component != 'MISSING': trend_bits.append(f'finishing-position {finish_component.lower().replace("_", " ")}')
    if sp_component != 'MISSING': trend_bits.append(f'market/SP {sp_component.lower().replace("_", " ")}')
    if margin_component != 'MISSING': trend_bits.append(f'margin {margin_component.lower().replace("_", " ")}')
    if not trend_bits and form_row:
        trend_bits.append((form_row.get('performance_intelligence_label') or form_row.get('form_signal') or 'limited current form context').lower())
    narrative = 'No usable trajectory history found.' if evidence == 'NO_HISTORY' else f"Recent trajectory: {', '.join(trend_bits[:3])}."
    if band in {'IMPROVING','POSITIVE'}:
        narrative += ' Current movement profile is constructive.'
    elif band in {'DECLINING','SHARP_DECLINE'}:
        narrative += ' Current movement profile is a caution.'
    elif band == 'STABLE':
        narrative += ' Current movement profile is broadly stable.'
    out = {
        'race_date': gr.get('race_date',''), 'track': gr.get('track',''), 'race_no': gr.get('race_no',''), 'horse': gr.get('horse',''), 'horse_key': gr.get('horse_key',''),
        'trajectory_score_v1': fmt(score), 'trajectory_band_v1': band, 'trajectory_evidence_status_v1': evidence,
        'recent_start_count_v1': len(starts),
        'rating_movement_v1': fmt(rating_slope), 'rating_delta_last_start_v1': fmt(rating_delta), 'rating_movement_band_v1': rating_component,
        'finish_position_movement_v1': fmt(finish_movement), 'finish_position_delta_last_start_v1': fmt(finish_delta), 'finish_position_movement_band_v1': finish_component,
        'sp_movement_v1': fmt(sp_movement), 'sp_delta_last_start_v1': fmt(sp_delta), 'sp_movement_band_v1': sp_component,
        'margin_movement_v1': fmt(margin_movement), 'margin_movement_band_v1': margin_component,
        'latest_rating_v1': fmt(recent_rating), 'latest_finish_position_v1': fmt(recent_finish), 'latest_sp_v1': fmt(recent_sp),
        'latest_run_date_v1': starts[0].get('_date','') if starts else '',
        'epf_context_v1': fmt(epf), 'form_signal_v1': form_row.get('form_signal',''), 'performance_label_v1': form_row.get('performance_intelligence_label',''),
        'trajectory_narrative_v1': narrative,
        'trajectory_source_v1': '|'.join(components) if components else ('FORM_INTELLIGENCE_ONLY' if form_row else 'NO_SOURCE_HISTORY'),
        'pricing_math_changed': 'NO', 'v6_1_changed': 'NO', 'v7_2g2_changed': 'NO',
    }
    for i, rec in enumerate(starts, 1):
        out[f'last_start_{i}_date_v1'] = rec.get('_date','')
        out[f'last_start_{i}_finish_v1'] = fmt(rec.get('_finish'))
        out[f'last_start_{i}_rating_v1'] = fmt(rec.get('_rating'))
        out[f'last_start_{i}_sp_v1'] = fmt(rec.get('_sp'))
        out[f'last_start_{i}_margin_v1'] = fmt(rec.get('_margin'))
    rows_out.append(out)
    audit_rows.append({
        'race_date': gr.get('race_date',''), 'track': gr.get('track',''), 'race_no': gr.get('race_no',''), 'horse': gr.get('horse',''),
        'has_historical_form': 'YES' if len(starts) else 'NO', 'has_rating_movement': 'YES' if rating_slope is not None else 'NO',
        'has_finish_position_movement': 'YES' if finish_movement is not None else 'NO', 'has_sp_movement': 'YES' if sp_movement is not None else 'NO',
        'has_form_intelligence': 'YES' if bool(form_row) else 'NO', 'trajectory_band': band, 'trajectory_evidence_status': evidence,
    })

# Add missing last-start fields consistently.
fields = list(rows_out[0].keys()) if rows_out else ['race_date','track','race_no','horse']
for i in range(1, 6):
    for suffix in ['date','finish','rating','sp','margin']:
        f = f'last_start_{i}_{suffix}_v1'
        if f not in fields: fields.append(f)
        for row in rows_out: row.setdefault(f, '')

races = set(rkey(r) for r in rows_out)
coverage_counts = {
    'rows': len(rows_out), 'races': len(races),
    'strong_history_rows': sum(1 for r in rows_out if r['trajectory_evidence_status_v1'] == 'STRONG_HISTORY'),
    'limited_history_rows': sum(1 for r in rows_out if r['trajectory_evidence_status_v1'] == 'LIMITED_HISTORY'),
    'form_intelligence_only_rows': sum(1 for r in rows_out if r['trajectory_evidence_status_v1'] == 'FORM_INTELLIGENCE_ONLY'),
    'no_history_rows': sum(1 for r in rows_out if r['trajectory_evidence_status_v1'] == 'NO_HISTORY'),
    'rating_movement_rows': sum(1 for r in rows_out if r['rating_movement_v1'] != ''),
    'finish_movement_rows': sum(1 for r in rows_out if r['finish_position_movement_v1'] != ''),
    'sp_movement_rows': sum(1 for r in rows_out if r['sp_movement_v1'] != ''),
}
readiness = 'READY_FOR_COMMAND_AUDIT' if len(rows_out) == len(gov) and len(races) == len(set(rkey(r) for r in gov)) else 'NOT_READY_ROW_MISMATCH'
summary = {'status': readiness, 'generated_at': datetime.now().isoformat(timespec='seconds'), **coverage_counts, 'pricing_math_changed': 'NO', 'v6_1_changed': 'NO', 'v7_2g2_changed': 'NO'}
write_csv(OUT, rows_out, fields)
write_csv(SUMMARY, [summary], list(summary.keys()))
write_csv(AUDIT, audit_rows, list(audit_rows[0].keys()) if audit_rows else ['status'])
REPORT.write_text('\n'.join([
    'EDGEiQ Runner Trajectory Feed V1', '='*38,
    f'Status: {readiness}', f'Rows/races: {coverage_counts["rows"]}/{coverage_counts["races"]}',
    f'Strong/limited/form-only/no-history: {coverage_counts["strong_history_rows"]}/{coverage_counts["limited_history_rows"]}/{coverage_counts["form_intelligence_only_rows"]}/{coverage_counts["no_history_rows"]}',
    f'Rating movement rows: {coverage_counts["rating_movement_rows"]}',
    f'Finish movement rows: {coverage_counts["finish_movement_rows"]}',
    f'SP movement rows: {coverage_counts["sp_movement_rows"]}',
    'Pricing maths changed: NO', 'V6.1 changed: NO', 'V7.2G2 changed: NO',
]) + '\n', encoding='utf-8')

# COMMAND coverage audit: no apply, only compare potential coverage.
command_rows = []
byrace = defaultdict(list)
for row in rows_out:
    byrace[(clean(row['race_date']), clean(row['track']), race_no(row['race_no']))].append(row)
for rk, members in sorted(byrace.items()):
    field_size = len(members)
    usable = sum(1 for r in members if r['trajectory_evidence_status_v1'] != 'NO_HISTORY')
    movement = sum(1 for r in members if r['rating_movement_v1'] or r['finish_position_movement_v1'] or r['sp_movement_v1'])
    narrative = sum(1 for r in members if r['trajectory_narrative_v1'] and r['trajectory_narrative_v1'] != 'No usable trajectory history found.')
    no_history = sum(1 for r in members if r['trajectory_evidence_status_v1'] == 'NO_HISTORY')
    status = 'COMMAND_TRAJECTORY_READY' if usable else 'COMMAND_TRAJECTORY_TRUE_ZERO_NO_HISTORY'
    command_rows.append({'race_date': rk[0], 'track': rk[1], 'race_no': rk[2], 'field_size': field_size, 'usable_trajectory_count': usable, 'movement_metric_count': movement, 'trajectory_narrative_count': narrative, 'no_history_count': no_history, 'status': status})
coverage_summary = {
    'status': 'COMMAND_TRAJECTORY_COVERAGE_AUDITED_NOT_APPLIED', 'generated_at': datetime.now().isoformat(timespec='seconds'),
    'rows': len(rows_out), 'races': len(byrace), 'races_with_usable_trajectory': sum(1 for r in command_rows if int(r['usable_trajectory_count']) > 0),
    'races_with_no_usable_trajectory': sum(1 for r in command_rows if int(r['usable_trajectory_count']) == 0),
    'usable_trajectory_rows': sum(int(r['usable_trajectory_count']) for r in command_rows),
    'movement_metric_rows': sum(int(r['movement_metric_count']) for r in command_rows),
    'applied_to_command': 'NO', 'pricing_math_changed': 'NO', 'v6_1_changed': 'NO', 'v7_2g2_changed': 'NO'
}
write_csv(COVERAGE, command_rows, list(command_rows[0].keys()) if command_rows else ['status'])
write_csv(COVERAGE_SUMMARY, [coverage_summary], list(coverage_summary.keys()))
COVERAGE_REPORT.write_text('\n'.join([
    'EDGEiQ Runner Trajectory COMMAND Coverage Audit V1', '='*55,
    f'Status: {coverage_summary["status"]}',
    f'Rows/races: {coverage_summary["rows"]}/{coverage_summary["races"]}',
    f'Usable trajectory rows: {coverage_summary["usable_trajectory_rows"]}',
    f'Movement metric rows: {coverage_summary["movement_metric_rows"]}',
    f'Races with usable trajectory: {coverage_summary["races_with_usable_trajectory"]}',
    f'Races with no usable trajectory: {coverage_summary["races_with_no_usable_trajectory"]}',
    'Applied to COMMAND: NO', 'Pricing maths changed: NO', 'V6.1 changed: NO', 'V7.2G2 changed: NO', '',
    'Race coverage:',
] + [f'{r["track"]} R{r["race_no"]}: usable {r["usable_trajectory_count"]}/{r["field_size"]}, movement {r["movement_metric_count"]}/{r["field_size"]}, status {r["status"]}' for r in command_rows]) + '\n', encoding='utf-8')
print(readiness)
print(coverage_summary['status'])
