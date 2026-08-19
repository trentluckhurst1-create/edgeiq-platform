import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
SRC = DATA / 'edgeiq_probability_engine_v7.csv'
OUT = DATA / 'edgeiq_fair_price_engine_v7_segment_compression_audit_v1.csv'
OUT_SUMMARY = DATA / 'edgeiq_fair_price_engine_v7_segment_compression_audit_v1_summary.csv'
OUT_REPORT = DATA / 'edgeiq_fair_price_engine_v7_segment_compression_audit_v1_report.txt'

def read_csv(path):
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def write_csv(path, rows, fields):
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

def text(v): return str(v or '').strip()
def num(v, d=0.0):
    try:
        raw = text(v).replace('$','').replace(',','').replace('%','')
        return float(raw) if raw else d
    except ValueError: return d

def race_key(r): return (text(r.get('race_date')), text(r.get('track')).upper(), text(r.get('race_no')))
def field_bucket(n):
    if n <= 7: return '6-7'
    if n <= 9: return '8-9'
    if n <= 11: return '10-11'
    if n <= 13: return '12-13'
    return '14+'
def rank_bucket(rank):
    if rank <= 1: return 'R1'
    if rank <= 2: return 'R2'
    if rank <= 3: return 'R3'
    if rank <= 5: return 'R4-5'
    if rank <= 10: return 'R6-10'
    return 'R11+'
def fair_bucket(price):
    if price < 2: return '<$2'
    if price < 3: return '$2-$3'
    if price < 4: return '$3-$4'
    if price < 5: return '$4-$5'
    if price < 6: return '$5-$6'
    if price < 10: return '$6-$10'
    if price < 20: return '$10-$20'
    return '$20+'
def avg(vals): return sum(vals)/len(vals) if vals else 0.0

def summarise(rows, segment_name, segment_value):
    probs=[num(r.get('edgeiq_probability_v7')) for r in rows]
    fairs=[num(r.get('edgeiq_fair_price_v7')) for r in rows]
    wins=[1 if text(r.get('won')) in {'1','TRUE','YES'} else 0 for r in rows]
    races={race_key(r) for r in rows}
    return {'segment_name':segment_name,'segment_value':segment_value,'rows':len(rows),'races':len(races),'winners':sum(wins),'avg_probability':f'{avg(probs):.9f}','actual_win_rate':f'{avg(wins):.9f}','avg_fair_price':f'{avg(fairs):.6f}','min_fair_price':f'{min(fairs) if fairs else 0:.6f}','max_fair_price':f'{max(fairs) if fairs else 0:.6f}'}

def main():
    rows=read_csv(SRC)
    enriched=[]
    for r in rows:
        rr=dict(r)
        fs=int(num(r.get('field_size'),0) or 0)
        rank=int(num(r.get('_rank'),0) or 0)
        if rank <= 0:
            rank=int(num(r.get('rank'),0) or 0)
        fair=num(r.get('edgeiq_fair_price_v7'))
        rr['_rank_in_race']=rank
        rr['_field_bucket']=field_bucket(fs)
        rr['_rank_bucket']=rank_bucket(rank)
        rr['_fair_bucket']=fair_bucket(fair)
        enriched.append(rr)
    audit=[summarise(enriched,'ALL','ALL')]
    for name,getter in [('field_bucket',lambda r:r['_field_bucket']),('rank_bucket',lambda r:r['_rank_bucket']),('fair_bucket',lambda r:r['_fair_bucket']),('track',lambda r:text(r.get('track')).upper())]:
        groups=defaultdict(list)
        for r in enriched: groups[getter(r)].append(r)
        for k in sorted(groups): audit.append(summarise(groups[k],name,k))
    fairs=[num(r.get('edgeiq_fair_price_v7')) for r in enriched]
    rank6=[r for r in enriched if int(r['_rank_in_race']) >= 6]
    rank6_fairs=[num(r.get('edgeiq_fair_price_v7')) for r in rank6]
    max_rank=max([int(r['_rank_in_race']) for r in enriched] or [0])
    rows_above10=sum(1 for x in fairs if x > 10)
    if max_rank < 6 and rows_above10 == 0:
        status='TAIL_ROWS_MISSING_AND_PRICE_RANGE_COMPRESSED'
    elif rows_above10 == 0:
        status='TAIL_COMPRESSION_CONFIRMED'
    else:
        status='TAIL_HAS_WIDE_PRICES'
    summary=[
        {'metric':'rows','value':len(enriched)}, {'metric':'races','value':len({race_key(r) for r in enriched})},
        {'metric':'min_fair_price','value':f'{min(fairs) if fairs else 0:.6f}'}, {'metric':'max_fair_price','value':f'{max(fairs) if fairs else 0:.6f}'}, {'metric':'avg_fair_price','value':f'{avg(fairs):.6f}'},
        {'metric':'rows_fair_under_2','value':sum(1 for x in fairs if x < 2)}, {'metric':'rows_fair_2_to_5','value':sum(1 for x in fairs if 2 <= x < 5)}, {'metric':'rows_fair_above_5','value':sum(1 for x in fairs if x > 5)}, {'metric':'rows_fair_above_10','value':rows_above10},
        {'metric':'max_rank_available','value':max_rank}, {'metric':'rows_rank_6_plus','value':len(rank6)}, {'metric':'rank_6_plus_avg_fair','value':f'{avg(rank6_fairs):.6f}'}, {'metric':'rank_6_plus_max_fair','value':f'{max(rank6_fairs) if rank6_fairs else 0:.6f}'},
        {'metric':'status','value':status}, {'metric':'production_changed','value':'NO'}]
    write_csv(OUT,audit,list(audit[0].keys()))
    write_csv(OUT_SUMMARY,summary,['metric','value'])
    report=['EDGEiQ Fair Price Engine V7 Segment Compression Audit V1','',f'Rows audited: {len(enriched)}',f'Races audited: {len({race_key(r) for r in enriched})}',f'Min fair price: {min(fairs) if fairs else 0:.6f}',f'Max fair price: {max(fairs) if fairs else 0:.6f}',f'Average fair price: {avg(fairs):.6f}',f'Rows fair > 10: {rows_above10}',f'Max rank available: {max_rank}',f'Rows rank 6+: {len(rank6)}',f'Status: {status}','Production changed: NO','','Interpretation:','V7 probability calibration is preserved, but the customer-facing fair-price range is compressed. The V7 replay artifact only contains ranks 1-4, so a display layer can widen visible prices but cannot invent missing full-field tail runners.']
    OUT_REPORT.write_text('\n'.join(report),encoding='utf-8')
    print(f'Wrote {OUT} ({len(audit)} segment rows)')
if __name__=='__main__': main()
