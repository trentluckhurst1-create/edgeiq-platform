from __future__ import annotations

import ast
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

PHASE03 = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase0_3"
)

ARCHITECTURE = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase0_4"
)

AUDIT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase0_4"
)


SCHEMA_TABLES: dict[str, list[dict[str, Any]]] = {
    "source_evidence": [
        {
            "field": "source_evidence_id",
            "type": "string",
            "required": True,
            "description": "Immutable ID for one ingested source record.",
        },
        {
            "field": "provider_code",
            "type": "string",
            "required": True,
            "description": "Provider identity such as RACING_COM or RACING_AUSTRALIA.",
        },
        {
            "field": "provider_record_id",
            "type": "string",
            "required": False,
            "description": "Provider-native record identifier.",
        },
        {
            "field": "source_url",
            "type": "string",
            "required": False,
            "description": "Original source endpoint or page.",
        },
        {
            "field": "source_file",
            "type": "string",
            "required": True,
            "description": "Repository or warehouse file holding the evidence.",
        },
        {
            "field": "source_sha256",
            "type": "string",
            "required": True,
            "description": "Hash of source payload or source file.",
        },
        {
            "field": "source_published_at",
            "type": "timestamp",
            "required": False,
            "description": "Provider publication timestamp.",
        },
        {
            "field": "ingested_at",
            "type": "timestamp",
            "required": True,
            "description": "EDGEiQ ingestion timestamp.",
        },
        {
            "field": "evidence_version",
            "type": "integer",
            "required": True,
            "description": "Immutable source evidence version.",
        },
        {
            "field": "supersedes_source_evidence_id",
            "type": "string",
            "required": False,
            "description": "Previous source evidence version.",
        },
        {
            "field": "is_current_version",
            "type": "boolean",
            "required": True,
            "description": "Whether this is the active evidence version.",
        },
        {
            "field": "raw_payload_location",
            "type": "string",
            "required": False,
            "description": "Location of preserved raw payload.",
        },
    ],
    "canonical_meeting": [
        {
            "field": "meeting_id",
            "type": "string",
            "required": True,
            "description": "Permanent canonical meeting identity.",
        },
        {
            "field": "jurisdiction_code",
            "type": "string",
            "required": True,
            "description": "Jurisdiction such as VIC or WA.",
        },
        {
            "field": "meeting_date",
            "type": "date",
            "required": True,
            "description": "Official local meeting date.",
        },
        {
            "field": "track_id",
            "type": "string",
            "required": True,
            "description": "Canonical track identity.",
        },
        {
            "field": "course_id",
            "type": "string",
            "required": False,
            "description": "Canonical course identity.",
        },
        {
            "field": "meeting_status",
            "type": "string",
            "required": True,
            "description": "Scheduled, completed, abandoned, transferred or corrected.",
        },
        {
            "field": "source_evidence_id",
            "type": "string",
            "required": True,
            "description": "Evidence supporting the meeting.",
        },
    ],
    "canonical_race": [
        {
            "field": "race_id",
            "type": "string",
            "required": True,
            "description": "Permanent canonical race identity.",
        },
        {
            "field": "meeting_id",
            "type": "string",
            "required": True,
            "description": "Canonical meeting identity.",
        },
        {
            "field": "race_number",
            "type": "integer",
            "required": True,
            "description": "Official race number.",
        },
        {
            "field": "race_name",
            "type": "string",
            "required": False,
            "description": "Official race name.",
        },
        {
            "field": "distance_metres",
            "type": "integer",
            "required": True,
            "description": "Official race distance.",
        },
        {
            "field": "class_id",
            "type": "string",
            "required": False,
            "description": "Canonical class identity.",
        },
        {
            "field": "going_id",
            "type": "string",
            "required": False,
            "description": "Canonical going identity.",
        },
        {
            "field": "rail_id",
            "type": "string",
            "required": False,
            "description": "Canonical rail identity.",
        },
        {
            "field": "race_status",
            "type": "string",
            "required": True,
            "description": "Official race status.",
        },
        {
            "field": "source_evidence_id",
            "type": "string",
            "required": True,
            "description": "Evidence supporting the race.",
        },
    ],
    "canonical_horse": [
        {
            "field": "horse_id",
            "type": "string",
            "required": True,
            "description": "Permanent canonical horse identity.",
        },
        {
            "field": "horse_name",
            "type": "string",
            "required": True,
            "description": "Current canonical horse name.",
        },
        {
            "field": "country_code",
            "type": "string",
            "required": False,
            "description": "Country suffix or registration country.",
        },
        {
            "field": "foaling_year",
            "type": "integer",
            "required": False,
            "description": "Foaling year where available.",
        },
        {
            "field": "sex",
            "type": "string",
            "required": False,
            "description": "Official sex.",
        },
        {
            "field": "identity_status",
            "type": "string",
            "required": True,
            "description": "Resolved, likely, ambiguous or unresolved.",
        },
        {
            "field": "identity_confidence",
            "type": "decimal",
            "required": False,
            "description": "Governed identity confidence.",
        },
    ],
    "performance_evidence": [
        {
            "field": "performance_id",
            "type": "string",
            "required": True,
            "description": "Permanent identity for one horse in one race.",
        },
        {
            "field": "race_id",
            "type": "string",
            "required": True,
            "description": "Canonical race identity.",
        },
        {
            "field": "horse_id",
            "type": "string",
            "required": True,
            "description": "Canonical horse identity.",
        },
        {
            "field": "source_evidence_id",
            "type": "string",
            "required": True,
            "description": "Evidence supporting the performance.",
        },
        {
            "field": "trainer_id",
            "type": "string",
            "required": False,
            "description": "Canonical trainer identity.",
        },
        {
            "field": "jockey_id",
            "type": "string",
            "required": False,
            "description": "Canonical jockey identity.",
        },
        {
            "field": "barrier",
            "type": "integer",
            "required": False,
            "description": "Official barrier.",
        },
        {
            "field": "weight_kg",
            "type": "decimal",
            "required": False,
            "description": "Official carried weight.",
        },
        {
            "field": "starting_price",
            "type": "decimal",
            "required": False,
            "description": "Official starting price.",
        },
        {
            "field": "finish_position",
            "type": "integer",
            "required": False,
            "description": "Official finish position.",
        },
        {
            "field": "finish_status",
            "type": "string",
            "required": True,
            "description": "Finished, scratched, DNF, disqualified or other.",
        },
        {
            "field": "margin_to_winner_lengths",
            "type": "decimal",
            "required": False,
            "description": "Official margin to winner.",
        },
        {
            "field": "official_race_time_seconds",
            "type": "decimal",
            "required": False,
            "description": "Official final race time.",
        },
        {
            "field": "performance_quality_state",
            "type": "string",
            "required": True,
            "description": "Complete, partial, mismatch, excluded or unresolved.",
        },
        {
            "field": "evidence_version",
            "type": "integer",
            "required": True,
            "description": "Evidence version used for this performance.",
        },
    ],
    "performance_sectional_evidence": [
        {
            "field": "performance_sectional_id",
            "type": "string",
            "required": True,
            "description": "Permanent split evidence identity.",
        },
        {
            "field": "performance_id",
            "type": "string",
            "required": True,
            "description": "Canonical performance identity.",
        },
        {
            "field": "split_start_metres",
            "type": "integer",
            "required": True,
            "description": "Split starting marker.",
        },
        {
            "field": "split_end_metres",
            "type": "integer",
            "required": True,
            "description": "Split ending marker.",
        },
        {
            "field": "split_type",
            "type": "string",
            "required": True,
            "description": "Incremental or cumulative.",
        },
        {
            "field": "raw_time_seconds",
            "type": "decimal",
            "required": False,
            "description": "Raw official or provider sectional time.",
        },
        {
            "field": "position_at_split",
            "type": "integer",
            "required": False,
            "description": "Official position at split.",
        },
        {
            "field": "margin_at_split_lengths",
            "type": "decimal",
            "required": False,
            "description": "Official margin at split.",
        },
        {
            "field": "timing_provider",
            "type": "string",
            "required": False,
            "description": "Timing provider identity.",
        },
        {
            "field": "timing_quality_state",
            "type": "string",
            "required": True,
            "description": "Complete, partial, inconsistent, mismatch or excluded.",
        },
        {
            "field": "source_evidence_id",
            "type": "string",
            "required": True,
            "description": "Source evidence for this split.",
        },
    ],
    "benchmark_definition": [
        {
            "field": "benchmark_id",
            "type": "string",
            "required": True,
            "description": "Permanent governed benchmark identity.",
        },
        {
            "field": "benchmark_type",
            "type": "string",
            "required": True,
            "description": "Final time, sectional, pace or race-strength benchmark.",
        },
        {
            "field": "hierarchy_level",
            "type": "string",
            "required": True,
            "description": "Track, course, distance, class, going or rail level.",
        },
        {
            "field": "track_id",
            "type": "string",
            "required": False,
            "description": "Canonical track dimension.",
        },
        {
            "field": "course_id",
            "type": "string",
            "required": False,
            "description": "Canonical course dimension.",
        },
        {
            "field": "distance_metres",
            "type": "integer",
            "required": False,
            "description": "Distance dimension.",
        },
        {
            "field": "class_id",
            "type": "string",
            "required": False,
            "description": "Class dimension.",
        },
        {
            "field": "going_id",
            "type": "string",
            "required": False,
            "description": "Going dimension.",
        },
        {
            "field": "rail_id",
            "type": "string",
            "required": False,
            "description": "Rail dimension.",
        },
        {
            "field": "benchmark_value",
            "type": "decimal",
            "required": True,
            "description": "Governed benchmark value.",
        },
        {
            "field": "benchmark_unit",
            "type": "string",
            "required": True,
            "description": "Seconds, metres per second, rating or other.",
        },
        {
            "field": "eligible_sample_count",
            "type": "integer",
            "required": True,
            "description": "Eligible sample count.",
        },
        {
            "field": "included_sample_count",
            "type": "integer",
            "required": True,
            "description": "Included sample count.",
        },
        {
            "field": "excluded_sample_count",
            "type": "integer",
            "required": True,
            "description": "Excluded sample count.",
        },
        {
            "field": "confidence",
            "type": "decimal",
            "required": True,
            "description": "Governed benchmark confidence.",
        },
        {
            "field": "quality_state",
            "type": "string",
            "required": True,
            "description": "Benchmark quality state.",
        },
        {
            "field": "benchmark_engine_version",
            "type": "string",
            "required": True,
            "description": "Engine version.",
        },
        {
            "field": "warehouse_snapshot_id",
            "type": "string",
            "required": True,
            "description": "Input warehouse snapshot.",
        },
        {
            "field": "valid_from",
            "type": "date",
            "required": True,
            "description": "Benchmark validity start.",
        },
        {
            "field": "valid_to",
            "type": "date",
            "required": False,
            "description": "Benchmark validity end.",
        },
        {
            "field": "generated_at",
            "type": "timestamp",
            "required": True,
            "description": "Generation timestamp.",
        },
    ],
    "performance_derivation": [
        {
            "field": "performance_derivation_id",
            "type": "string",
            "required": True,
            "description": "Permanent derivation record ID.",
        },
        {
            "field": "performance_id",
            "type": "string",
            "required": True,
            "description": "Canonical performance identity.",
        },
        {
            "field": "benchmark_id",
            "type": "string",
            "required": False,
            "description": "Selected benchmark.",
        },
        {
            "field": "benchmark_level_requested",
            "type": "string",
            "required": False,
            "description": "Requested benchmark hierarchy level.",
        },
        {
            "field": "benchmark_level_used",
            "type": "string",
            "required": False,
            "description": "Actual benchmark hierarchy level.",
        },
        {
            "field": "benchmark_fallback_reason",
            "type": "string",
            "required": False,
            "description": "Reason for benchmark fallback.",
        },
        {
            "field": "seconds_vs_benchmark",
            "type": "decimal",
            "required": False,
            "description": "Negative means faster than benchmark.",
        },
        {
            "field": "lengths_vs_benchmark",
            "type": "decimal",
            "required": False,
            "description": "Negative means faster than benchmark.",
        },
        {
            "field": "performance_quality_state",
            "type": "string",
            "required": True,
            "description": "Derived performance quality state.",
        },
        {
            "field": "performance_engine_version",
            "type": "string",
            "required": True,
            "description": "Performance engine version.",
        },
        {
            "field": "benchmark_engine_version",
            "type": "string",
            "required": False,
            "description": "Benchmark engine version.",
        },
        {
            "field": "length_conversion_version",
            "type": "string",
            "required": False,
            "description": "Length conversion version.",
        },
        {
            "field": "derivation_run_id",
            "type": "string",
            "required": True,
            "description": "Reproducible derivation run identity.",
        },
        {
            "field": "generated_at",
            "type": "timestamp",
            "required": True,
            "description": "Generation timestamp.",
        },
    ],
    "performance_sectional_derivation": [
        {
            "field": "sectional_derivation_id",
            "type": "string",
            "required": True,
            "description": "Permanent sectional derivation ID.",
        },
        {
            "field": "performance_sectional_id",
            "type": "string",
            "required": True,
            "description": "Raw sectional evidence identity.",
        },
        {
            "field": "benchmark_id",
            "type": "string",
            "required": False,
            "description": "Selected sectional benchmark.",
        },
        {
            "field": "seconds_vs_benchmark",
            "type": "decimal",
            "required": False,
            "description": "Negative means faster than benchmark.",
        },
        {
            "field": "lengths_vs_benchmark",
            "type": "decimal",
            "required": False,
            "description": "Negative means faster than benchmark.",
        },
        {
            "field": "conversion_method",
            "type": "string",
            "required": False,
            "description": "Governed seconds-to-lengths methodology.",
        },
        {
            "field": "conversion_version",
            "type": "string",
            "required": False,
            "description": "Conversion engine version.",
        },
        {
            "field": "quality_state",
            "type": "string",
            "required": True,
            "description": "Sectional derivation quality state.",
        },
        {
            "field": "derivation_run_id",
            "type": "string",
            "required": True,
            "description": "Reproducible derivation run identity.",
        },
        {
            "field": "generated_at",
            "type": "timestamp",
            "required": True,
            "description": "Generation timestamp.",
        },
    ],
    "engine_run": [
        {
            "field": "engine_run_id",
            "type": "string",
            "required": True,
            "description": "Permanent engine execution identity.",
        },
        {
            "field": "engine_name",
            "type": "string",
            "required": True,
            "description": "Canonical engine name.",
        },
        {
            "field": "engine_version",
            "type": "string",
            "required": True,
            "description": "Canonical engine version.",
        },
        {
            "field": "configuration_version",
            "type": "string",
            "required": True,
            "description": "Configuration version.",
        },
        {
            "field": "input_snapshot_id",
            "type": "string",
            "required": True,
            "description": "Input warehouse snapshot.",
        },
        {
            "field": "started_at",
            "type": "timestamp",
            "required": True,
            "description": "Run start timestamp.",
        },
        {
            "field": "completed_at",
            "type": "timestamp",
            "required": False,
            "description": "Run completion timestamp.",
        },
        {
            "field": "run_status",
            "type": "string",
            "required": True,
            "description": "Started, completed, failed or superseded.",
        },
        {
            "field": "output_manifest",
            "type": "string",
            "required": False,
            "description": "Manifest of generated outputs.",
        },
    ],
}


