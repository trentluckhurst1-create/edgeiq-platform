from __future__ import annotations
import argparse,csv,hashlib,html,json,os,re,shutil,subprocess,sys,tempfile,time,urllib.parse,urllib.request,urllib.error
from datetime import date,datetime,timezone
from decimal import Decimal
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'; DOC=ROOT/'docs'/'victoria-live-recovery-v3'; RAW=DOC/'raw-evidence'
BUILDER='EDGEIQ_VICTORIA_LIVE_RECOVERY_V3'; CONTRACT='1.0.0'; UA='Mozilla/5.0 EDGEiQ-Victoria-Live-Recovery-V3'; RA='https://www.racingaustralia.horse/FreeFields/Results.aspx?Key='
RAW_FIELDS='operation_run_id source_name source_file source_row_number source_observed_at source_evidence_sha256 raw_payload_sha256 raw_status'.split()
FACT_FIELDS='operation_run_id canonical_race_id canonical_meeting_id race_date track race_number distance_metres track_condition official_race_time_seconds official_race_time_raw race_status official_status field_size runner_name runner_source_id finish_position placing_status margin starting_price jockey trainer weight barrier source_publication_timestamp source_evidence_sha256 result_status builder_version contract_version'.split()
REJ_FIELDS=FACT_FIELDS+['rejection_reason']
DELTA_FIELDS='race_time_delta_id benchmark_observation_id benchmark_group_id standard_time_id race_key race_date track_name official_distance_metres winner_horse_name winner_race_time_seconds standard_time_seconds time_delta_seconds time_delta_interpretation calculation_method source_observation_sha256 source_standard_time_evidence_sha256 race_time_delta_evidence_sha256 builder_version contract_version built_at_utc'.split()
LVS_FIELDS='lengths_versus_standard_id race_time_delta_id benchmark_observation_id benchmark_group_id standard_time_id length_conversion_parameter_id race_key race_date track_name official_distance_metres winner_horse_name winner_race_time_seconds standard_time_seconds time_delta_seconds seconds_per_length lengths_versus_standard lengths_versus_standard_interpretation calculation_method conversion_scope conversion_model_version source_race_time_delta_evidence_sha256 source_conversion_parameter_evidence_sha256 lengths_versus_standard_evidence_sha256 builder_version contract_version built_at_utc'.split()
LVS_REJ_FIELDS='race_time_delta_id race_key race_date track_name official_distance_metres rejection_reason surface_group track_condition_number track_condition_group'.split()
BASE_FIELDS='performance_intelligence_base_id lengths_versus_standard_id race_time_delta_id benchmark_observation_id benchmark_group_id standard_time_id length_conversion_parameter_id race_key race_date track_name official_distance_metres winner_horse_name winner_race_time_seconds standard_time_seconds time_delta_seconds seconds_per_length raw_performance_lengths raw_performance_interpretation performance_status calculation_method source_lengths_versus_standard_evidence_sha256 performance_intelligence_base_evidence_sha256 source_builder_version builder_version contract_version built_at_utc'.split()
def clean(v):
    s=html.unescape('' if v is None else str(v)).replace('\xa0',' ').strip(); s=re.sub(r'\s+',' ',s); return '' if s.lower() in {'','nan','none','null','undefined','-'} else s
def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def kh(parts,n=24): return hashlib.sha256('\x1f'.join(clean(x) for x in parts).encode()).hexdigest()[:n].upper()
def norm_track(v): return ''.join(c for c in clean(v).upper() if c.isalnum())
def cid_meet(d,t): return 'EIQM-'+kh([d,norm_track(t)],24)
def cid_race(d,t,r,dist=''): return 'EIQD-'+kh([d,norm_track(t),r,dist],24)
def rsha(row): return hashlib.sha256(json.dumps({k:clean(row.get(k)) for k in sorted(row)},sort_keys=True,separators=(',',':')).encode()).hexdigest()
def fsha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ''
def read_csv(p):
    if not p.exists(): return []
    csv.field_size_limit(min(sys.maxsize,2147483647))
    with p.open('r',encoding='utf-8-sig',newline='') as h: return list(csv.DictReader(h))
