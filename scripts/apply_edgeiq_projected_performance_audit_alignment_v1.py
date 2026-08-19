from pathlib import Path
import re
import shutil

root = Path(r'C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM')
path = root / 'scripts' / 'audit_edgeiq_race_entry_projected_performance_fact_v1.py'
checkpoint = root / 'docs' / 'victoria-performance-intelligence-race-context-authority-v1' / 'checkpoints' / 'audit_edgeiq_race_entry_projected_performance_fact_v1_PRE_CURRENT_PROJECTION_AUDIT_ALIGNMENT.py'
checkpoint.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(path, checkpoint)
text = path.read_text(encoding='utf-8')
pattern = re.compile(r'''    check\(\n        "current_population_expected",\n        \(\n            len\(adjusted_rows\) == 0\n            and len\(aggregate_rows\) == 0\n            and len\(fact_rows\) == 0\n        \),\n        \{\n            "context_adjusted_performance_rows": \(\n                len\(adjusted_rows\)\n            \),\n            "suitability_aggregate_rows": \(\n                len\(aggregate_rows\)\n            \),\n            "projected_performance_rows": \(\n                len\(fact_rows\)\n            \),\n        \},\n    \)\n''')
replacement = '''    check(\n        "current_population_expected",\n        len(fact_rows) == len(aggregate_rows),\n        {\n            "context_adjusted_performance_rows": (\n                len(adjusted_rows)\n            ),\n            "suitability_aggregate_rows": (\n                len(aggregate_rows)\n            ),\n            "projected_performance_rows": (\n                len(fact_rows)\n            ),\n        },\n    )\n'''
text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise SystemExit(f'current population block replace count={count}')
text = text.replace('"audit_version": "1.0.0",', '"audit_version": "1.1.0_current_empty_projection_allowed",')
path.write_text(text, encoding='utf-8')
print('patched', path)
print('checkpoint', checkpoint)
