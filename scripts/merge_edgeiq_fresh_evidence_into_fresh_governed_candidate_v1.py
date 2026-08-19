import csv
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
IN_GOV = DATA / 'edgeiq_live_runner_board_governed_v7_2g2_FRESH_CURRENT_CANDIDATE.csv'
IN_EVID = DATA / 'edgeiq_current_intelligence_evidence_fix_candidate_FRESH_v1.csv'
OUT = DATA / 'edgeiq_live_runner_board_governed_v7_2g2_FRESH_CURRENT_EVIDENCE_MERGED.csv'
AUDIT = DATA / 'edgeiq_fresh_governed_evidence_merge_v1.csv'
SUMMARY = DATA / 'edgeiq_fresh_governed_evidence_merge_v1_summary.csv'
REPORT = DATA / 'edgeiq_fresh_governed_evidence_merge_v1_report.txt'

EXPECTED_ROWS = 383
EXPECTED_RACES = 25

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
        writer.writeheader()
        writer.writerows(rows)

def clean_text(v):
    return ' '.join(str(v or '').strip().upper().replace('\u00a0', ' ').split())

def race_no(v):
    s = clean_text(v).replace('RACE ', '').replace('R', '')
    return s.lstrip('0') or s

def clean_horse(v):
    return ''.join(ch for ch in clean_text(v) if ch.isalnum())

def key(row):
    return (clean_text(row.get('race_date') or row.get('current_race_date')), clean_text(row.get('track')), race_no(row.get('race_no')), clean_horse(row.get('horse') or row.get('horse_key')))

def race_key(row):
    return (clean_text(row.get('race_date') or row.get('current_race_date')), clean_text(row.get('track')), race_no(row.get('race_no')))

def runner_key_text(k):
    return '|'.join(k)

