import csv
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
input_path = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
out_detail = DATA / 'edgeiq_v7_2g2_post_on_overwrite_v1.csv'
out_summary = DATA / 'edgeiq_v7_2g2_post_on_overwrite_v1_summary.csv'
out_report = DATA / 'edgeiq_v7_2g2_post_on_overwrite_v1_report.txt'
EXPECTED_ROWS = 378
EXPECTED_RACES = 27
PASS_STATUS = 'V7_2G2_POST_ON_AUDIT_PASS'
BLOCK_STATUS = 'V7_2G2_POST_ON_AUDIT_BLOCKED_REVIEW_REQUIRED'

def read_rows(path):
    if not path.exists(): return []
    with path.open('r', newline='', encoding='utf-8-sig') as f: return list(csv.DictReader(f))
def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def to_float(v):
    try:
        s=str(v).replace('$','').replace(',','').strip(); return float(s) if s else None
    except Exception: return None
def uniq(rows,col): return sorted({str(r.get(col,'')).strip() for r in rows if str(r.get(col,'')).strip()})
def race_key(r): return (r.get('race_date') or r.get('current_race_date') or '', r.get('track') or '', r.get('race_no') or '')
def rank_checks(rows, price_col):
    groups={}
    for r in rows: groups.setdefault(race_key(r), []).append(r)
    breaks=0; top_longer=0
    for group in groups.values():
        priced=[(to_float(r.get(price_col)),r) for r in group]
        priced=[x for x in priced if x[0] is not None]
        if len(priced)<2: continue
        ordered=sorted(priced,key=lambda x:x[0])
        if ordered[0][0] > ordered[1][0]: top_longer += 1
        last=None
        for p,_ in ordered:
            if last is not None and p < last - 1e-9: breaks += 1
            last=p
    return breaks, top_longer

rows=read_rows(input_path); fields=list(rows[0].keys()) if rows else []
active_col='edgeiq_v7_2g2_active_display_fair_price_shadow'; preview_col='edgeiq_v7_2g2_on_preview_display_fair_price'
prices=[to_float(r.get(active_col)) for r in rows]
valid=[p for p in prices if p is not None]
races=len({race_key(r) for r in rows})
fallback_fields=['fair_price','ui_fair_price','live_price','win_pct']
checks=[]; blockers=[]
def add(name, obs, exp, passed):
    checks.append({'check':name,'observed':obs,'expected':exp,'passed':'YES' if passed else 'NO','notes':'' if passed else f'Expected {exp}; observed {obs}'})
    if not passed: blockers.append(name)
add('rows', str(len(rows)), str(EXPECTED_ROWS), len(rows)==EXPECTED_ROWS)
add('races', str(races), str(EXPECTED_RACES), races==EXPECTED_RACES)
add('feature_flag_values_on', '|'.join(uniq(rows,'edgeiq_v7_2g2_feature_flag')), 'ON', uniq(rows,'edgeiq_v7_2g2_feature_flag')==['ON'])
add('live_wired_values_yes_controlled_on', '|'.join(uniq(rows,'edgeiq_v7_2g2_live_wired_flag')), 'YES_CONTROLLED_ON', uniq(rows,'edgeiq_v7_2g2_live_wired_flag')==['YES_CONTROLLED_ON'])
add('active_display_rows', str(len(valid)), str(EXPECTED_ROWS), len(valid)==EXPECTED_ROWS)
add('active_display_below_1_01_count', str(sum(1 for p in valid if p < 1.01)), '0', sum(1 for p in valid if p < 1.01)==0)
add('active_display_above_50_count', str(sum(1 for p in valid if p > 50)), '0', sum(1 for p in valid if p > 50)==0)
add('null_active_display_rows', str(len(rows)-len(valid)), '0', len(rows)==len(valid))
add('fallback_production_fields_present', '|'.join([c for c in fallback_fields if c in fields]), '|'.join(fallback_fields), set(fallback_fields).issubset(set(fields)))
add('on_preview_fields_present', str(preview_col in fields), 'True', preview_col in fields)
breaks,top_longer=rank_checks(rows, active_col)
add('rank_order_breaks', str(breaks), '0', breaks==0)
add('top_pick_longer_than_second', str(top_longer), '0', top_longer==0)
status=PASS_STATUS if not blockers else BLOCK_STATUS
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'rows':len(rows),'races':races,'feature_flag_values':'|'.join(uniq(rows,'edgeiq_v7_2g2_feature_flag')),'live_wired_values':'|'.join(uniq(rows,'edgeiq_v7_2g2_live_wired_flag')),'active_display_rows':len(valid),'active_display_min':min(valid) if valid else '','active_display_max':max(valid) if valid else '','active_display_below_1_01_count':sum(1 for p in valid if p < 1.01),'active_display_above_50_count':sum(1 for p in valid if p > 50),'null_active_display_rows':len(rows)-len(valid),'fallback_fields_present':'|'.join([c for c in fallback_fields if c in fields]),'on_preview_fields_present':'YES' if preview_col in fields else 'NO','rank_order_breaks':breaks,'top_pick_longer_than_second':top_longer,'blocked_reasons':'; '.join(blockers)}]
write_csv(out_detail, checks, ['check','observed','expected','passed','notes']); write_csv(out_summary, summary, list(summary[0].keys()))
report=['EDGEiQ V7.2G2 Post-ON Overwrite Audit V1','='*52,f'Status: {status}',f'Generated: {summary[0]["generated_at"]}',f'Rows/races: {len(rows)} / {races}',f'Feature flag values: {summary[0]["feature_flag_values"]}',f'Live wired values: {summary[0]["live_wired_values"]}',f'Active display rows: {len(valid)}',f'Active display min/max: {summary[0]["active_display_min"]} / {summary[0]["active_display_max"]}',f'Below 1.01 / above 50 / null: {summary[0]["active_display_below_1_01_count"]} / {summary[0]["active_display_above_50_count"]} / {summary[0]["null_active_display_rows"]}',f'Rank order breaks: {breaks}',f'Top pick longer than second: {top_longer}',f'Blocked reasons: {summary[0]["blocked_reasons"] or "None"}']
out_report.write_text('\n'.join(report)+'\n',encoding='utf-8')
print(status)
print('rows',len(rows),'races',races,'active_display_rows',len(valid),'min',summary[0]['active_display_min'],'max',summary[0]['active_display_max'])
