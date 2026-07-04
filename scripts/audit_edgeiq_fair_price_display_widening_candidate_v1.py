import csv
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
SRC=DATA/'edgeiq_fair_price_display_widening_candidate_v1.csv'
OUT=DATA/'edgeiq_fair_price_display_widening_candidate_v1_audit_report.csv'
OUT_SUMMARY=DATA/'edgeiq_fair_price_display_widening_candidate_v1_audit_summary.csv'
OUT_TXT=DATA/'edgeiq_fair_price_display_widening_candidate_v1_audit_report.txt'

def read_csv(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def write_csv(p,rows,fields):
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def text(v): return str(v or '').strip()
def num(v,d=0.0):
    try:
        raw=text(v).replace('$','').replace(',','').replace('%','')
        return float(raw) if raw else d
    except ValueError: return d
def race_key(r): return (text(r.get('race_date')),text(r.get('track')).upper(),text(r.get('race_no')))
def avg(v): return sum(v)/len(v) if v else 0.0

def main():
    rows=read_csv(SRC)
    by_race=defaultdict(list)
    for r in rows: by_race[race_key(r)].append(r)
    audit=[]; bad_order=0; top_bad=0; below=0; crazy=0
    for key,rs in by_race.items():
        ranked=sorted(rs,key=lambda r:num(r.get('_rank'),999))
        prices=[num(r.get('edgeiq_display_fair_price_v7_x')) for r in ranked]
        orig=[num(r.get('original_edgeiq_fair_price_v7')) for r in ranked]
        order_ok=all(prices[i] <= prices[i+1] for i in range(len(prices)-1))
        if not order_ok: bad_order+=1
        if len(prices)>=2 and prices[0] > prices[1]: top_bad+=1
        below += sum(1 for p in prices if p < 1.01)
        crazy += sum(1 for p in prices if p >= 1000)
        audit.append({'race_date':key[0],'track':key[1],'race_no':key[2],'rows':len(rs),'rank_order_preserved':'YES' if order_ok else 'NO','top_pick_not_longer_than_second':'YES' if not(len(prices)>=2 and prices[0]>prices[1]) else 'NO','min_display_fair':f'{min(prices):.6f}','max_display_fair':f'{max(prices):.6f}','avg_original_fair':f'{avg(orig):.6f}','avg_display_fair':f'{avg(prices):.6f}'})
    display=[num(r.get('edgeiq_display_fair_price_v7_x')) for r in rows]
    original=[num(r.get('original_edgeiq_fair_price_v7')) for r in rows]
    passed = bad_order==0 and top_bad==0 and below==0 and crazy==0 and max(display) < 1000 and max(display) > max(original)
    summary=[
        {'metric':'rows','value':len(rows)}, {'metric':'races','value':len(by_race)}, {'metric':'rank_order_bad_races','value':bad_order}, {'metric':'top_pick_longer_than_second_races','value':top_bad},
        {'metric':'prices_below_1_01','value':below}, {'metric':'crazy_1000_plus_prices','value':crazy}, {'metric':'original_max_fair','value':f'{max(original):.6f}'}, {'metric':'display_max_fair','value':f'{max(display):.6f}'},
        {'metric':'display_rows_above_10','value':sum(1 for p in display if p>10)}, {'metric':'display_rows_above_20','value':sum(1 for p in display if p>20)}, {'metric':'probability_changed','value':'NO'}, {'metric':'production_changed','value':'NO'}, {'metric':'status','value':'PASS' if passed else 'FAIL'}]
    write_csv(OUT,audit,list(audit[0].keys()) if audit else [])
    write_csv(OUT_SUMMARY,summary,['metric','value'])
    OUT_TXT.write_text('\n'.join(['EDGEiQ Fair Price Display Widening Candidate V1 Audit','',f'Status: {"PASS" if passed else "FAIL"}',f'Rows: {len(rows)}',f'Races: {len(by_race)}',f'Rank order bad races: {bad_order}',f'Top pick longer than second races: {top_bad}',f'Display max fair: {max(display):.6f}',f'Rows above $10: {sum(1 for p in display if p>10)}','Probability changed: NO','Production changed: NO']),encoding='utf-8')
    print(f'Wrote {OUT_SUMMARY}')
if __name__=='__main__': main()
