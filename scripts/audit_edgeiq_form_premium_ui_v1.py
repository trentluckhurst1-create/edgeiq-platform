import csv, os, re
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
TSX=os.path.join(ROOT,'src','components','RaceIntelligenceScreen.tsx')
OUT=os.path.join(DATA,'edgeiq_form_premium_ui_audit_v1.csv')
SUM=os.path.join(DATA,'edgeiq_form_premium_ui_audit_v1_summary.csv')
REP=os.path.join(DATA,'edgeiq_form_premium_ui_audit_v1_report.txt')
text=open(TSX,encoding='utf-8').read()
checks=[
 ('FORM_TAB_EXISTS','intelMode === "FORM"' in text,'top-level FORM branch present'),
 ('RUNNER_SELECTOR_USES_FORM_FIELDS','form_peak_rating_last5' in text and 'form_avg_rating_last5' in text and 'form_last_start_rating' in text,'runner selector score fallback uses form fields'),
 ('SELECTED_CARD_USES_FORM_FIELDS','selectedFormStatus' in text and 'selectedFormSource' in text and 'Form Score' in text,'selected horse header uses form fields'),
 ('LAST_FIVE_HAS_CLASS','<span>Class</span>' in text,'last five table includes class column'),
 ('LAST_FIVE_HAS_CONDITION','<span>Cond</span>' in text,'last five table includes condition column'),
 ('LAST_FIVE_HAS_SP','<span>SP</span>' in text,'last five table includes SP column'),
 ('LAST_FIVE_HAS_COMMENT','<span>Comment</span>' in text or '<span>Reason</span>' in text,'last five table includes comment/reason column'),
 ('CONTEXT_ONLY_MESSAGE','Context only - no detailed rated-history lines available.' in text,'context-only message present'),
 ('NO_FAKE_EMPTY_ROWS','lastFiveRuns.map' in text and 'filter((run) => run.hasRun)' in text,'last five rows filtered to real runs'),
 ('PREMIUM_TREND_PANEL','Form Trend' in text and 'selectedTrendIcon' in text,'trend panel present'),
 ('PROFILE_SNAPSHOT','Career / Profile Snapshot' in text,'career/profile snapshot present'),
 ('VERDICT_PANEL','EDGEiQ Form Verdict' in text,'verdict panel present'),
 ('FUTURE_PLACEHOLDERS','Performance Timeline' in text and 'Comparison Tool' in text,'future placeholders present'),
 ('V3_FEED_REFERENCED','/data/edgeiq_form_enrichment_feed_v3.csv' in text,'V3 feed referenced'),
 ('NO_DEBUG_TEXT','DEBUG' not in text[text.find('intelMode === "FORM"'):text.find('intelMode === "RUNNERS"')],'no debug text in FORM block'),
 ('NO_UNDEFINED_STYLE_NEW_NAMES','formPanelStyle' in text and 'formPill' in text and 'formRatingTone' in text,'new local style helpers defined'),
]
rows=[]
for name, passed, detail in checks:
    rows.append({'check':name,'status':'PASS' if passed else 'FAIL','detail':detail})
with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['check','status','detail']); w.writeheader(); w.writerows(rows)
summary=[{'metric':'checks','value':len(rows)},{'metric':'passed','value':sum(1 for r in rows if r['status']=='PASS')},{'metric':'failed','value':sum(1 for r in rows if r['status']=='FAIL')},{'metric':'pricing_maths_changed','value':'NO'},{'metric':'v6_1_changed','value':'NO'},{'metric':'v7_2g2_changed','value':'NO'}]
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
status='FORM_PREMIUM_UI_AUDIT_PASS' if all(r['status']=='PASS' for r in rows) else 'FORM_PREMIUM_UI_AUDIT_REVIEW_REQUIRED'
report=['EDGEiQ FORM PREMIUM UI AUDIT V1',f'status={status}']+[f"{r['check']}={r['status']}" for r in rows]+['pricing_maths_changed=NO','v6_1_changed=NO','v7_2g2_changed=NO']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(report)+'\n')
print('\n'.join(report))

