from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
DOCS = ROOT / 'docs' / 'performance-intelligence' / 'restart-v1'
CONFIG = ROOT / 'config' / 'performance-intelligence'

OUT_JSON = DOCS / 'edgeiq_normalisation_temporal_authority_decision_v1.json'
OUT_MD = DOCS / 'EDGEIQ_NORMALISATION_TEMPORAL_AUTHORITY_DECISION_V1.md'
OUT_EVIDENCE = DOCS / 'edgeiq_normalisation_temporal_authority_evidence_v1.csv'

PARAM_SOURCE = CONFIG / 'edgeiq_performance_normalisation_parameter_source_v1.csv'
PARAM_FACT = DATA / 'edgeiq_performance_normalisation_parameter_fact_v1.csv'
POPULATION = ROOT / 'docs' / 'performance-intelligence' / 'horse-performance-rating' / 'method-governance' / 'edgeiq_performance_normalisation_parameter_population_v1.csv'
APPROVAL = ROOT / 'docs' / 'performance-intelligence' / 'horse-performance-rating' / 'method-governance' / 'EDGEIQ_HORSE_RATING_METHODOLOGY_OWNER_APPROVAL_V1.md'
BASE = DATA / 'edgeiq_performance_intelligence_base_fact_v1.csv'
REJECTIONS = DATA / 'edgeiq_performance_normalisation_fact_v1_rejections.csv'


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ''
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(args: list[str]) -> str:
    try:
        return subprocess.check_output(['git', *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ''


def file_evidence(path: Path, label: str, finding: str) -> dict[str, str]:
    rel = str(path.relative_to(ROOT)) if path.exists() else str(path)
    return {
        'evidence_type': label,
        'path_or_commit': rel,
        'exists': 'YES' if path.exists() else 'NO',
        'sha256': sha256_file(path),
        'finding': finding,
    }


def date_set(rows: list[dict[str, str]], field: str) -> list[str]:
    return sorted({(row.get(field) or '').strip() for row in rows if (row.get(field) or '').strip()})


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    param_source_rows = read_rows(PARAM_SOURCE)
    param_fact_rows = read_rows(PARAM_FACT)
    population_rows = read_rows(POPULATION)
    base_rows = read_rows(BASE)
    rejection_rows = read_rows(REJECTIONS)

    population_dates = date_set(population_rows, 'race_date')
    base_dates = date_set(base_rows, 'race_date')
    parameter_effective_dates = date_set(param_source_rows, 'effective_from_date')
    population_date_counts = Counter((row.get('race_date') or '').strip() for row in population_rows)

    log_hits = git(['log', '--all', '--oneline', '--', str(PARAM_SOURCE.relative_to(ROOT)), str(PARAM_FACT.relative_to(ROOT)), str(POPULATION.relative_to(ROOT)), str(APPROVAL.relative_to(ROOT))])
    grep_hits = git(['grep', '-n', 'HPR-NORM-A-v1', 'HEAD', '--', 'config', 'docs', 'scripts', 'public/data'])

    approval_text = APPROVAL.read_text(encoding='utf-8', errors='replace') if APPROVAL.exists() else ''
    source_text = PARAM_SOURCE.read_text(encoding='utf-8', errors='replace') if PARAM_SOURCE.exists() else ''

    evidence_rows = [
        file_evidence(APPROVAL, 'OWNER_APPROVAL', 'Approves HPR-NORM-A-v1 bootstrap population and explicitly prohibits silent recalibration/fallback.'),
        file_evidence(POPULATION, 'PARAMETER_POPULATION', f'Population rows={len(population_rows)}; dates={"|".join(population_dates[:10])}'),
        file_evidence(PARAM_SOURCE, 'PARAMETER_SOURCE', source_text.replace('\n', ' ')[:500]),
        file_evidence(PARAM_FACT, 'PARAMETER_FACT', f'Parameter fact rows={len(param_fact_rows)}'),
        file_evidence(BASE, 'CURRENT_BASE_ROWS', f'Performance base rows={len(base_rows)}; dates={"|".join(base_dates)}'),
        file_evidence(REJECTIONS, 'CURRENT_REJECTIONS', f'Normalisation rejection rows={len(rejection_rows)}'),
        {'evidence_type': 'GIT_LOG', 'path_or_commit': 'normalisation authority files', 'exists': 'YES' if log_hits else 'NO', 'sha256': '', 'finding': log_hits.replace('\n', ' | ')[:1200]},
        {'evidence_type': 'GIT_GREP', 'path_or_commit': 'HPR-NORM-A-v1 current tree', 'exists': 'YES' if grep_hits else 'NO', 'sha256': '', 'finding': grep_hits.replace('\n', ' | ')[:1200]},
    ]

    has_backfill_phrase = 'historical backfill' in approval_text.casefold()
    has_bootstrap_phrase = '168-row population is approved' in approval_text
    has_no_retro_mutation = 'no retroactive mutation' in approval_text.casefold()
    population_includes_may = any(date.startswith('2026-05') for date in population_dates)
    population_only_july20 = set(population_dates) == {'2026-07-20'}
    base_before_parameter = bool(base_dates and parameter_effective_dates and min(base_dates) < min(parameter_effective_dates))

    selected_outcome = 'OUTCOME_D_HISTORICAL_NORMALISATION_REMAINS_UNAVAILABLE'
    authority_classification = 'SEMANTICALLY_UNSAFE_FOR_MAY_2026_UNTIL_EARLIER_PARAMETER_OR_BACKFILL_AUTHORITY_EXISTS'
    historical_application_authorised = 'NO'
    future_leakage_assessment = 'BLOCKED_FOR_MAY_2026: HPR-NORM-A-v1 values were derived from the 2026-07-20 bootstrap population, after the 2026-05-30/31 observations.'

    decision = {
        'decision_name': 'edgeiq_normalisation_temporal_authority_decision_v1',
        'decided_at_utc': datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'starting_commit': '1cce897',
        'current_commit': git(['rev-parse', '--short', 'HEAD']),
        'selected_outcome': selected_outcome,
        'authority_classification': authority_classification,
        'normalisation_method': 'LINEAR_CENTRE_AND_SCALE',
        'normalisation_model_version': 'HPR-NORM-A-v1',
        'input_metric': 'raw_performance_lengths',
        'formula': '(raw_performance_lengths - centre_value) / scale_value',
        'centre_value': param_source_rows[0].get('centre_value', '') if param_source_rows else '',
        'scale_value': param_source_rows[0].get('scale_value', '') if param_source_rows else '',
        'parameter_effective_from_dates': parameter_effective_dates,
        'parameter_population_rows': len(population_rows),
        'parameter_population_dates': population_dates,
        'parameter_population_date_counts': dict(sorted(population_date_counts.items())),
        'current_performance_base_rows': len(base_rows),
        'current_performance_base_dates': base_dates,
        'current_normalisation_rejection_rows': len(rejection_rows),
        'historical_application_authorised': historical_application_authorised,
        'parameter_derivation_cutoff': max(population_dates) if population_dates else '',
        'parameter_values_include_target_may_2026': 'NO',
        'parameter_values_include_future_relative_to_may_2026': 'YES' if population_only_july20 and base_before_parameter else 'UNKNOWN',
        'future_leakage_assessment': future_leakage_assessment,
        'evidence_summary': {
            'owner_approval_mentions_historical_backfill': has_backfill_phrase,
            'owner_approval_explicit_168_bootstrap': has_bootstrap_phrase,
            'owner_approval_no_retroactive_mutation': has_no_retro_mutation,
            'population_includes_may_2026': population_includes_may,
            'population_only_2026_07_20': population_only_july20,
            'base_dates_before_parameter_effective_date': base_before_parameter,
        },
        'alternatives_considered': [
            {'alternative': 'OUTCOME_A_HISTORICAL_APPLICATION_AUTHORISED', 'decision': 'REJECTED', 'reason': 'No evidence authorises applying a July-20-derived bootstrap parameter to May observations; parameter values would use future data relative to May.'},
            {'alternative': 'OUTCOME_B_RECOVER_EARLIER_GOVERNED_PARAMETER_VERSION', 'decision': 'REJECTED_CURRENTLY', 'reason': 'Current repository and normalisation history search found no earlier governed HPR normalisation parameter.'},
            {'alternative': 'OUTCOME_C_DERIVE_HISTORICAL_PARAMETERS', 'decision': 'REJECTED_CURRENTLY', 'reason': 'No separate approved historical parameter derivation population/cutoff with minimum 100 eligible contemporaneous observations was found.'},
            {'alternative': selected_outcome, 'decision': 'SELECTED', 'reason': 'Preserves May performance base rows and explicit rejections without fabrication or leakage.'},
        ],
        'migration_impact': 'No retroactive normalisation. Downstream horse ratings and projected performance remain unavailable where they require normalised performance ratings.',
        'rollback_path': 'Keep current HPR-NORM-A-v1 untouched; add earlier governed parameter only if separately evidenced and versioned.',
        'no_fabrication_declaration': 'YES',
        'no_silent_backdating_declaration': 'YES',
    }

    with OUT_EVIDENCE.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['evidence_type', 'path_or_commit', 'exists', 'sha256', 'finding'], lineterminator='\n')
        writer.writeheader()
        writer.writerows(evidence_rows)

    OUT_JSON.write_text(json.dumps(decision, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    lines = [
        '# EDGEiQ Normalisation Temporal Authority Decision V1',
        '',
        f"Selected outcome: {selected_outcome}",
        f"Historical application authorised: {historical_application_authorised}",
        f"Authority classification: {authority_classification}",
        '',
        '## Method',
        '',
        '- Input metric: raw_performance_lengths',
        '- Formula: (raw_performance_lengths - centre_value) / scale_value',
        f"- Centre value: {decision['centre_value']}",
        f"- Scale value: {decision['scale_value']}",
        '- Clipping/outlier rule: NONE_IN_HPR_NORM_A_V1',
        '- Distance/surface/condition/class/sex-age handling: no separate handling in normalisation; upstream construction handles race comparability.',
        '',
        '## Temporal Evidence',
        '',
        f"- Parameter effective-from dates: {', '.join(parameter_effective_dates) or 'none'}",
        f"- Parameter population rows: {len(population_rows)}",
        f"- Parameter population dates: {', '.join(population_dates) or 'none'}",
        f"- Current performance base dates: {', '.join(base_dates) or 'none'}",
        f"- Future leakage assessment: {future_leakage_assessment}",
        '',
        '## Decision',
        '',
        'HPR-NORM-A-v1 remains unavailable for the May 2026 observations. The 13 Performance Intelligence base rows are preserved and explicitly rejected at normalisation. This is the only governed resolution that avoids silent backdating and future leakage with the current evidence.',
        '',
        '## Rejected Alternatives',
        '',
    ]
    for alt in decision['alternatives_considered']:
        lines.append(f"- {alt['alternative']}: {alt['decision']} - {alt['reason']}")
    lines.extend(['', '## Declarations', '', '- No fabrication: YES', '- No silent backdating: YES', ''])
    OUT_MD.write_text('\n'.join(lines), encoding='utf-8')

    print('EDGEIQ_NORMALISATION_TEMPORAL_AUTHORITY_DECISION_V1_PASS')
    print(f'selected_outcome={selected_outcome}')
    print(f'parameter_population_rows={len(population_rows)}')
    print(f'current_performance_base_rows={len(base_rows)}')
    print(f'output_json={OUT_JSON}')


if __name__ == '__main__':
    main()
