import csv, shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
CHECKPOINT = DATA / 'checkpoints'
END_SUM = DATA / 'edgeiq_fresh_current_governed_end_to_end_v1_summary.csv'
SRC_GOV = DATA / 'edgeiq_live_runner_board_governed_v7_2g2_FRESH_CURRENT_EVIDENCE_MERGED.csv'
SRC_CMD = DATA / 'edgeiq_command_enrichment_feed_v2_FRESH_CURRENT.csv'
TGT_GOV = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
TGT_CMD = DATA / 'edgeiq_command_enrichment_feed_v2.csv'
OUT = DATA / 'edgeiq_fresh_current_apply_v1.csv'
SUMMARY = DATA / 'edgeiq_fresh_current_apply_v1_summary.csv'
REPORT = DATA / 'edgeiq_fresh_current_apply_v1_report.txt'
EXPECTED_ROWS = 383
EXPECTED_RACES = 25

def read_csv(path):
    if not path.exists(): return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        r = csv.DictReader(f); return list(r), list(r.fieldnames or [])

def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)

def clean(v): return ' '.join(str(v or '').strip().upper().replace('\u00a0',' ').split())
def clean_horse(v): return ''.join(ch for ch in clean(v) if ch.isalnum())
def race_no(v):
    s = clean(v).replace('RACE ', '').replace('R','')
    return s.lstrip('0') or s
def rkey(r): return (clean(r.get('race_date') or r.get('current_race_date')), clean(r.get('track')), race_no(r.get('race_no')))
def runner_key(r): return (clean(r.get('race_date') or r.get('current_race_date')), clean(r.get('track')), race_no(r.get('race_no')), clean_horse(r.get('horse') or r.get('horse_key')))
def yes(v): return clean(v) in {'YES','TRUE','1','Y','ON'}

def validate():
    gov, gov_fields = read_csv(TGT_GOV)
    cmd, cmd_fields = read_csv(TGT_CMD)
    caulfield = ('2026-06-27','CAULFIELD','7')
    checks = []
    checks.append(('governed_rows_383', len(gov) == EXPECTED_ROWS, len(gov)))
    checks.append(('command_rows_383', len(cmd) == EXPECTED_ROWS, len(cmd)))
    checks.append(('governed_races_25', len(set(rkey(r) for r in gov)) == EXPECTED_RACES, len(set(rkey(r) for r in gov))))
    checks.append(('command_races_25', len(set(rkey(r) for r in cmd)) == EXPECTED_RACES, len(set(rkey(r) for r in cmd))))
    checks.append(('caulfield_r7_governed_19', sum(1 for r in gov if rkey(r) == caulfield) == 19, sum(1 for r in gov if rkey(r) == caulfield)))
    checks.append(('caulfield_r7_command_19', sum(1 for r in cmd if rkey(r) == caulfield) == 19, sum(1 for r in cmd if rkey(r) == caulfield)))
    checks.append(('governed_no_duplicates', len(set(runner_key(r) for r in gov)) == len(gov), len(gov)-len(set(runner_key(r) for r in gov))))
    checks.append(('command_no_duplicates', len(set(runner_key(r) for r in cmd)) == len(cmd), len(cmd)-len(set(runner_key(r) for r in cmd))))
    checks.append(('v7_2g2_on', all(yes(r.get('edgeiq_v7_2g2_feature_flag')) for r in gov), sum(1 for r in gov if yes(r.get('edgeiq_v7_2g2_feature_flag')))))
    checks.append(('live_wired_yes_controlled_on', all(clean(r.get('edgeiq_v7_2g2_live_wired_flag')) == 'YES_CONTROLLED_ON' for r in gov), sum(1 for r in gov if clean(r.get('edgeiq_v7_2g2_live_wired_flag')) == 'YES_CONTROLLED_ON')))
    checks.append(('evidence_fields_present', all(f in gov_fields for f in ['edgeiq_market_evidence_available','edgeiq_connection_evidence_available','edgeiq_hidden_gem_evidence_available']), ','.join(f for f in ['edgeiq_market_evidence_available','edgeiq_connection_evidence_available','edgeiq_hidden_gem_evidence_available'] if f not in gov_fields)))
    checks.append(('command_count_fields_present', all(f in cmd_fields for f in ['race_market_count_v2','race_connection_count_v2','race_hidden_gem_count_v2','race_field_size_v2']), ','.join(f for f in ['race_market_count_v2','race_connection_count_v2','race_hidden_gem_count_v2','race_field_size_v2'] if f not in cmd_fields)))
    return gov, cmd, checks

