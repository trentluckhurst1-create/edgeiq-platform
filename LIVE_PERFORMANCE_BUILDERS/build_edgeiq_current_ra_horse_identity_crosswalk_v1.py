from __future__ import annotations
import base64,csv,hashlib,html,json,re,urllib.parse,os,tempfile
from collections import defaultdict,Counter
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
CONFIG=ROOT/'config'/'performance-intelligence'
DOC=ROOT/'docs'/'victoria-live-recovery-v4'
RAW=ROOT/'docs'/'victoria-live-recovery-v3'/'raw-evidence'
RESULTS=DATA/'edgeiq_daily_official_results_fact_v1.csv'
RATING=DATA/'edgeiq_performance_rating_base_fact_v1.csv'
IDENTITY=CONFIG/'edgeiq_horse_performance_identity_map_v1.csv'
CROSSWALK_CONFIG=CONFIG/'edgeiq_racing_australia_horse_identity_crosswalk_v1.csv'
CROSSWALK_PUBLIC=DATA/'edgeiq_current_horse_identity_crosswalk_v1.csv'
BASELINE_CSV=DOC/'EDGEIQ_HORSE_IDENTITY_BASELINE.csv'
BASELINE_JSON=DOC/'EDGEIQ_HORSE_IDENTITY_BASELINE.json'
BASELINE_MD=DOC/'EDGEIQ_HORSE_IDENTITY_BASELINE.md'
UNRES_CSV=DOC/'EDGEIQ_CURRENT_UNRESOLVED_HORSE_IDENTITIES.csv'
UNRES_JSON=DOC/'EDGEIQ_CURRENT_UNRESOLVED_HORSE_IDENTITIES.json'
UNRES_MD=DOC/'EDGEIQ_CURRENT_UNRESOLVED_HORSE_IDENTITIES.md'
DECISION_MD=DOC/'EDGEIQ_CURRENT_HORSE_IDENTITY_DECISION.md'
DECISION_JSON=DOC/'EDGEIQ_CURRENT_HORSE_IDENTITY_DECISION.json'
REPORT_CSV=DOC/'EDGEIQ_CURRENT_HORSE_IDENTITY_CROSSWALK_REPORT.csv'
REPORT_JSON=DOC/'EDGEIQ_CURRENT_HORSE_IDENTITY_CROSSWALK_REPORT.json'
REPORT_MD=DOC/'EDGEIQ_CURRENT_HORSE_IDENTITY_CROSSWALK_REPORT.md'

IDENTITY_FIELDS=['source_horse_name','canonical_horse_id','canonical_horse_name','identity_status','evidence_reference','evidence_sha256']
CROSSWALK_FIELDS='source_system source_horse_id source_race_entry_id source_horse_name canonical_horse_id canonical_horse_name match_method evidence_type evidence_reference approval_status policy_version effective_from created_at source_meeting_date track race_number trainer jockey barrier saddlecloth result_fact_evidence_sha256 identity_evidence_sha256'.split()
UNRES_FIELDS='source_horse_name normalised_display_name source_system source_meeting_date track race_number runner_number trainer country_or_suffix source_horse_identifier current_canonical_match rejection_reason'.split()

def text(v:Any)->str:
    return str(v if v is not None else '').strip()
def clean_spaces(v):
    return re.sub(r'\s+',' ',html.unescape(text(v)).replace('\xa0',' ')).strip()
def norm(v):
    return ''.join(ch for ch in clean_spaces(v).upper() if ch.isalnum())
def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def sha(parts): return hashlib.sha256('\x1f'.join(text(p) for p in parts).encode('utf-8')).hexdigest()
def kh(parts,n=24): return sha(parts)[:n].upper()
def read_csv(p:Path):
    if not p.exists(): return []
    with p.open('r',encoding='utf-8-sig',newline='') as h: return list(csv.DictReader(h))
def write_csv(p:Path,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.'+p.name+'.',suffix='.tmp',dir=p.parent); os.close(fd); tp=Path(tmp)
    try:
        with tp.open('w',encoding='utf-8',newline='') as h:
            w=csv.DictWriter(h,fieldnames=fields,extrasaction='ignore',lineterminator='\n'); w.writeheader();
            for r in rows: w.writerow({f:text(r.get(f,'')) for f in fields})
        os.replace(tp,p)
    finally:
        if tp.exists(): tp.unlink()
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def write_text(p,s): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s if s.endswith('\n') else s+'\n',encoding='utf-8')
def b64decode_param(v):
    raw=urllib.parse.unquote(html.unescape(text(v)))
    try: return base64.b64decode(raw).decode('ascii')
    except Exception: return ''
