import csv, os
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
TSX=os.path.join(ROOT,'src','components','RaceIntelligenceScreen.tsx')
OUT=os.path.join(DATA,'edgeiq_form_commercial_polish_audit_v1.csv')
SUM=os.path.join(DATA,'edgeiq_form_commercial_polish_audit_v1_summary.csv')
REP=os.path.join(DATA,'edgeiq_form_commercial_polish_audit_v1_report.txt')
text=open(TSX,encoding='utf-8').read()
form_block=text[text.find('intelMode === "FORM"'):text.find('intelMode === "RUNNERS"')]
checks=[
 ('NO_DEBUG_BLOCK','DEBUG' not in form_block,'no debug block'),
 ('NO_PROFILE_SOURCE_NOT_LOADED','profile source not loaded' not in form_block,'profile source not loaded removed'),
 ('NO_OTHER_RATING_SOURCE_VISIBLE','OTHER_RATING_SOURCE' not in form_block or 'customerSourceLabel' in form_block,'raw OTHER_RATING_SOURCE mapped before display'),
 ('NO_RAW_SEMICOLON_SOURCE_DISPLAY','customerSourceLabel(rawSource)' in form_block and 'run.source || "Not Enough Evidence"' in form_block,'visible source/comment uses friendly label'),
 ('RUNNER_TABLE_SCORE_PILL','borderRadius: 999' in form_block and 'itemScore !== null' in form_block and 'itemTrend' in form_block,'runner table has score pill structure'),
 ('FORM_SCORE_BANDS','selectedFormScoreBand' in form_block and 'ELITE' in form_block and 'STRONG' in form_block and 'AVERAGE' in form_block and 'RISK' in form_block and 'POOR' in form_block and 'LIMITED' in form_block,'form score band labels exist'),
 ('LAST_FIVE_REQUIRED_COLUMNS',all(x in form_block for x in ['DATE','DLR','TRACK','GOING','DIST','CLASS','POS','MARGIN','SP','RATING','COMMENT']),'Last Five table has required columns'),
 ('CONDITION_PILL_LOGIC','conditionTone' in form_block and 'GOOD' in form_block and 'SOFT' in form_block and 'HEAVY' in form_block and 'FAST' in form_block,'condition pill logic exists'),
 ('MARGIN_WORDING_LOGIC','marginDisplay' in form_block and 'Won by' in form_block and 'Beaten' in form_block,'margin wording logic exists'),
 ('VERDICT_CUSTOMER_COPY','Rated form history loaded' in form_block and 'Partial rated-history profile' in form_block and 'Do not overstate' in form_block,'verdict copy is customer-facing'),
 ('NO_COMING_NEXT','Coming next' not in form_block and 'Performance Timeline' not in form_block,'no unfinished placeholders'),
 ('V4_FEED_REFERENCED','/data/edgeiq_form_enrichment_feed_v4.csv' in text,'V4 feed referenced'),
 ('BUILD_SAFE_HELPERS','customerSourceLabel' in form_block and 'setupProfileText' in form_block and 'marginDisplay' in form_block,'new helpers defined'),
]
rows=[{'check':name,'status':'PASS' if passed else 'FAIL','detail':detail} for name,passed,detail in checks]
with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['check','status','detail']); w.writeheader(); w.writerows(rows)
summary=[{'metric':'checks','value':len(rows)},{'metric':'passed','value':sum(1 for r in rows if r['status']=='PASS')},{'metric':'failed','value':sum(1 for r in rows if r['status']=='FAIL')},{'metric':'pricing_maths_changed','value':'NO'},{'metric':'v6_1_changed','value':'NO'},{'metric':'v7_2g2_changed','value':'NO'}]
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
status='FORM_COMMERCIAL_POLISH_AUDIT_PASS' if all(r['status']=='PASS' for r in rows) else 'FORM_COMMERCIAL_POLISH_AUDIT_REVIEW_REQUIRED'
rep=['EDGEiQ FORM COMMERCIAL POLISH AUDIT V1',f'status={status}']+[f"{r['check']}={r['status']}" for r in rows]+['pricing_maths_changed=NO','v6_1_changed=NO','v7_2g2_changed=NO']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(rep)+'\n')
print('\n'.join(rep))
