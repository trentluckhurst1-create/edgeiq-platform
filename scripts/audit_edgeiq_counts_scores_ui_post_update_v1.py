import csv,re
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'; TSX=ROOT/'src'/'components'/'RaceIntelligenceScreen.tsx'; FEED=DATA/'edgeiq_command_enrichment_feed_v2.csv'; LIVE=DATA/'edgeiq_live_runner_board_governed_v1.csv'
out=DATA/'edgeiq_counts_scores_ui_post_update_v1.csv'; sumout=DATA/'edgeiq_counts_scores_ui_post_update_v1_summary.csv'; report=DATA/'edgeiq_counts_scores_ui_post_update_v1_report.txt'
text=TSX.read_text(encoding='utf-8', errors='replace') if TSX.exists() else ''
checks=[]; blockers=[]; review=[]
def add(name, obs, exp, passed, sev='BLOCKER'):
    checks.append({'check':name,'observed':obs,'expected':exp,'passed':'YES' if passed else 'NO','severity':sev})
    if not passed and sev=='BLOCKER': blockers.append(name)
    elif not passed: review.append(name)
add('tsx_exists',str(TSX.exists()),'True',TSX.exists())
add('references_v2_feed',str('edgeiq_command_enrichment_feed_v2.csv' in text),'True','edgeiq_command_enrichment_feed_v2.csv' in text)
for f in ['edgeiq_score_overall_v2','edgeiq_score_distance_v2','edgeiq_score_condition_v2','edgeiq_score_class_v2','edgeiq_score_campaign_v2','edgeiq_score_pace_v2','edgeiq_score_connections_v2','edgeiq_score_market_v2','edgeiq_score_confidence_v2']:
    add(f'references_{f}',str(f in text),'True',f in text)
for f in ['edgeiq_connection_evidence_available_v2','edgeiq_market_evidence_available_v2','edgeiq_hidden_gem_evidence_available_v2']:
    add(f'references_{f}',str(f in text),'True',f in text)
score_block_match=re.search(r'const scoreBreakdownRows[\s\S]{0,2500}?\n\s+: \[\];', text)
score_block=score_block_match.group(0) if score_block_match else ''
add('score_block_no_runner_no_barrier_rank',str(any(x in score_block for x in ['runner_no','barrier','rank','saddlecloth'])),'False',not any(x in score_block for x in ['runner_no','barrier','rank','saddlecloth']))
add('footer_count_logic_v2',str('commandEvidenceAvailable(row.item' in text and 'connectionsCoverageCount' in text and 'marketCoverageCount' in text and 'hiddenGemCoverageCount' in text),'True','commandEvidenceAvailable(row.item' in text and 'connectionsCoverageCount' in text and 'marketCoverageCount' in text and 'hiddenGemCoverageCount' in text)
add('connection_command_v2_logic',str('connectionCommandRows' in text and 'edgeiq_connection_evidence_available_v2' in text),'True','connectionCommandRows' in text and 'edgeiq_connection_evidence_available_v2' in text)
add('market_command_v2_logic',str('marketCommandRows' in text and 'edgeiq_market_evidence_available_v2' in text),'True','marketCommandRows' in text and 'edgeiq_market_evidence_available_v2' in text)
add('score_bar_colour_logic_exists',str('scoreToneValue' in text and 'value >= 80' in text and 'value >= 60' in text),'True','scoreToneValue' in text and 'value >= 80' in text and 'value >= 60' in text)
add('build_not_yet_run_by_audit','NOT_RUN_BY_THIS_AUDIT','NOT_RUN',True,'INFO')
status='BLOCKED' if blockers else ('COUNTS_SCORES_POST_AUDIT_REVIEW_REQUIRED' if review else 'COUNTS_SCORES_POST_AUDIT_PASS')
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'checks_total':len(checks),'blockers':len(blockers),'review_items':len(review),'feed_exists':'YES' if FEED.exists() else 'NO','live_exists':'YES' if LIVE.exists() else 'NO','blocked_reasons':'|'.join(blockers),'review_reasons':'|'.join(review)}]
with out.open('w', newline='', encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=list(checks[0].keys())); w.writeheader(); w.writerows(checks)
with sumout.open('w', newline='', encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=list(summary[0].keys())); w.writeheader(); w.writerows(summary)
report.write_text('\n'.join(['EDGEiQ Counts/Scores UI Post Update Audit V1','='*58,f'Status: {status}',f'Checks: {len(checks)}',f'Blockers: {len(blockers)}',f'Review items: {len(review)}',f'Feed exists: {summary[0]["feed_exists"]}',f'Blocked reasons: {summary[0]["blocked_reasons"] or "None"}'])+'\n', encoding='utf-8')
print(status); print('blockers',len(blockers),'review',len(review))
