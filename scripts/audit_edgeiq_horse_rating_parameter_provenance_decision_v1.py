from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating" / "method-governance"
CONFIG_DIR = ROOT / "config" / "performance-intelligence"
DECISION_CSV = DOC_DIR / "edgeiq_horse_rating_parameter_provenance_decision_v1.csv"
REPORT_MD = DOC_DIR / "edgeiq_horse_rating_parameter_provenance_decision_report_v1.md"
PACKAGE_MD = DOC_DIR / "EDGEIQ_HORSE_RATING_GOVERNANCE_DECISION_PACKAGE_V1.md"


def exists(rel: str) -> str:
    return "YES" if (ROOT / rel).exists() else "NO"


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = [
        {
            "governance_source": "edgeiq_performance_normalisation_parameter_source_v1.csv",
            "source_type": "METHODOLOGY_PARAMETER_SOURCE",
            "active_consumer": "scripts/build_edgeiq_performance_normalisation_parameter_fact_v1.py; scripts/build_edgeiq_performance_normalisation_fact_v1.py",
            "schema_recovered": "YES",
            "formula_recovered": "PARTIAL",
            "source_rows_recovered": "NO",
            "unresolved_items": "centre_value;scale_value;effective_date_ranges;parameter_status_provenance;minimum_population_count",
            "candidate_build_status": "BLOCKED_NOT_BUILT",
            "provenance_decision": "NEW_ARCHITECTURAL_APPROVAL_REQUIRED",
            "reason": "Active formula requires centre_value and scale_value, but repository and git evidence recovered schema/formula only, not governed values or approval provenance.",
        },
        {
            "governance_source": "edgeiq_horse_performance_aggregation_parameter_source_v1.csv",
            "source_type": "METHODOLOGY_PARAMETER_SOURCE",
            "active_consumer": "scripts/build_edgeiq_horse_performance_aggregation_parameter_fact_v1.py; scripts/build_edgeiq_horse_performance_aggregate_fact_v1.py",
            "schema_recovered": "YES",
            "formula_recovered": "PARTIAL",
            "source_rows_recovered": "NO",
            "unresolved_items": "aggregation_method;lookback_days;min_observations;max_observations;recency_weight_method;recency_half_life_days;effective_date_ranges;parameter_status_provenance",
            "candidate_build_status": "BLOCKED_NOT_BUILT",
            "provenance_decision": "NEW_ARCHITECTURAL_APPROVAL_REQUIRED",
            "reason": "Active aggregate formula supports arithmetic and half-life weighted arithmetic means, but governed policy values were not recovered from active repo or git evidence.",
        },
        {
            "governance_source": "edgeiq_horse_performance_identity_map_v1.csv",
            "source_type": "IDENTITY_GOVERNANCE_SOURCE",
            "active_consumer": "scripts/build_edgeiq_horse_performance_observation_fact_v1.py",
            "schema_recovered": "YES",
            "formula_recovered": "NOT_METHOD_FORMULA",
            "source_rows_recovered": "YES",
            "unresolved_items": "NONE_FOR_CURRENT_24_SOURCE_IDS",
            "candidate_build_status": "BUILT_AND_PROMOTED",
            "provenance_decision": "RECOVERED_FROM_AUTHORITATIVE_RACINGCOM_IDENTITY_PAYLOAD",
            "reason": "Exact Racing.com race-entry IDs from the governed performance base were mapped to canonical horse IDs/names from raw GraphQL payloads; audit validated 24/24 with no horse-ID conflicts.",
        },
    ]
    fields = [
        "governance_source", "source_type", "active_consumer", "schema_recovered", "formula_recovered",
        "source_rows_recovered", "unresolved_items", "candidate_build_status", "provenance_decision", "reason",
    ]
    write_csv(DECISION_CSV, rows, fields)

    report = """# EDGEiQ Horse Rating Parameter Provenance Decision V1

Status: EDGEIQ_PERFORMANCE_INTELLIGENCE_BLOCKED_BY_NORMALISATION_METHOD

## Decision Summary

- Identity governance source: recovered and validated from authoritative Racing.com payloads.
- Performance normalisation source: not recovered; methodological approval required.
- Horse performance aggregation source: not recovered; methodological approval required after normalisation is approved.

No normalisation or aggregation parameter candidate was built because doing so would require inventing centre/scale and aggregation policy values. That would violate the governance directive.

## Current First Blocking Stage

The first unresolved zero-row stage remains performance normalisation: the active formula cannot calculate `normalised_performance_value` without governed `centre_value` and `scale_value` rows.

## Production Safety

No pricing, probability, V6.1, V7.2G2, UI, EPI redesign, or production runner warehouse changes were made.
"""
    REPORT_MD.write_text(report, encoding="utf-8")

    package = """# EDGEiQ Horse Rating Governance Decision Package V1

## Objective

Recover or certify the governed sources required to build horse-level historical performance ratings without fabricating parameters, reducing thresholds, changing the EPI method, or introducing current/future leakage.

## Proven Inputs

- Historical performance intelligence base rows: 168
- Historical runner identities eligible for rating aggregation: 24
- Horses/race-entry IDs with 5+ eligible segments: 24/24
- Identity map coverage after recovery: 24/24
- Normalisation parameter source rows: 0
- Aggregation parameter source rows: 0

## Recovered Consumer Contracts

### Performance Normalisation

Active formula:

`normalised_performance_value = (raw_performance_lengths - centre_value) / scale_value`

Recovered fields include `centre_value`, `scale_value`, effective date range, method, status, evidence reference, and evidence hash.

Unresolved methodology values:

- `centre_value`
- `scale_value`
- effective date ranges
- parameter approval provenance
- minimum population/source evidence requirements

### Horse Performance Aggregation

Recovered aggregate shape:

- Arithmetic mean with weight `1`, or
- Weighted arithmetic mean using exponential half-life weights: `0.5 ** (age_days / recency_half_life_days)`

Unresolved methodology values:

- aggregation method
- lookback days
- minimum observation count
- maximum observation count
- recency weight method
- recency half-life days
- effective date ranges
- parameter approval provenance

### Horse Identity Map

Recovered independently from authoritative Racing.com raw GraphQL payloads using exact source race-entry IDs. No fuzzy matching was used.

## Owner Decision Required

Normalisation and aggregation methodology source rows cannot be reconstructed from repository evidence. Any new parameter source would be a new architectural/methodological approval, not a recovered source.

## Options Requiring Approval

### Option A: Historical Population Normalisation

Define centre/scale from a governed historical population of `raw_performance_lengths`.

Status: NEW METHODOLOGY REQUIRING OWNER APPROVAL.

### Option B: Segment-Class Normalisation

Define centre/scale by governed segment/distance/surface/class buckets.

Status: NEW METHODOLOGY REQUIRING OWNER APPROVAL.

### Option C: Direct Raw-Length Aggregate

Skip normalisation and aggregate raw lengths directly.

Status: NEW METHODOLOGY REQUIRING OWNER APPROVAL and active builder redesign; not permitted under this directive.

## Recommendation

Do not build horse performance ratings until the owner approves a normalisation parameter source and aggregation parameter source with documented provenance. The identity map is ready, but the methodology remains blocked.

## Explicit Non-Changes

- Production pricing changed: NO
- Probability engine changed: NO
- V6.1 changed: NO
- V7.2G2 changed: NO
- UI changed: NO
- EPI redesigned: NO
- Production runner warehouse changed: NO
"""
    PACKAGE_MD.write_text(package, encoding="utf-8")

    print("status=EDGEIQ_PERFORMANCE_INTELLIGENCE_BLOCKED_BY_NORMALISATION_METHOD")
    print("identity_source=RECOVERED")
    print("normalisation_source=NEW_ARCHITECTURAL_APPROVAL_REQUIRED")
    print("aggregation_source=NEW_ARCHITECTURAL_APPROVAL_REQUIRED")
    print("parameter_candidates_built=NO")


if __name__ == "__main__":
    main()
