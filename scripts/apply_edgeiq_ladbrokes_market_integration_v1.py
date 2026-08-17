from __future__ import annotations
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'scripts'
STAMP='20260726_LADBROKES_MARKET_INTEGRATION_V1'

def checkpoint(path:Path):
    cp=path.with_name(path.stem+f'_CHECKPOINT_PRE_{STAMP}'+path.suffix)
    if path.exists() and not cp.exists(): cp.write_text(path.read_text(encoding='utf-8'),encoding='utf-8')

def replace_once(text:str, old:str, new:str, label:str)->str:
    if old not in text:
        if new in text: return text
        raise RuntimeError(f'missing patch target: {label}')
    return text.replace(old,new,1)

def patch_adapter():
    p=SCRIPTS/'build_edgeiq_ladbrokes_affiliate_market_adapter_v1.py'; checkpoint(p); s=p.read_text(encoding='utf-8')
    s=replace_once(s,'REQUIRED_ENV = ["EDGEIQ_LADBROKES_EMAIL", "EDGEIQ_LADBROKES_PARTNER_NAME"]','PREFERRED_ENV = ["EDGEIQ_LADBROKES_FROM", "EDGEIQ_LADBROKES_X_PARTNER"]\nLEGACY_ENV = ["EDGEIQ_LADBROKES_EMAIL", "EDGEIQ_LADBROKES_PARTNER_NAME"]\nREQUIRED_ENV = PREFERRED_ENV + LEGACY_ENV','env constants')
    s=replace_once(s,'email = os.environ.get("EDGEIQ_LADBROKES_EMAIL", "").strip()\n    partner = os.environ.get("EDGEIQ_LADBROKES_PARTNER_NAME", "").strip()','email = os.environ.get("EDGEIQ_LADBROKES_FROM", "").strip() or os.environ.get("EDGEIQ_LADBROKES_EMAIL", "").strip()\n    partner = os.environ.get("EDGEIQ_LADBROKES_X_PARTNER", "").strip() or os.environ.get("EDGEIQ_LADBROKES_PARTNER_NAME", "").strip()','env resolution')
    s=replace_once(s,'market_availability = "LIVE_MARKET" if text(record.get("fixed_win")) and text(record.get("race_status")).upper() in {"OPEN", "LIVE", ""} else ("SCRATCHED" if text(record.get("is_scratched")) == "true" else "MARKET_UNAVAILABLE")','market_availability = "SCRATCHED" if text(record.get("is_scratched")) == "true" else ("LIVE_MARKET" if text(record.get("fixed_win")) else "MARKET_UNAVAILABLE")','availability precedence')
    p.write_text(s,encoding='utf-8')

