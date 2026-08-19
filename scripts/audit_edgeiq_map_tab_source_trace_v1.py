import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
TSX = ROOT / 'src' / 'components' / 'RaceIntelligenceScreen.tsx'
GOV = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
SOURCES = {
    'runner_intel': DATA / 'edgeiq_runner_intelligence_v1.csv',
    'factor_scorecard': DATA / 'edgeiq_live_runner_factor_scorecard_v2.csv',
    'dna_drawer': DATA / 'edgeiq_runner_dna_drawer_feed_v2.csv',
    'race_shape_fallback': DATA / 'edgeiq_race_shape_fallback_engine_v1.csv',
    'live_speed_map_v3': DATA / 'live_speed_map_v3.csv',
    'tactical_dna_speed_map_v2': DATA / 'edgeiq_tactical_dna_speed_map_v2.csv',
    'real_speed_map_positions': DATA / 'edgeiq_real_speed_map_positions.csv',
    'race_shape_fit_v4': DATA / 'edgeiq_race_shape_fit_v4.csv',
    'pace_advantage_ui': DATA / 'edgeiq_pace_advantage_ui_feed_v1.csv',
    'runner_pace_pressure_v2': DATA / 'edgeiq_runner_pace_pressure_v2.csv',
    'pace_pressure_engine_v2_runners': DATA / 'edgeiq_pace_pressure_engine_v2_runners.csv',
    'map_enrichment': DATA / 'edgeiq_map_enrichment_feed_v1.csv',
}
OUT = DATA / 'edgeiq_map_tab_source_trace_v1.csv'
RACE = DATA / 'edgeiq_map_tab_race_summary_v1.csv'
REPORT = DATA / 'edgeiq_map_tab_fix_report_v1.txt'

FIELDS = [
    'speed_map_source_feed', 'projected_speed', 'pace_fit', 'runner_run_style', 'early_speed',
    'late_speed', 'settling_position', 'barrier', 'lane', 'leader_midfield_backmarker_groupings',
    'race_pressure', 'race_shape', 'rail', 'track_condition', 'track_direction',
    'barrier_orientation', 'left_right_handed_logic', 'selected_runner_pace_summary',
    'UI_fallback_rendering_fields'
]
FIX_CLASSES = {'JOIN_FAILED','FIELD_NAME_MISMATCH','UI_FALLBACK_MISSING','FEED_FAILURE'}


def read_csv(path):
    if not path.exists():
        return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader(); writer.writerows(rows)


def clean(v):
    return ' '.join(str(v or '').strip().upper().replace('\u00a0',' ').split())


def clean_track(v):
    return ''.join(ch for ch in clean(v) if ch.isalnum())


def clean_horse(v):
    s = clean(v)
    while '(' in s and ')' in s:
        start = s.find('('); end = s.find(')', start)
        if end <= start: break
        s = (s[:start] + s[end+1:]).strip()
    return ''.join(ch for ch in s if ch.isalnum()).removesuffix('NZ').removesuffix('GB').removesuffix('IRE').removesuffix('FR').removesuffix('USA').removesuffix('JPN').removesuffix('AUS')


def race_no(v):
    s = clean(v).replace('RACE ', '').replace('R', '')
    try:
        return str(int(float(s)))
    except Exception:
        return s.lstrip('0') or s


def date_value(r):
    return clean(r.get('race_date') or r.get('meeting_date') or r.get('meeting_date_join') or r.get('current_race_date') or r.get('date'))


def track_value(r):
    return clean_track(r.get('track') or r.get('track_join'))


def horse_value(r):
    return clean_horse(r.get('horse') or r.get('horse_name') or r.get('horse_display') or r.get('horse_key') or r.get('horse_key_join'))


def runner_key(r):
    return (date_value(r), track_value(r), race_no(r.get('race_no') or r.get('race_no_join')), horse_value(r))


def race_key(r):
    k = runner_key(r)
    return k[:3]


def populated(v):
    return str(v or '').strip() not in {'','-','--','N/A','NA','NULL','None'}


def num(v):
    s = str(v or '').replace('$','').replace('%','').strip()
    if not s: return None
    try:
        n = float(s)
        return n if n == n else None
    except Exception:
        return None


def nz(v):
    n = num(v)
    return n is not None and abs(n) > 1e-9


