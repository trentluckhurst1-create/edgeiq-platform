from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
DOCS = ROOT / 'docs' / 'performance-intelligence' / 'restart-v1'
OUT_JSON = DOCS / 'edgeiq_performance_recovery_current_status_v2.json'
OUT_MD = DOCS / 'EDGEIQ_PERFORMANCE_RECOVERY_CURRENT_STATUS_V2.md'
OUT_FUNNEL = DOCS / 'edgeiq_performance_recovery_current_row_funnel_v2.csv'

FILES = {
    'length_conversion_parameter_v2': DATA / 'edgeiq_length_conversion_parameter_fact_v2.csv',
    'race_time_delta': DATA / 'edgeiq_race_time_delta_versus_standard_fact_v1.csv',
    'lengths_versus_standard': DATA / 'edgeiq_lengths_versus_standard_fact_v1.csv',
    'lengths_versus_standard_rejections': DATA / 'edgeiq_lengths_versus_standard_fact_v1_rejections.csv',
    'performance_base': DATA / 'edgeiq_performance_intelligence_base_fact_v1.csv',
    'normalisation': DATA / 'edgeiq_performance_normalisation_fact_v1.csv',
    'normalisation_rejections': DATA / 'edgeiq_performance_normalisation_fact_v1_rejections.csv',
    'rating_base': DATA / 'edgeiq_performance_rating_base_fact_v1.csv',
    'horse_observation': DATA / 'edgeiq_horse_performance_observation_fact_v1.csv',
    'horse_aggregate': DATA / 'edgeiq_horse_performance_aggregate_fact_v1.csv',
    'horse_rating': DATA / 'edgeiq_horse_performance_rating_fact_v1.csv',
    'race_entry_snapshot': DATA / 'edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv',
    'projected_performance': DATA / 'edgeiq_race_entry_projected_performance_fact_v1.csv',
}


def count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        return sum(1 for _ in csv.DictReader(handle))


def git(args: list[str]) -> str:
    try:
        return subprocess.check_output(['git', *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ''


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    row_counts = {name: count(path) for name, path in FILES.items()}
    payload = {
        'status': 'NORMALISATION_TEMPORAL_AUTHORITY_RESOLVED_OUTCOME_D_DOWNSTREAM_REBUILT_BLOCKED_BY_GOVERNANCE',
        'starting_commit': '1cce897',
        'current_commit_before_commit': git(['rev-parse', '--short', 'HEAD']),
        'built_at_utc': datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'normalisation_temporal_authority': 'OUTCOME_D_HISTORICAL_NORMALISATION_REMAINS_UNAVAILABLE',
        'parameter_derivation_cutoff': '2026-07-20',
        'historical_application_authorised': 'NO',
        'normalisation_rejection_reason': 'NORMALISATION_PARAMETER_NOT_EFFECTIVE_FOR_PERFORMANCE_DATE',
        'lengths_condition_rejection_decision': 'RETAIN_EXPLICIT_REJECTIONS',
        'build_status': 'PASS',
        'epi_release_status': 'BLOCKED_EMPTY_GOVERNED_PUBLICATION_POPULATION',
        'row_counts': row_counts,
        'protected_systems': {
            'pricing_changed': 'NO',
            'probability_changed': 'NO',
            'v6_1_changed': 'NO',
            'v7_2g2_changed': 'NO',
            'ui_changed': 'NO',
        },
        'remaining_blockers': [
            'No earlier governed normalisation parameter exists for 2026-05-30/31 observations.',
            'HPR-NORM-A-v1 was derived from the 2026-07-20 bootstrap population and cannot be applied to May observations without future leakage.',
            'Four July Sandown race-time deltas still lack authoritative condition evidence.',
            'Canonical timed observation population is currently 39 rows, limiting race-time delta coverage to 17 rows.',
            'EPI publication cannot release with zero projected performance rows.',
        ],
        'exact_next_action': 'Recover or approve a separate earlier governed historical normalisation parameter with documented derivation cutoff, or expand canonical timing observations and condition evidence without weakening identity standards.',
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    with OUT_FUNNEL.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['stage','rows'], lineterminator='\n')
        writer.writeheader()
        for key, value in row_counts.items():
            writer.writerow({'stage': key, 'rows': value})
    OUT_MD.write_text('\n'.join([
        '# EDGEiQ Performance Recovery Current Status V2',
        '',
        f"Status: {payload['status']}",
        f"Normalisation temporal authority: {payload['normalisation_temporal_authority']}",
        f"Parameter derivation cutoff: {payload['parameter_derivation_cutoff']}",
        f"Historical application authorised: {payload['historical_application_authorised']}",
        f"Build status: {payload['build_status']}",
        f"EPI release status: {payload['epi_release_status']}",
        '',
        'Row counts:',
        *[f"- {key}: {value}" for key, value in sorted(row_counts.items())],
        '',
        'Remaining blockers:',
        *[f"- {item}" for item in payload['remaining_blockers']],
        '',
    ]), encoding='utf-8')
    print('EDGEIQ_PERFORMANCE_RECOVERY_CURRENT_STATUS_V2_PASS')
    print(f'output={OUT_JSON}')


if __name__ == '__main__':
    main()
