from pathlib import Path
import shutil

root = Path(r'C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM')
path = root / 'scripts' / 'audit_edgeiq_race_entry_context_adjustment_fact_v1.py'
checkpoint = root / 'docs' / 'victoria-performance-intelligence-race-context-authority-v1' / 'checkpoints' / 'audit_edgeiq_race_entry_context_adjustment_fact_v1_PRE_CURRENT_ADJUSTMENT_AUDIT_ALIGNMENT.py'
checkpoint.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(path, checkpoint)
text = path.read_text(encoding='utf-8')
old = '''    check(\n        "current_population_expected",\n        len(selection_rows) == 0\n        and len(fact_rows) == 0,\n        {\n            "selection_rows": len(selection_rows),\n            "adjustment_rows": len(fact_rows),\n        },\n    )\n'''
new = '''    check(\n        "current_population_expected",\n        len(fact_rows) == len(selection_rows),\n        {\n            "selection_rows": len(selection_rows),\n            "adjustment_rows": len(fact_rows),\n            "adjustment_applied_rows": applied_rows,\n            "context_ineligible_rows": ineligible_rows,\n        },\n    )\n'''
if old not in text:
    raise SystemExit('current population block not found')
text = text.replace(old, new, 1)
text = text.replace('"audit_version": "1.0.0",', '"audit_version": "1.1.0_current_ineligible_context_allowed",')
path.write_text(text, encoding='utf-8')
print('patched', path)
print('checkpoint', checkpoint)
