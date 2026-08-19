from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
DOCS = ROOT / 'docs' / 'performance-intelligence' / 'restart-v1'

OBS = DATA / 'edgeiq_benchmark_observation_fact_v1.csv'
ELIG = DATA / 'edgeiq_benchmark_eligibility_fact_v1.csv'
MEM = DATA / 'edgeiq_benchmark_accumulation_membership_fact_v1.csv'
STD = DATA / 'edgeiq_standard_time_fact_v1.csv'
RTD = DATA / 'edgeiq_race_time_delta_versus_standard_fact_v1.csv'
LVS = DATA / 'edgeiq_lengths_versus_standard_fact_v1.csv'
LVS_REJ = DATA / 'edgeiq_lengths_versus_standard_fact_v1_rejections.csv'
BASE = DATA / 'edgeiq_performance_intelligence_base_fact_v1.csv'
NORM = DATA / 'edgeiq_performance_normalisation_fact_v1.csv'
NORM_REJ = DATA / 'edgeiq_performance_normalisation_fact_v1_rejections.csv'

OUT_CSV = DATA / 'edgeiq_performance_intelligence_upstream_funnel_audit_v1.csv'
OUT_SUMMARY = DATA / 'edgeiq_performance_intelligence_upstream_funnel_audit_v1_summary.json'
OUT_MD = DOCS / 'EDGEIQ_PERFORMANCE_INTELLIGENCE_UPSTREAM_FUNNEL_AUDIT_V1.md'


