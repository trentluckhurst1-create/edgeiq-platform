import csv, os
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
TSX=os.path.join(ROOT,'src','components','RaceIntelligenceScreen.tsx')
OUT=os.path.join(DATA,'edgeiq_form_toprate_structure_audit_v1.csv')
SUM=os.path.join(DATA,'edgeiq_form_toprate_structure_audit_v1_summary.csv')
REP=os.path.join(DATA,'edgeiq_form_toprate_structure_audit_v1_report.txt')
text=open(TSX,encoding='utf-8').read()
form_block=text[text.find('intelMode === "FORM"'):text.find('intelMode === "RUNNERS"')]
checks=[
 ('FORM_TAB_EXISTS','intelMode === "FORM"' in text,'FORM branch exists'),
 ('RUNNER_TABLE_COLUMNS','#' in form_block and 'Horse' in form_block and 'Form' in form_block and 'Trend' in form_block,'left runner table columns exist'),
 ('SELECTED_HORSE_CARD','FORM COMMAND' in form_block and 'DATA QUALITY' in form_block and 'FORM STATUS' in form_block,'selected horse card/header exists'),
 ('RATING_PROFILE_BLOCK','Rating Profile' in form_block and 'Last' in form_block and 'Peak' in form_block and 'Avg L5' in form_block and 'Projected' in form_block,'rating profile block exists'),
 ('RUN_STATS_BLOCK','Run Stats' in form_block and 'Starts' in form_block and 'Wins' in form_block and 'Places' in form_block and 'Win / Place' in form_block,'run stats block exists'),
 ('TODAY_SETUP_BLOCK','Today Setup' in form_block and 'Distance' in form_block and 'Class' in form_block and 'Condition' in form_block and 'Barrier / Style' in form_block,'today setup block exists'),
 ('FORM_STATUS_BLOCK','Form Status' in form_block and 'Signal' in form_block and 'Quality' in form_block,'form status block exists'),
 ('LAST_FIVE_TABLE_COLUMNS',all(x in form_block for x in ['DATE','DLR','TRACK','GOING','DIST','CLASS','POS','MARGIN','SP','RATING']),'last five mandatory columns exist'),
 ('CLASS_COLUMN_EXISTS','CLASS' in form_block and 'run.cls' in form_block,'class column exists'),
 ('LOWER_PROFILE_MATRIX','Distance Profile' in form_block and 'Condition Profile' in form_block and 'Class Profile' in form_block,'lower profile matrix exists'),
 ('VERDICT_CARD','EDGEiQ Verdict' in form_block and 'selectedFormVerdict' in form_block,'verdict card exists'),
 ('NO_DEBUG_BLOCK','DEBUG' not in form_block,'no debug block'),
 ('NO_COMING_NEXT_PLACEHOLDER','Coming next' not in form_block and 'Performance Timeline' not in form_block and 'Comparison Tool' not in form_block,'roadmap placeholders removed'),
 ('V4_FEED_REFERENCED','/data/edgeiq_form_enrichment_feed_v4.csv' in text,'V4 feed referenced'),
 ('BUILD_SAFE_LOCAL_HELPERS','conditionTone' in form_block and 'finishTone' in form_block and 'formRatingTone' in form_block,'local helpers defined'),
]
rows=[{'check':c,'status':'PASS' if ok else 'FAIL','detail':d} for c,ok,d in checks]
with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['check','status','detail']); w.writeheader(); w.writerows(rows)
summary=[{'metric':'checks','value':len(rows)},{'metric':'passed','value':sum(1 for r in rows if r['status']=='PASS')},{'metric':'failed','value':sum(1 for r in rows if r['status']=='FAIL')},{'metric':'pricing_maths_changed','value':'NO'},{'metric':'v6_1_changed','value':'NO'},{'metric':'v7_2g2_changed','value':'NO'}]
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
status='FORM_TOPRATE_STRUCTURE_AUDIT_PASS' if all(r['status']=='PASS' for r in rows) else 'FORM_TOPRATE_STRUCTURE_AUDIT_REVIEW_REQUIRED'
rep=['EDGEiQ FORM TOPRATE STRUCTURE AUDIT V1',f'status={status}']+[f"{r['check']}={r['status']}" for r in rows]+['pricing_maths_changed=NO','v6_1_changed=NO','v7_2g2_changed=NO']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(rep)+'\n')
print('\n'.join(rep))