status = 'BLOCKED_ROLLED_BACK'
error = ''
audit = []
backup_gov = ''
backup_cmd = ''
try:
    end_rows, _ = read_csv(END_SUM)
    if not end_rows or end_rows[0].get('status') != 'FRESH_CURRENT_END_TO_END_PASS':
        raise RuntimeError('End-to-end summary is not PASS; apply blocked.')
    if not SRC_GOV.exists() or not SRC_CMD.exists():
        raise RuntimeError('Fresh current source file missing.')
    CHECKPOINT.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_gov = str(CHECKPOINT / f'edgeiq_live_runner_board_governed_v1_BEFORE_FRESH_CURRENT_APPLY_{ts}.csv')
    backup_cmd = str(CHECKPOINT / f'edgeiq_command_enrichment_feed_v2_BEFORE_FRESH_CURRENT_APPLY_{ts}.csv')
    shutil.copy2(TGT_GOV, backup_gov)
    shutil.copy2(TGT_CMD, backup_cmd)
    shutil.copy2(SRC_GOV, TGT_GOV)
    shutil.copy2(SRC_CMD, TGT_CMD)
    gov, cmd, checks = validate()
    for name, ok, detail in checks:
        audit.append({'check': name, 'result': 'PASS' if ok else 'FAIL', 'detail': str(detail)})
    if all(ok for _, ok, _ in checks):
        status = 'FRESH_CURRENT_GOVERNED_APPLY_SUCCESS'
    else:
        shutil.copy2(backup_gov, TGT_GOV)
        shutil.copy2(backup_cmd, TGT_CMD)
        status = 'BLOCKED_ROLLED_BACK'
except Exception as exc:
    error = str(exc)
    try:
        if backup_gov and Path(backup_gov).exists(): shutil.copy2(backup_gov, TGT_GOV)
        if backup_cmd and Path(backup_cmd).exists(): shutil.copy2(backup_cmd, TGT_CMD)
    except Exception as rollback_exc:
        error += f' | rollback_error={rollback_exc}'
    audit.append({'check': 'apply_exception', 'result': 'FAIL', 'detail': error})

gov, _ = read_csv(TGT_GOV)
cmd, _ = read_csv(TGT_CMD)
caulfield = ('2026-06-27','CAULFIELD','7')
summary = {
    'status': status,
    'generated_at': datetime.now().isoformat(timespec='seconds'),
    'backup_governed': backup_gov,
    'backup_command_enrichment': backup_cmd,
    'governed_rows': len(gov),
    'command_rows': len(cmd),
    'governed_races': len(set(rkey(r) for r in gov)),
    'command_races': len(set(rkey(r) for r in cmd)),
    'caulfield_r7_governed_rows': sum(1 for r in gov if rkey(r) == caulfield),
    'caulfield_r7_command_rows': sum(1 for r in cmd if rkey(r) == caulfield),
    'production_changed': 'NO_PRICING_LOGIC_CHANGED__GOVERNED_FEED_REPLACED_WITH_FRESH_CURRENT_APPROVED_CANDIDATE',
    'error': error,
}
write_csv(OUT, audit, ['check','result','detail'])
write_csv(SUMMARY, [summary], list(summary.keys()))
REPORT.write_text('\n'.join(['EDGEiQ Fresh Current Apply V1','='*34,f'Status: {status}',f'Governed rows/races: {summary["governed_rows"]}/{summary["governed_races"]}',f'Command rows/races: {summary["command_rows"]}/{summary["command_races"]}',f'CAULFIELD R7 governed/command: {summary["caulfield_r7_governed_rows"]}/{summary["caulfield_r7_command_rows"]}',f'Backup governed: {backup_gov}',f'Backup command enrichment: {backup_cmd}',f'Error: {error or "None"}',''] + [f'{r["check"]}: {r["result"]} ({r["detail"]})' for r in audit]) + '\n', encoding='utf-8')
print(status)
