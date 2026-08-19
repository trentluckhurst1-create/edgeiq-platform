from __future__ import annotations
import csv,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'; DOCS=ROOT/'docs'; PERF=DOCS/'performance-intelligence'
def rows(p):
    if not p.exists(): return []
    with p.open('r',encoding='utf-8-sig',errors='replace',newline='') as f: return list(csv.DictReader(f))
def clean(v):
    if v is None: return ''
    s=str(v).strip(); return '' if s.lower() in {'','none','null','nan','n/a','na','-','missing'} else s
def fnum(v):
    try: return float(str(v).replace('$','').replace(',',''))
    except Exception: return None
def assert_true(name, cond, detail=''):
    return {'test':name,'status':'PASS' if cond else 'FAIL','detail':detail}
def main():
    tests=[]
    std=rows(PERF/'standard-times'/'edgeiq_standard_time_fact_v1.csv')
    runner_lvs=rows(PERF/'lengths-v-standard'/'edgeiq_runner_lengths_v_standard_fact_v1.csv')
    race_lvs=rows(PERF/'lengths-v-standard'/'edgeiq_race_lengths_v_standard_fact_v1.csv')
    epi=rows(PERF/'epi'/'edgeiq_epi_performance_fact_v1.csv')
    eri=rows(PERF/'epi'/'edgeiq_epi_race_strength_fact_v1.csv')
    fair=rows(DATA/'edgeiq_fair_price_v7_2.csv')
    market=rows(DATA/'edgeiq_market_terminal_feed_v1.csv')
    current_epi=json.loads((DATA/'edgeiq_epi_current_rating_v1.json').read_text(encoding='utf-8')) if (DATA/'edgeiq_epi_current_rating_v1.json').exists() else {'runners':[]}
    tests.append(assert_true('standard_time_rows_gt_zero',len(std)>0,str(len(std))))
    tests.append(assert_true('standard_times_plausible',all((fnum(r.get('standard_time_seconds')) or 0)>35 for r in std), 'all standard times >35s'))
    tests.append(assert_true('standard_min_observation_enforced',all((fnum(r.get('observation_count')) or 0)>=20 for r in std),'min obs >=20'))
    tests.append(assert_true('lengths_v_standard_rows_gt_zero',len(runner_lvs)>0,str(len(runner_lvs))))
    tests.append(assert_true('race_lengths_rows_gt_zero',len(race_lvs)>0,str(len(race_lvs))))
    tests.append(assert_true('epi_rows_gt_zero',len(epi)>0,str(len(epi))))
    tests.append(assert_true('eri_rows_gt_zero',len(eri)>0,str(len(eri))))
    tests.append(assert_true('epi_range_valid',all((fnum(r.get('epi_value')) is None) or (0<=fnum(r.get('epi_value'))<=100) for r in epi[:50000]),'first 50k sampled'))
    tests.append(assert_true('current_epi_available_gt_zero',sum(1 for r in current_epi.get('runners',[]) if clean(r.get('value') or (r.get('epi') or {}).get('value')))>0,''))
    tests.append(assert_true('current_eri_available_gt_zero',sum(1 for r in current_epi.get('runners',[]) if clean(r.get('eriValue') or (r.get('eri') or {}).get('value')))>0,''))
    priced=[r for r in fair if clean(r.get('fair_price_v7_2'))]
    tests.append(assert_true('fair_price_rows_gt_zero',len(priced)>0,str(len(priced))))
    tests.append(assert_true('fair_prices_gt_one',all((fnum(r.get('fair_price_v7_2')) or 0)>1 for r in priced),'all priced >1'))
    by={}
    for r in priced:
        key=(r.get('race_date'),r.get('track'),r.get('race_no')); by.setdefault(key,0.0); by[key]+=fnum(r.get('edgeiq_probability_v7_2')) or 0
    tests.append(assert_true('race_probability_sums_ok',all(abs(v-1)<0.0015 for v in by.values()),str(len(by))+' races'))
    tests.append(assert_true('market_edge_rows_gt_zero',sum(1 for r in market if clean(r.get('edge')))>0,''))
    tests.append(assert_true('market_not_used_as_feature',all(r.get('model_score_source_v7_2')!='MARKET' for r in fair),'fair price source check'))
    fields=['test','status','detail']
    out=PERF/'recovery'/'edgeiq_performance_recovery_tests_v1.csv'; out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',encoding='utf-8',newline='') as h:
        w=csv.DictWriter(h,fieldnames=fields); w.writeheader(); w.writerows(tests)
    payload={'status':'PASS' if all(t['status']=='PASS' for t in tests) else 'FAIL','tests':tests}
    (PERF/'recovery'/'edgeiq_performance_recovery_tests_v1.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(payload,indent=2)); return 0 if payload['status']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
