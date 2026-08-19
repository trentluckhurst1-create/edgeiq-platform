import csv, re
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public/data'
LIVE=DATA/'edgeiq_live_runner_board_v1.csv'; GOV=DATA/'edgeiq_live_runner_board_governed_v1.csv'; MISS=DATA/'edgeiq_governed_board_missing_races_v1.csv'
OUT=DATA/'edgeiq_live_runner_board_governed_v1_RECOVERY_CANDIDATE.csv'; AUD=DATA/'edgeiq_governed_board_recovery_candidate_v1.csv'; SUM=DATA/'edgeiq_governed_board_recovery_candidate_v1_summary.csv'; REPORT=DATA/'edgeiq_governed_board_recovery_candidate_v1_report.txt'
def read(path):
    with path.open('r',newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return r.fieldnames or [], list(r)
def write(path,rows,fields=None):
    if fields is None: fields=list(rows[0].keys())
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n'); w.writeheader(); w.writerows(rows)
def rno(v):
    m=re.search(r'\d+',str(v or '')); return m.group(0) if m else str(v or '').strip()
def rk(r): return (str(r.get('race_date') or r.get('meeting_date') or '').strip(),str(r.get('track','')).strip().upper(),rno(r.get('race_no')))
lcols,live=read(LIVE); gcols,gov=read(GOV); mcols,miss=read(MISS)
missing_keys={(r['race_date'],r['track'].upper(),r['race_no']) for r in miss if r['status']=='MISSING_FROM_GOVERNED'}
append=[r for r in live if rk(r) in missing_keys]
fields=list(gcols)
for c in lcols:
    if c not in fields: fields.append(c)
# Fill controlled metadata as candidate only where absent.
for r in append:
    r.setdefault('edgeiq_v7_2g2_feature_flag','ON')
    r.setdefault('edgeiq_v7_2g2_live_wired_flag','YES_RECOVERY_CANDIDATE_ONLY')
    r.setdefault('edgeiq_v7_2g2_production_changed','NO')
    r.setdefault('edgeiq_recovery_candidate_source','edgeiq_live_runner_board_v1_missing_race_append')
    if 'edgeiq_recovery_candidate_source' not in fields: fields.append('edgeiq_recovery_candidate_source')
candidate=gov+append
write(OUT,candidate,fields)
gov_races={rk(r) for r in gov}; cand_races={rk(r) for r in candidate}; rec_races={rk(r) for r in append}
audit=[{'race_date':k[0],'track':k[1],'race_no':k[2],'recovered_rows':sum(1 for r in append if rk(r)==k),'status':'RECOVERED_IN_CANDIDATE'} for k in sorted(rec_races)]
summary=[{'status':'GOVERNED_BOARD_RECOVERY_CANDIDATE_BUILT','generated_at':datetime.now().isoformat(timespec='seconds'),'rows_before':len(gov),'rows_after':len(candidate),'rows_added':len(append),'races_before':len(gov_races),'races_after':len(cand_races),'recovered_races':len(rec_races),'candidate_file':str(OUT)}]
write(AUD,audit if audit else [{'status':'NO_RECOVERY_ROWS'}]); write(SUM,summary)
REPORT.write_text('\n'.join(['EDGEiQ Governed Board Recovery Candidate V1','='*52,f"Status: {summary[0]['status']}",f"Rows before/after/added: {len(gov)} / {len(candidate)} / {len(append)}",f"Races before/after/recovered: {len(gov_races)} / {len(cand_races)} / {len(rec_races)}",f"Candidate: {OUT}",'','Recovered races:']+[f"- {a['race_date']} {a['track']} R{a['race_no']}: rows={a['recovered_rows']}" for a in audit])+'\n',encoding='utf-8')
print(summary[0]['status']); print('rows',len(gov),len(candidate),'added',len(append),'races',len(gov_races),len(cand_races),'recovered',len(rec_races))
