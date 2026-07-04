import csv, os, re, collections
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
FORM=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4.csv')
OUT=os.path.join(DATA,'edgeiq_form_remaining_gaps_v1.csv')
SUM=os.path.join(DATA,'edgeiq_form_remaining_gaps_v1_summary.csv')
REP=os.path.join(DATA,'edgeiq_form_remaining_gaps_v1_report.txt')
BAD_RAW={'','--','-','—','N/A','NA','NULL','NONE','UNKNOWN','NAN','NOT LOADED','SOURCE GAP','UNDEFINED','0.0','0'}
VISIBLE_BAD={'UNKNOWN','NOT LOADED','SOURCE GAP','NULL','0.0','NAN','UNDEFINED'}
FIELDS=['position','sp','condition','class','distance','margin','rating','comment']

def bad(v): return str(v or '').strip().upper() in BAD_RAW

def visible_bad(v): return any(tok in str(v or '').upper() for tok in VISIBLE_BAD)

def has_run(r,p): return not bad(r.get(p+'date')) or not bad(r.get(p+'track')) or not bad(r.get(p+'rating'))
rows=[]; counts=collections.Counter(); coverage=collections.Counter(); totals=collections.Counter()
with open(FORM,newline='',encoding='utf-8-sig',errors='replace') as f:
    reader=csv.DictReader(f)
    for r in reader:
        for i in range(1,6):
            p=f'last_start_{i}_'
            if not has_run(r,p): continue
            vals={
                'position':r.get(p+'position_display') or r.get(p+'finish') or r.get(p+'finishing_position'),
                'sp':r.get(p+'sp_display') or r.get(p+'sp') or r.get(p+'SP'),
                'condition':r.get(p+'condition_display') or r.get(p+'condition'),
                'class':r.get(p+'class_display') or r.get(p+'class'),
                'distance':r.get(p+'distance_display') or r.get(p+'distance'),
                'margin':r.get(p+'margin_display') or r.get(p+'margin') or r.get(p+'beaten_margin'),
                'rating':r.get(p+'rating_display') or r.get(p+'rating'),
                'comment':r.get(p+'comment_display') or r.get(p+'source') or r.get(p+'reason'),
            }
            for fld,val in vals.items():
                totals[fld]+=1
                if not bad(val) and not visible_bad(val): coverage[fld]+=1
                else:
                    dtype=f'{fld.upper()}_DISPLAY_GAP'
                    if visible_bad(val): dtype=f'{fld.upper()}_RAW_PLACEHOLDER_VISIBLE'
                    counts[dtype]+=1
                    rows.append({'runner_key':r.get('runner_key',''),'horse':r.get('horse',''),'run_index':i,'field':fld,'raw_display_value':val,'defect_type':dtype,'run_date':r.get(p+'date'),'track':r.get(p+'track')})
            src=' '.join(str(vals.get(k,'')) for k in vals)
            if any(tok in src.upper() for tok in ['OTHER_RATING_SOURCE','SOURCE_MISSING','RUNNER_BOARD_SNAPSHOT;',';RESULTS_WAREHOUSE','V6_1_RESEARCH_ARCHIVE','UNDEFINED','NAN']):
                counts['RAW_BACKEND_TOKEN_VISIBLE']+=1
                rows.append({'runner_key':r.get('runner_key',''),'horse':r.get('horse',''),'run_index':i,'field':'row','raw_display_value':src[:220],'defect_type':'RAW_BACKEND_TOKEN_VISIBLE','run_date':r.get(p+'date'),'track':r.get(p+'track')})
with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['runner_key','horse','run_index','field','raw_display_value','defect_type','run_date','track']); w.writeheader(); w.writerows(rows)
summary=[{'metric':'visible_defect_rows','value':len(rows)}]
for fld in FIELDS:
    summary.append({'metric':f'{fld}_total_run_rows','value':totals[fld]})
    summary.append({'metric':f'{fld}_covered','value':coverage[fld]})
    summary.append({'metric':f'{fld}_coverage_pct','value':f'{coverage[fld]/max(1,totals[fld])*100:.2f}'})
for k,v in counts.most_common(): summary.append({'metric':k,'value':v})
summary += [{'metric':'pricing_maths_changed','value':'NO'},{'metric':'v6_1_changed','value':'NO'},{'metric':'v7_2g2_changed','value':'NO'}]
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
rep=['EDGEiQ FORM REMAINING GAPS AUDIT V1',f'visible_defect_rows={len(rows)}']
for fld in FIELDS: rep.append(f'{fld}_coverage={coverage[fld]}/{totals[fld]} ({coverage[fld]/max(1,totals[fld])*100:.2f}%)')
rep += [f'{k}={v}' for k,v in counts.most_common()]+['pricing_maths_changed=NO','v6_1_changed=NO','v7_2g2_changed=NO','status=FORM_REMAINING_GAPS_AUDIT_COMPLETE']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(rep)+'\n')
print('\n'.join(rep))