def strip_tags(x): return clean_spaces(re.sub(r'<[^>]+>',' ',x,flags=re.S))
def cells_raw(row_html): return re.findall(r'<td\b[^>]*>(.*?)</td>',row_html,flags=re.S|re.I)
def cell_texts(cells): return [strip_tags(c) for c in cells]
def map_row(cells_txt,cells_html):
    candidates=[]
    if len(cells_txt)>=12: candidates.append(({'finish':cells_txt[1],'saddle':cells_txt[3],'horse':cells_txt[4],'trainer':cells_txt[5],'jockey':cells_txt[6],'barrier':cells_txt[8]},4))
    if len(cells_txt)>=11: candidates.append(({'finish':cells_txt[1],'saddle':cells_txt[2],'horse':cells_txt[3],'trainer':cells_txt[4],'jockey':cells_txt[5],'barrier':cells_txt[7]},3))
    for d,horse_idx in candidates:
        if re.search(r'[A-Za-z]',d.get('horse','')) and d.get('horse','').upper() not in {'SCR','SCRATCHED'}:
            d['horse_cell_html']=cells_html[horse_idx] if horse_idx < len(cells_html) else ''
            return d
    return {}
def race_num_from_block(prefix):
    m=re.search(r"<a\s+name=['\"]Race(\d+)['\"]\s*></a>",prefix,flags=re.I)
    return m.group(1) if m else ''