def first_pop(*vals):
    for v in vals:
        if populated(v):
            return v
    return ''


def get_factor(factor_rows, factor):
    for r in factor_rows:
        if clean(r.get('factor')) == clean(factor):
            return r
    return {}


def build_index(rows):
    idx = {}
    loose = defaultdict(list)
    race = defaultdict(list)
    for r in rows:
        k = runner_key(r)
        if all(k): idx.setdefault(k, r)
        hk = horse_value(r)
        if hk: loose[hk].append(r)
        rk = race_key(r)
        if all(rk): race[rk].append(r)
    return idx, loose, race


def by_field_index(rows):
    d = defaultdict(list)
    for r in rows:
        k = runner_key(r)
        d[k].append(r)
    return d


def classify(ok, alt_available, source_available, missing_reason, true_zero_reason='No material source value exists for this runner.'):
    if ok:
        return 'OK', 'UI path/source field is populated.'
    if alt_available:
        return 'UI_FALLBACK_MISSING', missing_reason
    if source_available:
        return 'SOURCE_MISSING', true_zero_reason
    return 'SOURCE_MISSING', 'No matching source feed value exists.'


gov, gov_fields = read_csv(GOV)
source_rows = {}; source_fields = {}; idx = {}; loose = {}; race_idx = {}
for name, path in SOURCES.items():
    rows, fields = read_csv(path)
    source_rows[name] = rows; source_fields[name] = fields
    idx[name], loose[name], race_idx[name] = build_index(rows)
factor_rows_by_key = by_field_index(source_rows['factor_scorecard'])

text = TSX.read_text(encoding='utf-8') if TSX.exists() else ''
ui_tokens = {
    'MAP tab': 'MAP' in text,
    'Projected SPD label': 'Projected SPD' in text,
    'Pace Fit label': 'Pace Fit' in text,
    'speedMapLanes': 'speedMapLanes' in text,
    'paceMapRole': 'paceMapRole' in text,
    'Race Shape labels': 'Race Shape' in text,
}
ui_ok = all(ui_tokens.values())

rows_out = []
race_members = defaultdict(list)

