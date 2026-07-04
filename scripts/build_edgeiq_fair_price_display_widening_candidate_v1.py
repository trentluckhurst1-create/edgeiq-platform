import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
SRC = DATA / 'edgeiq_probability_engine_v7.csv'
OUT = DATA / 'edgeiq_fair_price_display_widening_candidate_v1.csv'
OUT_SUMMARY = DATA / 'edgeiq_fair_price_display_widening_candidate_v1_summary.csv'
OUT_AUDIT = DATA / 'edgeiq_fair_price_display_widening_candidate_v1_audit.csv'

def read_csv(path):
    with path.open('r', encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def write_csv(path, rows, fields):
    with path.open('w', encoding='utf-8', newline='') as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
def text(v): return str(v or '').strip()
def num(v,d=0.0):
    try:
        raw=text(v).replace('$','').replace(',','').replace('%','')
        return float(raw) if raw else d
    except ValueError: return d
def race_key(r): return (text(r.get('race_date')), text(r.get('track')).upper(), text(r.get('race_no')))
def field_bucket(n):
    if n <= 7: return '6-7'
    if n <= 9: return '8-9'
    if n <= 11: return '10-11'
    if n <= 13: return '12-13'
    return '14+'
def rank_multiplier(rank):
    if rank <= 1: return 1.00
    if rank == 2: return 1.15
    if rank == 3: return 1.55
    return 2.35
def field_multiplier(bucket):
    return {'6-7':1.00,'8-9':1.06,'10-11':1.12,'12-13':1.22,'14+':1.35}.get(bucket,1.0)
def avg(vals): return sum(vals)/len(vals) if vals else 0.0

def main():
    rows=read_csv(SRC)
    by_race=defaultdict(list)
    for r in rows: by_race[race_key(r)].append(r)
    out=[]; audit=[]
    for key, race_rows in by_race.items():
        ranked=sorted(race_rows, key=lambda r: num(r.get('_rank'), 9999))
        last_price=1.01
        display_prices=[]
        for r in ranked:
            rank=int(num(r.get('_rank'), 0) or 0)
            field_size=int(num(r.get('field_size'), len(race_rows)) or len(race_rows))
            bucket=field_bucket(field_size)
            original=max(1.01, num(r.get('edgeiq_fair_price_v7'), 1.01))
            widened=original * rank_multiplier(rank) * field_multiplier(bucket)
            if rank <= 1:
                widened=original
            widened=max(1.01, widened)
            if widened <= last_price and rank > 1:
                widened=last_price + 0.05
            widened=min(widened, 40.0)
            last_price=widened
            display_prices.append(widened)
            rr=dict(r)
            rr['edgeiq_display_probability_v7']=r.get('edgeiq_probability_v7','')
            rr['edgeiq_display_fair_price_v7_x']=f'{widened:.6f}'
            rr['original_edgeiq_fair_price_v7']=r.get('edgeiq_fair_price_v7','')
            rr['display_price_delta']=f'{widened-original:.6f}'
            rr['display_price_multiplier']=f'{(widened/original) if original else 0:.6f}'
            rr['display_rank_source']='V7_ARCHIVED_RANK'
            rr['probability_source']='V7_TEMPERATURE6_TAB_QUALITY'
            rr['display_price_engine']='V7_DISPLAY_WIDENING_RESEARCH'
            rr['production_changed']='NO'
            out.append(rr)
        audit.append({'race_date':key[0],'track':key[1],'race_no':key[2],'rows':len(ranked),'min_display_fair':f'{min(display_prices):.6f}','max_display_fair':f'{max(display_prices):.6f}','display_rank_order_ok':'YES' if all(display_prices[i] <= display_prices[i+1] for i in range(len(display_prices)-1)) else 'NO'})
    original=[num(r.get('edgeiq_fair_price_v7')) for r in out]
    display=[num(r.get('edgeiq_display_fair_price_v7_x')) for r in out]
    summary=[
        {'metric':'rows','value':len(out)}, {'metric':'races','value':len(by_race)},
        {'metric':'original_min_fair','value':f'{min(original):.6f}'}, {'metric':'original_max_fair','value':f'{max(original):.6f}'}, {'metric':'original_avg_fair','value':f'{avg(original):.6f}'},
        {'metric':'display_min_fair','value':f'{min(display):.6f}'}, {'metric':'display_max_fair','value':f'{max(display):.6f}'}, {'metric':'display_avg_fair','value':f'{avg(display):.6f}'},
        {'metric':'display_rows_above_10','value':sum(1 for x in display if x > 10)}, {'metric':'display_rows_above_20','value':sum(1 for x in display if x > 20)},
        {'metric':'probability_changed','value':'NO'}, {'metric':'rank_order_bad_races','value':sum(1 for a in audit if a['display_rank_order_ok']!='YES')}, {'metric':'production_changed','value':'NO'}]
    fields=list(out[0].keys()) if out else []
    write_csv(OUT,out,fields); write_csv(OUT_AUDIT,audit,list(audit[0].keys()) if audit else []); write_csv(OUT_SUMMARY,summary,['metric','value'])
    print(f'Wrote {OUT} ({len(out)} rows)')
if __name__=='__main__': main()
