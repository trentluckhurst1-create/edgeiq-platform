from pathlib import Path
import re
import shutil

root = Path(r'C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM')
path = root / 'scripts' / 'audit_edgeiq_race_entry_suitability_component_fact_v1.py'
checkpoint = root / 'docs' / 'victoria-performance-intelligence-race-context-authority-v1' / 'checkpoints' / 'audit_edgeiq_race_entry_suitability_component_fact_v1_PRE_CURRENT_COMPONENT_AUDIT_ALIGNMENT.py'
checkpoint.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(path, checkpoint)
text = path.read_text(encoding='utf-8')
pattern = re.compile(r'''    check\(\n        "current_population_expected",\n        \(\n            len\(adjusted_rows\) == 0\n            and len\(adjustment_rows\) == 0\n            and len\(fact_rows\) == 0\n            and unavailable_rows == 0\n            and ineligible_rows == 0\n        \),\n        \{\n            "context_adjusted_performance_rows": \(\n                len\(adjusted_rows\)\n            \),\n            "context_adjustment_rows": \(\n                len\(adjustment_rows\)\n            \),\n            "eligible_adjusted_performance_rows": \(\n                len\(eligible_adjusted_ids\)\n            \),\n            "parameter_not_available_rows": \(\n                unavailable_rows\n            \),\n            "context_ineligible_rows": \(\n                ineligible_rows\n            \),\n            "suitability_component_rows": \(\n                len\(fact_rows\)\n            \),\n        \},\n    \)\n''')
replacement = '''    check(\n        "current_population_expected",\n        len(fact_rows) == expected_component_rows,\n        {\n            "context_adjusted_performance_rows": (\n                len(adjusted_rows)\n            ),\n            "context_adjustment_rows": (\n                len(adjustment_rows)\n            ),\n            "eligible_adjusted_performance_rows": (\n                len(eligible_adjusted_ids)\n            ),\n            "expected_component_rows": (\n                expected_component_rows\n            ),\n            "parameter_not_available_rows": (\n                unavailable_rows\n            ),\n            "context_ineligible_rows": (\n                ineligible_rows\n            ),\n            "suitability_component_rows": (\n                len(fact_rows)\n            ),\n        },\n    )\n'''
text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise SystemExit(f'current population block replace count={count}')
text = text.replace('"audit_version": "1.0.0",', '"audit_version": "1.1.0_current_ineligible_context_allowed",')
path.write_text(text, encoding='utf-8')
print('patched', path)
print('checkpoint', checkpoint)