for g in gov:
    k = runner_key(g); rk = k[:3]
    race_members[rk].append(g)
    joined = {name: idx[name].get(k, {}) for name in SOURCES}
    factor_rows = factor_rows_by_key.get(k, [])
    factor_pace = get_factor(factor_rows, 'PACE')

    source_feed_hit = any(joined[name] for name in ['map_enrichment','runner_intel','live_speed_map_v3','tactical_dna_speed_map_v2','real_speed_map_positions','race_shape_fit_v4','runner_pace_pressure_v2','pace_pressure_engine_v2_runners'])

    ui_projected_speed_ok = nz(joined['map_enrichment'].get('projected_speed')) or nz(joined['runner_intel'].get('projected_spd')) or nz(g.get('projected_spd')) or nz(g.get('early_speed_rating'))
    alt_projected_speed = any([
        nz(joined['runner_intel'].get('tactical_score')),
        nz(joined['tactical_dna_speed_map_v2'].get('avg_early_speed')),
        nz(joined['runner_pace_pressure_v2'].get('avg_early_speed')),
        nz(joined['real_speed_map_positions'].get('settling_score')),
        populated(joined['live_speed_map_v3'].get('speed_map_bucket')),
        populated(joined['race_shape_fit_v4'].get('tactical_speed_bucket')),
        populated(joined['pace_pressure_engine_v2_runners'].get('pace_role_v2')),
    ])
    projected_status, projected_reason = classify(ui_projected_speed_ok, alt_projected_speed, source_feed_hit, 'Projected speed exists in sidecar/recovery feeds but not in current UI lookup fields.')

    ui_pace_fit_ok = nz(joined['map_enrichment'].get('pace_fit')) or nz(factor_pace.get('factor_score'))
    alt_pace_fit = any([
        nz(joined['race_shape_fit_v4'].get('race_shape_fit_score')),
        nz(joined['race_shape_fit_v4'].get('tempo_fit_score')),
        nz(joined['pace_advantage_ui'].get('pace_advantage_score')),
        populated(joined['live_speed_map_v3'].get('tempo_fit')),
        populated(joined['runner_intel'].get('tempo_fit')),
    ])
    pace_fit_status, pace_fit_reason = classify(ui_pace_fit_ok, alt_pace_fit, source_feed_hit, 'Pace fit exists in pace/race-shape sources but not in current factor-score lookup.')

    run_style_ok = populated(first_pop(joined['map_enrichment'].get('run_style'), g.get('settling_band'), g.get('run_style'), g.get('speed_map_bucket'), g.get('early_speed_band'), joined['runner_intel'].get('settling_band'), joined['runner_intel'].get('run_style')))
    alt_run_style = any(populated(joined[n].get(c)) for n,c in [('live_speed_map_v3','speed_map_bucket'),('tactical_dna_speed_map_v2','speed_map_bucket'),('real_speed_map_positions','settling_band'),('race_shape_fit_v4','tactical_speed_bucket'),('pace_pressure_engine_v2_runners','pace_role_v2'),('runner_pace_pressure_v2','tactical_speed_bucket')])
    run_style_status, run_style_reason = classify(run_style_ok, alt_run_style, source_feed_hit, 'Run style exists in speed-map feeds but not in current UI lookup fields.')

    early_ok = nz(joined['map_enrichment'].get('early_speed')) or nz(g.get('early_speed_rating')) or nz(joined['runner_intel'].get('projected_spd'))
    alt_early = any([nz(joined['tactical_dna_speed_map_v2'].get('avg_early_speed')), nz(joined['runner_pace_pressure_v2'].get('avg_early_speed')), nz(joined['real_speed_map_positions'].get('settling_score'))])
    early_status, early_reason = classify(early_ok, alt_early, source_feed_hit, 'Early speed exists in speed-map feeds but current governed/UI fields are blank or zero.')

    late_ok = nz(joined['map_enrichment'].get('late_speed')) or nz(joined['runner_intel'].get('late_power_index'))
    alt_late = any([nz(joined['live_speed_map_v3'].get('late_power_index')), nz(joined['runner_pace_pressure_v2'].get('avg_late_speed')), nz(joined['tactical_dna_speed_map_v2'].get('avg_late_speed'))])
    late_status, late_reason = classify(late_ok, alt_late, source_feed_hit, 'Late speed exists in pace sidecars but not in current UI late-power lookup.')

    settling_ok = populated(first_pop(joined['map_enrichment'].get('settling_position'), g.get('settling_band'), joined['runner_intel'].get('settling_band'), joined['real_speed_map_positions'].get('settling_band')))
    settling_status, settling_reason = classify(settling_ok, alt_run_style, source_feed_hit, 'Settling position exists in speed-map feeds but not in current UI lookup fields.')

    barrier_ok = populated(g.get('barrier'))
    barrier_status, barrier_reason = ('OK','Barrier field is populated.') if barrier_ok else ('SOURCE_MISSING','Barrier is missing from governed board.')
    lane_ok = run_style_ok
    lane_status, lane_reason = ('OK','Lane grouping can be derived from run style.') if lane_ok else (run_style_status, run_style_reason)

    race_fallback = race_idx['race_shape_fallback'].get(rk, [])
    race_pressure_src = race_fallback[0] if race_fallback else {}
    pressure_ok = populated(first_pop(joined['map_enrichment'].get('race_pressure'), race_pressure_src.get('pressure_risk'), race_pressure_src.get('tempo_label'), joined['race_shape_fit_v4'].get('pace_pressure'), joined['pace_pressure_engine_v2_runners'].get('pressure_band_v2')))
    pressure_status, pressure_reason = ('OK','Race pressure field is populated.') if pressure_ok else ('SOURCE_MISSING','No race pressure source found for this race.')
    race_shape_ok = populated(first_pop(joined['map_enrichment'].get('race_shape'), race_pressure_src.get('race_shape_label'), race_pressure_src.get('race_shape_narrative'), joined['race_shape_fit_v4'].get('race_tempo'), joined['pace_pressure_engine_v2_runners'].get('pressure_shape_v2')))
    race_shape_status, race_shape_reason = ('OK','Race shape field is populated.') if race_shape_ok else ('SOURCE_MISSING','No race-shape source found for this race.')

    rail_ok = populated(joined['map_enrichment'].get('rail')) or populated(g.get('rail_position'))
    rail_status, rail_reason = ('OK','Rail position is populated.') if rail_ok else ('SOURCE_MISSING','Rail position missing from governed board/source feeds.')
    condition_ok = populated(joined['map_enrichment'].get('track_condition')) or populated(g.get('track_condition'))
    condition_status, condition_reason = ('OK','Track condition is populated.') if condition_ok else ('SOURCE_MISSING','Track condition missing from governed board.')

    direction_known_tracks = {'CAULFIELD','CAULFIELDHEATH','BENDIGO','SALE','GEELONG','CRANBOURNE','BALLARAT','SANDOWN','SANDOWNLAKESIDE','SANDOWNHILLSIDE','FLEMINGTON','MORNINGTON','PAKENHAM','WERRIBEE','WARRNAMBOOL'}
    track_direction_ok = populated(joined['map_enrichment'].get('track_direction')) or clean_track(g.get('track')) in direction_known_tracks
    track_direction_status = 'OK' if track_direction_ok else 'SOURCE_MISSING'
    track_direction_reason = 'Track direction can be derived from Victorian track defaults.' if track_direction_ok else 'Track direction default missing for this venue.'
    barrier_orientation_status = 'OK' if track_direction_ok and barrier_ok else ('SOURCE_MISSING' if not track_direction_ok else 'TRUE_ZERO')
    barrier_orientation_reason = 'Barrier orientation can be derived from track direction and barrier.' if barrier_orientation_status == 'OK' else 'Barrier orientation unavailable because direction/barrier is missing.'
    lr_status = track_direction_status
    lr_reason = track_direction_reason

    selected_summary_ok = populated(joined['map_enrichment'].get('selected_runner_pace_summary')) or run_style_ok or projected_status == 'OK' or pace_fit_status == 'OK'
    selected_summary_alt = alt_projected_speed or alt_pace_fit or alt_run_style
    selected_summary_status, selected_summary_reason = classify(selected_summary_ok, selected_summary_alt, source_feed_hit, 'Selected runner pace summary has source values but current UI fallbacks can show blanks.')

    row = {
        'race_date': g.get('race_date',''), 'track': g.get('track',''), 'race_no': g.get('race_no',''), 'horse': g.get('horse',''),
        'speed_map_source_feed_classification': 'OK' if source_feed_hit else 'SOURCE_MISSING',
        'speed_map_source_feed_reason': 'At least one speed/pace source matched this runner.' if source_feed_hit else 'No speed/pace source matched this runner.',
        'projected_speed_classification': projected_status, 'projected_speed_reason': projected_reason,
        'pace_fit_classification': pace_fit_status, 'pace_fit_reason': pace_fit_reason,
        'runner_run_style_classification': run_style_status, 'runner_run_style_reason': run_style_reason,
        'early_speed_classification': early_status, 'early_speed_reason': early_reason,
        'late_speed_classification': late_status, 'late_speed_reason': late_reason,
        'settling_position_classification': settling_status, 'settling_position_reason': settling_reason,
        'barrier_classification': barrier_status, 'barrier_reason': barrier_reason,
        'lane_classification': lane_status, 'lane_reason': lane_reason,
        'leader_midfield_backmarker_groupings_classification': lane_status, 'leader_midfield_backmarker_groupings_reason': lane_reason,
        'race_pressure_classification': pressure_status, 'race_pressure_reason': pressure_reason,
        'race_shape_classification': race_shape_status, 'race_shape_reason': race_shape_reason,
        'rail_classification': rail_status, 'rail_reason': rail_reason,
        'track_condition_classification': condition_status, 'track_condition_reason': condition_reason,
        'track_direction_classification': track_direction_status, 'track_direction_reason': track_direction_reason,
        'barrier_orientation_classification': barrier_orientation_status, 'barrier_orientation_reason': barrier_orientation_reason,
        'left_right_handed_logic_classification': lr_status, 'left_right_handed_logic_reason': lr_reason,
        'selected_runner_pace_summary_classification': selected_summary_status, 'selected_runner_pace_summary_reason': selected_summary_reason,
        'UI_fallback_rendering_fields_classification': 'OK' if ui_ok else 'UI_FALLBACK_MISSING',
        'UI_fallback_rendering_fields_reason': 'MAP labels and render helpers are mounted.' if ui_ok else 'Missing MAP UI tokens: ' + ', '.join(k for k,v in ui_tokens.items() if not v),
        'matched_sources': '|'.join(name for name,val in joined.items() if val),
        'ui_projected_speed_current_value': joined['map_enrichment'].get('projected_speed') or joined['runner_intel'].get('projected_spd') or g.get('projected_spd') or g.get('early_speed_rating'),
        'ui_pace_fit_current_value': joined['map_enrichment'].get('pace_fit') or factor_pace.get('factor_score',''),
        'alt_projected_speed_candidate': first_pop(joined['tactical_dna_speed_map_v2'].get('avg_early_speed'), joined['runner_pace_pressure_v2'].get('avg_early_speed'), joined['real_speed_map_positions'].get('settling_score'), joined['runner_intel'].get('tactical_score')),
        'alt_pace_fit_candidate': first_pop(joined['race_shape_fit_v4'].get('race_shape_fit_score'), joined['race_shape_fit_v4'].get('tempo_fit_score'), joined['pace_advantage_ui'].get('pace_advantage_score'), joined['runner_intel'].get('tempo_fit')),
    }
    rows_out.append(row)

