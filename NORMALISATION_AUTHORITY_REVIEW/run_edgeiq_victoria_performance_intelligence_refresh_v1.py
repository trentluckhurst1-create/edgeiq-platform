from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
DOCS = ROOT / 'docs' / 'performance-intelligence' / 'restart-v1'
MANIFEST = DATA / 'edgeiq_victoria_performance_intelligence_refresh_manifest_v1.json'
SUMMARY = DATA / 'edgeiq_victoria_performance_intelligence_refresh_manifest_v1.csv'
REPORT = DOCS / 'EDGEIQ_VICTORIA_PERFORMANCE_INTELLIGENCE_REFRESH_MANIFEST_V1.md'

STEPS = [
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
    ('performance_normalisation_build', 'scripts/build_edgeiq_performance_normalisation_fact_v1.py', True),
    ('performance_normalisation_audit', 'scripts/audit_edgeiq_performance_normalisation_fact_v1.py', True),
    ('performance_rating_base_build', 'scripts/build_edgeiq_performance_rating_base_fact_v1.py', True),
    ('performance_rating_base_audit', 'scripts/audit_edgeiq_performance_rating_base_fact_v1.py', True),
    ('horse_observation_build', 'scripts/build_edgeiq_horse_performance_observation_fact_v1.py', True),
    ('horse_observation_audit', 'scripts/audit_edgeiq_horse_performance_observation_fact_v1.py', True),
    ('horse_aggregate_build', 'scripts/build_edgeiq_horse_performance_aggregate_fact_v1.py', True),
    ('horse_aggregate_audit', 'scripts/audit_edgeiq_horse_performance_aggregate_fact_v1.py', True),
    ('horse_rating_build', 'scripts/build_edgeiq_horse_performance_rating_fact_v1.py', True),
    ('horse_rating_audit', 'scripts/audit_edgeiq_horse_performance_rating_fact_v1.py', True),
    ('race_entry_snapshot_build', 'scripts/build_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py', True),
    ('race_entry_snapshot_audit', 'scripts/audit_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py', True),
    ('race_entry_context_build', 'scripts/build_edgeiq_race_entry_performance_context_fact_v1.py', True),
    ('race_entry_context_audit', 'scripts/audit_edgeiq_race_entry_performance_context_fact_v1.py', True),
    ('context_adjusted_build', 'scripts/build_edgeiq_race_entry_context_adjusted_performance_fact_v1.py', True),
    ('context_adjusted_audit', 'scripts/audit_edgeiq_race_entry_context_adjusted_performance_fact_v1.py', True),
    ('projected_performance_build', 'scripts/build_edgeiq_race_entry_projected_performance_fact_v1.py', True),
    ('projected_performance_audit', 'scripts/audit_edgeiq_race_entry_projected_performance_fact_v1.py', True),
    ('epi_dependency_audit', 'scripts/audit_edgeiq_epi_performance_dependency_v1.py', False),
]

ROW_FILES = {
    'recovered_timing_warehouse': DATA / 'edgeiq_recovered_timing_warehouse_v1.csv',
    'recovered_standard_time': DATA / 'edgeiq_standard_time_fact_recovered_v1.csv',
    'recovered_race_time_delta': DATA / 'edgeiq_race_time_delta_versus_standard_recovered_v1.csv',
    'recovered_lengths_versus_standard': DATA / 'edgeiq_lengths_versus_standard_recovered_v1.csv',
    'recovered_performance_base': DATA / 'edgeiq_performance_intelligence_base_recovered_v1.csv',
    'recovered_normalisation': DATA / 'edgeiq_performance_normalisation_recovered_v1.csv',
    'recovered_normalisation_rejections': DATA / 'edgeiq_performance_normalisation_recovered_v1_rejections.csv',
    'length_conversion_parameter_v2': DATA / 'edgeiq_length_conversion_parameter_fact_v2.csv',
    'race_time_delta': DATA / 'edgeiq_race_time_delta_versus_standard_fact_v1.csv',
    'lengths_versus_standard': DATA / 'edgeiq_lengths_versus_standard_fact_v1.csv',
    'lengths_versus_standard_rejections': DATA / 'edgeiq_lengths_versus_standard_fact_v1_rejections.csv',
    'performance_base': DATA / 'edgeiq_performance_intelligence_base_fact_v1.csv',
    'performance_normalisation': DATA / 'edgeiq_performance_normalisation_fact_v1.csv',
    'performance_normalisation_rejections': DATA / 'edgeiq_performance_normalisation_fact_v1_rejections.csv',
    'performance_rating_base': DATA / 'edgeiq_performance_rating_base_fact_v1.csv',
    'horse_observation': DATA / 'edgeiq_horse_performance_observation_fact_v1.csv',
    'horse_aggregate': DATA / 'edgeiq_horse_performance_aggregate_fact_v1.csv',
    'horse_rating': DATA / 'edgeiq_horse_performance_rating_fact_v1.csv',
    'race_entry_snapshot': DATA / 'edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv',
    'race_context_authority': DATA / 'edgeiq_race_context_authority_fact_v1.csv',
    'race_entry_context': DATA / 'edgeiq_race_entry_performance_context_fact_v1.csv',
    'context_eligibility': DATA / 'edgeiq_race_entry_context_eligibility_fact_v1.csv',
    'context_parameter_registry': DATA / 'edgeiq_context_parameter_registry_v1.csv',
    'context_parameter_selection': DATA / 'edgeiq_race_entry_context_parameter_selection_fact_v1.csv',
    'context_adjustment': DATA / 'edgeiq_race_entry_context_adjustment_fact_v1.csv',
    'context_adjusted_performance': DATA / 'edgeiq_race_entry_context_adjusted_performance_fact_v1.csv',
    'suitability_component': DATA / 'edgeiq_race_entry_suitability_component_fact_v1.csv',
    'suitability_aggregate': DATA / 'edgeiq_race_entry_suitability_aggregate_fact_v1.csv',
    'projected_performance': DATA / 'edgeiq_race_entry_projected_performance_fact_v1.csv',
    'eri_context': DATA / 'edgeiq_race_entry_eri_context_fact_v1.csv',
    'epi_component': DATA / 'edgeiq_race_entry_epi_component_fact_v1.csv',
    'epi': DATA / 'edgeiq_race_entry_epi_fact_v1.csv',
}


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        return sum(1 for _ in csv.DictReader(handle))


