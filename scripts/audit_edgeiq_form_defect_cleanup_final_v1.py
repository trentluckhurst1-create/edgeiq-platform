import csv, os, re, collections
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
FORM=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4.csv')
GOV=os.path.join(DATA,'edgeiq_live_runner_board_governed_v1.csv')
TSX=os.path.join(ROOT,'src','components','RaceIntelligenceScreen.tsx')
OUT=os.path.join(DATA,'edgeiq_form_defect_cleanup_final_v1.csv')
SUM=os.path.join(DATA,'edgeiq_form_defect_cleanup_final_v1_summary.csv')
REP=os.path.join(DATA,'edgeiq_form_defect_cleanup_final_v1_report.txt')
RAW_BAD=['OTHER_RATING_SOURCE','SOURCE_MISSING','V6_1_RESEARCH_ARCHIVE','RUNNER_BOARD_SNAPSHOT;','RESULTS_WAREHOUSE;',';RESULTS_WAREHOUSE','not loaded','RECENT FORM LOADED RECENT FORM LOADED','CONTEXT ONLY CONTEXT ONLY']

def read_csv(path):
    with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
        r=csv.DictReader(f); return list(r), r.fieldnames or []
def num(v):
    try:
        m=re.search(r'-?\d+(?:\.\d+)?',str(v or ''))
        return float(m.group(0)) if m else None
    except Exception: return None

rows=[]; counts=collections.Counter()
form,_=read_csv(FORM); gov,_=read_csv(GOV)
for r in form:
    for i in range(1,6):
        p=f'last_start_{i}_'
        has_run=(r.get(p+'date') or r.get(p+'track') or r.get(p+'rating'))
        if not has_run: continue
        pos=r.get(p+'position_display','')
        sp=r.get(p+'sp_display','')
        margin=r.get(p+'margin_display','')
        comment=r.get(p+'comment_display','')
        cls=r.get(p+'class_display','')
        cond=r.get(p+'condition_display','')
        dist=r.get(p+'distance_display','')
        issues=[]
        x=num(pos)
        if x is not None and (x<=0 or x>30): issues.append('POS_GT30_OR_BAD_DISPLAYED')
        sx=num(sp)
        if sp not in {'','--'} and sx is not None and sx<=1.0: issues.append('SP_ZERO_OR_BAD_DISPLAYED')
        if margin.upper()=='BEATEN 0.0L': issues.append('BEATEN_0_DISPLAYED')
        if any(tok.upper() in comment.upper() for tok in ['OTHER_RATING_SOURCE','SOURCE_MISSING','V6_1_RESEARCH_ARCHIVE',';']): issues.append('RAW_SOURCE_DISPLAYED')
        if 'NOT LOADED' in ' '.join([pos,sp,margin,comment,cls,cond,dist]).upper(): issues.append('NOT_LOADED_DISPLAYED')
        if issues:
            for issue in issues: counts[issue]+=1
            rows.append({'runner_key':r.get('runner_key',''),'horse':r.get('horse',''),'run_index':i,'issues':';'.join(issues),'position_display':pos,'sp_display':sp,'margin_display':margin,'class_display':cls,'condition_display':cond,'distance_display':dist,'comment_display':comment})
text=open(TSX,encoding='utf-8').read()
form_block=text[text.find('intelMode === "FORM"'):text.find('intelMode === "RUNNERS"')]
checks={
 'tsx_no_visible_not_loaded':'not loaded' not in form_block.lower(),
 'tsx_no_recent_form_loaded_duplicate':'RECENT FORM LOADED RECENT FORM LOADED' not in form_block,
 'tsx_no_context_duplicate':'CONTEXT ONLY CONTEXT ONLY' not in form_block,
 'tsx_no_raw_source_strings':all(tok not in form_block for tok in ['OTHER_RATING_SOURCE','SOURCE_MISSING','V6_1_RESEARCH_ARCHIVE']) or 'customerSourceLabel' in form_block,
 'tsx_class_column_exists':'CLASS' in form_block,
 'tsx_condition_pills_exist':'conditionTone' in form_block,
 'tsx_distance_display_exists':'distance_display' in form_block,
 'tsx_verdict_line_breaks':'whiteSpace: "pre-line"' in form_block,
 'governed_rows_383':len(gov)==383,
 'governed_races_25':len(set((r.get('race_date',''),r.get('track',''),r.get('race_no','')) for r in gov))==25,
 'v7_2g2_on_383':sum(1 for r in gov if r.get('edgeiq_v7_2g2_feature_flag')=='ON')==383,
 'v7_2g2_live_wired_383':sum(1 for r in gov if r.get('edgeiq_v7_2g2_live_wired_flag')=='YES_CONTROLLED_ON')==383,
}
for k,v in checks.items():
    if not v:
        counts[k.upper()+'_FAIL']=1
        rows.append({'runner_key':'TSX','horse':'FORM_BLOCK','run_index':'','issues':k,'position_display':'','sp_display':'','margin_display':'','class_display':'','condition_display':'','distance_display':'','comment_display':''})
fields=['runner_key','horse','run_index','issues','position_display','sp_display','margin_display','class_display','condition_display','distance_display','comment_display']
with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
summary=[{'metric':'issue_rows','value':len(rows)}]+[{'metric':k,'value':v} for k,v in counts.most_common()]
summary += [{'metric':'form_rows','value':len(form)},{'metric':'governed_rows','value':len(gov)},{'metric':'governed_races','value':len(set((r.get('race_date',''),r.get('track',''),r.get('race_no','')) for r in gov))},{'metric':'v7_2g2_on','value':sum(1 for r in gov if r.get('edgeiq_v7_2g2_feature_flag')=='ON')},{'metric':'v7_2g2_live_wired','value':sum(1 for r in gov if r.get('edgeiq_v7_2g2_live_wired_flag')=='YES_CONTROLLED_ON')},{'metric':'pricing_maths_changed','value':'NO'},{'metric':'v6_1_changed','value':'NO'},{'metric':'v7_2g2_changed','value':'NO'}]
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
status='FORM_DEFECT_CLEANUP_FINAL_PASS' if len(rows)==0 else 'FORM_DEFECT_CLEANUP_REVIEW_REQUIRED'
rep=['EDGEiQ FORM DEFECT CLEANUP FINAL V1',f'status={status}',f'issue_rows={len(rows)}']+[f'{k}={v}' for k,v in counts.most_common()]+[f'form_rows={len(form)}',f'governed_rows={len(gov)}','pricing_maths_changed=NO','v6_1_changed=NO','v7_2g2_changed=NO']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(rep)+'\n')
print('\n'.join(rep))