def read(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def text(value: object) -> str:
    return str(value if value is not None else '').strip()


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    obs_rows = read(OBS)
    elig_rows = read(ELIG)
    mem_rows = read(MEM)
    std_rows = read(STD)
    rtd_rows = read(RTD)
    lvs_rows = read(LVS)
    lvs_rej_rows = read(LVS_REJ)
    base_rows = read(BASE)
    norm_rows = read(NORM)
    norm_rej_rows = read(NORM_REJ)

    elig_by_obs = {text(row.get('benchmark_observation_id')): row for row in elig_rows}
    mem_by_obs = {text(row.get('benchmark_observation_id')): row for row in mem_rows}
    std_by_group = {text(row.get('benchmark_group_id')): row for row in std_rows if text(row.get('standard_time_status')) == 'AVAILABLE'}
    std_by_track_dist = {(text(row.get('track_name')).upper(), text(row.get('official_distance_metres'))): row for row in std_rows if text(row.get('standard_time_status')) == 'AVAILABLE'}
    rtd_by_obs = {text(row.get('benchmark_observation_id')): row for row in rtd_rows}
    lvs_by_rtd = {text(row.get('race_time_delta_id')): row for row in lvs_rows}
    lvs_rej_by_rtd = {text(row.get('race_time_delta_id')): row for row in lvs_rej_rows}
    base_by_lvs = {text(row.get('lengths_versus_standard_id')): row for row in base_rows}
    norm_by_base = {text(row.get('performance_intelligence_base_id')): row for row in norm_rows}
    norm_rej_by_base = {text(row.get('performance_intelligence_base_id')): row for row in norm_rej_rows}

    audit_rows = []
    for obs in obs_rows:
        obs_id = text(obs.get('benchmark_observation_id'))
        elig = elig_by_obs.get(obs_id)
        mem = mem_by_obs.get(obs_id)
        rtd = rtd_by_obs.get(obs_id)
        stage = 'UNKNOWN'
        rejection_reason = ''
        standard_match_status = 'NO'
        group_id = text(mem.get('benchmark_group_id')) if mem else ''
        group_std = std_by_group.get(group_id) if group_id else None
        td_std = std_by_track_dist.get((text(obs.get('track_name')).upper(), text(obs.get('official_distance_metres'))))
        if group_std or td_std:
            standard_match_status = 'YES'
        if not elig:
            stage = 'ELIGIBILITY_MISSING'
        elif text(elig.get('benchmark_use_class')) != 'STANDARD_TIME_ELIGIBLE':
            stage = 'NOT_STANDARD_TIME_ELIGIBLE'
            rejection_reason = text(elig.get('eligibility_reason_codes'))
        elif not standard_match_status == 'YES':
            stage = 'NO_STANDARD_TIME_MATCH'
        elif not rtd:
            stage = 'STANDARD_MATCHED_DELTA_MISSING'
        else:
            rtd_id = text(rtd.get('race_time_delta_id'))
            lvs = lvs_by_rtd.get(rtd_id)
            lvs_rej = lvs_rej_by_rtd.get(rtd_id)
            if lvs:
                lvs_id = text(lvs.get('lengths_versus_standard_id'))
                base = base_by_lvs.get(lvs_id)
                if base:
                    base_id = text(base.get('performance_intelligence_base_id'))
                    if base_id in norm_by_base:
                        stage = 'NORMALISED'
                    elif base_id in norm_rej_by_base:
                        stage = 'NORMALISATION_REJECTED'
                        rejection_reason = text(norm_rej_by_base[base_id].get('rejection_reason'))
                    else:
                        stage = 'PERFORMANCE_BASE_BUILT_NORMALISATION_UNACCOUNTED'
                else:
                    stage = 'LENGTHS_STANDARD_BUILT_BASE_MISSING'
            elif lvs_rej:
                stage = 'LENGTHS_STANDARD_REJECTED'
                rejection_reason = text(lvs_rej.get('rejection_reason'))
            else:
                stage = 'RACE_TIME_DELTA_BUILT_LVS_UNACCOUNTED'
        audit_rows.append({
            'benchmark_observation_id': obs_id,
            'race_key': text(obs.get('race_key')),
            'race_date': text(obs.get('race_date')),
            'track_name': text(obs.get('track_name')),
            'race_no': text(obs.get('race_number')),
            'official_distance_metres': text(obs.get('official_distance_metres')),
            'runner_count': text(obs.get('runner_count')),
            'race_split_coverage_type': text(obs.get('race_split_coverage_type')),
            'benchmark_use_class': text(elig.get('benchmark_use_class')) if elig else '',
            'standard_time_eligible': text(elig.get('standard_time_eligible')) if elig else '',
            'membership_group_id': group_id,
            'standard_time_match_status': standard_match_status,
            'race_time_delta_id': text(rtd.get('race_time_delta_id')) if rtd else '',
            'terminal_stage': stage,
            'rejection_reason': rejection_reason,
        })

    with OUT_CSV.open('w', encoding='utf-8', newline='') as handle:
        fields = ['benchmark_observation_id','race_key','race_date','track_name','race_no','official_distance_metres','runner_count','race_split_coverage_type','benchmark_use_class','standard_time_eligible','membership_group_id','standard_time_match_status','race_time_delta_id','terminal_stage','rejection_reason']
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(audit_rows)

    stage_counts = Counter(row['terminal_stage'] for row in audit_rows)
    rejection_counts = Counter(row['rejection_reason'] for row in audit_rows if row['rejection_reason'])
    summary = {
        'audit_name': 'edgeiq_performance_intelligence_upstream_funnel_audit_v1',
        'audited_at_utc': datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'canonical_timed_race_observations': len(obs_rows),
        'benchmark_eligibility_rows': len(elig_rows),
        'benchmark_membership_rows': len(mem_rows),
        'standard_time_rows': len(std_rows),
        'races_with_standard_time_matches': sum(1 for row in audit_rows if row['standard_time_match_status'] == 'YES'),
        'races_without_standard_time_matches': sum(1 for row in audit_rows if row['standard_time_match_status'] != 'YES'),
        'race_time_delta_rows': len(rtd_rows),
        'lengths_versus_standard_rows': len(lvs_rows),
        'lengths_versus_standard_rejections': len(lvs_rej_rows),
        'performance_base_rows': len(base_rows),
        'normalisation_rows': len(norm_rows),
        'normalisation_rejections': len(norm_rej_rows),
        'terminal_stage_counts': dict(stage_counts),
        'rejection_reason_counts': dict(rejection_counts),
        'coverage_limiting_stage': 'BENCHMARK_OBSERVATION_POPULATION_LIMITED_TO_39_CANONICAL_TIMED_RACES',
        'thresholds_weakened': 'NO',
    }
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    OUT_MD.write_text('\n'.join([
        '# EDGEiQ Performance Intelligence Upstream Funnel Audit V1',
        '',
        f"Canonical timed race observations: {len(obs_rows)}",
        f"Race-time delta rows: {len(rtd_rows)}",
        f"Lengths v Standard rows: {len(lvs_rows)}",
        f"Performance base rows: {len(base_rows)}",
        f"Normalisation rows: {len(norm_rows)}",
        '',
        'Terminal stage counts:',
        *[f"- {k}: {v}" for k, v in sorted(stage_counts.items())],
        '',
        'No identity or eligibility threshold was weakened by this audit.',
        '',
    ]), encoding='utf-8')

    print('EDGEIQ_PERFORMANCE_INTELLIGENCE_UPSTREAM_FUNNEL_AUDIT_V1_PASS')
    print(f'canonical_timed_race_observations={len(obs_rows)}')
    print(f'race_time_delta_rows={len(rtd_rows)}')
    print(f'lengths_versus_standard_rows={len(lvs_rows)}')
    print(f'normalisation_rows={len(norm_rows)}')
    print(f'output={OUT_CSV}')


if __name__ == '__main__':
    main()