def run_step(name: str, script: str, mandatory: bool) -> dict[str, object]:
    started = datetime.now(timezone.utc).replace(microsecond=0)
    proc = subprocess.run(['python', script], cwd=ROOT, text=True, capture_output=True)
    ended = datetime.now(timezone.utc).replace(microsecond=0)
    return {
        'step': name,
        'script': script,
        'mandatory': mandatory,
        'returncode': proc.returncode,
        'status': 'PASS' if proc.returncode == 0 else ('FAIL_MANDATORY' if mandatory else 'FAIL_OPTIONAL'),
        'started_at_utc': started.isoformat().replace('+00:00', 'Z'),
        'ended_at_utc': ended.isoformat().replace('+00:00', 'Z'),
        'stdout_tail': proc.stdout[-2000:],
        'stderr_tail': proc.stderr[-2000:],
    }


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    results = [run_step(*step) for step in STEPS]
    mandatory_failures = [row for row in results if row['mandatory'] and row['returncode'] != 0]
    row_counts = {name: count_rows(path) for name, path in ROW_FILES.items()}
    normalisation_available = row_counts.get('performance_normalisation', 0) > 0
    manifest_status = 'PASS_WITH_GOVERNED_UNAVAILABLE_STAGES' if not mandatory_failures else 'FAIL_MANDATORY_STAGE'
    payload = {
        'manifest_name': 'edgeiq_victoria_performance_intelligence_refresh_manifest_v1',
        'built_at_utc': datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'status': manifest_status,
        'mandatory_failures': [row['step'] for row in mandatory_failures],
        'normalisation_available': normalisation_available,
        'normalisation_unavailable_reason': '' if normalisation_available else 'NO_AUTHORISED_NORMALISATION_ROWS_AFTER_REFRESH',
        'row_counts': row_counts,
        'steps': results,
        'protected_systems': {
            'pricing_changed': 'NO',
            'probability_changed': 'NO',
            'v6_1_changed': 'NO',
            'v7_2g2_changed': 'NO',
            'ui_changed': 'NO',
        },
    }
    MANIFEST.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    with SUMMARY.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['step','script','mandatory','returncode','status'], lineterminator='\n')
        writer.writeheader()
        for row in results:
            writer.writerow({key: row[key] for key in ['step','script','mandatory','returncode','status']})
    REPORT.write_text('\n'.join([
        '# EDGEiQ Victoria Performance Intelligence Refresh Manifest V1',
        '',
        f"Status: {manifest_status}",
        f"Normalisation available: {normalisation_available}",
        f"Normalisation unavailable reason: {payload['normalisation_unavailable_reason']}",
        '',
        'Row counts:',
        *[f"- {key}: {value}" for key, value in sorted(row_counts.items())],
        '',
        'Mandatory failures:',
        *([f"- {row['step']}" for row in mandatory_failures] or ['- none']),
        '',
    ]), encoding='utf-8')
    print('EDGEIQ_VICTORIA_PERFORMANCE_INTELLIGENCE_REFRESH_MANIFEST_V1_' + manifest_status)
    print(f'manifest={MANIFEST}')
    raise SystemExit(1 if mandatory_failures else 0)


if __name__ == '__main__':
    main()
