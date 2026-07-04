import csv, os, re, collections
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
FORM=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4.csv')
OUT=os.path.join(DATA,'edgeiq_form_visible_defects_v1.csv')
SUM=os.path.join(DATA,'edgeiq_form_visible_defects_v1_summary.csv')
REP=os.path.join(DATA,'edgeiq_form_visible_defects_v1_report.txt')
BAD_RAW={'','--','N/A','NA','NULL','NONE','UNKNOWN','NAN','NOT LOADED','NO_CLASS','0.0','0'}
RAW_SOURCE_TOKENS=['OTHER_RATING_SOURCE','SOURCE_MISSING','V6_1_RESEARCH_ARCHIVE','RUNNER_BOARD_SNAPSHOT','REPLAY_ARCHIVE','INTELLIGENCE_SNAPSHOT',';']

def blank(v): return v is None or str(v).strip().upper() in BAD_RAW

def num(v):
    try:
        if blank(v): return None
        m=re.search(r'-?\d+(?:\.\d+)?',str(v))
        return float(m.group(0)) if m else None
    except Exception: return None

rows=[]; counts=collections.Counter()
with open(FORM,newline='',encoding='utf-8-sig',errors='replace') as f:
    reader=csv.DictReader(f)
    for r in reader:
        rk=r.get('runner_key','')
        # runner/status defects
        signal=str(r.get('form_signal','')).strip().upper()
        trend=str(r.get('form_trend','')).strip().upper()
        quality=str(r.get('form_data_quality','')).strip().upper()
        status=str(r.get('form_truth_status','')).strip().upper()
        if signal and trend and signal==trend:
            rows.append({'runner_key':rk,'horse':r.get('horse',''),'run_index':'','field':'form_signal/form_trend','raw_value':signal,'defect_type':'REPEATED_SIGNAL_TREND','action':'MAP_TO_CLEAN_TREND'}); counts['REPEATED_SIGNAL_TREND']+=1
        if status=='CONTEXT_ONLY' and quality=='CONTEXT ONLY' and signal=='CONTEXT ONLY':
            rows.append({'runner_key':rk,'horse':r.get('horse',''),'run_index':'','field':'context_labels','raw_value':'CONTEXT ONLY repeated','defect_type':'CONTEXT_ONLY_DUPLICATED_LABELS','action':'SHOW_ONE_STATUS_LINE'}); counts['CONTEXT_ONLY_DUPLICATED_LABELS']+=1
        for field in ['distance_profile','condition_profile','class_profile','distance_score','condition_score','class_score','score_distance','score_condition','score_class','edgeiq_score_distance_v3','edgeiq_score_condition_v3','edgeiq_score_class_v3']:
            if str(r.get(field,'')).strip() in {'0','0.0'}:
                rows.append({'runner_key':rk,'horse':r.get('horse',''),'run_index':'','field':field,'raw_value':r.get(field,''),'defect_type':'ZERO_SCORE_PROFILE_REVIEW','action':'DISPLAY_NOT_ENOUGH_EVIDENCE_UNLESS_VALID'}); counts['ZERO_SCORE_PROFILE_REVIEW']+=1
        for i in range(1,6):
            p=f'last_start_{i}_'
            has_run=not blank(r.get(p+'date')) or not blank(r.get(p+'track')) or not blank(r.get(p+'rating'))
            if not has_run: continue
            pos=num(r.get(p+'finish') or r.get(p+'finishing_position'))
            sp=num(r.get(p+'sp') or r.get(p+'SP'))
            margin=num(r.get(p+'margin') or r.get(p+'beaten_margin'))
            cls=str(r.get(p+'class','')).strip()
            cond=str(r.get(p+'condition','')).strip()
            dist=str(r.get(p+'distance','')).strip()
            source=str(r.get(p+'source','')+' '+r.get(p+'reason',''))
            if pos is None or pos<=0 or pos>30:
                rows.append({'runner_key':rk,'horse':r.get('horse',''),'run_index':i,'field':p+'finish','raw_value':r.get(p+'finish',''),'defect_type':'BAD_POSITION_SANITISED','action':'DISPLAY_DASH'}); counts['BAD_POSITION_SANITISED']+=1
            if sp is None or sp<=1.0:
                rows.append({'runner_key':rk,'horse':r.get('horse',''),'run_index':i,'field':p+'sp','raw_value':r.get(p+'sp',''),'defect_type':'BAD_SP_SANITISED','action':'DISPLAY_DASH'}); counts['BAD_SP_SANITISED']+=1
            if margin is None:
                rows.append({'runner_key':rk,'horse':r.get('horse',''),'run_index':i,'field':p+'margin','raw_value':r.get(p+'margin',''),'defect_type':'BAD_MARGIN_SANITISED','action':'DISPLAY_DASH'}); counts['BAD_MARGIN_SANITISED']+=1
            elif margin<=0:
                rows.append({'runner_key':rk,'horse':r.get('horse',''),'run_index':i,'field':p+'margin','raw_value':r.get(p+'margin',''),'defect_type':'ZERO_MARGIN_SANITISED','action':'DISPLAY_WON_OR_DASH'}); counts['ZERO_MARGIN_SANITISED']+=1
            if blank(cls):
                rows.append({'runner_key':rk,'horse':r.get('horse',''),'run_index':i,'field':p+'class','raw_value':cls,'defect_type':'CLASS_UNKNOWN_SANITISED','action':'DISPLAY_UNKNOWN_MUTED'}); counts['CLASS_UNKNOWN_SANITISED']+=1
            if blank(cond):
                rows.append({'runner_key':rk,'horse':r.get('horse',''),'run_index':i,'field':p+'condition','raw_value':cond,'defect_type':'CONDITION_UNKNOWN_SANITISED','action':'DISPLAY_UNKNOWN_MUTED'}); counts['CONDITION_UNKNOWN_SANITISED']+=1
            if blank(dist) or num(dist)==0:
                rows.append({'runner_key':rk,'horse':r.get('horse',''),'run_index':i,'field':p+'distance','raw_value':dist,'defect_type':'DISTANCE_UNKNOWN_SANITISED','action':'DISPLAY_DASH'}); counts['DISTANCE_UNKNOWN_SANITISED']+=1
            if any(tok in source.upper() for tok in RAW_SOURCE_TOKENS):
                rows.append({'runner_key':rk,'horse':r.get('horse',''),'run_index':i,'field':p+'source/reason','raw_value':source[:180],'defect_type':'RAW_SOURCE_LABEL_SANITISED','action':'MAP_TO_CUSTOMER_LABEL'}); counts['RAW_SOURCE_LABEL_SANITISED']+=1
            if 'NOT LOADED' in ' '.join([cls,cond,dist,source]).upper():
                rows.append({'runner_key':rk,'horse':r.get('horse',''),'run_index':i,'field':'visible_text','raw_value':'not loaded','defect_type':'RAW_NOT_LOADED_VALUE','action':'REPLACE_WITH_UNKNOWN_OR_NOT_ENOUGH_EVIDENCE'}); counts['RAW_NOT_LOADED_VALUE']+=1

fields=['runner_key','horse','run_index','field','raw_value','defect_type','action']
with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
summary=[{'metric':'defect_rows','value':len(rows)}]+[{'metric':k,'value':v} for k,v in counts.most_common()]+[{'metric':'pricing_maths_changed','value':'NO'},{'metric':'v6_1_changed','value':'NO'},{'metric':'v7_2g2_changed','value':'NO'}]
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
rep=['EDGEiQ FORM VISIBLE DEFECTS AUDIT V1',f'defect_rows={len(rows)}']+[f'{k}={v}' for k,v in counts.most_common()]+['pricing_maths_changed=NO','v6_1_changed=NO','v7_2g2_changed=NO','status=FORM_VISIBLE_DEFECT_AUDIT_COMPLETE']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(rep)+'\n')
print('\n'.join(rep))
