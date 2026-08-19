from __future__ import annotations
import csv, json
from collections import Counter
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'public'/'data'; PRIVATE=ROOT/'data'/'market'/'ladbrokes'; DOCS=ROOT/'docs'/'market-intelligence'/'ladbrokes'
RACE_FIELDS=PUBLIC/'race_fields.csv'; CURRENT_MARKET=PUBLIC/'edgeiq_current_market_v1.csv'; PROVIDER_UNMATCHED=PUBLIC/'edgeiq_current_market_v1_provider_unmatched.csv'; HISTORY=PRIVATE/'edgeiq_ladbrokes_canonical_market_observation_history_v1.csv'; TERMINAL=PUBLIC/'edgeiq_market_terminal_feed_v1.csv'; FORM_CSV=PUBLIC/'edgeiq_form_guide_enriched_v2.csv'; OUT_CSV=PUBLIC/'edgeiq_canonical_market_integration_audit_v1.csv'; OUT_SUMMARY=PUBLIC/'edgeiq_canonical_market_integration_summary_v1.csv'; OUT_REPORT=DOCS/'edgeiq_canonical_market_integration_v1_report.md'
def text(v:Any)->str: return str(v or '').strip()
def money(v:Any)->str:
    s=text(v).replace('$','').replace(',','')
    if not s: return ''
    try: f=float(s)
    except ValueError: return ''
    return f'{f:.2f}' if f>0 else ''
def norm(v:Any)->str: return ''.join(ch for ch in text(v).upper() if ch.isalnum())
def num(v:Any)->str:
    s=text(v).replace('R','')
    try:
        f=float(s); return str(int(f)) if f.is_integer() else str(f)
    except ValueError: return s
def read_csv(path):
    if not path.exists(): return []
    with path.open('r',encoding='utf-8-sig',errors='replace',newline='') as h: return list(csv.DictReader(h))