def write_market_terminal():
    p=SCRIPTS/'build_edgeiq_market_terminal_feed_v1.py'; checkpoint(p)
    p.write_text(r"""
from __future__ import annotations
import csv, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
CATALOG=DATA/'edgeiq_three_day_product_catalog_v1.json'
ENRICHED=DATA/'edgeiq_form_guide_enriched_v2.json'
CURRENT_MARKET=DATA/'edgeiq_current_market_v1.csv'
EPR_PRICE=DATA/'edgeiq_fair_price_epr_v1.csv'
OUT=DATA/'edgeiq_market_terminal_feed_v1.csv'
SUMMARY=DATA/'edgeiq_market_terminal_feed_summary_v1.csv'
TRACE=DATA/'edgeiq_market_engineering_build_v1_trace.txt'
FIELDNAMES='''workspace_id meeting_key race_key generated_at race_date track race_no no horse epi market open high low move edgeiq_price edge status source source_timestamp source_confidence row_status market_availability_status market_source_status market_observed_at market_generated_at market_age_minutes market_freshness_status market_is_live'''.split()
def clean(v:Any)->str:
    if v is None: return ''
    s=str(v).strip(); return '' if s.lower() in {'none','null','nan','n/a','na','-','missing'} else s
def normalise(v:Any)->str: return ''.join(ch for ch in clean(v).upper() if ch.isalnum())
def number_text(v:Any)->str:
    s=clean(v).replace('$','').replace(',','').replace('R','')
    if not s: return ''
    try:
        f=float(s); return str(int(f)) if f.is_integer() else str(f)
    except ValueError: return s
def decimal_text(v:Any,places:int=2)->str:
    s=clean(v).replace('$','').replace(',','')
    if not s: return ''
    try: f=float(s)
    except ValueError: return ''
    return f'{f:.{places}f}' if f>0 else ''
def value_from_source(v:Any)->str: return decimal_text(v.get('value')) if isinstance(v,dict) else decimal_text(v)
def source_name(v:Any,fallback='')->str: return clean(v.get('source')) if isinstance(v,dict) else fallback
def source_time(v:Any)->str: return clean(v.get('asAt')) if isinstance(v,dict) else ''
def runner_name(r):
    o=r.get('official') if isinstance(r.get('official'),dict) else {}; s=r.get('source') if isinstance(r.get('source'),dict) else {}
    return clean(o.get('runner')) or clean(s.get('horseName')) or clean(s.get('runnerName')) or clean(s.get('horse'))
def runner_no(r,i):
    o=r.get('official') if isinstance(r.get('official'),dict) else {}; s=r.get('source') if isinstance(r.get('source'),dict) else {}
    return number_text(o.get('no')) or number_text(o.get('number')) or number_text(s.get('runnerNumber')) or number_text(s.get('runner_no')) or number_text(s.get('saddlecloth')) or str(i+1)
def is_scratched(r,en=None):
    o=r.get('official') if isinstance(r.get('official'),dict) else {}; s=r.get('source') if isinstance(r.get('source'),dict) else {}; vals=[o.get('scratched'),s.get('scratched'),s.get('is_scratched'),en.get('scratched') if en else None]
    return any(str(v).strip().lower() in {'true','scr','scratched','lscr'} for v in vals)
def price_edge(market,edgeiq):
    if not market or not edgeiq: return ''
    try: return f'{((float(market)/float(edgeiq))-1)*100:+.1f}%'
    except Exception: return ''
def read_csv(path):
    if not path.exists(): return []
    with path.open('r',encoding='utf-8-sig',errors='replace',newline='') as h: return list(csv.DictReader(h))
def build_current_market_index():
    out={}
    for r in read_csv(CURRENT_MARKET):
        key=(clean(r.get('race_date')),normalise(r.get('canonical_track') or r.get('track')),number_text(r.get('race_number') or r.get('race_no')),normalise(r.get('horse_name') or r.get('horse')))
        if all(key): out[key]=r
    return out
def build_epr_price_index():
    out={}
    for r in read_csv(EPR_PRICE):
        key=(
            clean(r.get('race_date')),
            normalise(r.get('track')),
            number_text(r.get('race_no')),
            normalise(r.get('horse'))
        )
        if all(key):
            out[key]=r
    return out
def build_enriched_index():
    if not ENRICHED.exists(): return {}
    payload=json.loads(ENRICHED.read_text(encoding='utf-8')); out={}
    for race in payload.get('races',[]) if isinstance(payload,dict) else []:
        d=clean(race.get('raceDate')); t=clean(race.get('meeting')); rn=number_text(race.get('raceNumber'))
        for runner in race.get('runners',[]) or []:
            if isinstance(runner,dict): out[(d,normalise(t),rn,normalise(runner.get('runnerName')))]=runner
    return out
def disclosure(cm,generated_at,market):
    if cm:
        return {'market_availability_status':clean(cm.get('market_availability_status')) or ('LIVE_MARKET' if market else 'MARKET_UNAVAILABLE'),'market_source_status':'LADBROKES_CANONICAL','market_observed_at':clean(cm.get('edgeiq_observed_at')),'market_generated_at':generated_at,'market_age_minutes':'','market_freshness_status':clean(cm.get('market_freshness_status')) or 'CURRENT_PROVIDER_OBSERVATION','market_is_live':'true' if clean(cm.get('market_availability_status'))=='LIVE_MARKET' else 'false'}
    return {'market_availability_status':'MARKET_UNAVAILABLE' if not market else 'MARKET_SNAPSHOT','market_source_status':'UNAVAILABLE' if not market else 'STATIC_SNAPSHOT','market_observed_at':'','market_generated_at':generated_at,'market_age_minutes':'','market_freshness_status':'MARKET_UNAVAILABLE' if not market else 'MARKET_TIMESTAMP_UNKNOWN','market_is_live':'false'}
def row_status(scratched,market,edgeiq):
    if scratched: return 'Scratched'
    if not market: return 'Pending Market'
    if not edgeiq: return 'EDGEiQ Price Pending'
    return 'Governed Price Context'
def main():
    if not CATALOG.exists(): raise FileNotFoundError(CATALOG)
    catalog=json.loads(CATALOG.read_text(encoding='utf-8')); generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
    enriched=build_enriched_index(); current_market=build_current_market_index(); epr_price=build_epr_price_index(); rows=[]; matched_enriched=0; matched_current_market=0; matched_epr_price=0
    for m in catalog.get('meetings',[]) if isinstance(catalog,dict) else []:
        mk=clean(m.get('meetingKey')); d=clean(m.get('date')); track=clean(m.get('meeting'))
        for race in m.get('races',[]) or []:
            rn=number_text(race.get('raceNumber')); rk=clean(race.get('raceKey')) or f'{mk}|R{rn}'
            for i,runner in enumerate(race.get('runners',[]) or []):
                if not isinstance(runner,dict): continue
                horse=runner_name(runner); key=(d,normalise(track),rn,normalise(horse)); en=enriched.get(key); cm=current_market.get(key); ep=epr_price.get(key); matched_enriched+=1 if en else 0; matched_current_market+=1 if cm else 0; matched_epr_price+=1 if ep else 0
                epi=value_from_source(en.get('epi')) if en else ''; edgeiq=decimal_text(ep.get('edgeiq_price_epr_v1')) if ep else ''
                market=decimal_text(cm.get('fixed_win') if cm else '') or (value_from_source(en.get('marketPrice')) if en else '')
                openp=decimal_text(cm.get('opening_price') if cm else ''); high=decimal_text(cm.get('high_price') if cm else ''); low=decimal_text(cm.get('low_price') if cm else ''); move=clean(cm.get('price_movement') if cm else '')
                scratched=is_scratched(runner,en); source='LADBROKES_CANONICAL_MARKET_V1' if cm else (source_name(en.get('marketPrice'),'edgeiq_form_guide_enriched_v2') if en and market else 'THREE_DAY_PRODUCT_CATALOG_V1')
                timestamp=clean(cm.get('edgeiq_observed_at') if cm else '') or (source_time(en.get('marketPrice')) if en else '') or generated_at
                rows.append({'workspace_id':'BETA-010','meeting_key':mk,'race_key':rk,'generated_at':generated_at,'race_date':d,'track':track,'race_no':rn,'no':runner_no(runner,i),'horse':horse,'epi':epi,'market':market,'open':openp,'high':high,'low':low,'move':move,'edgeiq_price':edgeiq,'edge':price_edge(market,edgeiq),'status':row_status(scratched,market,edgeiq),'source':source,'source_timestamp':timestamp,'source_confidence':'governed' if cm else ('governed' if market or edgeiq or epi else 'unavailable'),'row_status':'scratched' if scratched else 'current' if market or edgeiq or epi else 'pending_market',**disclosure(cm,generated_at,market)})
    with OUT.open('w',encoding='utf-8',newline='') as h:
        w=csv.DictWriter(h,fieldnames=FIELDNAMES); w.writeheader(); w.writerows(rows)
    races=len({r['race_key'] for r in rows if r['race_key']})
    with SUMMARY.open('w',encoding='utf-8',newline='') as h:
        w=csv.DictWriter(h,fieldnames=['metric','value']); w.writeheader(); w.writerows([{'metric':'rows','value':len(rows)},{'metric':'races','value':races},{'metric':'matched_enriched_rows','value':matched_enriched},{'metric':'matched_current_market_rows','value':matched_current_market},{'metric':'frontend_limit','value':10000},{'metric':'status','value':'PASS' if len(rows)<=10000 else 'WARN_OVER_LIMIT'}])
    TRACE.write_text('\n'.join(['EDGEIQ_MARKET_TERMINAL_FEED_V1',f'generated_at={generated_at}',f'rows={len(rows)}',f'races={races}',f'matched_enriched_rows={matched_enriched}',f'matched_current_market_rows={matched_current_market}',f'source_current_market={CURRENT_MARKET.name if CURRENT_MARKET.exists() else "missing"}'])+'\n',encoding='utf-8')
    if len(rows)>10000: raise RuntimeError('edgeiq_market_terminal_feed_v1 exceeds frontend limit')
    print(f'EDGEIQ_MARKET_TERMINAL_FEED_V1 rows={len(rows)} races={races} matched_current_market={matched_current_market}')
if __name__=='__main__': main()
""",encoding='utf-8')