race_out = []
for rk, members in sorted(defaultdict(list, {rk:[r for r in rows_out if (clean(r['race_date']), clean_track(r['track']), race_no(r['race_no'])) == rk] for rk in race_members}).items()):
    if not members: continue
    rec = {'race_date': rk[0], 'track': rk[1], 'race_no': rk[2], 'field_size': len(members)}
    fix_required = 0; true_zero = 0; source_missing = 0
    for f in FIELDS:
        col = f'{f}_classification'
        counts = defaultdict(int)
        for m in members: counts[m.get(col,'')] += 1
        rec[f'{f}_ok_count'] = counts['OK']
        rec[f'{f}_fix_required_count'] = sum(counts[c] for c in FIX_CLASSES)
        rec[f'{f}_true_zero_count'] = counts['TRUE_ZERO']
        rec[f'{f}_source_missing_count'] = counts['SOURCE_MISSING']
        fix_required += rec[f'{f}_fix_required_count']; true_zero += counts['TRUE_ZERO']; source_missing += counts['SOURCE_MISSING']
    rec['fix_required_count'] = fix_required; rec['true_zero_count'] = true_zero; rec['source_missing_count'] = source_missing
    rec['status'] = 'FIX_REQUIRED' if fix_required else 'MAP_SOURCE_TRACE_PASS_WITH_PROVEN_GAPS'
    race_out.append(rec)