def parse_ra_evidence():
    rows=[]
    for path in sorted(RAW.glob('RA_RESULTS_*.html')):
        s=path.read_text(encoding='utf-8',errors='ignore')
        if 'HorseFullForm.aspx' not in s: continue
        parts=re.split(r"(<a\s+name=['\"]Race\d+['\"]\s*></a>)",s,flags=re.I)
        current_race=''
        for part in parts:
            rn=race_num_from_block(part)
            if rn:
                current_race=rn; continue
            if not current_race: continue
            tab=re.search(r"<table\b[^>]*class=['\"]race-strip-fields['\"][^>]*>(.*?)</table>",part,flags=re.S|re.I)
            if not tab: continue
            for rh in re.findall(r"<tr\b[^>]*class=['\"](?:EvenRow|OddRow)['\"][^>]*>(.*?)</tr>",tab.group(1),flags=re.S|re.I):
                raw_cells=cells_raw(rh); texts=cell_texts(raw_cells); mapped=map_row(texts,raw_cells)
                if not mapped: continue
                href_m=re.search(r'href=["\'](?P<href>[^"\']*HorseFullForm\.aspx[^"\']*)["\']',mapped.get('horse_cell_html',''),flags=re.I)
                if not href_m: continue
                href=html.unescape(href_m.group('href'))
                horsecode_m=re.search(r'horsecode=([^&"\']+)',href,flags=re.I)
                raceentry_m=re.search(r'raceentry=([^&"\']+)',href,flags=re.I)
                key_m=re.search(r'Key=([^&"\']+)',href,flags=re.I)
                key=urllib.parse.unquote(html.unescape(key_m.group(1))) if key_m else ''
                date_text=''; track=''
                km=re.match(r'(\d{4})([A-Za-z]{3})(\d{2}),VIC,([^&]+)',key)
                if km:
                    months={m:i for i,m in enumerate('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(),start=1)}
                    date_text=f"{km.group(1)}-{months.get(km.group(2).title(),0):02d}-{int(km.group(3)):02d}"; track=km.group(4).upper()
                horsecode=b64decode_param(horsecode_m.group(1) if horsecode_m else '')
                raceentry=b64decode_param(raceentry_m.group(1) if raceentry_m else '')
                rows.append({'source_system':'RACING_AUSTRALIA','source_horse_id':horsecode,'source_race_entry_id':raceentry,'source_horse_name':clean_spaces(mapped.get('horse')),'source_meeting_date':date_text,'track':track,'race_number':current_race,'trainer':clean_spaces(mapped.get('trainer')),'jockey':clean_spaces(mapped.get('jockey')),'barrier':clean_spaces(mapped.get('barrier')),'saddlecloth':clean_spaces(mapped.get('saddle')),'evidence_reference':str(path.relative_to(ROOT)).replace('\\','/')+f"#horsecode={horsecode};raceentry={raceentry}",'raw_file':str(path.relative_to(ROOT)).replace('\\','/')})
    return rows

def component_inventory():
    comps=[
      ('horse identity source facts','scripts/build_edgeiq_current_ra_horse_identity_crosswalk_v1.py','docs/victoria-live-recovery-v3/raw-evidence/*.html','config/performance-intelligence/edgeiq_racing_australia_horse_identity_crosswalk_v1.csv','source_system+source_horse_id','RACING_AUSTRALIA horsecode','public HorseFullForm horsecode retained; exact source id only'),
      ('approved identity map','scripts/build_edgeiq_current_ra_horse_identity_crosswalk_v1.py','current RA crosswalk + existing map','config/performance-intelligence/edgeiq_horse_performance_identity_map_v1.csv','source_horse_name','canonical_horse_id','APPROVED rows only; exact RA source ID creates deterministic RA_HORSE id'),
      ('horse observation builder','scripts/build_edgeiq_horse_performance_observation_fact_v1.py','edgeiq_performance_rating_base_fact_v1.csv + identity map','edgeiq_horse_performance_observation_fact_v1.csv','performance_rating_base_id','canonical_horse_id','exact normalised source name in approved map; unresolved rows rejected'),
      ('horse aggregate builder','scripts/build_edgeiq_horse_performance_aggregate_fact_v1.py','edgeiq_horse_performance_observation_fact_v1.csv','edgeiq_horse_performance_aggregate_fact_v1.csv','canonical_horse_id+as_of_date','canonical_horse_id','minimum observations and effective aggregation parameter unchanged'),
      ('horse rating builder','scripts/build_edgeiq_horse_performance_rating_fact_v1.py','edgeiq_horse_performance_aggregate_fact_v1.csv','edgeiq_horse_performance_rating_fact_v1.csv','horse_performance_aggregate_id','canonical_horse_id','direct historical aggregate value; formula unchanged'),
      ('snapshot builder','scripts/build_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py','edgeiq_race_entry_fact_v1.csv + horse ratings','edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv','race_entry_id','canonical_horse_id','as-of date filter; no future rating leakage'),
      ('EPI builder','scripts/build_edgeiq_race_entry_epi_fact_v1.py','edgeiq_race_entry_epi_component_fact_v1.csv + epi parameter','edgeiq_race_entry_epi_fact_v1.csv','race_entry_id','race_entry_id','existing weighted additive EPI; formula unchanged'),
    ]
    rows=[]
    for name,script,inputp,output,pk,ik,rule in comps:
        op=ROOT/output if output.startswith('config') else DATA/output if not output.startswith('edgeiq_') else DATA/output
        current_rows=len(read_csv(op)) if op.exists() and op.suffix.lower()=='.csv' else ''
        latest=''
        if op.exists() and op.suffix.lower()=='.csv':
            rr=read_csv(op)
            for fld in ['race_date','rating_as_of_date','aggregate_as_of_date','source_meeting_date']:
                vals=sorted({text(r.get(fld)) for r in rr if text(r.get(fld))})
                if vals: latest=vals[-1]; break
        rows.append({'component':name,'script_path':script,'input_path':inputp,'output_path':output,'primary_key':pk,'identity_key':ik,'approval_mechanism':rule,'exact_match_rules':'No fuzzy automatic promotion; exact source ID or exact unique canonical name only','current_row_count':current_rows,'latest_date':latest,'current_rejection_reasons':''})
    return rows

def main():
    DOC.mkdir(parents=True,exist_ok=True); CONFIG.mkdir(parents=True,exist_ok=True)
    created_at=now(); evidence=parse_ra_evidence(); facts=read_csv(RESULTS); ratings=read_csv(RATING)
    existing_crosswalk_rows=read_csv(CROSSWALK_CONFIG)
    existing_created_at={text(r.get('source_horse_id')):text(r.get('created_at')) for r in existing_crosswalk_rows if text(r.get('source_horse_id')) and text(r.get('created_at'))}
    existing_crosswalk_by_source={text(r.get('source_horse_id')):r for r in existing_crosswalk_rows if text(r.get('source_horse_id'))}
    current_names={text(r.get('winner_horse_name')).upper() for r in ratings if text(r.get('race_date'))>='2026-07-20'} | {text(r.get('runner_name')).upper() for r in facts if text(r.get('race_date'))>='2026-07-20'}
    evidence=[r for r in evidence if text(r.get('source_horse_name')).upper() in current_names]
    fact_by_key={(text(r.get('race_date')),text(r.get('track')).upper(),text(r.get('race_number')),text(r.get('runner_name')).upper()):r for r in facts}
    existing=read_csv(IDENTITY)
    existing_by_name=defaultdict(set)
    for r in existing:
        if text(r.get('identity_status'))=='APPROVED': existing_by_name[norm(r.get('canonical_horse_name'))].add(text(r.get('canonical_horse_id')))
    by_source=defaultdict(list)
    for r in evidence:
        by_source[text(r.get('source_horse_id'))].append(r)
    cross=[]; unresolved=[]; selected_minimal=[]
    for source_id, group in sorted(by_source.items()):
        names={norm(r.get('source_horse_name')) for r in group if norm(r.get('source_horse_name'))}
        display_names=sorted({text(r.get('source_horse_name')) for r in group if text(r.get('source_horse_name'))})
        if not source_id or len(names)!=1:
            for r in group:
                unresolved.append({'source_horse_name':r.get('source_horse_name'),'normalised_display_name':norm(r.get('source_horse_name')),'source_system':'RACING_AUSTRALIA','source_meeting_date':r.get('source_meeting_date'),'track':r.get('track'),'race_number':r.get('race_number'),'runner_number':r.get('saddlecloth'),'trainer':r.get('trainer'),'country_or_suffix':'','source_horse_identifier':source_id,'current_canonical_match':'','rejection_reason':'MISSING_SOURCE_HORSE_ID' if not source_id else 'SOURCE_ID_NAME_CONFLICT'})
            continue
        source_name=display_names[0]
        exact_existing=existing_by_name.get(norm(source_name),set())
        previous=existing_crosswalk_by_source.get(source_id,{})
        if text(previous.get('canonical_horse_id')):
            canonical_id=text(previous.get('canonical_horse_id'))
            method='EXACT_SOURCE_ID_NEW_CANONICAL' if canonical_id == f'RA_HORSE_{source_id}' else (text(previous.get('match_method')) or 'EXACT_NAME_EXISTING_UNIQUE')
        elif f'RA_HORSE_{source_id}' in exact_existing:
            canonical_id=f'RA_HORSE_{source_id}'; method='EXACT_SOURCE_ID_NEW_CANONICAL'
        elif len(exact_existing)==1:
            canonical_id=next(iter(exact_existing)); method='EXACT_NAME_EXISTING_UNIQUE'
        elif len(exact_existing)>1:
            for r in group:
                unresolved.append({'source_horse_name':source_name,'normalised_display_name':norm(source_name),'source_system':'RACING_AUSTRALIA','source_meeting_date':r.get('source_meeting_date'),'track':r.get('track'),'race_number':r.get('race_number'),'runner_number':r.get('saddlecloth'),'trainer':r.get('trainer'),'country_or_suffix':'','source_horse_identifier':source_id,'current_canonical_match':'|'.join(sorted(exact_existing)),'rejection_reason':'EXACT_NAME_EXISTING_AMBIGUOUS'})
            continue
        else:
            canonical_id=f'RA_HORSE_{source_id}'; method='EXACT_SOURCE_ID_NEW_CANONICAL'
        canonical_name=source_name
        evref=';'.join(sorted({r.get('evidence_reference','') for r in group if r.get('evidence_reference')}))
        evhash=sha([source_id,source_name,canonical_id,evref,method])
        first=sorted(group,key=lambda r:(r.get('source_meeting_date',''),r.get('track',''),r.get('race_number',''),r.get('saddlecloth','')))[0]
        fk=(first.get('source_meeting_date',''),first.get('track','').upper(),first.get('race_number',''),source_name.upper())
        fact=fact_by_key.get(fk,{})
        cross.append({'source_system':'RACING_AUSTRALIA','source_horse_id':source_id,'source_race_entry_id':'|'.join(sorted({r.get('source_race_entry_id','') for r in group if r.get('source_race_entry_id')})),'source_horse_name':source_name,'canonical_horse_id':canonical_id,'canonical_horse_name':canonical_name,'match_method':method,'evidence_type':'PUBLIC_RA_HORSEFULLFORM_HORSECODE','evidence_reference':evref,'approval_status':'APPROVED','policy_version':'RA-HORSE-ID-GOV-V4','effective_from':'2026-07-20','created_at':existing_created_at.get(source_id, created_at),'source_meeting_date':first.get('source_meeting_date',''),'track':first.get('track',''),'race_number':first.get('race_number',''),'trainer':first.get('trainer',''),'jockey':first.get('jockey',''),'barrier':first.get('barrier',''),'saddlecloth':first.get('saddlecloth',''),'result_fact_evidence_sha256':fact.get('source_evidence_sha256',''),'identity_evidence_sha256':evhash})
        selected_minimal.append({'source_horse_name':source_name,'canonical_horse_id':canonical_id,'canonical_horse_name':canonical_name,'identity_status':'APPROVED','evidence_reference':evref,'evidence_sha256':evhash})
    # Merge minimal map without replacing existing rows.
    merged={text(r.get('source_horse_name')):r for r in existing if text(r.get('source_horse_name'))}
    for r in selected_minimal:
        key=text(r.get('source_horse_name'))
        existing_row=merged.get(key)
        if existing_row is None or text(existing_row.get('canonical_horse_id')).startswith('RA_HORSE_'):
            merged[key]=r
    merged_rows=[merged[k] for k in sorted(merged,key=lambda x:(not x.isdigit(),x.upper()))]
    write_csv(IDENTITY,merged_rows,IDENTITY_FIELDS)
    write_csv(CROSSWALK_CONFIG,cross,CROSSWALK_FIELDS); write_csv(CROSSWALK_PUBLIC,cross,CROSSWALK_FIELDS)
    write_csv(REPORT_CSV,cross,CROSSWALK_FIELDS); write_json(REPORT_JSON,{'rows':len(cross),'approved':sum(1 for r in cross if r['approval_status']=='APPROVED'),'new_canonical_horses':sum(1 for r in cross if r['match_method']=='EXACT_SOURCE_ID_NEW_CANONICAL'),'existing_canonical_horses_matched':sum(1 for r in cross if r['match_method']=='EXACT_NAME_EXISTING_UNIQUE'),'unresolved':len(unresolved),'source_ids_retained':sum(1 for r in cross if r['source_horse_id']),'chigurh':[r for r in cross if r['source_horse_name'].upper()=='CHIGURH']})
    write_text(REPORT_MD,'# EDGEiQ Current Horse Identity Crosswalk Report V4\n\n'+f"Approved rows: {len(cross)}\n\nUnresolved rows: {len(unresolved)}\n\nCHIGURH: "+json.dumps([r for r in cross if r['source_horse_name'].upper()=='CHIGURH'],indent=2))
    write_csv(UNRES_CSV,unresolved,UNRES_FIELDS); write_json(UNRES_JSON,{'distinct_unresolved_horses':len({r['source_horse_name'] for r in unresolved}),'affected_runner_observations':len(unresolved),'affected_races':len({(r['source_meeting_date'],r['track'],r['race_number']) for r in unresolved}),'rows':unresolved}); write_text(UNRES_MD,'# EDGEiQ Current Unresolved Horse Identities V4\n\n'+f"Distinct unresolved horses: {len({r['source_horse_name'] for r in unresolved})}\n")
    baseline=component_inventory(); write_csv(BASELINE_CSV,baseline,'component script_path input_path output_path primary_key identity_key approval_mechanism exact_match_rules current_row_count latest_date current_rejection_reasons'.split()); write_json(BASELINE_JSON,{'components':baseline}); write_text(BASELINE_MD,'# EDGEiQ Horse Identity Baseline V4\n\n'+'\n'.join(f"- {r['component']}: {r['output_path']} rows={r['current_row_count']}" for r in baseline))
    decision={'status':'HORSE_IDENTITY_APPROVED' if cross else 'HORSE_IDENTITY_UNRESOLVED','source':'Racing Australia public HorseFullForm horsecode in retained result HTML','protected_endpoint_used':'NO','fuzzy_auto_promotion':'NO','policy_version':'RA-HORSE-ID-GOV-V4','crosswalk_rows':len(cross),'unresolved_rows':len(unresolved),'chigurh_resolution':next((r for r in cross if r['source_horse_name'].upper()=='CHIGURH'),{})}
    write_json(DECISION_JSON,decision); write_text(DECISION_MD,'# EDGEiQ Current Horse Identity Decision V4\n\n'+'\n'.join(f'- {k}: {v}' for k,v in decision.items()))
    print(json.dumps({'status':decision['status'],'crosswalk_rows':len(cross),'identity_map_rows':len(merged_rows),'unresolved':len(unresolved),'chigurh':decision['chigurh_resolution']},indent=2))
if __name__=='__main__': main()
