from pathlib import Path
import shutil

root = Path(r'C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM')
path = root / 'scripts' / 'audit_edgeiq_race_entry_context_parameter_selection_fact_v1.py'
checkpoint = root / 'docs' / 'victoria-performance-intelligence-race-context-authority-v1' / 'checkpoints' / 'audit_edgeiq_race_entry_context_parameter_selection_fact_v1_PRE_CURRENT_SELECTION_AUDIT_ALIGNMENT.py'
checkpoint.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(path, checkpoint)
text = path.read_text(encoding='utf-8')
old = '''        check(\n            "parameter_registry_required_when_eligibility_rows_exist",\n            parameter_exists,\n            parameter_exists,\n        )\n'''
new = '''        eligible_context_rows = [\n            row\n            for row in eligibility_rows\n            if text(row.get("complete_context_eligibility")) == "ELIGIBLE"\n        ]\n\n        check(\n            "parameter_registry_required_when_eligible_context_rows_exist",\n            parameter_exists or not eligible_context_rows,\n            {\n                "parameter_registry_exists": parameter_exists,\n                "eligible_context_rows": len(eligible_context_rows),\n            },\n        )\n'''
if old not in text:
    raise SystemExit('parameter registry audit block not found')
text = text.replace(old, new, 1)
old = '''    check(\n        "current_population_expected",\n        len(eligibility_rows) == 0\n        and len(fact_rows) == 0,\n        {\n            "eligibility_rows": len(eligibility_rows),\n            "selection_rows": len(fact_rows),\n        },\n    )\n'''
new = '''    check(\n        "current_population_expected",\n        len(fact_rows) == len(eligibility_rows),\n        {\n            "eligibility_rows": len(eligibility_rows),\n            "selection_rows": len(fact_rows),\n            "parameter_selected_rows": selected_rows,\n            "context_ineligible_rows": ineligible_rows,\n        },\n    )\n'''
if old not in text:
    raise SystemExit('current population audit block not found')
text = text.replace(old, new, 1)
text = text.replace('"audit_version": "1.0.0",', '"audit_version": "1.1.0_all_ineligible_context_allowed",')
path.write_text(text, encoding='utf-8')
print('patched', path)
print('checkpoint', checkpoint)
