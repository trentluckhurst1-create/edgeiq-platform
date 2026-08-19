from __future__ import annotations
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'scripts' / 'run_edgeiq_victoria_performance_intelligence_refresh_v1.py'
CHECKPOINT = ROOT / 'docs' / 'victoria-performance-intelligence-race-context-authority-v1' / 'checkpoints' / 'run_edgeiq_victoria_performance_intelligence_refresh_v1_PRE_RACE_CONTEXT_AUTHORITY.py'
CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
if not CHECKPOINT.exists():
    shutil.copy2(TARGET, CHECKPOINT)
text = TARGET.read_text(encoding='utf-8')
needle = "    ('race_entry_snapshot_audit', 'scripts/audit_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py', True),\n    ('race_entry_context_build', 'scripts/build_edgeiq_race_entry_performance_context_fact_v1.py', True),"
replacement = "    ('race_entry_snapshot_audit', 'scripts/audit_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py', True),\n    ('race_context_authority_build', 'scripts/build_edgeiq_race_context_authority_fact_v1.py', True),\n    ('race_entry_context_build', 'scripts/build_edgeiq_race_entry_performance_context_fact_v1.py', True),"
if needle not in text:
    raise RuntimeError('Refresh step insertion point not found or already changed.')
text = text.replace(needle, replacement)
needle2 = "    'race_entry_snapshot': DATA / 'edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv',\n    'projected_performance': DATA / 'edgeiq_race_entry_projected_performance_fact_v1.csv',"
replacement2 = "    'race_entry_snapshot': DATA / 'edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv',\n    'race_context_authority': DATA / 'edgeiq_race_context_authority_fact_v1.csv',\n    'projected_performance': DATA / 'edgeiq_race_entry_projected_performance_fact_v1.csv',"
if needle2 not in text:
    raise RuntimeError('Refresh row file insertion point not found or already changed.')
text = text.replace(needle2, replacement2)
TARGET.write_text(text, encoding='utf-8')
print('EDGEIQ_REFRESH_RACE_CONTEXT_AUTHORITY_STEP_APPLIED')
print(f'checkpoint={CHECKPOINT}')
print(f'target={TARGET}')
