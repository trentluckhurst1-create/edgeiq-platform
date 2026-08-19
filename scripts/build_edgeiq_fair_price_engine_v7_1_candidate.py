import csv
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
SRC=DATA/'edgeiq_fair_price_display_widening_candidate_v1.csv'
OUT=DATA/'edgeiq_fair_price_engine_v7_1_candidate.csv'
OUT_SUMMARY=DATA/'edgeiq_fair_price_engine_v7_1_candidate_summary.csv'
OUT_REPORT=DATA/'edgeiq_fair_price_engine_v7_1_candidate_report.txt'

def read_csv(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def write_csv(p,rows,fields):
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def num(v,d=0.0):
    try: return float(str(v or '').replace('$','').replace(',',''))
    except ValueError: return d

def main():
    rows=read_csv(SRC)
    out=[]
    for r in rows:
        out.append({
            'race_date':r.get('race_date',''), 'track':r.get('track',''), 'race_no':r.get('race_no',''), 'horse':r.get('horse',''),
            'edgeiq_probability_v7':r.get('edgeiq_probability_v7',''), 'edgeiq_fair_price_v7':r.get('edgeiq_fair_price_v7',''),
            'edgeiq_display_probability_v7_1':r.get('edgeiq_display_probability_v7',''), 'edgeiq_display_fair_price_v7_1':r.get('edgeiq_display_fair_price_v7_x',''),
            'display_price_delta':r.get('display_price_delta',''), 'display_price_multiplier':r.get('display_price_multiplier',''),
            'probability_source':'V7_TEMPERATURE6_TAB_QUALITY', 'display_price_engine':'V7_1_DISPLAY_WIDENING_CANDIDATE',
            'artifact_status':'CANDIDATE_NOT_LIVE_WIRED', 'production_changed':'NO'
        })
    display=[num(r['edgeiq_display_fair_price_v7_1']) for r in out]
    orig=[num(r['edgeiq_fair_price_v7']) for r in out]
    races={(r['race_date'],r['track'],r['race_no']) for r in out}
    summary=[{'metric':'rows','value':len(out)},{'metric':'races','value':len(races)},{'metric':'original_max_fair','value':f'{max(orig):.6f}'},{'metric':'display_max_fair','value':f'{max(display):.6f}'},{'metric':'display_rows_above_10','value':sum(1 for p in display if p>10)},{'metric':'live_wired','value':'NO'},{'metric':'production_changed','value':'NO'},{'metric':'status','value':'V7_1_DISPLAY_CANDIDATE_CREATED_RESEARCH_ONLY'}]
    write_csv(OUT,out,list(out[0].keys()) if out else [])
    write_csv(OUT_SUMMARY,summary,['metric','value'])
    OUT_REPORT.write_text('\n'.join(['EDGEiQ Fair Price Engine V7.1 Candidate','',f'Rows: {len(out)}',f'Races: {len(races)}',f'Original max fair: {max(orig):.6f}',f'Display max fair: {max(display):.6f}',f'Display rows above $10: {sum(1 for p in display if p>10)}','Live wired: NO','Production changed: NO','Status: V7_1_DISPLAY_CANDIDATE_CREATED_RESEARCH_ONLY']),encoding='utf-8')
    print(f'Wrote {OUT} ({len(out)} rows)')
if __name__=='__main__': main()