MIGRATION_MAP: list[dict[str, Any]] = [
    {
        "domain": "raw_results",
        "source_asset": "public/data/edgeiq_historical_results_warehouse_v2_graphql.csv",
        "classification": "REUSABLE_AFTER_IDENTITY_REPAIR",
        "target_table": "source_evidence + performance_evidence",
        "priority": 1,
        "reason": "Deepest official historical coverage with provider race and runner identifiers.",
        "required_actions": "Resolve 89 duplicate performance keys; preserve monthly GraphQL files as source evidence; add immutable evidence versions.",
    },
    {
        "domain": "results_consolidation",
        "source_asset": "public/data/edgeiq_results_master_v1.csv",
        "classification": "REUSABLE_AFTER_SCHEMA_MIGRATION",
        "target_table": "performance_evidence",
        "priority": 2,
        "reason": "Largest consolidated result asset and broadest race coverage.",
        "required_actions": "Identify missing horse field mapping; create horse_id and performance_id; separate source evidence from derived fields.",
    },
    {
        "domain": "canonical_truth_experiment",
        "source_asset": "public/data/edgeiq_canonical_results_truth_v1.csv",
        "classification": "REUSABLE_LOGIC_NOT_CANONICAL_DATA",
        "target_table": "identity resolution and conflict-resolution rules",
        "priority": 3,
        "reason": "Contains useful canonicalisation concepts and complete derived performance keys over a smaller window.",
        "required_actions": "Extract rules; do not treat limited 2025-2026 output as global canonical warehouse.",
    },
    {
        "domain": "sectional_source",
        "source_asset": "public/data/racingcom_sectional_warehouse_v2.csv",
        "classification": "STRONG_RAW_SECTIONAL_CANDIDATE",
        "target_table": "performance_sectional_evidence",
        "priority": 1,
        "reason": "Runner-level sectional records with 130,484 unique performance rows and no duplicate performance keys.",
        "required_actions": "Attach canonical race_id and horse_id; preserve timing provider; formalise sectional quality states.",
    },
    {
        "domain": "standardised_sectionals",
        "source_asset": "public/data/edgeiq_standardised_sectionals_v1.csv",
        "classification": "DERIVED_ASSET_REQUIRES_DECOMPOSITION",
        "target_table": "performance_sectional_derivation",
        "priority": 2,
        "reason": "Large historical derived asset with benchmark and quality metadata.",
        "required_actions": "Do not use as raw sectional warehouse; reconstruct performance identities; add engine and conversion versions; separate raw seconds from derived lengths.",
    },
    {
        "domain": "sectional_identity",
        "source_asset": "public/data/edgeiq_sectional_identity_engine_v3.csv",
        "classification": "REUSABLE_IDENTITY_EVIDENCE",
        "target_table": "identity_resolution_event",
        "priority": 1,
        "reason": "Contains trusted, likely, unsafe and unresolved identity evidence.",
        "required_actions": "Do not treat rows as unique performances; preserve multiple candidate rows and resolution evidence; remove duplicated-performance assumption.",
    },
    {
        "domain": "runner_identity",
        "source_asset": "public/data/edgeiq_runner_entity_graph_v1.csv",
        "classification": "REUSABLE_ENTITY_GRAPH",
        "target_table": "canonical_horse + horse_alias + provider_horse_identifier",
        "priority": 1,
        "reason": "Largest existing identity-oriented asset.",
        "required_actions": "Audit columns and graph semantics; define permanent horse_id; retain aliases and provider IDs separately.",
    },
    {
        "domain": "benchmark_definitions",
        "source_asset": "public/data/edgeiq_standard_times_v1.csv",
        "classification": "LEGACY_BENCHMARK_SEED",
        "target_table": "benchmark_definition",
        "priority": 1,
        "reason": "Existing standard-time definitions can seed benchmark migration.",
        "required_actions": "Add benchmark_id, hierarchy level, eligibility counts, exclusions, confidence, version, validity window and warehouse snapshot.",
    },
    {
        "domain": "race_strength",
        "source_asset": "public/data/edgeiq_race_strength_v1.csv",
        "classification": "LEGACY_DERIVED_BENCHMARK",
        "target_table": "race_derivation",
        "priority": 2,
        "reason": "Existing race-strength history is useful but lacks complete canonical governance.",
        "required_actions": "Trace source inputs; add engine version and derivation run; separate retrospective and pre-race strength.",
    },
    {
        "domain": "performance_ratings",
        "source_asset": "public/data/edgeiq_historical_performance_rating_v5_1.csv",
        "classification": "REUSABLE_RESEARCH_OUTPUT",
        "target_table": "performance_derivation",
        "priority": 1,
        "reason": "Broad historical rating coverage and mature existing performance work.",
        "required_actions": "Create performance_id links; distinguish source evidence from rating outputs; preserve formula and engine version.",
    },
    {
        "domain": "runner_history",
        "source_asset": "public/data/edgeiq_runner_history_detail_v1.csv",
        "classification": "REUSABLE_APPLICATION_VIEW",
        "target_table": "query view generated from canonical warehouse",
        "priority": 3,
        "reason": "Best current integrated performance view but only 2,280 rows.",
        "required_actions": "Do not promote as warehouse; rebuild as a query product over canonical performance records.",
    },
    {
        "domain": "length_conversion",
        "source_asset": "scripts/build_edgeiq_standardised_sectionals_v1.py",
        "classification": "LEGACY_FIXED_CONVERSION",
        "target_table": "length_conversion_definition",
        "priority": 1,
        "reason": "Current conversion uses a fixed 0.17 seconds per length.",
        "required_actions": "Preserve as conversion version LEGACY_FIXED_0_17_V1; do not silently reuse as permanent universal conversion; formally test contextual alternatives.",
    },
    {
        "domain": "lengths_per_point",
        "source_asset": "public/data/edgeiq_lengths_per_point_engine_v1.csv",
        "classification": "RESEARCH_CANDIDATE",
        "target_table": "length_conversion_definition",
        "priority": 2,
        "reason": "May contain contextual conversion evidence.",
        "required_actions": "Trace creator logic and inputs; compare against fixed 0.17 methodology; validate units and sign convention.",
    },
]


