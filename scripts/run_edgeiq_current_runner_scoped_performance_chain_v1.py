from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def count_governed_snapshot_rows() -> int:
    path = (
        ROOT
        / "public"
        / "data"
        / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv"
    )

    if not path.exists():
        raise RuntimeError(
            f"Missing governed performance snapshot: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if not reader.fieldnames:
            raise RuntimeError(
                f"Governed snapshot has no header: {path}"
            )

        return sum(1 for _ in reader)




ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
REPORTS = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "final-current-runner-orchestration-repair-v1"
)

ROOT_CAUSE_DECISION = "ORCHESTRATOR_USES_CONTEXT_ONLY_CHAIN"
AUTHORITY_DECISION = "PRODUCTION_CHAIN_REQUIRES_NEW_NARROW_CURRENT_RUNNER_ORCHESTRATOR"

EXPECTED_COUNTS = {
    "current_runners": 114,
    "suitability_component": 51,
    "suitability_aggregate": 51,
    "race_context": 17,
    "performance_context": count_governed_snapshot_rows(),
    "context_parameter_selection": count_governed_snapshot_rows(),
    "context_adjustment": count_governed_snapshot_rows(),
    "context_adjusted_performance": count_governed_snapshot_rows(),
    "projected_performance": 51,
    "epi_component": 153,
    "epi": 51,
    "epi_distribution": 7,
    "epi_relative_context": 51,
    "epi_ordering": 51,
    "epi_ordering_summary": 7,
    "publication": 114,
    "publication_epi_attachments": 51,
    "publication_missing_epi": 63,
}

OUTPUT_FILES = {
    "race_entry_snapshot": "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv",
    "race_context": "edgeiq_race_context_authority_fact_v1.csv",
    "performance_context": "edgeiq_race_entry_performance_context_fact_v1.csv",
    "context_eligibility": "edgeiq_race_entry_context_eligibility_fact_v1.csv",
    "context_parameter_selection": "edgeiq_race_entry_context_parameter_selection_fact_v1.csv",
    "context_adjustment": "edgeiq_race_entry_context_adjustment_fact_v1.csv",
    "context_adjusted_performance": "edgeiq_race_entry_context_adjusted_performance_fact_v1.csv",
    "suitability_component": "edgeiq_race_entry_suitability_component_fact_v1.csv",
    "suitability_aggregate": "edgeiq_race_entry_suitability_aggregate_fact_v1.csv",
    "projected_performance": "edgeiq_race_entry_projected_performance_fact_v1.csv",
    "epi_component": "edgeiq_race_entry_epi_component_fact_v1.csv",
    "epi": "edgeiq_race_entry_epi_fact_v1.csv",
    "epi_distribution": "edgeiq_race_epi_distribution_fact_v1.csv",
    "epi_relative_context": "edgeiq_race_entry_epi_relative_context_fact_v1.csv",
    "epi_ordering": "edgeiq_race_entry_epi_ordering_fact_v1.csv",
    "epi_ordering_summary": "edgeiq_race_epi_ordering_summary_fact_v1.csv",
    "publication": "edgeiq_performance_intelligence_current_publication_v1.csv",
}

