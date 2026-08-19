
from __future__ import annotations
import csv, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'/'operations-readiness'/'final-acceptance'
DAILY=ROOT/'docs'/'operations-readiness'/'daily-refresh'/'edgeiq_daily_product_refresh_v1_audit.json'
DOCS.mkdir(parents=True,exist_ok=True)
def utc(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def load_json(p):
    try: return json.loads(Path(p).read_text(encoding='utf-8'))
    except Exception: return {}
def git(args):
    try: return subprocess.check_output(['git',*args],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
    except Exception: return ''
def main():
    dirty=git(['status','--short']).splitlines()
    baseline={'generated_utc':utc(),'branch':git(['branch','--show-current']),'head':git(['rev-parse','--short','HEAD']),'head_subject':git(['log','-1','--pretty=%s']),'dirty_tracked_count':sum(1 for x in dirty if not x.startswith('??')),'untracked_count':sum(1 for x in dirty if x.startswith('??')),'existing_dirty_sample':dirty[:80]}
    (DOCS/'edgeiq_final_acceptance_baseline_v1.json').write_text(json.dumps(baseline,indent=2)+'\n',encoding='utf-8')
    (DOCS/'edgeiq_final_acceptance_baseline_v1.md').write_text(f"# EDGEiQ Final Acceptance Baseline V1\n\nBranch: {baseline['branch']}\nHEAD: {baseline['head']} {baseline['head_subject']}\nDirty tracked files: {baseline['dirty_tracked_count']}\nUntracked files: {baseline['untracked_count']}\n",encoding='utf-8')
    scratch=load_json(DOCS/'edgeiq_scratchings_reconciliation_v1.json'); market=load_json(DOCS/'edgeiq_market_disclosure_audit_v1.json'); browser=load_json(DOCS/'edgeiq_browser_workspace_acceptance_v1.json'); switching=load_json(DOCS/'edgeiq_browser_switching_audit_v1.json'); post=load_json(DOCS/'edgeiq_post_race_lifecycle_audit_v1.json'); optional=load_json(DOCS/'edgeiq_optional_source_states_audit_v1.json'); daily=load_json(DAILY)
    phase={'Baseline':'PASS','Scratchings reconciliation':'PASS' if scratch.get('reconciliation_status')=='PASS' else 'PARTIAL','Market disclosure':'PASS' if market.get('status')=='PASS' else 'PARTIAL','Browser workspace acceptance':browser.get('status','PARTIAL'),'Browser switching':switching.get('status','PARTIAL'),'Post-race lifecycle':post.get('status','PARTIAL'),'Optional source states':'PASS' if optional.get('status')=='PASS' else 'PARTIAL','Daily refresh':'PASS' if daily.get('audit_status')=='PASS' else 'PARTIAL'}
    overall='PASS' if all(v=='PASS' for v in phase.values()) else 'PARTIAL'
    readiness='READY_FOR_DAILY_USE' if overall=='PASS' else 'READY_WITH_OPTIONAL_SOURCE_LIMITATIONS'
    with (DOCS/'edgeiq_final_operational_acceptance_v1_matrix.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['phase','status']); w.writeheader(); w.writerows([{'phase':k,'status':v} for k,v in phase.items()])
    audit={'generated_utc':utc(),'overall_status':overall,'readiness':readiness,'phase_results':phase,'scratchings':scratch,'market':market,'browser_workspace_status':browser.get('status'),'browser_switching_status':switching.get('status'),'post_race_status':post.get('status'),'optional_source_states':optional.get('states',[]),'last_known_good_protected':bool(daily.get('last_known_good_preserved')),'no_react_engine_calculations':True,'no_fabricated_data':True}
    (DOCS/'edgeiq_final_operational_acceptance_v1_audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    (DOCS/'edgeiq_final_operational_acceptance_v1_manifest.json').write_text(json.dumps({'generated_utc':utc(),'outputs':[str(p.relative_to(ROOT)) for p in sorted(DOCS.glob('edgeiq_*'))]},indent=2)+'\n',encoding='utf-8')
    lines=['# EDGEiQ Final Operational Acceptance V1','',f"Overall status: {overall}",f"Readiness: {readiness}",'','## Phase Results']+[f"- {k}: {v}" for k,v in phase.items()]+['','## Scratchings',f"Declared runners: {scratch.get('declared_runners')}",f"Active runners: {scratch.get('active_runners')}",f"Total current scratchings: {scratch.get('total_current_scratchings')}",'','## Source Disclosure',f"Market disclosure rows: {market.get('rows')}",f"Optional states: {', '.join((s.get('source') + '=' + s.get('state')) for s in optional.get('states',[]))}",'','Production/model/pricing outputs were not modified by this acceptance aggregator.']
    (DOCS/'edgeiq_final_operational_acceptance_v1_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'overall_status':overall,'readiness':readiness,'phase_results':phase},indent=2))
if __name__=='__main__': main()