status = 'FRESH_GOVERNED_EVIDENCE_MERGE_READY'
error = ''
try:
    gov_rows, gov_fields = read_csv(IN_GOV)
    evid_rows, evid_fields = read_csv(IN_EVID)
    evid_by_key = {key(r): r for r in evid_rows}
    evidence_fields = [f for f in evid_fields if f.startswith('edgeiq_')]
    required_evidence_fields = [
        'edgeiq_connection_evidence_available', 'edgeiq_connection_angle_summary',
        'edgeiq_market_evidence_available', 'edgeiq_market_signal_summary',
        'edgeiq_hidden_gem_evidence_available', 'edgeiq_hidden_gem_summary',
        'edgeiq_evidence_fix_source', 'edgeiq_evidence_fix_status'
    ]
    for f in required_evidence_fields:
        if f not in evidence_fields:
            evidence_fields.append(f)
    out_fields = list(gov_fields)
    for f in evidence_fields:
        if f not in out_fields:
            out_fields.append(f)
    out_rows = []
    audit_rows = []
    matched = 0
    for r in gov_rows:
        nr = dict(r)
        k = key(r)
        er = evid_by_key.get(k)
        if er:
            matched += 1
            for f in evidence_fields:
                nr[f] = er.get(f, nr.get(f, ''))
            evidence_status = er.get('edgeiq_evidence_fix_status', 'EVIDENCE_AVAILABLE')
        else:
            for f in required_evidence_fields:
                nr.setdefault(f, '')
            nr['edgeiq_connection_evidence_available'] = nr.get('edgeiq_connection_evidence_available') or 'NO'
            nr['edgeiq_market_evidence_available'] = nr.get('edgeiq_market_evidence_available') or 'NO'
            nr['edgeiq_hidden_gem_evidence_available'] = nr.get('edgeiq_hidden_gem_evidence_available') or 'NO'
            nr['edgeiq_evidence_fix_status'] = nr.get('edgeiq_evidence_fix_status') or 'NO_MATCHED_EVIDENCE_ROW'
            evidence_status = 'NO_MATCHED_EVIDENCE_ROW'
        out_rows.append(nr)
        audit_rows.append({
            'race_date': r.get('race_date', ''),
            'track': r.get('track', ''),
            'race_no': r.get('race_no', ''),
            'horse': r.get('horse', ''),
            'merge_key': runner_key_text(k),
            'evidence_matched': 'YES' if er else 'NO',
            'market_available': nr.get('edgeiq_market_evidence_available', ''),
            'connection_available': nr.get('edgeiq_connection_evidence_available', ''),
            'hidden_gem_available': nr.get('edgeiq_hidden_gem_evidence_available', ''),
            'evidence_status': evidence_status,
        })
    runner_keys = [key(r) for r in out_rows]
    duplicate_count = len(runner_keys) - len(set(runner_keys))
    races = set(race_key(r) for r in out_rows)
    caulfield_r7_rows = sum(1 for r in out_rows if clean_text(r.get('race_date')) == '2026-06-27' and clean_text(r.get('track')) == 'CAULFIELD' and race_no(r.get('race_no')) == '7')
    v7_fields_present = any(f.startswith('edgeiq_v7_2g2_') for f in out_fields)
    evidence_fields_present = all(f in out_fields for f in required_evidence_fields)
    market_count = sum(1 for r in out_rows if clean_text(r.get('edgeiq_market_evidence_available')) == 'YES')
    connection_count = sum(1 for r in out_rows if clean_text(r.get('edgeiq_connection_evidence_available')) == 'YES')
    hidden_count = sum(1 for r in out_rows if clean_text(r.get('edgeiq_hidden_gem_evidence_available')) == 'YES')
    if len(out_rows) != EXPECTED_ROWS or len(races) != EXPECTED_RACES or caulfield_r7_rows != 19 or duplicate_count or not v7_fields_present or not evidence_fields_present:
        status = 'BLOCKED'
    summary_row = {
        'status': status,
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'input_governed_rows': len(gov_rows),
        'input_evidence_rows': len(evid_rows),
        'output_rows': len(out_rows),
        'output_races': len(races),
        'evidence_matched_rows': matched,
        'duplicate_runner_keys': duplicate_count,
        'caulfield_r7_rows': caulfield_r7_rows,
        'v7_2g2_fields_present': 'YES' if v7_fields_present else 'NO',
        'evidence_fields_present': 'YES' if evidence_fields_present else 'NO',
        'market_available_rows': market_count,
        'connection_available_rows': connection_count,
        'hidden_gem_available_rows': hidden_count,
        'production_changed': 'NO',
        'error': error,
    }
    write_csv(OUT, out_rows, out_fields)
    write_csv(AUDIT, audit_rows, list(audit_rows[0].keys()) if audit_rows else ['status'])
    write_csv(SUMMARY, [summary_row], list(summary_row.keys()))
    REPORT.write_text('\n'.join([
        'EDGEiQ Fresh Governed Evidence Merge V1',
        '=' * 44,
        f'Status: {status}',
        f'Generated: {summary_row["generated_at"]}',
        f'Rows: {len(out_rows)} / Races: {len(races)}',
        f'CAULFIELD R7 rows: {caulfield_r7_rows}',
        f'Evidence matched rows: {matched}',
        f'Market evidence rows: {market_count}',
        f'Connection evidence rows: {connection_count}',
        f'Hidden gem evidence rows: {hidden_count}',
        f'Duplicate runner keys: {duplicate_count}',
        f'V7.2G2 fields present: {summary_row["v7_2g2_fields_present"]}',
        f'Evidence fields present: {summary_row["evidence_fields_present"]}',
        'Production changed: NO',
    ]) + '\n', encoding='utf-8')
except Exception as exc:
    status = 'BLOCKED'
    error = str(exc)
    row = {'status': status, 'generated_at': datetime.now().isoformat(timespec='seconds'), 'error': error}
    write_csv(SUMMARY, [row], list(row.keys()))
    REPORT.write_text(f'EDGEiQ Fresh Governed Evidence Merge V1\nStatus: {status}\nError: {error}\n', encoding='utf-8')
    raise
print(status)