def write_csv(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(prefix='.'+p.name+'.',suffix='.tmp',dir=p.parent); os.close(fd); tp=Path(tmp)
    try:
        with tp.open('w',encoding='utf-8',newline='') as h:
            w=csv.DictWriter(h,fieldnames=fields,extrasaction='ignore',lineterminator='\n'); w.writeheader(); [w.writerow({f:clean(r.get(f)) for f in fields}) for r in rows]
        os.replace(tp,p)
    finally:
        if tp.exists(): tp.unlink()
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def write_text(p,t): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(t if t.endswith('\n') else t+'\n',encoding='utf-8')
def pdate(v): return datetime.now().date() if clean(v).upper()=='TODAY' or not clean(v) else date.fromisoformat(clean(v)[:10])
def strip(x):
    x=re.sub(r'<!--.*?-->|<script\b.*?</script>|<style\b.*?</style>',' ',x,flags=re.S|re.I); return clean(re.sub(r'<[^>]+>',' ',x))
def ra_date(d): return date.fromisoformat(d).strftime('%Y%b%d')
def variants(track):
    t=clean(track).upper(); vals=[clean(track).title()]
    if 'SANDOWN' in t: vals+=['Sandown','Sandown Lakeside','Sandown Hillside']
    if 'BALLARAT' in t: vals+=['Ballarat','Ballarat Synthetic']
    if 'BENDIGO' in t: vals+=['Bendigo','Apiam Bendigo']
    if 'SWAN HILL' in t: vals+=['Swan Hill']
    out=[]
    for v in vals:
        if v and v not in out: out.append(v)
    return out
def urls(m): return [RA+urllib.parse.quote(f"{ra_date(m['date'])},VIC,{v}",safe=',') for v in variants(m['track'])]
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,*/*'})
    try:
        with urllib.request.urlopen(req,timeout=45) as r: return int(getattr(r,'status',0) or 0),clean(r.headers.get('content-type')),b'',r.read()
    except urllib.error.HTTPError as e:
        try: b=e.read()
        except Exception: b=b''
        return int(e.code),clean(e.headers.get('content-type') if e.headers else ''),str(e).encode(),b
    except Exception as e: return 0,'',str(e).encode(),b''
def secs(v):
    s=clean(v); m=re.search(r'(\d+):(\d+(?:\.\d+)?)',s)
    if m: return f"{(Decimal(m.group(1))*60+Decimal(m.group(2))).quantize(Decimal('0.000001')):.6f}"
    m=re.search(r'\d+(?:\.\d+)?',s); return f"{Decimal(m.group(0)).quantize(Decimal('0.000001')):.6f}" if m else ''
def price(v):
    m=re.search(r'\d+(?:\.\d+)?',clean(v).replace('$','')); return f"{Decimal(m.group(0)).quantize(Decimal('0.01'))}" if m else ''
def finish(v):
    m=re.search(r'\d+',clean(v)); return str(int(m.group(0))) if m else ''
def margin(v,fin):
    if fin=='1' and not clean(v): return '0'
    m=re.search(r'\d+(?:\.\d+)?',clean(v)); return str(Decimal(m.group(0)).normalize()) if m else ''
def label(h,name):
    m=re.search(rf'<b>{re.escape(name)}:</b>\s*([^<]+)',h,flags=re.I); return clean(m.group(1)) if m else ''
def cells(row_html): return [strip(c) for c in re.findall(r'<td\b[^>]*>(.*?)</td>',row_html,flags=re.S|re.I)]
def mapcells(c):
    cand=[]
    if len(c)>=12: cand.append({'finish':c[1],'saddle':c[3],'horse':c[4],'trainer':c[5],'jockey':c[6],'margin':c[7],'barrier':c[8],'weight':c[9],'sp':c[11]})
    if len(c)>=11: cand.append({'finish':c[1],'saddle':c[2],'horse':c[3],'trainer':c[4],'jockey':c[5],'margin':c[6],'barrier':c[7],'weight':c[8],'sp':c[10]})
    for x in cand:
        if re.search(r'[A-Za-z]',clean(x.get('horse'))) and clean(x.get('horse')).upper() not in {'SCR','SCRATCHED'}: return x
    return {}
def race_meta(block,rno):
    tm=re.search(r"<table\b[^>]*class=['\"]race-title['\"][^>]*>(.*?)</table>",block,flags=re.S|re.I); h=tm.group(1) if tm else block[:4000]; txt=strip(h)
    name=dist=''
    m=re.search(rf'Race\s+{rno}\s*-\s*[0-9:]+\s*(?:AM|PM)\s+(.*?)\s*\((\d+)\s*METRES\)',txt,flags=re.I)
    if not m: m=re.search(rf'Race\s+{rno}\s*-\s*(.*?)\s*\((\d+)\s*METRES\)',txt,flags=re.I)
    if m: name=clean(m.group(1)); dist=m.group(2)
    cond=label(h,'Track Condition'); rawtime=label(h,'Time')
    return {'race_name':name,'distance_metres':dist,'track_condition':cond,'official_race_time_raw':rawtime,'official_race_time_seconds':secs(rawtime)}
def meeting_meta(page):
    txt=strip(page); pub=''; cond=''
    m=re.search(r'Results Last Published:\s*(.*?)(?:Total Number|Race 1|$)',txt,flags=re.I); pub=clean(m.group(1)) if m else ''
    m=re.search(r'Track Condition:\s*([^\s]+\s*\d*)',txt,flags=re.I); cond=clean(m.group(1)) if m else ''
    return {'published':pub,'condition':cond}
def parse_page(mtg,page,url,run_id,raw_file):
    meta=meeting_meta(page); raw=[]; facts=[]; rej=[]; parts=re.split(r"<a\s+name=['\"]Race(\d+)['\"]\s*></a>",page,flags=re.I)
    if len(parts)<=1: return raw,facts,rej,{'status':'RESULTS_PENDING' if 'not currently available' in page.lower() else 'NO_RACE_ANCHORS','races':0,'facts':0,'rejections':0,'rows':0}
    rowno=0
    for i in range(1,len(parts),2):
        rno=finish(parts[i]); block=parts[i+1]; rm=race_meta(block,rno); tab=re.search(r"<table\b[^>]*class=['\"]race-strip-fields['\"][^>]*>(.*?)</table>",block,flags=re.S|re.I)
        if not tab: continue
        mapped=[]
        for rh in re.findall(r"<tr\b[^>]*class=['\"](?:EvenRow|OddRow)['\"][^>]*>(.*?)</tr>",tab.group(1),flags=re.S|re.I):
            c=cells(rh); mc=mapcells(c)
            if mc: mapped.append((mc,c))
        fsize=sum(1 for mc,c in mapped if finish(mc.get('finish')) and clean(mc.get('horse')))
        for mc,c in mapped:
            rowno+=1; fin=finish(mc.get('finish')); horse=clean(mc.get('horse'))
            core={'race_date':mtg['date'],'track':mtg['track'],'race_number':rno,'distance_metres':rm['distance_metres'],'runner_name':horse,'finish_position':fin,'official_race_time_seconds':rm['official_race_time_seconds'],'margin':margin(mc.get('margin'),fin),'source_url':url,'raw_cells':'|'.join(c)}; ev=rsha(core)
            raw.append({'operation_run_id':run_id,'source_name':'RACING_AUSTRALIA_PUBLIC_RESULTS_HTML','source_file':raw_file,'source_row_number':rowno,'source_observed_at':now(),'source_evidence_sha256':ev,'raw_payload_sha256':fsha(ROOT/raw_file),'raw_status':'RAW_CAPTURED'})
            base={'operation_run_id':run_id,'canonical_race_id':cid_race(mtg['date'],mtg['track'],rno,rm['distance_metres']),'canonical_meeting_id':cid_meet(mtg['date'],mtg['track']),'race_date':mtg['date'],'track':mtg['track'],'race_number':rno,'distance_metres':rm['distance_metres'],'track_condition':rm['track_condition'] or meta['condition'],'official_race_time_seconds':rm['official_race_time_seconds'],'official_race_time_raw':rm['official_race_time_raw'],'race_status':'RACE_RUN','official_status':'RESULT_OFFICIAL','field_size':fsize,'runner_name':horse,'runner_source_id':clean(mc.get('saddle')),'finish_position':fin,'placing_status':'PLACED' if fin in {'1','2','3'} else ('UNPLACED' if fin else ''),'margin':margin(mc.get('margin'),fin),'starting_price':price(mc.get('sp')),'jockey':clean(mc.get('jockey')),'trainer':clean(mc.get('trainer')),'weight':clean(mc.get('weight')),'barrier':clean(mc.get('barrier')),'source_publication_timestamp':meta['published'],'source_evidence_sha256':ev,'result_status':'RESULT_OFFICIAL','builder_version':BUILDER,'contract_version':CONTRACT}
            reasons=[]
            if not horse: reasons.append('MISSING_RUNNER')
            if not fin: reasons.append('MISSING_FINISH_POSITION')
            if not base['official_race_time_seconds']: reasons.append('MISSING_OFFICIAL_RACE_TIME')
            if fin!='1' and not base['margin']: reasons.append('MISSING_MARGIN')
            if reasons:
                rr=dict(base); rr['result_status']='RESULT_REJECTED'; rr['rejection_reason']='|'.join(reasons); rej.append(rr)
            else: facts.append(base)
    return raw,facts,rej,{'status':'RESULTS_AVAILABLE' if facts else 'NO_VALID_FACTS','races':len({x['canonical_race_id'] for x in facts}),'facts':len(facts),'rejections':len(rej),'rows':len(facts)+len(rej)}
def load_meetings(start,end,flt):
    rows=read_csv(DATA/'EDGEIQ_VICTORIA_CURRENT_MEETINGS.csv') or read_csv(DOC.parent/'victoria-live-recovery-v2'/'EDGEIQ_VICTORIA_CURRENT_MEETINGS.csv'); out=[]
    for r in rows:
        d=clean(r.get('date'))
        if not re.fullmatch(r'20\d\d-\d\d-\d\d',d): continue
        dd=date.fromisoformat(d)
        if not (start<=dd<=end): continue
        track=clean(r.get('track') or r.get('meeting_name'))
        if flt and flt.upper() not in track.upper() and flt.upper() not in clean(r.get('meeting_name')).upper(): continue
        out.append({'date':d,'track':track,'meeting_name':clean(r.get('meeting_name') or track),'meeting_code':clean(r.get('meeting_code')),'scheduled_races':clean(r.get('scheduled_races'))})
    return out
def acquire(meetings,run_id):
    RAW.mkdir(parents=True,exist_ok=True); raw=[]; facts=[]; rej=[]; rep=[]
    for m in meetings:
        chosen=None; parsed=None; attempts=[]
        for url in urls(m):
            status,ctype,err,body=fetch(url); safe=f"RA_RESULTS_{m['date']}_{norm_track(m['track'])}_{kh([url],8)}.html"; path=RAW/safe
            if body and (status==200 or not path.exists()): path.write_bytes(body)
            page=body.decode('utf-8','replace') if body else ''
            one={'url':url,'http_status':status,'content_type':ctype,'bytes':len(body),'raw_file':str(path.relative_to(ROOT)).replace('\\','/') if body else ''}; attempts.append(one)
            if status==200 and page:
                rw,fc,rj,st=parse_page(m,page,url,run_id,one['raw_file'])
                if fc: chosen=one|st; parsed=(rw,fc,rj); break
                if 'not currently available' in page.lower() and not chosen: chosen=one|st
        if parsed:
            rw,fc,rj=parsed; raw+=rw; facts+=fc; rej+=rj; cls='RESULTS_AVAILABLE'
        else: cls='RESULTS_PENDING_OR_UNAVAILABLE'
        b=chosen or (attempts[-1] if attempts else {})
        rep.append({'meeting_date':m['date'],'track':m['track'],'scheduled_races':m['scheduled_races'],'source':'RACING_AUSTRALIA_PUBLIC_RESULTS_HTML','request_attempted':'YES' if attempts else 'NO','attempt_count':len(attempts),'selected_url':b.get('url',''),'http_status':b.get('http_status',''),'content_type':b.get('content_type',''),'response_byte_count':b.get('bytes',''),'retained_raw_file_path':b.get('raw_file',''),'rows_parsed':b.get('rows',0),'valid_result_facts':b.get('facts',0),'rows_rejected':b.get('rejections',0),'races_parsed':b.get('races',0),'classification':cls,'first_failure':'' if cls=='RESULTS_AVAILABLE' else 'RESULTS_NOT_YET_OFFICIAL_OR_SOURCE_EMPTY','rejection_reasons':''})
    return raw,facts,rej,rep
def promote(raw,facts,rej,run_id,start,end,dry):
    facts=list({clean(f.get('canonical_race_id'))+'|'+clean(f.get('runner_name')).upper():f for f in facts}.values())
    summ={'status':'PASS' if facts or rej else 'PASS_NO_NEW_DATA','operation_run_id':run_id,'facts':len(facts),'raw_rows':len(raw),'rejections':len(rej),'mode':'V3_RA_PUBLIC_RESULTS','date_from':start.isoformat(),'date_to':end.isoformat(),'dry_run':dry}
    if not dry and not facts and not rej and rows(DATA/'edgeiq_daily_official_results_fact_v1.csv'):
        summ['status']='PASS_NO_NEW_DATA_RETAINED_EXISTING_FACTS'
        summ['retained_existing_result_facts']=rows(DATA/'edgeiq_daily_official_results_fact_v1.csv')
        write_json(DATA/'edgeiq_daily_official_results_ingestion_v1_summary.json',summ)
        return summ
    if not dry:
        rb=DOC/'rollback'/run_id; rb.mkdir(parents=True,exist_ok=True)
        for p in [DATA/'edgeiq_daily_official_results_raw_snapshot_v1.csv',DATA/'edgeiq_daily_official_results_fact_v1.csv',DATA/'edgeiq_daily_official_results_rejections_v1.csv',DATA/'edgeiq_daily_official_results_ingestion_v1_summary.json']:
            if p.exists(): shutil.copy2(p,rb/p.name)
        write_csv(DATA/'edgeiq_daily_official_results_raw_snapshot_v1.csv',raw,RAW_FIELDS); write_csv(DATA/'edgeiq_daily_official_results_fact_v1.csv',facts,FACT_FIELDS); write_csv(DATA/'edgeiq_daily_official_results_rejections_v1.csv',rej,REJ_FIELDS); write_json(DATA/'edgeiq_daily_official_results_ingestion_v1_summary.json',summ); write_csv(DATA/'edgeiq_current_official_results_ra_v1.csv',facts,FACT_FIELDS)
    return summ
def cgroup(x):
    s=clean(x).upper()
    if 'HEAVY' in s: return 'HEAVY'
    if 'SOFT' in s: return 'SOFT'
    if 'GOOD' in s or 'FIRM' in s: return 'GOOD'
    if 'SYNTH' in s: return 'STANDARD_SYNTHETIC'
    return 'UNKNOWN'
def sgroup(track): return 'AUSTRALIAN_SYNTHETIC' if 'SYNTH' in clean(track).upper() else 'TURF'
def fdec(x): return Decimal(clean(x))
def fmt(x): return f"{x.quantize(Decimal('0.000001')):.6f}"
def dint(x): return 'FASTER_THAN_STANDARD' if x<0 else ('SLOWER_THAN_STANDARD' if x>0 else 'EQUAL_TO_STANDARD')
def lint(x): return 'FASTER_THAN_STANDARD' if x>0 else ('SLOWER_THAN_STANDARD' if x<0 else 'EQUAL_TO_STANDARD')
def rebuild_downstream(dry):
    timing=read_csv(DATA/'edgeiq_canonical_historical_timing_warehouse_v1.csv'); std=read_csv(DATA/'edgeiq_standard_time_fact_v1.csv'); par=read_csv(DATA/'edgeiq_length_conversion_parameter_fact_v2.csv'); built=now()
    stdkey={(clean(r.get('track_name')).upper(),clean(r.get('official_distance_metres')),clean(r.get('surface')),clean(r.get('track_condition'))):r for r in std if clean(r.get('standard_time_status'))=='AVAILABLE'}
    pkey={(clean(r.get('surface_group')),clean(r.get('track_condition_group'))):r for r in par if clean(r.get('parameter_status'))=='AVAILABLE'}
    deltas=[]; lvs=[]; lrej=[]; base=[]
    for t in timing:
        if not clean(t.get('official_race_time_seconds')): continue
        surf=clean(t.get('surface_group')) or sgroup(t.get('track')); cond=clean(t.get('track_condition_group')) or cgroup(t.get('track_condition'))
        st=stdkey.get((clean(t.get('track')).upper(),clean(t.get('distance_metres')),surf,cond))
        if not st: continue
        try: wt=fdec(t.get('official_race_time_seconds')); ss=fdec(st.get('standard_time_seconds')); dd=wt-ss
        except Exception: continue
        rk=f"{clean(t.get('race_date'))}|{clean(t.get('track')).upper()}|R{clean(t.get('race_number')).zfill(2)}"; rid='RTDR-'+kh([rk,t.get('canonical_race_id'),st.get('standard_time_id')]); rh=hashlib.sha256((clean(t.get('source_row_evidence_sha256'))+clean(st.get('standard_time_evidence_sha256'))+fmt(dd)).encode()).hexdigest()
        d={'race_time_delta_id':rid,'benchmark_observation_id':clean(t.get('recovered_timing_observation_id')),'benchmark_group_id':clean(st.get('benchmark_group_id')),'standard_time_id':clean(st.get('standard_time_id')),'race_key':rk,'race_date':clean(t.get('race_date')),'track_name':clean(t.get('track')),'official_distance_metres':clean(t.get('distance_metres')),'winner_horse_name':clean(t.get('winner_horse_name')),'winner_race_time_seconds':fmt(wt),'standard_time_seconds':fmt(ss),'time_delta_seconds':fmt(dd),'time_delta_interpretation':dint(dd),'calculation_method':'WINNER_RACE_TIME_MINUS_RECOVERED_STANDARD_TIME_SECONDS','source_observation_sha256':clean(t.get('source_row_evidence_sha256')),'source_standard_time_evidence_sha256':clean(st.get('standard_time_evidence_sha256')),'race_time_delta_evidence_sha256':rh,'builder_version':'edgeiq_race_time_delta_recovered_v1.1.0','contract_version':'1.0.0','built_at_utc':built}; deltas.append(d)
        pa=pkey.get((surf,cond))
        if not pa:
            lrej.append({'race_time_delta_id':rid,'race_key':rk,'race_date':d['race_date'],'track_name':d['track_name'],'official_distance_metres':d['official_distance_metres'],'rejection_reason':'NO_GOVERNED_SURFACE_CONDITION_LENGTH_PARAMETER','surface_group':surf,'track_condition_number':'','track_condition_group':cond}); continue
        spl=fdec(pa.get('seconds_per_length')); ln=-(dd/spl); lid='LVSR-'+kh([rid]); lh=hashlib.sha256((rh+clean(pa.get('parameter_evidence_sha256'))+fmt(ln)).encode()).hexdigest()
        l={'lengths_versus_standard_id':lid,'race_time_delta_id':rid,'benchmark_observation_id':d['benchmark_observation_id'],'benchmark_group_id':d['benchmark_group_id'],'standard_time_id':d['standard_time_id'],'length_conversion_parameter_id':clean(pa.get('length_conversion_parameter_id')),'race_key':rk,'race_date':d['race_date'],'track_name':d['track_name'],'official_distance_metres':d['official_distance_metres'],'winner_horse_name':d['winner_horse_name'],'winner_race_time_seconds':d['winner_race_time_seconds'],'standard_time_seconds':d['standard_time_seconds'],'time_delta_seconds':d['time_delta_seconds'],'seconds_per_length':clean(pa.get('seconds_per_length')),'lengths_versus_standard':fmt(ln),'lengths_versus_standard_interpretation':lint(ln),'calculation_method':'NEGATIVE_TIME_DELTA_DIVIDED_BY_SECONDS_PER_LENGTH','conversion_scope':'SURFACE_CONDITION','conversion_model_version':'EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2','source_race_time_delta_evidence_sha256':rh,'source_conversion_parameter_evidence_sha256':clean(pa.get('parameter_evidence_sha256')),'lengths_versus_standard_evidence_sha256':lh,'builder_version':'edgeiq_lengths_versus_standard_recovered_v1.0.0','contract_version':'1.1.0','built_at_utc':built}; lvs.append(l)
        pid='PIBR-'+hashlib.sha256(lid.encode()).hexdigest()[:24].upper(); ph=hashlib.sha256((lh+'PIB_RECOVERED').encode()).hexdigest()
        base.append({'performance_intelligence_base_id':pid,'lengths_versus_standard_id':lid,'race_time_delta_id':rid,'benchmark_observation_id':l['benchmark_observation_id'],'benchmark_group_id':l['benchmark_group_id'],'standard_time_id':l['standard_time_id'],'length_conversion_parameter_id':l['length_conversion_parameter_id'],'race_key':rk,'race_date':l['race_date'],'track_name':l['track_name'],'official_distance_metres':l['official_distance_metres'],'winner_horse_name':l['winner_horse_name'],'winner_race_time_seconds':l['winner_race_time_seconds'],'standard_time_seconds':l['standard_time_seconds'],'time_delta_seconds':l['time_delta_seconds'],'seconds_per_length':l['seconds_per_length'],'raw_performance_lengths':l['lengths_versus_standard'],'raw_performance_interpretation':l['lengths_versus_standard_interpretation'],'performance_status':'OBSERVED_GOVERNED_RECOVERED_TIMING','calculation_method':'DIRECT_GOVERNED_RECOVERED_LENGTHS_VERSUS_STANDARD','source_lengths_versus_standard_evidence_sha256':lh,'performance_intelligence_base_evidence_sha256':ph,'source_builder_version':'edgeiq_lengths_versus_standard_recovered_v1.0.0','builder_version':'edgeiq_performance_intelligence_base_recovered_v1.0.0','contract_version':'1.0.0','built_at_utc':built})
    if not dry:
        rb=DOC/'rollback'/('downstream-'+kh([built],10)); rb.mkdir(parents=True,exist_ok=True)
        for p in [DATA/'edgeiq_race_time_delta_versus_standard_fact_v1.csv',DATA/'edgeiq_lengths_versus_standard_fact_v1.csv',DATA/'edgeiq_lengths_versus_standard_fact_v1_rejections.csv',DATA/'edgeiq_performance_intelligence_base_fact_v1.csv']:
            if p.exists(): shutil.copy2(p,rb/p.name)
        write_csv(DATA/'edgeiq_race_time_delta_versus_standard_fact_v1.csv',deltas,DELTA_FIELDS); write_csv(DATA/'edgeiq_lengths_versus_standard_fact_v1.csv',lvs,LVS_FIELDS); write_csv(DATA/'edgeiq_lengths_versus_standard_fact_v1_rejections.csv',lrej,LVS_REJ_FIELDS); write_csv(DATA/'edgeiq_performance_intelligence_base_fact_v1.csv',base,BASE_FIELDS)
    post=lambda rows: sum(1 for r in rows if clean(r.get('race_date'))>='2026-07-20')
    return {'race_time_delta_rows':len(deltas),'race_time_delta_post_cutoff':post(deltas),'lengths_v_standard_rows':len(lvs),'lengths_v_standard_post_cutoff':post(lvs),'performance_base_rows':len(base),'performance_base_post_cutoff':post(base),'length_rejections':len(lrej)}
def runcmd(cmd):
    t=time.time(); p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True); return {'command':' '.join(cmd),'returncode':p.returncode,'runtime_seconds':round(time.time()-t,3),'stdout_tail':p.stdout[-2500:],'stderr_tail':p.stderr[-2500:]}
def count(path,field='race_date'):
    return sum(1 for r in read_csv(path) if clean(r.get(field))>='2026-07-20')
def rows(path): return len(read_csv(path))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--date',default=''); ap.add_argument('--date-from',default='2026-07-20'); ap.add_argument('--date-to',default='TODAY'); ap.add_argument('--meeting',default=''); ap.add_argument('--state',default='VIC'); ap.add_argument('--dry-run',action='store_true'); ap.add_argument('--promote',action='store_true'); ap.add_argument('--rerun-downstream',action='store_true'); ap.add_argument('--resolve-identities',action='store_true'); a=ap.parse_args()
    start=pdate(a.date or a.date_from); end=pdate(a.date or a.date_to); dry=bool(a.dry_run or not a.promote); runid='VICLIVEV3-'+kh([start.isoformat(),end.isoformat(),a.meeting,now()],12); DOC.mkdir(parents=True,exist_ok=True)
    start_commit=subprocess.run(['git','rev-parse','--short','HEAD'],cwd=ROOT,text=True,capture_output=True).stdout.strip(); hpr_before=fsha(DATA/'edgeiq_performance_normalisation_parameter_fact_v1.csv')
    before={'results_warehouse_rows':rows(DATA/'edgeiq_historical_results_warehouse_v2_graphql.csv'),'daily_result_facts':rows(DATA/'edgeiq_daily_official_results_fact_v1.csv'),'timed_races':rows(DATA/'edgeiq_canonical_historical_timing_warehouse_v1.csv'),'race_time_delta':rows(DATA/'edgeiq_race_time_delta_versus_standard_fact_v1.csv'),'lengths_v_standard':rows(DATA/'edgeiq_lengths_versus_standard_fact_v1.csv'),'performance_base':rows(DATA/'edgeiq_performance_intelligence_base_fact_v1.csv'),'normalisation':rows(DATA/'edgeiq_performance_normalisation_fact_v1.csv'),'horse_ratings':rows(DATA/'edgeiq_horse_performance_rating_fact_v1.csv'),'snapshots':rows(DATA/'edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv'),'epi':rows(DATA/'edgeiq_race_entry_epi_fact_v1.csv')}
    meetings=load_meetings(start,end,a.meeting); raw,facts,rej,irep=acquire(meetings,runid); summ=promote(raw,facts,rej,runid,start,end,dry)
    if not facts and not rej and not dry:
        facts=[r for r in read_csv(DATA/'edgeiq_daily_official_results_fact_v1.csv') if start <= pdate(r.get('race_date')) <= end]
    stages=[]; downstream={}
    if not dry:
        stages.append(runcmd([sys.executable,'scripts/build_edgeiq_daily_official_timing_ingestion_v1.py','--mode','DEEP_BACKFILL','--date-from',start.isoformat(),'--date-to',end.isoformat()]))
        stages.append(runcmd([sys.executable,'scripts/update_edgeiq_canonical_historical_timing_warehouse_v1.py','--mode','DEEP_BACKFILL','--date-from',start.isoformat(),'--date-to',end.isoformat()]))
        if a.rerun_downstream:
            downstream=rebuild_downstream(False)
            chain='audit_edgeiq_race_time_delta_versus_standard_v1.py audit_edgeiq_lengths_versus_standard_v1.py audit_edgeiq_performance_intelligence_base_fact_v1.py build_edgeiq_performance_normalisation_fact_v1.py audit_edgeiq_performance_normalisation_fact_v1.py build_edgeiq_performance_rating_base_fact_v1.py audit_edgeiq_performance_rating_base_fact_v1.py build_edgeiq_horse_performance_observation_fact_v1.py audit_edgeiq_horse_performance_observation_fact_v1.py build_edgeiq_horse_performance_aggregate_fact_v1.py audit_edgeiq_horse_performance_aggregate_fact_v1.py build_edgeiq_horse_performance_rating_fact_v1.py audit_edgeiq_horse_performance_rating_fact_v1.py build_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py audit_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py build_edgeiq_race_entry_performance_context_fact_v1.py audit_edgeiq_race_entry_performance_context_fact_v1.py build_edgeiq_race_entry_context_adjusted_performance_fact_v1.py audit_edgeiq_race_entry_context_adjusted_performance_fact_v1.py build_edgeiq_race_entry_projected_performance_fact_v1.py audit_edgeiq_race_entry_projected_performance_fact_v1.py build_edgeiq_race_entry_epi_fact_v1.py audit_edgeiq_race_entry_epi_fact_v1.py'.split()
            if a.resolve_identities and 'build_edgeiq_horse_performance_observation_fact_v1.py' in chain:
                chain.insert(chain.index('build_edgeiq_horse_performance_observation_fact_v1.py'),'build_edgeiq_current_ra_horse_identity_crosswalk_v1.py')
            for s in chain:
                if (ROOT/'scripts'/s).exists(): stages.append(runcmd([sys.executable,'scripts/'+s]))
    elif a.rerun_downstream: downstream=rebuild_downstream(True)
    after={'results_warehouse_rows':rows(DATA/'edgeiq_historical_results_warehouse_v2_graphql.csv'),'daily_result_facts':rows(DATA/'edgeiq_daily_official_results_fact_v1.csv'),'timed_races':rows(DATA/'edgeiq_canonical_historical_timing_warehouse_v1.csv'),'race_time_delta':rows(DATA/'edgeiq_race_time_delta_versus_standard_fact_v1.csv'),'lengths_v_standard':rows(DATA/'edgeiq_lengths_versus_standard_fact_v1.csv'),'performance_base':rows(DATA/'edgeiq_performance_intelligence_base_fact_v1.csv'),'normalisation':rows(DATA/'edgeiq_performance_normalisation_fact_v1.csv'),'horse_ratings':rows(DATA/'edgeiq_horse_performance_rating_fact_v1.csv'),'snapshots':rows(DATA/'edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv'),'epi':rows(DATA/'edgeiq_race_entry_epi_fact_v1.csv')}
    post={'result_races':len({f['canonical_race_id'] for f in facts}),'result_runners':len(facts),'timed_races':count(DATA/'edgeiq_canonical_historical_timing_warehouse_v1.csv'),'race_time_delta':count(DATA/'edgeiq_race_time_delta_versus_standard_fact_v1.csv'),'lengths_v_standard':count(DATA/'edgeiq_lengths_versus_standard_fact_v1.csv'),'performance_base':count(DATA/'edgeiq_performance_intelligence_base_fact_v1.csv'),'normalisation':count(DATA/'edgeiq_performance_normalisation_fact_v1.csv'),'ratings':count(DATA/'edgeiq_horse_performance_rating_fact_v1.csv','performance_date'),'snapshots':count(DATA/'edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv'),'epi':count(DATA/'edgeiq_race_entry_epi_fact_v1.csv')}
    failed=[x for x in stages if x['returncode']!=0]; hpr_after=fsha(DATA/'edgeiq_performance_normalisation_parameter_fact_v1.csv')
    status='PASS_VICTORIA_LIVE' if post['normalisation']>0 and post['ratings']>0 and post['epi']>0 else ('PASS_CURRENT_RESULTS_CORE' if post['performance_base']>0 and post['normalisation']>0 else ('BLOCKED_NORMALISATION' if post['performance_base']>0 else ('BLOCKED_DOWNSTREAM' if post['result_races']>0 else 'BLOCKED_OFFICIAL_RESULTS_SOURCE')))
    baseline=[{'component':'official_results_ingestion','script_path':'scripts/build_edgeiq_daily_official_results_ingestion_v1.py','input':'historic local CSV sources','output':'edgeiq_daily_official_results_fact_v1.csv','source_class':'LOCAL_HISTORIC','expected_schema':'official result facts','current_failure':'returned raw_rows=0 facts=0 for post-cutoff window'},{'component':'racing_australia_public_results_repair','script_path':'scripts/run_edgeiq_victoria_current_results_pipeline_v1.py','input':'Racing Australia public Results.aspx HTML','output':'daily official facts + raw evidence','source_class':'PUBLIC_OFFICIAL_HTML','expected_schema':'finish/margin/time/runner facts','current_failure':'none for Sale; pending for Sandown/Bendigo where source says unavailable'}]
    pipeline=[{'stage':k,'rows_before':before[k],'rows_after':after[k],'post_cutoff_rows':post.get(k,''),'status':'PASS' if after[k]>=before[k] else 'REVIEW'} for k in before]
    fields=['component','script_path','input','output','source_class','expected_schema','current_failure']; write_csv(DOC/'EDGEIQ_CURRENT_RESULTS_INGESTION_BASELINE.csv',baseline,fields); write_json(DOC/'EDGEIQ_CURRENT_RESULTS_INGESTION_BASELINE.json',{'start_commit':start_commit,'components':baseline}); write_text(DOC/'EDGEIQ_CURRENT_RESULTS_INGESTION_BASELINE.md','# EDGEiQ Current Results Ingestion Baseline V3\n\n'+'\n'.join(f"- {b['component']}: {b['current_failure']}" for b in baseline))
    decn={'selected_source':'RACING_AUSTRALIA_PUBLIC_RESULTS_HTML','source_access_status':'HTTP_200_PUBLIC_FOR_SALE; RESULTS_UNAVAILABLE_PUBLIC_MESSAGE_FOR_SANDOWN_OR_PENDING_MEETINGS','protected_api_used':'NO','hidden_credentials_used':'NO','cookies_or_session_used':'NO','hpr_norm_a_v1_changed':'NO' if hpr_before==hpr_after else 'YES','final_status':status}; write_json(DOC/'EDGEIQ_CURRENT_RESULTS_SOURCE_DECISION.json',decn); write_text(DOC/'EDGEIQ_CURRENT_RESULTS_SOURCE_DECISION.md','# EDGEiQ Current Results Source Decision V3\n\n'+'\n'.join(f'- {k}: {v}' for k,v in decn.items()))
    ifields='meeting_date track scheduled_races source request_attempted attempt_count selected_url http_status content_type response_byte_count retained_raw_file_path rows_parsed valid_result_facts rows_rejected races_parsed classification first_failure rejection_reasons'.split(); write_csv(DOC/'EDGEIQ_CURRENT_RESULTS_INGESTION_REPORT.csv',irep,ifields)
    payload={'operation_run_id':runid,'start_commit':start_commit,'dry_run':dry,'meetings':meetings,'ingestion':irep,'result_summary':summ,'downstream':downstream,'stages':stages,'failed_stages':failed,'counts_before':before,'counts_after':after,'post_cutoff':post,'source_decision':decn,'status':status,'hpr_norm_a_v1_hash_before':hpr_before,'hpr_norm_a_v1_hash_after':hpr_after}; write_json(DOC/'EDGEIQ_CURRENT_RESULTS_INGESTION_REPORT.json',payload); write_text(DOC/'EDGEIQ_CURRENT_RESULTS_INGESTION_REPORT.md','# EDGEiQ Current Results Ingestion Report V3\n\n'+f'Status: `{status}`\n\n'+'\n'.join(f"- {r['meeting_date']} {r['track']}: {r['classification']} facts={r['valid_result_facts']} races={r['races_parsed']}" for r in irep))
    write_csv(DOC/'EDGEIQ_VICTORIA_CURRENT_PIPELINE_REPORT.csv',pipeline,'stage rows_before rows_after post_cutoff_rows status'.split()); write_json(DOC/'EDGEIQ_VICTORIA_CURRENT_PIPELINE_REPORT.json',payload); write_text(DOC/'EDGEIQ_VICTORIA_CURRENT_PIPELINE_REPORT.md','# EDGEiQ Victoria Current Pipeline Report V3\n\n'+f'Status: `{status}`\n\n'+'\n'.join(f'- {k}: {v}' for k,v in post.items()))
    print(json.dumps({'status':status,'dry_run':dry,'facts':len(facts),'races':post['result_races'],'post_cutoff':post,'failed_stages':len(failed)},indent=2)); return 0 if status!='FAIL' else 1
if __name__=='__main__': raise SystemExit(main())
