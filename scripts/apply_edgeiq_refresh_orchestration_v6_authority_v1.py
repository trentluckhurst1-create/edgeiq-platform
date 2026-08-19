from pathlib import Path
import shutil

root = Path(r'C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM')
path = root / 'scripts' / 'run_edgeiq_victoria_performance_intelligence_refresh_v1.py'
checkpoint = root / 'docs' / 'victoria-performance-intelligence-race-context-authority-v1' / 'checkpoints' / 'run_edgeiq_victoria_performance_intelligence_refresh_v1_PRE_V6_AUTHORITY_ORCHESTRATION.py'
checkpoint.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(path, checkpoint)
text = path.read_text(encoding='utf-8')
start = text.index('STEPS = [')
end = text.index('\n\nROW_FILES = {', start)
new_steps = '''STEPS = [
    ('normalisation_authority_decision', 'scripts/audit_edgeiq_normalisation_temporal_authority_v1.py', True),
    ('length_conversion_parameter_v2_build', 'scripts/build_edgeiq_length_conversion_parameter_fact_v2.py', True),
    ('length_conversion_parameter_v2_audit', 'scripts/audit_edgeiq_length_conversion_parameter_fact_v2.py', True),
    ('performance_normalisation_parameter_build', 'scripts/build_edgeiq_performance_normalisation_parameter_fact_v1.py', True),
    ('performance_normalisation_parameter_audit', 'scripts/audit_edgeiq_performance_normalisation_parameter_fact_v1.py', True),
    ('timing_warehouse_recovery_side_by_side', 'scripts/build_edgeiq_timing_warehouse_recovery_v1.py', True),
    ('timing_canonical_promotion', 'scripts/promote_edgeiq_timing_warehouse_canonical_v1.py', True),
    ('race_time_delta_audit', 'scripts/audit_edgeiq_race_time_delta_versus_standard_v1.py', True),
    ('lengths_versus_standard_audit', 'scripts/audit_edgeiq_lengths_versus_standard_v1.py', True),
    ('condition_rejection_audit', 'scripts/audit_edgeiq_lengths_standard_condition_rejections_v1.py', True),
    ('performance_base_audit', 'scripts/audit_edgeiq_performance_intelligence_base_fact_v1.py', True),
    ('historical_normalisation_authority_apply', 'scripts/apply_edgeiq_historical_normalisation_authority_v1.py', True),
    ('race_context_authority_build', 'scripts/build_edgeiq_race_context_authority_fact_v1.py', True),
    ('race_entry_context_build', 'scripts/build_edgeiq_race_entry_performance_context_fact_v1.py', True),
    ('race_entry_context_audit', 'scripts/audit_edgeiq_race_entry_performance_context_fact_v1.py', True),
    ('context_eligibility_build', 'scripts/build_edgeiq_race_entry_context_eligibility_fact_v1.py', True),
    ('context_eligibility_audit', 'scripts/audit_edgeiq_race_entry_context_eligibility_fact_v1.py', True),
    ('context_parameter_selection_build', 'scripts/build_edgeiq_race_entry_context_parameter_selection_fact_v1.py', True),
    ('context_parameter_selection_audit', 'scripts/audit_edgeiq_race_entry_context_parameter_selection_fact_v1.py', True),
    ('context_adjustment_build', 'scripts/build_edgeiq_race_entry_context_adjustment_fact_v1.py', True),
    ('context_adjustment_audit', 'scripts/audit_edgeiq_race_entry_context_adjustment_fact_v1.py', True),
    ('context_adjusted_build', 'scripts/build_edgeiq_race_entry_context_adjusted_performance_fact_v1.py', True),
    ('context_adjusted_audit', 'scripts/audit_edgeiq_race_entry_context_adjusted_performance_fact_v1.py', True),
    ('suitability_component_build', 'scripts/build_edgeiq_race_entry_suitability_component_fact_v1.py', True),
    ('suitability_component_audit', 'scripts/audit_edgeiq_race_entry_suitability_component_fact_v1.py', True),
    ('suitability_aggregate_build', 'scripts/build_edgeiq_race_entry_suitability_aggregate_fact_v1.py', True),
    ('suitability_aggregate_audit', 'scripts/audit_edgeiq_race_entry_suitability_aggregate_fact_v1.py', True),
    ('projected_performance_build', 'scripts/build_edgeiq_race_entry_projected_performance_fact_v1.py', True),
    ('projected_performance_audit', 'scripts/audit_edgeiq_race_entry_projected_performance_fact_v1.py', True),
    ('eri_context_build', 'scripts/build_edgeiq_race_entry_eri_context_fact_v1.py', True),
    ('eri_context_audit', 'scripts/audit_edgeiq_race_entry_eri_context_fact_v1.py', True),
    ('epi_component_build', 'scripts/build_edgeiq_race_entry_epi_component_fact_v1.py', True),
    ('epi_component_audit', 'scripts/audit_edgeiq_race_entry_epi_component_fact_v1.py', True),
    ('epi_build', 'scripts/build_edgeiq_race_entry_epi_fact_v1.py', True),
    ('epi_audit', 'scripts/audit_edgeiq_race_entry_epi_fact_v1.py', True),
    ('epi_dependency_audit', 'scripts/audit_edgeiq_epi_performance_dependency_v1.py', False),
]'''
text = text[:start] + new_steps + text[end:]
old_reason = "'normalisation_unavailable_reason': '' if normalisation_available else 'NORMALISATION_PARAMETER_NOT_EFFECTIVE_FOR_PERFORMANCE_DATE',"
new_reason = "'normalisation_unavailable_reason': '' if normalisation_available else 'NO_AUTHORISED_NORMALISATION_ROWS_AFTER_REFRESH',"
text = text.replace(old_reason, new_reason)
# Add row counts for the race-context chain if not already present.
old_row = "    'race_context_authority': DATA / 'edgeiq_race_context_authority_fact_v1.csv',\n    'projected_performance': DATA / 'edgeiq_race_entry_projected_performance_fact_v1.csv',"
new_row = "    'race_context_authority': DATA / 'edgeiq_race_context_authority_fact_v1.csv',\n    'race_entry_context': DATA / 'edgeiq_race_entry_performance_context_fact_v1.csv',\n    'context_eligibility': DATA / 'edgeiq_race_entry_context_eligibility_fact_v1.csv',\n    'context_parameter_selection': DATA / 'edgeiq_race_entry_context_parameter_selection_fact_v1.csv',\n    'context_adjustment': DATA / 'edgeiq_race_entry_context_adjustment_fact_v1.csv',\n    'context_adjusted_performance': DATA / 'edgeiq_race_entry_context_adjusted_performance_fact_v1.csv',\n    'suitability_component': DATA / 'edgeiq_race_entry_suitability_component_fact_v1.csv',\n    'suitability_aggregate': DATA / 'edgeiq_race_entry_suitability_aggregate_fact_v1.csv',\n    'projected_performance': DATA / 'edgeiq_race_entry_projected_performance_fact_v1.csv',\n    'eri_context': DATA / 'edgeiq_race_entry_eri_context_fact_v1.csv',\n    'epi_component': DATA / 'edgeiq_race_entry_epi_component_fact_v1.csv',\n    'epi': DATA / 'edgeiq_race_entry_epi_fact_v1.csv',"
if old_row not in text:
    raise SystemExit('row file insertion point not found')
text = text.replace(old_row, new_row, 1)
path.write_text(text, encoding='utf-8')
print('patched', path)
print('checkpoint', checkpoint)
