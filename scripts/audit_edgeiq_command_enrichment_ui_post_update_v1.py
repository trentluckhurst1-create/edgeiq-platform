import csv, re
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
ts=ROOT/'src'/'components'/'RaceIntelligenceScreen.tsx'; live=DATA/'edgeiq_live_runner_board_governed_v1.csv'; feed=DATA/'edgeiq_command_enrichment_feed_v1.csv'
out=DATA/'edgeiq_command_enrichment_ui_post_update_v1.csv'; sumout=DATA/'edgeiq_command_enrichment_ui_post_update_v1_summary.csv'; report=DATA/'edgeiq_command_enrichment_ui_post_update_v1_report.txt'
text=ts.read_text(encoding='utf-8', errors='replace') if ts.exists() else ''
checks=[]; blockers=[]; review=[]
def add(name, obs, exp, passed, severity='BLOCKER'):
    checks.append({'check':name,'observed':obs,'expected':exp,'passed':'YES' if passed else 'NO','severity':severity,'notes':'' if passed else f'Expected {exp}; observed {obs}'})
    if not passed and severity=='BLOCKER': blockers.append(name)
    if not passed and severity!='BLOCKER': review.append(name)
add('tsx_exists',str(ts.exists()),'True',ts.exists())
add('market_command_text_exists',str('Market Command' in text or 'MARKET COMMAND' in text),'True','Market Command' in text or 'MARKET COMMAND' in text)
add('connection_command_text_exists',str('Connection Command' in text or 'CONNECTION COMMAND' in text),'True','Connection Command' in text or 'CONNECTION COMMAND' in text)
add('edgeiq_score_breakdown_text_exists',str('EDGEiQ Score Breakdown' in text or 'EDGEIQ SCORE BREAKDOWN' in text),'True','EDGEiQ Score Breakdown' in text or 'EDGEIQ SCORE BREAKDOWN' in text)
add('evidence_footer_or_coverage_text_exists',str('factorCoverageTiles' in text and 'Connections' in text and 'Hidden Gem' in text and 'Market' in text),'True','factorCoverageTiles' in text and 'Connections' in text and 'Hidden Gem' in text and 'Market' in text)
for ref in ['edgeiq_connection_evidence_available','edgeiq_market_evidence_available','edgeiq_hidden_gem_evidence_available']:
    add(f'evidence_ref_{ref}',str(ref in text),'True',ref in text)
add('no_fake_success_data_hardcoded',str('378/378' in text or '197/378' in text),'False',not ('378/378' in text or '197/378' in text))
add('v7_2g2_price_refs_intact',str('edgeiq_v7_2g2_active_display_fair_price_shadow' in text),'True','edgeiq_v7_2g2_active_display_fair_price_shadow' in text)
add('fallback_logic_exists',str('No market signal loaded.' in text and 'No connection angle triggered.' in text and 'not loaded' in text),'True','No market signal loaded.' in text and 'No connection angle triggered.' in text and 'not loaded' in text)
add('feed_exists',str(feed.exists()),'True',feed.exists(),'REVIEW')
status='BLOCKED' if blockers else ('COMMAND_ENRICHMENT_UI_POST_AUDIT_REVIEW_REQUIRED' if review else 'COMMAND_ENRICHMENT_UI_POST_AUDIT_PASS')
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'checks_total':len(checks),'blockers':len(blockers),'review_items':len(review),'tsx_exists':'YES' if ts.exists() else 'NO','market_command_text_exists':'YES' if 'Market Command' in text or 'MARKET COMMAND' in text else 'NO','connection_command_text_exists':'YES' if 'Connection Command' in text or 'CONNECTION COMMAND' in text else 'NO','score_breakdown_text_exists':'YES' if 'EDGEiQ Score Breakdown' in text or 'EDGEIQ SCORE BREAKDOWN' in text else 'NO','fallback_logic_exists':'YES' if 'No market signal loaded.' in text and 'No connection angle triggered.' in text and 'not loaded' in text else 'NO','blocked_reasons':'|'.join(blockers),'review_reasons':'|'.join(review)}]
with out.open('w', newline='', encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=list(checks[0].keys())); w.writeheader(); w.writerows(checks)
with sumout.open('w', newline='', encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=list(summary[0].keys())); w.writeheader(); w.writerows(summary)
report.write_text('\n'.join(['EDGEiQ Command Enrichment UI Post Update Audit V1','='*62,f'Status: {status}',f'Checks: {len(checks)}',f'Blockers: {len(blockers)}',f'Review items: {len(review)}',f'Market Command: {summary[0]["market_command_text_exists"]}',f'Connection Command: {summary[0]["connection_command_text_exists"]}',f'Score Breakdown: {summary[0]["score_breakdown_text_exists"]}',f'Fallback logic: {summary[0]["fallback_logic_exists"]}',f'Blocked reasons: {summary[0]["blocked_reasons"] or "None"}',f'Review reasons: {summary[0]["review_reasons"] or "None"}'])+'\n', encoding='utf-8')
print(status); print('blockers',len(blockers),'review',len(review))