def patch_form():
    p=SCRIPTS/'build_edgeiq_form_guide_enriched_v2.py'; checkpoint(p); s=p.read_text(encoding='utf-8')
    s=replace_once(s,"FAIR_PRICE = DATA / \"edgeiq_fair_price_v7_2.csv\"","FAIR_PRICE = DATA / \"edgeiq_fair_price_v7_2.csv\"\nCURRENT_MARKET = DATA / \"edgeiq_current_market_v1.csv\"",'current market const')
    s=replace_once(s,"current_price = load_exact_current(FAIR_PRICE, current_runner_keys, \"horse\", \"race_date\", \"track\", \"race_no\")","current_price = load_exact_current(FAIR_PRICE, current_runner_keys, \"horse\", \"race_date\", \"track\", \"race_no\")\n    current_market = load_exact_current(CURRENT_MARKET, current_runner_keys, \"horse_name\", \"race_date\", \"canonical_track\", \"race_number\")",'current market load')
    s=replace_once(s,"price_row = current_price.get(race_identity)","price_row = current_price.get(race_identity)\n            market_row = current_market.get(race_identity)",'market row')
    s=replace_once(s,"runner[\"marketPrice\"] = source_value(runner.get(\"marketPrice\"), runner.get(\"marketSource\"), \"edgeiq_three_day_product_catalog_v1\", runner.get(\"marketAsAt\"))\n            runner[\"marketSource\"] = runner.get(\"marketPrice\", {}).get(\"source\") if isinstance(runner.get(\"marketPrice\"), dict) else runner.get(\"marketSource\")","market_price_value = num((market_row or {}).get(\"fixed_win\") or runner.get(\"marketPrice\"))\n            market_price_source = \"edgeiq_current_market_v1.csv:fixed_win\" if (market_row or {}).get(\"fixed_win\") else runner.get(\"marketSource\")\n            market_price_version = \"LADBROKES_CANONICAL_MARKET_V1\" if (market_row or {}).get(\"fixed_win\") else \"edgeiq_three_day_product_catalog_v1\"\n            market_price_as_at = clean_text((market_row or {}).get(\"edgeiq_observed_at\")) or runner.get(\"marketAsAt\")\n            runner[\"marketPrice\"] = source_value(market_price_value, market_price_source, market_price_version, market_price_as_at)\n            runner[\"marketSource\"] = runner.get(\"marketPrice\", {}).get(\"source\") if isinstance(runner.get(\"marketPrice\"), dict) else runner.get(\"marketSource\")",'market price source')
    p.write_text(s,encoding='utf-8')

def patch_daily():
    p=SCRIPTS/'run_edgeiq_daily_product_refresh_v1.py'; checkpoint(p); s=p.read_text(encoding='utf-8')
    target="'scripts/build_edgeiq_current_race_fields_from_product_catalog_v1.py', 'scripts/build_edgeiq_form_guide_current_base_v1.py'"
    replacement="'scripts/build_edgeiq_current_race_fields_from_product_catalog_v1.py', 'scripts/build_edgeiq_ladbrokes_active_market_refresh_v1.py', 'scripts/build_edgeiq_current_market_v1.py', 'scripts/build_edgeiq_form_guide_current_base_v1.py'"
    s=replace_once(s,target,replacement,'daily stage insertion')
    p.write_text(s,encoding='utf-8')

def main():
    patch_adapter(); write_market_terminal(); patch_form(); patch_daily(); print('EDGEIQ_LADBROKES_MARKET_INTEGRATION_PATCH_APPLIED')
if __name__=='__main__': main()
