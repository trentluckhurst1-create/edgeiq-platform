from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
MATCHES = DATA / 'edgeiq_sectional_crosswalk_raceid_v9_matches.csv'
REFERENCE = DATA / 'edgeiq_historical_results_warehouse_v2_graphql.csv'
OUT = DATA / 'edgeiq_sectional_raceid_to_raceno_v13.csv'
SUMMARY = DATA / 'edgeiq_sectional_raceid_to_raceno_v13_summary.csv'


def clean(v):
    return str(v or '').strip()


def norm_id(v):
    s = clean(v)
    if not s:
        return ''
    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
    except Exception:
        pass
    return s


def norm_race_no(v):
    s = clean(v)
    if not s:
        return ''
    try:
        return str(int(float(s)))
    except Exception:
        return ''


def main():
    if not MATCHES.exists():
        raise SystemExit(f'Missing required file: {MATCHES}')
    if not REFERENCE.exists():
        raise SystemExit(f'Missing required file: {REFERENCE}')

    race_map = defaultdict(set)
    ref_rows = 0
    with REFERENCE.open('r', newline='', encoding='utf-8-sig') as h:
        rd = csv.DictReader(h)
        fields = rd.fieldnames or []
        if 'race_id' not in fields or 'race_no' not in fields:
            raise SystemExit(f'Reference missing race_id/race_no columns: {fields}')
        for r in rd:
            ref_rows += 1
            rid = norm_id(r.get('race_id'))
            rn = norm_race_no(r.get('race_no'))
            if rid and rn:
                race_map[rid].add(rn)

    counts = Counter()
    rows = []
    with MATCHES.open('r', newline='', encoding='utf-8-sig') as h:
        rd = csv.DictReader(h)
        fields = rd.fieldnames or []
        print('MATCH_FIELDS', fields)
        for r in rd:
            counts['rows'] += 1
            rid = norm_id(r.get('recovered_race_id'))
            prior_rn = norm_race_no(r.get('recovered_race_no'))
            candidates = sorted(race_map.get(rid, set()), key=lambda x: int(x)) if rid else []

            if not rid:
                status = 'MISSING_RECOVERED_RACE_ID'
                counts[status.lower()] += 1
                resolved = ''
            elif len(candidates) == 1:
                resolved = candidates[0]
                if prior_rn:
                    if prior_rn == resolved:
                        status = 'CERTIFIED_RACE_ID_TO_RACE_NO_AGREES'
                        counts['certified_agrees'] += 1
                    else:
                        status = 'CONFLICT_PRIOR_RACE_NO'
                        counts['conflict_prior_race_no'] += 1
                else:
                    status = 'CERTIFIED_RACE_ID_TO_RACE_NO'
                    counts['certified_recovered'] += 1
            elif len(candidates) == 0:
                status = 'RACE_ID_NOT_FOUND_IN_REFERENCE'
                counts['race_id_not_found'] += 1
                resolved = ''
            else:
                status = 'AMBIGUOUS_RACE_ID_TO_RACE_NO'
                counts['ambiguous_race_id'] += 1
                resolved = ''

            rows.append({
                'source_file': r.get('source_file',''),
                'row_no': r.get('row_no',''),
                'race_date': r.get('race_date',''),
                'track': r.get('track',''),
                'horse_key': r.get('horse_key',''),
                'distance': r.get('distance',''),
                'recovered_race_id': rid,
                'prior_recovered_race_no': prior_rn,
                'resolved_race_no': resolved,
                'race_no_candidates': '|'.join(candidates),
                'identity_method': r.get('identity_method',''),
                'race_no_resolution_method': 'EXACT_RACE_ID_REFERENCE_LOOKUP' if resolved else '',
                'status': status,
            })

    fields = ['source_file','row_no','race_date','track','horse_key','distance','recovered_race_id',
              'prior_recovered_race_no','resolved_race_no','race_no_candidates','identity_method',
              'race_no_resolution_method','status']
    with OUT.open('w', newline='', encoding='utf-8') as h:
        w = csv.DictWriter(h, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

    unique_ref_ids = len(race_map)
    ambiguous_ref_ids = sum(1 for v in race_map.values() if len(v) > 1)
    with SUMMARY.open('w', newline='', encoding='utf-8') as h:
        w = csv.writer(h); w.writerow(['metric','value'])
        w.writerow(['reference_rows', ref_rows])
        w.writerow(['reference_unique_race_ids', unique_ref_ids])
        w.writerow(['reference_ambiguous_race_ids', ambiguous_ref_ids])
        for k,v in counts.items(): w.writerow([k,v])

    print('='*90)
    print('EDGEIQ SECTIONAL RACE-ID TO RACE-NUMBER REPAIR AUDIT V13')
    print('='*90)
    print('reference_rows:', ref_rows)
    print('reference_unique_race_ids:', unique_ref_ids)
    print('reference_ambiguous_race_ids:', ambiguous_ref_ids)
    for k,v in counts.items(): print(f'{k}: {v}')
    print('OUT:', OUT)
    print('SUMMARY:', SUMMARY)

if __name__ == '__main__':
    main()