fields = ['race_date','track','race_no','horse']
for f in FIELDS: fields += [f'{f}_classification', f'{f}_reason']
fields += ['matched_sources','ui_projected_speed_current_value','ui_pace_fit_current_value','alt_projected_speed_candidate','alt_pace_fit_candidate']
write_csv(OUT, rows_out, fields)
write_csv(RACE, race_out, list(race_out[0].keys()) if race_out else [])

fix_total = sum(1 for r in rows_out for f in FIELDS if r.get(f'{f}_classification') in FIX_CLASSES)
status = 'MAP_SOURCE_TRACE_FIX_REQUIRED' if fix_total else 'MAP_SOURCE_TRACE_PASS'
summary = []
for f in FIELDS:
    counts = defaultdict(int)
    for r in rows_out: counts[r.get(f'{f}_classification')] += 1
    summary.append(f'{f}: ' + ', '.join(f'{k}={v}' for k,v in sorted(counts.items())))
REPORT.write_text('\n'.join([
    'EDGEiQ MAP Tab Source Trace V1', '='*38,
    f'Generated: {datetime.now().isoformat(timespec="seconds")}',
    f'Status: {status}',
    f'Governed rows/races: {len(gov)}/{len(race_members)}',
    f'Fix-required classifications: {fix_total}',
    f'UI token presence: {ui_tokens}', '',
    'Classification counts:', *summary, '',
    'Race statuses:', *[f'{r["track"]} R{r["race_no"]}: {r["status"]}, fix_required={r["fix_required_count"]}, source_missing={r["source_missing_count"]}, true_zero={r["true_zero_count"]}' for r in race_out]
])+'\n', encoding='utf-8')
print(status)
print(f'governed_rows={len(gov)}')
print(f'governed_races={len(race_members)}')
print(f'fix_required={fix_total}')

