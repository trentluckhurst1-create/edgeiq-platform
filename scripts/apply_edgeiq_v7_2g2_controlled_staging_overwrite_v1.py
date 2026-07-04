from pathlib import Path
from datetime import datetime, timezone
import shutil
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
CHECK=DATA/'checkpoints'
CHECK.mkdir(parents=True,exist_ok=True)
TARGET=DATA/'edgeiq_live_runner_board_governed_v1.csv'
CAND=DATA/'edgeiq_live_runner_board_v7_2g2_staging_candidate.csv'
AUDSUM=DATA/'edgeiq_v7_2g2_staging_candidate_audit_v1_summary.csv'
OUT=DATA/'edgeiq_v7_2g2_controlled_staging_overwrite_v1.csv'
SUM=DATA/'edgeiq_v7_2g2_controlled_staging_overwrite_v1_summary.csv'
REP=DATA/'edgeiq_v7_2g2_controlled_staging_overwrite_v1_report.txt'

def m(path):
    if not path.exists(): return {}
    df=pd.read_csv(path,dtype=str,keep_default_na=False)
    return dict(zip(df['metric'],df['value'])) if {'metric','value'}.issubset(df.columns) else {}
def read(path): return pd.read_csv(path,dtype=str,keep_default_na=False,low_memory=False) if path.exists() else pd.DataFrame()
def vals(df,c): return ','.join(sorted(df[c].fillna('').astype(str).unique())) if c in df.columns and len(df) else ''

status='V7_2G2_CONTROLLED_STAGING_OVERWRITE_BLOCKED'; err=''; backup=''
metrics={}
if m(AUDSUM).get('status')!='V7_2G2_STAGING_CANDIDATE_AUDIT_PASS':
    err='staging audit did not pass'
else:
    ts=datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path=CHECK/f'edgeiq_live_runner_board_governed_v1_IMMEDIATE_BACKUP_BEFORE_V7_2G2_STAGING_{ts}.csv'
    backup=str(backup_path.relative_to(BASE))
    try:
        before=read(TARGET); cand=read(CAND)
        shutil.copy2(TARGET,backup_path)
        shutil.copy2(CAND,TARGET)
        after=read(TARGET)
        ok=len(after)==378 and vals(after,'edgeiq_v7_2g2_feature_flag')=='OFF' and vals(after,'edgeiq_v7_2g2_live_wired_flag')=='NO' and vals(after,'edgeiq_v7_2g2_production_changed')=='NO' and 'edgeiq_v7_2g2_on_preview_display_fair_price' in after.columns and vals(after,'edgeiq_v7_2g2_active_price_source_shadow')=='PRODUCTION_FALLBACK_FEATURE_FLAG_OFF'
        status='V7_2G2_CONTROLLED_STAGING_OVERWRITE_APPLIED_FLAG_OFF' if ok else 'V7_2G2_CONTROLLED_STAGING_OVERWRITE_BLOCKED_ROLLED_BACK'
        if not ok:
            shutil.copy2(backup_path,TARGET)
            after=read(TARGET)
        metrics={'target_file':str(TARGET.relative_to(BASE)),'candidate_file':str(CAND.relative_to(BASE)),'backup_file':backup,'target_rows_before':len(before),'candidate_rows':len(cand),'target_rows_after':len(after),'feature_flag_values_after':vals(after,'edgeiq_v7_2g2_feature_flag'),'live_wired_values_after':vals(after,'edgeiq_v7_2g2_live_wired_flag'),'production_changed_values_after':vals(after,'edgeiq_v7_2g2_production_changed'),'on_preview_present':'YES' if 'edgeiq_v7_2g2_on_preview_display_fair_price' in after.columns else 'NO','active_shadow_fallback':'YES' if vals(after,'edgeiq_v7_2g2_active_price_source_shadow')=='PRODUCTION_FALLBACK_FEATURE_FLAG_OFF' else 'NO','status':status}
    except Exception as exc:
        err=str(exc)
        try:
            if backup_path.exists(): shutil.copy2(backup_path,TARGET)
        except Exception as rex:
            err += '; restore_error=' + str(rex)
if not metrics:
    metrics={'target_file':str(TARGET.relative_to(BASE)),'candidate_file':str(CAND.relative_to(BASE)),'backup_file':backup,'target_rows_before':'','candidate_rows':'','target_rows_after':'','feature_flag_values_after':'','live_wired_values_after':'','production_changed_values_after':'','on_preview_present':'','active_shadow_fallback':'','error':err,'status':status}
pd.DataFrame([metrics]).to_csv(OUT,index=False)
summary={'built_at':datetime.now(timezone.utc).isoformat(),**metrics}
pd.DataFrame([{'metric':k,'value':v} for k,v in summary.items()]).to_csv(SUM,index=False)
report=f'''EDGEiQ V7.2G2 CONTROLLED STAGING OVERWRITE V1

- Status: {metrics['status']}
- Target: {metrics['target_file']}
- Candidate: {metrics['candidate_file']}
- Backup: {metrics['backup_file']}
- Rows before: {metrics['target_rows_before']}
- Rows after: {metrics['target_rows_after']}
- Feature flag after: {metrics['feature_flag_values_after']}
- Live wired after: {metrics['live_wired_values_after']}
- Production changed after: {metrics['production_changed_values_after']}
- ON-preview present: {metrics['on_preview_present']}
- Active shadow fallback: {metrics['active_shadow_fallback']}

This is staging only, not activation. Terminal feed, UI, and build were not touched.
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in summary.items()]).to_string(index=False)); print(report)