QUALITY_STATES = [
    {
        "state": "COMPLETE",
        "meaning": "Required evidence is complete and internally consistent.",
        "usable_for_benchmarks": True,
        "usable_for_performance": True,
    },
    {
        "state": "PARTIAL",
        "meaning": "Some evidence exists but one or more expected fields are absent.",
        "usable_for_benchmarks": False,
        "usable_for_performance": "ENGINE_SPECIFIC",
    },
    {
        "state": "TIMING_INCONSISTENCY",
        "meaning": "Timing evidence is internally inconsistent.",
        "usable_for_benchmarks": False,
        "usable_for_performance": False,
    },
    {
        "state": "BENCHMARK_UNAVAILABLE",
        "meaning": "Valid performance evidence exists but no governed benchmark is available.",
        "usable_for_benchmarks": False,
        "usable_for_performance": False,
    },
    {
        "state": "SECTIONAL_MISMATCH",
        "meaning": "Sectional evidence does not reconcile with race or runner evidence.",
        "usable_for_benchmarks": False,
        "usable_for_performance": False,
    },
    {
        "state": "SOURCE_CONFLICT",
        "meaning": "Authoritative sources disagree.",
        "usable_for_benchmarks": False,
        "usable_for_performance": False,
    },
    {
        "state": "IDENTITY_UNRESOLVED",
        "meaning": "Race or horse identity cannot be safely resolved.",
        "usable_for_benchmarks": False,
        "usable_for_performance": False,
    },
    {
        "state": "INSUFFICIENT_EVIDENCE",
        "meaning": "Evidence does not satisfy minimum engine requirements.",
        "usable_for_benchmarks": False,
        "usable_for_performance": False,
    },
    {
        "state": "EXCLUDED",
        "meaning": "Explicitly excluded by a governed rule.",
        "usable_for_benchmarks": False,
        "usable_for_performance": False,
    },
    {
        "state": "SUPERSEDED",
        "meaning": "Replaced by a later immutable evidence version.",
        "usable_for_benchmarks": False,
        "usable_for_performance": False,
    },
    {
        "state": "PENDING_VALIDATION",
        "meaning": "Ingested but not yet validated.",
        "usable_for_benchmarks": False,
        "usable_for_performance": False,
    },
]