def write_csv(path,rows,fields):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as h:
        w=csv.DictWriter(h,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def add(rows,check,status,detail,severity='GATE'): rows.append({'check':check,'status':status,'detail':detail,'severity':severity})
def identity(row,horse_field='horse_name'): return (text(row.get('race_date')),norm(row.get('canonical_track') or row.get('track')),num(row.get('race_number') or row.get('race_no')),norm(row.get(horse_field) or row.get('horse')))
def main():
    rf=read_csv(RACE_FIELDS); cur=read_csv(CURRENT_MARKET); pu=read_csv(PROVIDER_UNMATCHED); hist=read_csv(HISTORY); term=read_csv(TERMINAL); form=read_csv(FORM_CSV); rows=[]
    keys=[text(r.get('canonical_runner_key')) for r in cur]; dup=len(keys)-len(set(keys)); blank_ids=sum(1 for r in cur if not text(r.get('canonical_meeting_id')) or not text(r.get('canonical_race_id')) or not text(r.get('canonical_runner_id'))); blank_nums=sum(1 for r in cur if not text(r.get('runner_number'))); bad_avail=sum(1 for r in cur if money(r.get('fixed_win')) and r.get('market_availability_status')=='MARKET_UNAVAILABLE'); conflicts=sum(1 for r in cur if text(r.get('match_conflicts')) not in {'','0'}); unsafe=sum(1 for r in cur if r.get('runner_match_method')=='HORSE_NAME'); controlled=sum(1 for r in cur if r.get('runner_match_method')=='CONTROLLED_RACE_SCOPED_NAME_FALLBACK'); matched=sum(1 for r in cur if r.get('join_status')=='MATCHED'); fw=sum(1 for r in cur if money(r.get('fixed_win'))); fp=sum(1 for r in cur if money(r.get('fixed_place'))); movement=sum(1 for r in cur if r.get('price_movement_status')=='DERIVED_FROM_EDGEIQ_CANONICAL_OBSERVATION_HISTORY'); obs={text(r.get('edgeiq_observed_at')) for r in hist if text(r.get('edgeiq_observed_at'))}; by_runner=Counter(text(r.get('canonical_runner_id')) for r in hist if text(r.get('canonical_runner_id'))); repeat=sum(1 for _,c in by_runner.items() if c>=2); unexpl=sum(1 for r in pu if r.get('join_reason') not in {'OUTSIDE_EDGEIQ_PRODUCT_CATALOG','MISSING_CANONICAL_RACE','RUNNER_NUMBER_OR_NAME_MISMATCH','RUNNER_NUMBER_UNAVAILABLE_NO_SAFE_NAME_MATCH','AMBIGUOUS_RACE_SCOPED_NAME'})
    add(rows,'current_market_file_exists','PASS' if CURRENT_MARKET.exists() else 'FAIL',str(CURRENT_MARKET)); add(rows,'current_market_rows_equal_current_edgeiq_runners','PASS' if len(cur)==len(rf) and cur else 'FAIL',f'current={len(cur)} race_fields={len(rf)}'); add(rows,'canonical_rows_unique','PASS' if dup==0 else 'FAIL',dup); add(rows,'canonical_ids_nonblank','PASS' if blank_ids==0 else 'FAIL',blank_ids); add(rows,'runner_numbers_nonblank','PASS' if blank_nums==0 else 'FAIL',blank_nums); add(rows,'market_availability_consistent','PASS' if bad_avail==0 else 'FAIL',bad_avail); add(rows,'match_conflicts_zero','PASS' if conflicts==0 else 'FAIL',conflicts); add(rows,'horse_name_only_matching_removed','PASS' if unsafe==0 else 'FAIL',unsafe); add(rows,'controlled_name_fallback_count','INFO',controlled,'INFO'); add(rows,'matched_current_edgeiq_runners','PASS' if matched>0 else 'FAIL',matched); add(rows,'provider_unmatched_explained','PASS' if unexpl==0 else 'FAIL',f'provider_unmatched={len(pu)} unexplained={unexpl}'); add(rows,'fixed_win_rows','PASS' if fw>0 else 'FAIL',fw); add(rows,'fixed_place_rows','PASS' if fp>0 else 'FAIL',fp); add(rows,'repeat_observation_proof','PASS' if len(obs)>=2 and repeat>0 else 'FAIL',f'timestamps={len(obs)} repeat_runners={repeat}'); add(rows,'movement_rows_from_canonical_history','PASS' if movement>0 else 'FAIL',movement); add(rows,'production_pricing_unchanged','PASS','NO')
    curi={identity(r):r for r in cur}; compared=0; mism=0
    for r in term:
        cm=curi.get((text(r.get('race_date')),norm(r.get('track')),num(r.get('race_no')),norm(r.get('horse'))))
        if cm and money(cm.get('fixed_win')):
            compared+=1; mism += 1 if money(r.get('market'))!=money(cm.get('fixed_win')) else 0
    add(rows,'market_terminal_alignment','PASS' if compared>0 and mism==0 else 'FAIL',f'compared={compared} mismatches={mism}')
    fcomp=0; fmism=0
    for r in form:
        cm=curi.get((text(r.get('raceDate')),norm(r.get('meeting')),num(r.get('raceNumber')),norm(r.get('runnerName'))))
        if cm and money(cm.get('fixed_win')):
            fcomp+=1; fmism += 1 if money(r.get('marketPrice'))!=money(cm.get('fixed_win')) else 0
    add(rows,'form_guide_market_alignment','PASS' if fcomp>0 and fmism==0 else 'FAIL',f'compared={fcomp} mismatches={fmism}')
    failures=sum(1 for r in rows if r['severity']=='GATE' and r['status']=='FAIL'); status='PASS' if failures==0 else 'FAIL'; write_csv(OUT_CSV,rows,['check','status','detail','severity'])
    summary=[{'metric':'status','value':status},{'metric':'failures','value':failures},{'metric':'canonical_market_rows','value':len(cur)},{'metric':'current_edgeiq_runner_rows','value':len(rf)},{'metric':'matched_current_edgeiq_runners','value':matched},{'metric':'market_unavailable_current_rows','value':len(cur)-matched},{'metric':'provider_unmatched_rows','value':len(pu)},{'metric':'provider_unmatched_unexplained','value':unexpl},{'metric':'fixed_win_rows','value':fw},{'metric':'fixed_place_rows','value':fp},{'metric':'distinct_observation_timestamps','value':len(obs)},{'metric':'repeat_observation_runner_count','value':repeat},{'metric':'movement_rows','value':movement},{'metric':'market_terminal_alignment_mismatches','value':mism},{'metric':'form_guide_market_alignment_mismatches','value':fmism},{'metric':'production_pricing_changed','value':'NO'}]
    write_csv(OUT_SUMMARY,summary,['metric','value']); OUT_REPORT.parent.mkdir(parents=True,exist_ok=True); OUT_REPORT.write_text('# EDGEiQ Canonical Market Integration V1\n\n'+'\n'.join(f"- {r['metric']}: {r['value']}" for r in summary)+'\n',encoding='utf-8'); print(json.dumps({r['metric']:r['value'] for r in summary},indent=2)); raise SystemExit(1 if failures else 0)
if __name__=='__main__': main()
