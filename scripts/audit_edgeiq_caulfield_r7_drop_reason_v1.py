import csv, re
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public/data'; SCRIPTS=ROOT/'scripts'
OUT=DATA/'edgeiq_caulfield_r7_drop_reason_v1.csv'; SUM=DATA/'edgeiq_caulfield_r7_drop_reason_v1_summary.csv'; REPORT=DATA/'edgeiq_caulfield_r7_drop_reason_v1_report.txt'
FILES=['edgeiq_live_runner_board_v1.csv','edgeiq_live_runner_board_governed_v1.csv','edgeiq_live_runner_board_v7_2g2_flag_on_candidate.csv','edgeiq_command_enrichment_feed_v2.csv','edgeiq_current_intelligence_evidence_fix_candidate_v1.csv','edgeiq_live_runner_board_governed_v1_RACE_SHAPE_RECOVERY_CANDIDATE.csv','edgeiq_live_runner_board_governed_v1_RECOVERY_CANDIDATE.csv','edgeiq_vic_three_day_meeting_universe.csv','edgeiq_live_runner_factor_scorecard_v2.csv','edgeiq_connection_intelligence_v2_1.csv']
def read(path):
    if not path.exists(): return [], []
    with path.open('r',newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return r.fieldnames or [], list(r)
def rno(v):
    m=re.search(r'\d+',str(v or '')); return m.group(0) if m else str(v or '').strip()
def is_r7(r): return (str(r.get('race_date') or r.get('meeting_date') or '').strip()=='2026-06-27' and str(r.get('track','')).strip().upper()=='CAULFIELD' and rno(r.get('race_no'))=='7')
rows=[]
for name in FILES:
    cols,data=read(DATA/name)
    matches=[r for r in data if is_r7(r)]
    rows.append({'file_name':'public/data/'+name,'exists':'YES' if (DATA/name).exists() else 'NO','rows':len(data),'race_present':'YES' if matches else 'NO','race_rows':len(matches),'sample_horses':'|'.join([m.get('horse') or m.get('horse_name','') for m in matches[:5]]),'role':'DATA_STAGE'})
# script trace
script_notes=[]
for sp in [SCRIPTS/'build_edgeiq_live_runner_board_governed_v1.py',SCRIPTS/'build_edgeiq_live_runner_board_v7_2g2_flag_on_candidate_v1.py',SCRIPTS/'apply_edgeiq_v7_2g2_controlled_flag_on_overwrite_v1.py']:
    txt=sp.read_text(encoding='utf-8',errors='replace') if sp.exists() else ''
    note=[]
    for pat in ['edgeiq_live_runner_board_v1.csv','edgeiq_live_runner_board_governed_v1.csv','edgeiq_live_runner_board_v7_2g2_flag_on_candidate.csv','EXPECTED_ROWS = 378','write_rows(live_path, candidate_rows']:
        if pat in txt: note.append(pat)
    script_notes.append({'file_name':'scripts/'+sp.name,'exists':'YES' if sp.exists() else 'NO','rows':'','race_present':'N/A','race_rows':'','sample_horses':'|'.join(note),'role':'SCRIPT_TRACE'})
rows.extend(script_notes)
# responsible file determination
live=next(r for r in rows if r['file_name'].endswith('edgeiq_live_runner_board_v1.csv'))
gov=next(r for r in rows if r['file_name'].endswith('edgeiq_live_runner_board_governed_v1.csv'))
cand=next(r for r in rows if r['file_name'].endswith('edgeiq_live_runner_board_v7_2g2_flag_on_candidate.csv'))
if live['race_present']=='YES' and gov['race_present']=='NO' and cand['race_present']=='NO':
    status='DROP_REASON_IDENTIFIED'; reason='Governed board was overwritten from stale V7.2G2 flag-on candidate built from previous governed universe (378 rows / 27 races). Current live runner board later contains Caulfield R7, but governed/candidate/enrichment were not rebuilt from it.'; responsible='scripts/apply_edgeiq_v7_2g2_controlled_flag_on_overwrite_v1.py + public/data/edgeiq_live_runner_board_v7_2g2_flag_on_candidate.csv'
else:
    status='DROP_REASON_NOT_FOUND'; reason='Presence pattern did not isolate a single stale overwrite stage.'; responsible='UNKNOWN'
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'race':'2026-06-27|CAULFIELD|7','race_present_in_live':live['race_present'],'race_present_in_governed':gov['race_present'],'race_present_in_v7_2g2_candidate':cand['race_present'],'race_removed':'YES' if live['race_present']=='YES' and gov['race_present']=='NO' else 'NO','removal_reason':reason,'responsible_file':responsible}]
for p,data in [(OUT,rows),(SUM,summary)]:
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0].keys())); w.writeheader(); w.writerows(data)
report=['EDGEiQ Caulfield R7 Drop Reason Audit V1','='*50,f"Status: {status}",f"Race: {summary[0]['race']}",f"Race present in live board: {live['race_present']} ({live['race_rows']} rows)",f"Race present in governed board: {gov['race_present']} ({gov['race_rows']} rows)",f"Race present in V7.2G2 flag-on candidate: {cand['race_present']} ({cand['race_rows']} rows)",f"Race removed: {summary[0]['race_removed']}",f"Removal reason: {reason}",f"Responsible file: {responsible}",'','Trace:']
for r in rows: report.append(f"- {r['file_name']}: exists={r['exists']} rows={r['rows']} race_present={r['race_present']} race_rows={r['race_rows']} role={r['role']} notes={r['sample_horses']}")
REPORT.write_text('\n'.join(report)+'\n',encoding='utf-8')
print(status); print(reason)