SOURCE_PRIORITY = [
    {
        "field_group": "official_result",
        "priority_1": "Official jurisdictional result source",
        "priority_2": "Racing.com official result feed",
        "priority_3": "TAB result feed",
        "priority_4": "Legacy EDGEiQ consolidation",
    },
    {
        "field_group": "official_sectionals",
        "priority_1": "Official timing provider payload",
        "priority_2": "Racing.com sectional payload",
        "priority_3": "Validated historical sectional warehouse",
        "priority_4": "No substitution",
    },
    {
        "field_group": "track_condition",
        "priority_1": "Official steward or jurisdiction result",
        "priority_2": "Official track manager source",
        "priority_3": "Racing.com result record",
        "priority_4": "No inferred going",
    },
    {
        "field_group": "horse_identity",
        "priority_1": "Provider registration or runner ID",
        "priority_2": "Jurisdiction horse code",
        "priority_3": "Validated entity graph",
        "priority_4": "Name-only match remains unresolved",
    },
    {
        "field_group": "race_identity",
        "priority_1": "Provider race ID",
        "priority_2": "Jurisdiction meeting and race ID",
        "priority_3": "Date-track-race composite with validation",
        "priority_4": "Unresolved",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def latest_phase03_detail() -> Path:
    candidates = sorted(
        PHASE03.glob(
            "edgeiq_performance_intelligence_phase0_3_detail_*.json"
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not candidates:
        raise FileNotFoundError(
            "Phase 0.3 detail JSON was not found."
        )

    return candidates[0]


def read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    )


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames: list[str] = []

    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def flatten_schema() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for table_name, fields in SCHEMA_TABLES.items():
        for position, field in enumerate(
            fields,
            start=1,
        ):
            rows.append(
                {
                    "table_name": table_name,
                    "position": position,
                    **field,
                }
            )

    return rows


def audit_script_syntax(
    phase03: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    seen: set[str] = set()

    for item in phase03.get(
        "script_profiles",
        [],
    ):
        path_text = item.get("path", "")

        if not path_text or path_text in seen:
            continue

        seen.add(path_text)

        path = ROOT / path_text
        content = ""

        try:
            content = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except OSError as exc:
            rows.append(
                {
                    "path": path_text,
                    "exists": path.exists(),
                    "syntax_status": "UNREADABLE",
                    "error_line": "",
                    "error_offset": "",
                    "error_message": str(exc),
                    "recommended_action": "Inspect file accessibility.",
                }
            )
            continue

        try:
            ast.parse(content)
            rows.append(
                {
                    "path": path_text,
                    "exists": True,
                    "syntax_status": "PARSED",
                    "error_line": "",
                    "error_offset": "",
                    "error_message": "",
                    "recommended_action": "Preserve and inspect lineage.",
                }
            )
        except SyntaxError as exc:
            rows.append(
                {
                    "path": path_text,
                    "exists": True,
                    "syntax_status": "SYNTAX_ERROR",
                    "error_line": exc.lineno or "",
                    "error_offset": exc.offset or "",
                    "error_message": exc.msg,
                    "recommended_action": (
                        "Do not execute or promote. Inspect whether the file "
                        "is malformed, truncated or obsolete."
                    ),
                }
            )

    return sorted(
        rows,
        key=lambda row: (
            row["syntax_status"] != "SYNTAX_ERROR",
            row["path"],
        ),
    )


def architecture_markdown() -> str:
    return """# EDGEiQ Performance Intelligence Platform
## Canonical Architecture Specification V0.1

### Permanent pipeline

Raw source evidence  
↓  
Validation  
↓  
Normalisation  
↓  
Canonical identity resolution  
↓  
Immutable performance evidence  
↓  
Governed benchmarks  
↓  
Performance derivations  
↓  
Pattern and fingerprint engines  
↓  
Horse and campaign intelligence  
↓  
Query services  
↓  
EDGEiQ product services  
↓  
React display

### Permanent rules

1. React does not calculate racing intelligence.
2. Raw evidence is immutable.
3. Corrected evidence creates a new version.
4. Every horse in every race receives one permanent `performance_id`.
5. Raw sectional seconds and derived lengths are stored separately.
6. Negative deviation always means faster or better than benchmark.
7. Positive deviation always means slower or worse than benchmark.
8. Every benchmark records hierarchy level, sample count, exclusions, confidence and version.
9. Every derivation records source evidence, benchmark, engine version and derivation run.
10. Missing intelligence remains unavailable and is never fabricated.

### Initial canonical candidate direction

- Historical raw results foundation:
  `edgeiq_historical_results_warehouse_v2_graphql.csv`
- Broad consolidation and coverage reconciliation:
  `edgeiq_results_master_v1.csv`
- Runner sectional evidence:
  `racingcom_sectional_warehouse_v2.csv`
- Existing sectional identity evidence:
  `edgeiq_sectional_identity_engine_v3.csv`
- Existing horse entity graph:
  `edgeiq_runner_entity_graph_v1.csv`
- Benchmark seed definitions:
  `edgeiq_standard_times_v1.csv`
- Historical rating research:
  `edgeiq_historical_performance_rating_v5_1.csv`
- Existing integrated application view:
  `edgeiq_runner_history_detail_v1.csv`
- Legacy conversion baseline:
  fixed `0.17 seconds per length`, preserved only as
  `LEGACY_FIXED_0_17_V1`

No current asset is yet declared globally canonical.
"""


def migration_markdown() -> str:
    lines = [
        "# EDGEiQ Performance Intelligence",
        "## Phase 0.4 Migration Map",
        "",
        "No production data is changed by this specification.",
        "",
        "| Priority | Domain | Source | Classification | Target | Required actions |",
        "|---:|---|---|---|---|---|",
    ]

    for row in sorted(
        MIGRATION_MAP,
        key=lambda item: (
            item["priority"],
            item["domain"],
        ),
    ):
        lines.append(
            f"| {row['priority']} | "
            f"{row['domain']} | "
            f"`{row['source_asset']}` | "
            f"{row['classification']} | "
            f"{row['target_table']} | "
            f"{row['required_actions']} |"
        )

    lines.extend(
        [
            "",
            "## Critical blockers",
            "",
            "- No current global immutable `performance_id`.",
            "- Results assets contain overlapping and differently structured truths.",
            "- The largest consolidated result asset lacks a safely detected horse identity.",
            "- The GraphQL historical warehouse contains 89 duplicate performance keys.",
            "- Standardised sectionals mix derived benchmark output with incomplete identity.",
            "- Existing benchmark definitions lack complete versioning and validity governance.",
            "- Existing length conversion uses a fixed 0.17 seconds-per-length constant.",
            "- No audited sign-convention implementation was located in the conversion scripts.",
            "- Several historical scripts currently fail Python syntax parsing and must not be executed or promoted.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    ARCHITECTURE.mkdir(
        parents=True,
        exist_ok=True,
    )
    AUDIT.mkdir(
        parents=True,
        exist_ok=True,
    )

    phase03_path = latest_phase03_detail()
    phase03 = read_json(phase03_path)

    syntax_rows = audit_script_syntax(
        phase03
    )

    syntax_error_rows = [
        row
        for row in syntax_rows
        if row["syntax_status"] == "SYNTAX_ERROR"
    ]

    schema_rows = flatten_schema()

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    schema_json = (
        ARCHITECTURE
        / "edgeiq_canonical_performance_schema_v0_1.json"
    )
    schema_csv = (
        ARCHITECTURE
        / "edgeiq_canonical_performance_schema_v0_1.csv"
    )
    architecture_md = (
        ARCHITECTURE
        / "EDGEIQ_PERFORMANCE_INTELLIGENCE_ARCHITECTURE_V0_1.md"
    )
    migration_json = (
        ARCHITECTURE
        / "edgeiq_performance_intelligence_migration_map_v0_1.json"
    )
    migration_csv = (
        ARCHITECTURE
        / "edgeiq_performance_intelligence_migration_map_v0_1.csv"
    )
    migration_md = (
        ARCHITECTURE
        / "EDGEIQ_PERFORMANCE_INTELLIGENCE_MIGRATION_MAP_V0_1.md"
    )
    quality_json = (
        ARCHITECTURE
        / "edgeiq_performance_quality_states_v0_1.json"
    )
    source_priority_json = (
        ARCHITECTURE
        / "edgeiq_source_priority_framework_v0_1.json"
    )
    syntax_csv = (
        AUDIT
        / f"edgeiq_performance_intelligence_phase0_4_script_syntax_{run_id}.csv"
    )
    summary_json = (
        AUDIT
        / f"edgeiq_performance_intelligence_phase0_4_summary_{run_id}.json"
    )
    latest_json = (
        AUDIT
        / "edgeiq_performance_intelligence_phase0_4_latest.json"
    )

    write_json(
        schema_json,
        {
            "schema_name": (
                "EDGEiQ Canonical Performance Schema"
            ),
            "schema_version": "0.1",
            "generated_utc": utc_now(),
            "sign_convention": {
                "negative": (
                    "Faster or better than benchmark"
                ),
                "positive": (
                    "Slower or worse than benchmark"
                ),
            },
            "tables": SCHEMA_TABLES,
        },
    )

    write_csv(
        schema_csv,
        schema_rows,
    )

    architecture_md.write_text(
        architecture_markdown(),
        encoding="utf-8",
    )

    write_json(
        migration_json,
        {
            "migration_map_version": "0.1",
            "generated_utc": utc_now(),
            "migrations": MIGRATION_MAP,
        },
    )

    write_csv(
        migration_csv,
        MIGRATION_MAP,
    )

    migration_md.write_text(
        migration_markdown(),
        encoding="utf-8",
    )

    write_json(
        quality_json,
        {
            "quality_state_version": "0.1",
            "generated_utc": utc_now(),
            "states": QUALITY_STATES,
        },
    )

    write_json(
        source_priority_json,
        {
            "source_priority_version": "0.1",
            "generated_utc": utc_now(),
            "field_priorities": SOURCE_PRIORITY,
        },
    )

    write_csv(
        syntax_csv,
        syntax_rows,
    )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 0.4 Canonical Schema and Migration Map"
        ),
        "generated_utc": utc_now(),
        "phase0_3_source": str(
            phase03_path.relative_to(ROOT)
        ).replace("\\", "/"),
        "schema_version": "0.1",
        "schema_tables": len(
            SCHEMA_TABLES
        ),
        "schema_fields": len(
            schema_rows
        ),
        "migration_entries": len(
            MIGRATION_MAP
        ),
        "quality_states": len(
            QUALITY_STATES
        ),
        "source_priority_groups": len(
            SOURCE_PRIORITY
        ),
        "scripts_checked": len(
            syntax_rows
        ),
        "syntax_error_scripts": len(
            syntax_error_rows
        ),
        "syntax_error_paths": [
            row["path"]
            for row in syntax_error_rows
        ],
        "canonical_status": (
            "ARCHITECTURE_DEFINED_DATA_NOT_MIGRATED"
        ),
        "next_stage": (
            "Phase 0.5 canonical performance identity "
            "and source-evidence migration prototype"
        ),
    }

    write_json(
        summary_json,
        summary,
    )
    write_json(
        latest_json,
        summary,
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE0_4_SCHEMA_MIGRATION_MAP_PASS",
        flush=True,
    )
    print(
        f"SCHEMA_JSON={schema_json}",
        flush=True,
    )
    print(
        f"SCHEMA_CSV={schema_csv}",
        flush=True,
    )
    print(
        f"ARCHITECTURE={architecture_md}",
        flush=True,
    )
    print(
        f"MIGRATION_JSON={migration_json}",
        flush=True,
    )
    print(
        f"MIGRATION_CSV={migration_csv}",
        flush=True,
    )
    print(
        f"MIGRATION_MD={migration_md}",
        flush=True,
    )
    print(
        f"QUALITY_STATES={quality_json}",
        flush=True,
    )
    print(
        f"SOURCE_PRIORITY={source_priority_json}",
        flush=True,
    )
    print(
        f"SYNTAX_AUDIT={syntax_csv}",
        flush=True,
    )
    print(
        f"SUMMARY={summary_json}",
        flush=True,
    )


if __name__ == "__main__":
    main()