OVERLAY_INPUTS = [
    "edgeiq_daily_official_results_fact_v1.csv",
    "edgeiq_current_horse_identity_crosswalk_v1.csv",
    "edgeiq_ra_to_rcom_horse_identity_bridge_v1.csv",
    "edgeiq_form_guide_enriched_v2.csv",
    "edgeiq_race_entry_fact_v1.csv",
    "edgeiq_rcom_to_eiq_horse_identity_bridge_v1.csv",
    "edgeiq_rcom_to_eiq_horse_identity_bridge_v1_exceptions.csv",
    "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv",
    "edgeiq_race_entry_horse_performance_snapshot_fact_v1_exceptions.csv",
    "edgeiq_current_suitability_v1.csv",
    "edgeiq_context_parameter_registry_v1.csv",
    "edgeiq_epi_parameter_fact_v1.csv",
    "edgeiq_epi_component_normalisation_parameter_fact_v1.csv",
    "edgeiq_race_entry_eri_context_fact_v1.csv",
    "edgeiq_horse_performance_observation_fact_v1.csv",
    "edgeiq_horse_performance_aggregate_fact_v1.csv",
    "edgeiq_horse_performance_rating_fact_v1.csv",
    "edgeiq_race_entry_projected_performance_fact_v1.csv",
    "edgeiq_race_entry_suitability_component_fact_v1.csv",
    "edgeiq_race_entry_suitability_aggregate_fact_v1.csv",
    "edgeiq_race_entry_epi_component_fact_v1.csv",
    "edgeiq_race_entry_epi_fact_v1.csv",
]


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def row_count(path: Path) -> int:
    return len(read_csv(path)[1])


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def semantic_hash(path: Path) -> str:
    fields, rows = read_csv(path)
    volatile = {
        field
        for field in fields
        if "built_at" in field
        or "audited_at" in field
        or "generated_at" in field
        or "timestamp" in field
    }
    stable_rows = [
        {field: row.get(field, "") for field in fields if field not in volatile}
        for row in rows
    ]
    payload = json.dumps(stable_rows, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def import_script(relative_path: str):
    path = ROOT / relative_path
    module_name = "edgeiq_runtime_" + relative_path.replace("\\", "_").replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import script: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_main(relative_path: str, patches: dict[str, Any]) -> dict[str, Any]:
    module = import_script(relative_path)
    for name, value in patches.items():
        setattr(module, name, value)
    if hasattr(module, "COMPONENT_CONFIG"):
        config = module.COMPONENT_CONFIG
        if "HISTORICAL_PERFORMANCE" in config:
            config["HISTORICAL_PERFORMANCE"]["path"] = patches.get("PROJECTED_PATH", config["HISTORICAL_PERFORMANCE"]["path"])
        if "SUITABILITY" in config:
            config["SUITABILITY"]["path"] = patches.get("SUITABILITY_PATH", config["SUITABILITY"]["path"])
        if "RACE_CONTEXT" in config:
            config["RACE_CONTEXT"]["path"] = patches.get("ERI_CONTEXT_PATH", config["RACE_CONTEXT"]["path"])

    started = time.perf_counter()
    stdout = io.StringIO()
    stderr = io.StringIO()
    returncode = 0
    error = ""
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            module.main()
        except SystemExit as exc:
            code = exc.code
            returncode = int(code) if isinstance(code, int) else 1
            if returncode:
                error = str(code)
        except Exception as exc:
            returncode = 1
            error = f"{type(exc).__name__}: {exc}"
    return {
        "script": relative_path,
        "returncode": returncode,
        "runtime_seconds": round(time.perf_counter() - started, 3),
        "stdout_tail": stdout.getvalue()[-2000:],
        "stderr_tail": stderr.getvalue()[-2000:],
        "error": error,
    }


def prepare_overlay(output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    if output_root.resolve() == DATA.resolve():
        return
    for filename in OVERLAY_INPUTS:
        source = DATA / filename
        target = output_root / filename
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def make_empty_adjusted(source_path: Path, reports_root: Path) -> Path:
    fields, _ = read_csv(source_path)
    if not fields:
        fields = [
            "race_entry_context_adjusted_performance_id",
            "race_entry_context_adjustment_id",
            "race_entry_context_parameter_selection_id",
            "race_entry_context_eligibility_id",
            "race_entry_performance_context_id",
            "race_entry_id",
            "race_id",
            "race_date",
            "runner_id",
            "canonical_horse_id",
            "canonical_horse_name",
            "historical_rating_value",
            "context_parameter_id",
            "total_context_adjustment",
            "context_adjusted_performance_value",
            "context_adjusted_performance_decision",
            "race_entry_context_adjusted_performance_status",
            "source_adjustment_evidence_sha256",
            "race_entry_context_adjusted_performance_evidence_sha256",
            "source_adjustment_builder_version",
            "builder_version",
            "contract_version",
            "built_at_utc",
        ]
    path = reports_root / "runtime" / "edgeiq_current_runner_scoped_empty_context_adjusted_performance_fact_v1.csv"
    write_csv(path, fields, [])
    return path


def patches_for(stage: str, output_root: Path, reports_root: Path, scoped_adjusted: Path) -> dict[str, Any]:
    op = output_root
    audit = lambda name: op / name
    if stage == "performance_snapshot_build":
        return {
            "RACE_ENTRIES": op / "edgeiq_race_entry_fact_v1.csv",
            "IDENTITY_BRIDGE": op / "edgeiq_rcom_to_eiq_horse_identity_bridge_v1.csv",
            "IDENTITY_EXCEPTIONS": op / "edgeiq_rcom_to_eiq_horse_identity_bridge_v1_exceptions.csv",
            "HORSE_RATINGS": op / "edgeiq_horse_performance_rating_fact_v1.csv",
            "OUTPUT": op / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv",
            "REJECTIONS": op / "edgeiq_race_entry_horse_performance_snapshot_fact_v1_rejections.csv",
        }
    if stage == "race_context_build":
        docs = reports_root / "race-context-authority-task-local"
        return {
            "RACE_ENTRY_PATH": op / "edgeiq_race_entry_fact_v1.csv",
            "PERFORMANCE_CONTEXT_PATH": op / "edgeiq_race_entry_performance_context_fact_v1.csv",
            "SNAPSHOT_PATH": op / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv",
            "OUTPUT_PATH": op / "edgeiq_race_context_authority_fact_v1.csv",
            "AUDIT_PATH": op / "edgeiq_race_context_authority_fact_v1_audit.json",
            "SUMMARY_PATH": op / "edgeiq_race_context_authority_fact_v1_summary.csv",
            "DOCS": docs,
            "INVENTORY_CSV": docs / "EDGEIQ_RACE_CONTEXT_SOURCE_INVENTORY_V1.csv",
            "INVENTORY_JSON": docs / "EDGEIQ_RACE_CONTEXT_SOURCE_INVENTORY_V1.json",
            "INVENTORY_MD": docs / "EDGEIQ_RACE_CONTEXT_SOURCE_INVENTORY_V1.md",
            "TRACE_CSV": docs / "EDGEIQ_RACE_CONTEXT_TARGET_RACE_TRACE_V1.csv",
            "TRACE_JSON": docs / "EDGEIQ_RACE_CONTEXT_TARGET_RACE_TRACE_V1.json",
            "TRACE_MD": docs / "EDGEIQ_RACE_CONTEXT_TARGET_RACE_TRACE_V1.md",
            "REPORT_JSON": docs / "EDGEIQ_RACE_CONTEXT_AUTHORITY_DECISION_V1.json",
            "REPORT_MD": docs / "EDGEIQ_RACE_CONTEXT_AUTHORITY_DECISION_V1.md",
            "IDENTITY_MD": docs / "EDGEIQ_DETERMINISTIC_IDENTITY_BRIDGE_REQUIREMENT_V1.md",
        }
    if stage == "performance_context_build":
        return {
            "SNAPSHOT_PATH": op / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv",
            "RACE_ENTRY_PATH": op / "edgeiq_race_entry_fact_v1.csv",
            "OUTPUT_PATH": op / "edgeiq_race_entry_performance_context_fact_v1.csv",
        }
    if stage == "performance_context_audit":
        return {
            "SNAPSHOT_PATH": op / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv",
            "RACE_ENTRY_PATH": op / "edgeiq_race_entry_fact_v1.csv",
            "FACT_PATH": op / "edgeiq_race_entry_performance_context_fact_v1.csv",
            "AUDIT_PATH": op / "edgeiq_race_entry_performance_context_fact_v1_audit.json",
        }
    if stage == "context_eligibility_build":
        return {
            "INPUT_PATH": op / "edgeiq_race_entry_performance_context_fact_v1.csv",
            "OUTPUT_PATH": op / "edgeiq_race_entry_context_eligibility_fact_v1.csv",
        }
    if stage == "context_eligibility_audit":
        return {
            "SOURCE_PATH": op / "edgeiq_race_entry_performance_context_fact_v1.csv",
            "FACT_PATH": op / "edgeiq_race_entry_context_eligibility_fact_v1.csv",
            "AUDIT_PATH": op / "edgeiq_race_entry_context_eligibility_fact_v1_audit.json",
        }
    if stage == "context_parameter_selection_build":
        return {
            "ELIGIBILITY_PATH": op / "edgeiq_race_entry_context_eligibility_fact_v1.csv",
            "CONTEXT_PATH": op / "edgeiq_race_entry_performance_context_fact_v1.csv",
            "PARAMETER_PATH": op / "edgeiq_context_parameter_registry_v1.csv",
            "OUTPUT_PATH": op / "edgeiq_race_entry_context_parameter_selection_fact_v1.csv",
        }
    if stage == "context_parameter_selection_audit":
        return {
            "ELIGIBILITY_PATH": op / "edgeiq_race_entry_context_eligibility_fact_v1.csv",
            "CONTEXT_PATH": op / "edgeiq_race_entry_performance_context_fact_v1.csv",
            "PARAMETER_PATH": op / "edgeiq_context_parameter_registry_v1.csv",
            "FACT_PATH": op / "edgeiq_race_entry_context_parameter_selection_fact_v1.csv",
            "AUDIT_PATH": op / "edgeiq_race_entry_context_parameter_selection_fact_v1_audit.json",
        }
    if stage == "context_adjustment_build":
        return {
            "SELECTION_PATH": op / "edgeiq_race_entry_context_parameter_selection_fact_v1.csv",
            "CONTEXT_PATH": op / "edgeiq_race_entry_performance_context_fact_v1.csv",
            "PARAMETER_PATH": op / "edgeiq_context_parameter_registry_v1.csv",
            "OUTPUT_PATH": op / "edgeiq_race_entry_context_adjustment_fact_v1.csv",
        }
    if stage == "context_adjustment_audit":
        return {
            "SELECTION_PATH": op / "edgeiq_race_entry_context_parameter_selection_fact_v1.csv",
            "CONTEXT_PATH": op / "edgeiq_race_entry_performance_context_fact_v1.csv",
            "PARAMETER_PATH": op / "edgeiq_context_parameter_registry_v1.csv",
            "FACT_PATH": op / "edgeiq_race_entry_context_adjustment_fact_v1.csv",
            "AUDIT_PATH": op / "edgeiq_race_entry_context_adjustment_fact_v1_audit.json",
        }
    if stage == "context_adjusted_build":
        return {
            "SOURCE_PATH": op / "edgeiq_race_entry_context_adjustment_fact_v1.csv",
            "OUTPUT_PATH": op / "edgeiq_race_entry_context_adjusted_performance_fact_v1.csv",
        }
    if stage == "context_adjusted_audit":
        return {
            "SOURCE_PATH": op / "edgeiq_race_entry_context_adjustment_fact_v1.csv",
            "FACT_PATH": op / "edgeiq_race_entry_context_adjusted_performance_fact_v1.csv",
            "AUDIT_PATH": op / "edgeiq_race_entry_context_adjusted_performance_fact_v1_audit.json",
        }
    if stage == "suitability_component_build":
        return {
            "ADJUSTMENT_PATH": op / "edgeiq_race_entry_context_adjustment_fact_v1.csv",
            "ADJUSTED_PERFORMANCE_PATH": scoped_adjusted,
            "CURRENT_RESULTS_PATH": op / "edgeiq_daily_official_results_fact_v1.csv",
            "CURRENT_CROSSWALK_PATH": op / "edgeiq_current_horse_identity_crosswalk_v1.csv",
            "RA_TO_RCOM_BRIDGE_PATH": op / "edgeiq_ra_to_rcom_horse_identity_bridge_v1.csv",
            "FORM_GUIDE_PATH": op / "edgeiq_form_guide_enriched_v2.csv",
            "OUTPUT_PATH": op / "edgeiq_race_entry_suitability_component_fact_v1.csv",
        }
    if stage == "suitability_component_audit":
        return {
            "ADJUSTED_PATH": scoped_adjusted,
            "ADJUSTMENT_PATH": op / "edgeiq_race_entry_context_adjustment_fact_v1.csv",
            "FACT_PATH": op / "edgeiq_race_entry_suitability_component_fact_v1.csv",
            "AUDIT_PATH": op / "edgeiq_race_entry_suitability_component_fact_v1_audit.json",
        }
    if stage == "suitability_aggregate_build":
        return {
            "ADJUSTED_PERFORMANCE_PATH": scoped_adjusted,
            "COMPONENT_PATH": op / "edgeiq_race_entry_suitability_component_fact_v1.csv",
            "OUTPUT_PATH": op / "edgeiq_race_entry_suitability_aggregate_fact_v1.csv",
        }
    if stage == "suitability_aggregate_audit":
        return {
            "ADJUSTED_PATH": scoped_adjusted,
            "COMPONENT_PATH": op / "edgeiq_race_entry_suitability_component_fact_v1.csv",
            "FACT_PATH": op / "edgeiq_race_entry_suitability_aggregate_fact_v1.csv",
            "AUDIT_PATH": op / "edgeiq_race_entry_suitability_aggregate_fact_v1_audit.json",
        }
    if stage == "projected_build":
        return {
            "ADJUSTED_PATH": scoped_adjusted,
            "AGGREGATE_PATH": op / "edgeiq_race_entry_suitability_aggregate_fact_v1.csv",
            "OUTPUT_PATH": op / "edgeiq_race_entry_projected_performance_fact_v1.csv",
        }
    if stage == "projected_audit":
        return {
            "ADJUSTED_PATH": scoped_adjusted,
            "AGGREGATE_PATH": op / "edgeiq_race_entry_suitability_aggregate_fact_v1.csv",
            "FACT_PATH": op / "edgeiq_race_entry_projected_performance_fact_v1.csv",
            "AUDIT_PATH": op / "edgeiq_race_entry_projected_performance_fact_v1_audit.json",
        }
    if stage == "epi_component_build":
        return {
            "PROJECTED_PATH": op / "edgeiq_race_entry_projected_performance_fact_v1.csv",
            "SUITABILITY_PATH": op / "edgeiq_race_entry_suitability_aggregate_fact_v1.csv",
            "ERI_CONTEXT_PATH": op / "edgeiq_race_entry_eri_context_fact_v1.csv",
            "CURRENT_HORSE_IDENTITY_CROSSWALK_PATH": op / "edgeiq_current_horse_identity_crosswalk_v1.csv",
            "EPI_PARAMETER_PATH": op / "edgeiq_epi_parameter_fact_v1.csv",
            "NORMALISATION_PARAMETER_PATH": op / "edgeiq_epi_component_normalisation_parameter_fact_v1.csv",
            "OUTPUT_PATH": op / "edgeiq_race_entry_epi_component_fact_v1.csv",
        }
    if stage == "epi_component_audit":
        return {
            "FACT_PATH": op / "edgeiq_race_entry_epi_component_fact_v1.csv",
            "EPI_PARAMETER_PATH": op / "edgeiq_epi_parameter_fact_v1.csv",
            "NORMALISATION_PARAMETER_PATH": op / "edgeiq_epi_component_normalisation_parameter_fact_v1.csv",
            "AUDIT_PATH": op / "edgeiq_race_entry_epi_component_fact_v1_audit.json",
        }
    if stage == "epi_build":
        return {
            "COMPONENT_PATH": op / "edgeiq_race_entry_epi_component_fact_v1.csv",
            "PARAMETER_PATH": op / "edgeiq_epi_parameter_fact_v1.csv",
            "OUTPUT_PATH": op / "edgeiq_race_entry_epi_fact_v1.csv",
        }
    if stage == "epi_audit":
        return {
            "FACT_PATH": op / "edgeiq_race_entry_epi_fact_v1.csv",
            "COMPONENT_PATH": op / "edgeiq_race_entry_epi_component_fact_v1.csv",
            "PARAMETER_PATH": op / "edgeiq_epi_parameter_fact_v1.csv",
            "AUDIT_PATH": op / "edgeiq_race_entry_epi_fact_v1_audit.json",
        }
    if stage == "distribution_build":
        return {
            "SOURCE_PATH": op / "edgeiq_race_entry_epi_fact_v1.csv",
            "OUTPUT_PATH": op / "edgeiq_race_epi_distribution_fact_v1.csv",
        }
    if stage == "distribution_audit":
        return {
            "SOURCE_PATH": op / "edgeiq_race_entry_epi_fact_v1.csv",
            "FACT_PATH": op / "edgeiq_race_epi_distribution_fact_v1.csv",
            "AUDIT_PATH": op / "edgeiq_race_epi_distribution_fact_v1_audit.json",
        }
    if stage == "relative_context_build":
        return {
            "EPI_PATH": op / "edgeiq_race_entry_epi_fact_v1.csv",
            "DISTRIBUTION_PATH": op / "edgeiq_race_epi_distribution_fact_v1.csv",
            "OUTPUT_PATH": op / "edgeiq_race_entry_epi_relative_context_fact_v1.csv",
        }
    if stage == "relative_context_audit":
        return {
            "EPI_PATH": op / "edgeiq_race_entry_epi_fact_v1.csv",
            "DISTRIBUTION_PATH": op / "edgeiq_race_epi_distribution_fact_v1.csv",
            "FACT_PATH": op / "edgeiq_race_entry_epi_relative_context_fact_v1.csv",
            "AUDIT_PATH": op / "edgeiq_race_entry_epi_relative_context_fact_v1_audit.json",
        }
    if stage == "ordering_build":
        return {
            "SOURCE_PATH": op / "edgeiq_race_entry_epi_relative_context_fact_v1.csv",
            "OUTPUT_PATH": op / "edgeiq_race_entry_epi_ordering_fact_v1.csv",
        }
    if stage == "ordering_audit":
        return {
            "SOURCE_PATH": op / "edgeiq_race_entry_epi_relative_context_fact_v1.csv",
            "FACT_PATH": op / "edgeiq_race_entry_epi_ordering_fact_v1.csv",
            "AUDIT_PATH": op / "edgeiq_race_entry_epi_ordering_fact_v1_audit.json",
        }
    if stage == "summary_build":
        return {
            "SOURCE_PATH": op / "edgeiq_race_entry_epi_ordering_fact_v1.csv",
            "OUTPUT_PATH": op / "edgeiq_race_epi_ordering_summary_fact_v1.csv",
        }
    if stage == "summary_audit":
        return {
            "SOURCE_PATH": op / "edgeiq_race_entry_epi_ordering_fact_v1.csv",
            "FACT_PATH": op / "edgeiq_race_epi_ordering_summary_fact_v1.csv",
            "AUDIT_PATH": op / "edgeiq_race_epi_ordering_summary_fact_v1_audit.json",
        }
    if stage == "publication_build":
        return {
            "PUBLIC_DATA": op,
            "DOCS_OUT": reports_root / "current-lineage-publication",
        }
    return {}


STAGES = [
    ("race_context_build", "scripts/build_edgeiq_race_context_authority_fact_v1.py", "race_context"),
    ("performance_context_build", "scripts/build_edgeiq_race_entry_performance_context_fact_v1.py", "performance_context"),
    ("performance_context_audit", "scripts/audit_edgeiq_race_entry_performance_context_fact_v1.py", "performance_context"),
    ("context_eligibility_build", "scripts/build_edgeiq_race_entry_context_eligibility_fact_v1.py", "context_eligibility"),
    ("context_eligibility_audit", "scripts/audit_edgeiq_race_entry_context_eligibility_fact_v1.py", "context_eligibility"),
    ("context_parameter_selection_build", "scripts/build_edgeiq_race_entry_context_parameter_selection_fact_v1.py", "context_parameter_selection"),
    ("context_parameter_selection_audit", "scripts/audit_edgeiq_race_entry_context_parameter_selection_fact_v1.py", "context_parameter_selection"),
    ("context_adjustment_build", "scripts/build_edgeiq_race_entry_context_adjustment_fact_v1.py", "context_adjustment"),
    ("context_adjustment_audit", "scripts/audit_edgeiq_race_entry_context_adjustment_fact_v1.py", "context_adjustment"),
    ("context_adjusted_build", "scripts/build_edgeiq_race_entry_context_adjusted_performance_fact_v1.py", "context_adjusted_performance"),
    ("context_adjusted_audit", "scripts/audit_edgeiq_race_entry_context_adjusted_performance_fact_v1.py", "context_adjusted_performance"),
    ("suitability_component_build", "scripts/build_edgeiq_race_entry_suitability_component_fact_v1.py", "suitability_component"),
    ("suitability_component_audit", "scripts/audit_edgeiq_race_entry_suitability_component_fact_v1.py", "suitability_component"),
    ("suitability_aggregate_build", "scripts/build_edgeiq_race_entry_suitability_aggregate_fact_v1.py", "suitability_aggregate"),
    ("suitability_aggregate_audit", "scripts/audit_edgeiq_race_entry_suitability_aggregate_fact_v1.py", "suitability_aggregate"),
    ("projected_build", "scripts/build_edgeiq_race_entry_projected_performance_fact_v1.py", "projected_performance"),
    ("projected_audit", "scripts/audit_edgeiq_race_entry_projected_performance_fact_v1.py", "projected_performance"),
    ("epi_component_build", "scripts/build_edgeiq_race_entry_epi_component_fact_v1.py", "epi_component"),
    ("epi_component_audit", "scripts/audit_edgeiq_race_entry_epi_component_fact_v1.py", "epi_component"),
    ("epi_build", "scripts/build_edgeiq_race_entry_epi_fact_v1.py", "epi"),
    ("epi_audit", "scripts/audit_edgeiq_race_entry_epi_fact_v1.py", "epi"),
    ("distribution_build", "scripts/build_edgeiq_race_epi_distribution_fact_v1.py", "epi_distribution"),
    ("distribution_audit", "scripts/audit_edgeiq_race_epi_distribution_fact_v1.py", "epi_distribution"),
    ("relative_context_build", "scripts/build_edgeiq_race_entry_epi_relative_context_fact_v1.py", "epi_relative_context"),
    ("relative_context_audit", "scripts/audit_edgeiq_race_entry_epi_relative_context_fact_v1.py", "epi_relative_context"),
    ("ordering_build", "scripts/build_edgeiq_race_entry_epi_ordering_fact_v1.py", "epi_ordering"),
    ("ordering_audit", "scripts/audit_edgeiq_race_entry_epi_ordering_fact_v1.py", "epi_ordering"),
    ("summary_build", "scripts/build_edgeiq_race_epi_ordering_summary_fact_v1.py", "epi_ordering_summary"),
    ("summary_audit", "scripts/audit_edgeiq_race_epi_ordering_summary_fact_v1.py", "epi_ordering_summary"),
    ("publication_build", "scripts/build_edgeiq_performance_intelligence_current_lineage_repair_v1.py", "publication"),
]


REPRODUCTION_STAGES = [
    ("race_context_build", "scripts/build_edgeiq_race_context_authority_fact_v1.py", "race_context"),
    ("performance_context_build", "scripts/build_edgeiq_race_entry_performance_context_fact_v1.py", "performance_context"),
    ("context_eligibility_build", "scripts/build_edgeiq_race_entry_context_eligibility_fact_v1.py", "context_eligibility"),
    ("context_parameter_selection_build", "scripts/build_edgeiq_race_entry_context_parameter_selection_fact_v1.py", "context_parameter_selection"),
    ("context_adjustment_build", "scripts/build_edgeiq_race_entry_context_adjustment_fact_v1.py", "context_adjustment"),
    ("context_adjusted_build", "scripts/build_edgeiq_race_entry_context_adjusted_performance_fact_v1.py", "context_adjusted_performance"),
    ("suitability_component_build", "scripts/build_edgeiq_race_entry_suitability_component_fact_v1.py", "suitability_component"),
    ("suitability_aggregate_build", "scripts/build_edgeiq_race_entry_suitability_aggregate_fact_v1.py", "suitability_aggregate"),
    ("projected_build", "scripts/build_edgeiq_race_entry_projected_performance_fact_v1.py", "projected_performance"),
    ("epi_component_build", "scripts/build_edgeiq_race_entry_epi_component_fact_v1.py", "epi_component"),
    ("epi_build", "scripts/build_edgeiq_race_entry_epi_fact_v1.py", "epi"),
]


def stage_output(output_root: Path, count_name: str) -> Path | None:
    filename = OUTPUT_FILES.get(count_name)
    return output_root / filename if filename else None


def publication_counts(output_root: Path) -> tuple[int, int, int]:
    _, rows = read_csv(output_root / OUTPUT_FILES["publication"])
    yes = sum(1 for row in rows if row.get("epi_available") == "YES")
    return len(rows), yes, len(rows) - yes


def canonical_population_counts(output_root: Path) -> tuple[int, int]:
    path = output_root / "edgeiq_race_entry_fact_v1.csv"
    fields, rows = read_csv(path)

    if not rows:
        raise RuntimeError(
            "FAIL_FAST_CANONICAL_POPULATION: edgeiq_race_entry_fact_v1.csv has no rows"
        )

    required = {"race_date", "canonical_track", "race_number"}
    missing = sorted(required - set(fields))

    if missing:
        raise RuntimeError(
            f"FAIL_FAST_CANONICAL_POPULATION: missing columns={missing}"
        )

    race_keys = {
        (
            row.get("race_date", "").strip(),
            row.get("canonical_track", "").strip(),
            row.get("race_number", "").strip(),
        )
        for row in rows
    }

    race_keys = {
        key
        for key in race_keys
        if all(key)
    }

    if not race_keys:
        raise RuntimeError(
            "FAIL_FAST_CANONICAL_POPULATION: no canonical race keys"
        )

    return len(rows), len(race_keys)



def runtime_expected_counts(output_root: Path) -> dict[str, int]:
    expected = dict(EXPECTED_COUNTS)

    canonical_runners, canonical_races = canonical_population_counts(
        output_root
    )

    expected["current_runners"] = canonical_runners
    expected["race_context"] = canonical_races

    builder_path = (
        ROOT
        / "scripts"
        / "build_edgeiq_race_entry_suitability_component_fact_v1.py"
    )

    spec = importlib.util.spec_from_file_location(
        "edgeiq_runtime_current_suitability",
        builder_path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to load current suitability authority."
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    module.CURRENT_RACE_ENTRY_PATH = (
        output_root
        / "edgeiq_race_entry_fact_v1.csv"
    )
    module.CURRENT_RCOM_TO_EIQ_BRIDGE_PATH = (
        output_root
        / "edgeiq_rcom_to_eiq_horse_identity_bridge_v1.csv"
    )
    module.FORM_GUIDE_PATH = (
        output_root
        / "edgeiq_form_guide_enriched_v2.csv"
    )

    suitability_rows = (
        module.build_current_runner_component_rows()
    )

    suitability_count = len(
        suitability_rows
    )

    if suitability_count <= 0:
        raise RuntimeError(
            "No governed current suitability rows."
        )

    suitability_races = {
        str(row.get("race_id", "")).strip()
        for row in suitability_rows
        if str(row.get("race_id", "")).strip()
    }

    suitability_race_count = len(
        suitability_races
    )

    expected["suitability_component"] = suitability_count
    expected["suitability_aggregate"] = suitability_count
    expected["projected_performance"] = suitability_count
    expected["epi_component"] = suitability_count * 3
    expected["epi"] = suitability_count
    expected["epi_distribution"] = suitability_race_count
    expected["epi_relative_context"] = suitability_count
    expected["epi_ordering"] = suitability_count
    expected["epi_ordering_summary"] = suitability_race_count
    expected["publication"] = canonical_runners
    expected["publication_epi_attachments"] = suitability_count
    expected["publication_missing_epi"] = (
        canonical_runners - suitability_count
    )

    return expected



def gate_count(output_root: Path, count_name: str, expected: int) -> None:
    if count_name == "current_runners":
        actual, _ = canonical_population_counts(output_root)
    elif count_name == "publication_epi_attachments":
        _, actual, _ = publication_counts(output_root)
    elif count_name == "publication_missing_epi":
        _, _, actual = publication_counts(output_root)
    else:
        path = stage_output(output_root, count_name)
        actual = row_count(path) if path else 0
    if actual != expected:
        raise RuntimeError(
            f"FAIL_FAST_STAGE_GATE {count_name}: expected {expected}, actual {actual}"
        )


def validate_epi_ordering_enum(output_root: Path) -> None:
    _, rows = read_csv(output_root / OUTPUT_FILES["epi_ordering"])
    invalid = sorted(
        {
            row.get("epi_tie_status", "")
            for row in rows
            if row.get("epi_tie_status", "") not in {"EPI_UNIQUE", "EPI_TIED"}
        }
    )
    if invalid:
        raise RuntimeError(f"FAIL_FAST_STAGE_GATE epi_ordering_enum: invalid={invalid}")


def count_snapshot(output_root: Path) -> dict[str, int]:
    canonical_runners, _ = canonical_population_counts(output_root)
    counts = {
        "current_runners": canonical_runners,
        "race_context": row_count(output_root / OUTPUT_FILES["race_context"]),
        "performance_context": row_count(output_root / OUTPUT_FILES["performance_context"]),
        "context_parameter_selection": row_count(output_root / OUTPUT_FILES["context_parameter_selection"]),
        "context_adjustment": row_count(output_root / OUTPUT_FILES["context_adjustment"]),
        "context_adjusted_performance": row_count(output_root / OUTPUT_FILES["context_adjusted_performance"]),
        "suitability_component": row_count(output_root / OUTPUT_FILES["suitability_component"]),
        "suitability_aggregate": row_count(output_root / OUTPUT_FILES["suitability_aggregate"]),
        "projected_performance": row_count(output_root / OUTPUT_FILES["projected_performance"]),
        "epi_component": row_count(output_root / OUTPUT_FILES["epi_component"]),
        "epi": row_count(output_root / OUTPUT_FILES["epi"]),
        "epi_distribution": row_count(output_root / OUTPUT_FILES["epi_distribution"]),
        "epi_relative_context": row_count(output_root / OUTPUT_FILES["epi_relative_context"]),
        "epi_ordering": row_count(output_root / OUTPUT_FILES["epi_ordering"]),
        "epi_ordering_summary": row_count(output_root / OUTPUT_FILES["epi_ordering_summary"]),
    }
    publication, yes, missing = publication_counts(output_root)
    counts["publication"] = publication
    counts["publication_epi_attachments"] = yes
    counts["publication_missing_epi"] = missing
    return counts


def write_static_reports(reports_root: Path) -> None:
    write_csv(
        reports_root / "edgeiq_current_runner_orchestration_root_cause_v1.csv",
        [
            "primary_root_cause_decision",
            "production_chain_authority_decision",
            "first_divergence_stage",
            "decision_reason",
        ],
        [
            {
                "primary_root_cause_decision": ROOT_CAUSE_DECISION,
                "production_chain_authority_decision": AUTHORITY_DECISION,
                "first_divergence_stage": "Suitability Components Build",
                "decision_reason": (
                    "Failed production invoked the context-adjusted branch with two "
                    "PARAMETER_NOT_AVAILABLE rows, producing zero suitability rows while "
                    "returning success. The governed current-runner chain must preserve "
                    "official current-runner authority through suitability and projected "
                    "performance."
                ),
            }
        ],
    )
    write_csv(
        reports_root / "edgeiq_production_vs_task_local_command_comparison_v1.csv",
        [
            "stage",
            "failed_production_script",
            "failed_input_mode",
            "failed_output_rows",
            "repaired_orchestrator_mode",
            "expected_output_rows",
            "difference_from_successful_task_local_command",
        ],
        [
            {
                "stage": "Suitability Components",
                "failed_production_script": "scripts/build_edgeiq_race_entry_suitability_component_fact_v1.py",
                "failed_input_mode": "context_adjusted_performance_rows=2",
                "failed_output_rows": "0",
                "repaired_orchestrator_mode": "current_runner_scoped_empty_adjusted_authority",
                "expected_output_rows": "51",
                "difference_from_successful_task_local_command": "production used context-only branch instead of repaired current-runner branch",
            },
            {
                "stage": "Projected Performance",
                "failed_production_script": "scripts/build_edgeiq_race_entry_projected_performance_fact_v1.py",
                "failed_input_mode": "suitability_aggregate_rows=0",
                "failed_output_rows": "0",
                "repaired_orchestrator_mode": "current_runner_suitability_with_optional_context",
                "expected_output_rows": "51",
                "difference_from_successful_task_local_command": "production consumed zero aggregate rows after first divergence",
            },
            {
                "stage": "EPI Components",
                "failed_production_script": "scripts/build_edgeiq_race_entry_epi_component_fact_v1.py",
                "failed_input_mode": "projected_rows=0 suitability_rows=0",
                "failed_output_rows": "0",
                "repaired_orchestrator_mode": "multiple optional governed sources with current runner race context fallback",
                "expected_output_rows": "153",
                "difference_from_successful_task_local_command": "production propagated empty upstream facts",
            },
        ],
    )
    write_csv(
        reports_root / "edgeiq_current_runner_fail_fast_contract_v1.csv",
        ["stage", "required_count", "failure_action"],
        [
            {"stage": key, "required_count": value, "failure_action": "exit_nonzero_stop_later_stages"}
            for key, value in EXPECTED_COUNTS.items()
        ],
    )
    write_csv(
        reports_root / "edgeiq_current_runner_orchestration_source_diff_v1.csv",
        ["file", "change_type", "scope"],
        [
            {
                "file": "scripts/run_edgeiq_current_runner_scoped_performance_chain_v1.py",
                "change_type": "ADDED",
                "scope": "narrow production current-runner orchestration and fail-fast gates",
            }
        ],
    )


def run_chain(output_root: Path, reports_root: Path, mode: str, negative_test: str = "") -> dict[str, Any]:
    prepare_overlay(output_root)
    reports_root.mkdir(parents=True, exist_ok=True)
    write_static_reports(reports_root)

    snapshot_result = run_main(
        "scripts/build_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py",
        patches_for(
            "performance_snapshot_build",
            output_root,
            reports_root,
            output_root / OUTPUT_FILES["context_adjusted_performance"],
        ),
    )

    if snapshot_result["returncode"] != 0:
        return {
            "run_id": "EDGEIQ_CURRENT_RUNNER_SCOPED_PERFORMANCE_CHAIN_V1",
            "mode": mode,
            "negative_test": negative_test,
            "output_root": rel(output_root),
            "root_cause_decision": ROOT_CAUSE_DECISION,
            "production_chain_authority_decision": AUTHORITY_DECISION,
            "status": "FAIL",
            "failed_stage": "performance_snapshot_build",
            "failure_message": snapshot_result["error"],
            "counts": count_snapshot(output_root),
            "semantic_hashes": {
                key: semantic_hash(path)
                for key, filename in OUTPUT_FILES.items()
                if (path := output_root / filename).exists()
            },
            "built_at_utc": utc_now(),
        }

    expected_counts = runtime_expected_counts(output_root)

    gate_count(
        output_root,
        "current_runners",
        expected_counts["current_runners"],
    )

    if negative_test == "missing_suitability_input":
        target = output_root / "edgeiq_form_guide_enriched_v2.csv"
        if target.exists():
            target.unlink()
    elif negative_test == "empty_suitability_source":
        target = output_root / "edgeiq_form_guide_enriched_v2.csv"
        fields, _ = read_csv(target)
        write_csv(target, fields, [])

    actual_adjusted = output_root / OUTPUT_FILES["context_adjusted_performance"]
    scoped_adjusted = actual_adjusted
    if mode == "repaired":
        scoped_adjusted = make_empty_adjusted(actual_adjusted, reports_root)

    stage_records: list[dict[str, Any]] = []
    stages = REPRODUCTION_STAGES if mode == "reproduce-collapse" else STAGES

    status = "PASS"
    failed_stage = ""
    failure_message = ""

    for stage_key, script, count_name in stages:
        patches = patches_for(stage_key, output_root, reports_root, scoped_adjusted)
        if negative_test == "wrong_suitability_input_path" and stage_key == "suitability_component_build":
            patches["FORM_GUIDE_PATH"] = output_root / "does_not_exist" / "edgeiq_form_guide_enriched_v2.csv"
        if negative_test == "zero_publication_epi_input" and stage_key == "publication_build":
            epi_path = output_root / OUTPUT_FILES["epi"]
            fields, _ = read_csv(epi_path)
            write_csv(epi_path, fields, [])
        result = run_main(script, patches)
        output_path = stage_output(output_root, count_name)
        actual_count = row_count(output_path) if output_path else 0
        record = {
            "stage": stage_key,
            "script": script,
            "returncode": result["returncode"],
            "output_path": rel(output_path) if output_path else "",
            "produced_row_count": actual_count,
            "stdout_tail": result["stdout_tail"].replace("\n", "\\n"),
            "stderr_tail": result["stderr_tail"].replace("\n", "\\n"),
            "error": result["error"],
        }
        stage_records.append(record)
        if result["returncode"] != 0:
            status = "FAIL"
            failed_stage = stage_key
            failure_message = result["error"] or result["stderr_tail"]
            break

        try:
            if mode == "repaired":
                if stage_key == "projected_build" and negative_test == "missing_projected_performance_output":
                    (output_root / OUTPUT_FILES["projected_performance"]).unlink(missing_ok=True)
                if stage_key == "epi_component_build" and negative_test == "empty_epi_component_output":
                    fields, _ = read_csv(output_root / OUTPUT_FILES["epi_component"])
                    write_csv(output_root / OUTPUT_FILES["epi_component"], fields, [])
                if stage_key == "ordering_build" and negative_test == "invalid_epi_enum_token":
                    path = output_root / OUTPUT_FILES["epi_ordering"]
                    fields, rows = read_csv(path)
                    if rows:
                        rows[0]["epi_tie_status"] = "UNIQUE_EPI"
                    write_csv(path, fields, rows)

                gate_targets = {
                    "race_context_build": "race_context",
                    "performance_context_build": "performance_context",
                    "context_parameter_selection_build": "context_parameter_selection",
                    "context_adjustment_build": "context_adjustment",
                    "context_adjusted_build": "context_adjusted_performance",
                    "suitability_component_build": "suitability_component",
                    "suitability_aggregate_build": "suitability_aggregate",
                    "projected_build": "projected_performance",
                    "epi_component_build": "epi_component",
                    "epi_build": "epi",
                    "distribution_build": "epi_distribution",
                    "relative_context_build": "epi_relative_context",
                    "ordering_build": "epi_ordering",
                    "summary_build": "epi_ordering_summary",
                    "publication_build": "publication",
                }
                target = gate_targets.get(stage_key)
                if target in expected_counts:
                    gate_count(output_root, target, expected_counts[target])
                if stage_key == "ordering_build":
                    validate_epi_ordering_enum(output_root)
                if stage_key == "publication_build":
                    gate_count(
                        output_root,
                        "publication_epi_attachments",
                        expected_counts["publication_epi_attachments"],
                    )
                    gate_count(
                        output_root,
                        "publication_missing_epi",
                        expected_counts["publication_missing_epi"],
                    )
        except Exception as exc:
            status = "FAIL"
            failed_stage = stage_key
            failure_message = str(exc)
            stage_records[-1]["gate_error"] = failure_message
            break

    trace_fields = [
        "stage",
        "script",
        "returncode",
        "output_path",
        "produced_row_count",
        "stdout_tail",
        "stderr_tail",
        "error",
        "gate_error",
    ]
    write_csv(reports_root / "edgeiq_current_runner_stage_trace_v1.csv", trace_fields, stage_records)

    counts = count_snapshot(output_root)
    hashes = {
        name: semantic_hash(output_root / filename)
        for name, filename in OUTPUT_FILES.items()
        if (output_root / filename).exists()
    }
    payload = {
        "run_id": "EDGEIQ_CURRENT_RUNNER_SCOPED_PERFORMANCE_CHAIN_V1",
        "built_at_utc": utc_now(),
        "mode": mode,
        "negative_test": negative_test,
        "status": status,
        "failed_stage": failed_stage,
        "failure_message": failure_message,
        "root_cause_decision": ROOT_CAUSE_DECISION,
        "production_chain_authority_decision": AUTHORITY_DECISION,
        "output_root": rel(output_root),
        "counts": counts,
        "semantic_hashes": hashes,
    }
    write_json(reports_root / "EDGEIQ_FINAL_CURRENT_RUNNER_ORCHESTRATION_REPAIR_V1.json", payload)
    write_csv(
        reports_root / "edgeiq_current_runner_task_local_validation_v1.csv",
        ["metric", "expected", "actual", "status"],
        [
            {
                "metric": key,
                "expected": expected,
                "actual": counts.get(key, ""),
                "status": "PASS" if counts.get(key) == expected else "FAIL",
            }
            for key, expected in expected_counts.items()
        ],
    )
    (reports_root / "EDGEIQ_FINAL_CURRENT_RUNNER_ORCHESTRATION_REPAIR_V1.md").write_text(
        "\n".join(
            [
                "# EDGEiQ Final Current Runner Orchestration Repair V1",
                "",
                f"Status: `{status}`",
                f"Root cause: `{ROOT_CAUSE_DECISION}`",
                f"Authority: `{AUTHORITY_DECISION}`",
                f"First failed stage: `{failed_stage}`",
                f"Failure message: `{failure_message}`",
                "",
                "## Counts",
                *[f"- {key}: `{value}`" for key, value in counts.items()],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    if status != "PASS":
        raise SystemExit(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DATA)
    parser.add_argument("--reports-root", type=Path, default=REPORTS)
    parser.add_argument("--mode", choices=["repaired", "reproduce-collapse"], default="repaired")
    parser.add_argument("--negative-test", default="")
    args = parser.parse_args()
    run_chain(
        args.output_root.resolve(),
        args.reports_root.resolve(),
        args.mode,
        args.negative_test,
    )


if __name__ == "__main__":
    main()
