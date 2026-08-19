from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "victoria-performance-intelligence-race-context-authority-v1"

OUTPUT_PATH = DATA / "edgeiq_context_parameter_registry_v1.csv"
SUMMARY_PATH = DATA / "edgeiq_context_parameter_registry_v1_summary.csv"
AUDIT_PATH = DATA / "edgeiq_context_parameter_registry_v1_audit.json"
REPORT_PATH = DOCS / "EDGEIQ_CONTEXT_PARAMETER_REGISTRY_V1.md"

BUILDER_VERSION = "edgeiq_context_parameter_registry_v1.0.0_header_only_governed_unavailable"
CONTRACT_VERSION = "1.0.0"
BUILT_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

FIELDS = [
    "context_parameter_id",
    "race_distance_m",
    "race_class_code",
    "track_id",
    "track_configuration",
    "track_condition",
    "racing_surface",
    "barrier_band",
    "weight_band",
    "field_size_band",
    "distance_adjustment",
    "class_adjustment",
    "track_adjustment",
    "track_configuration_adjustment",
    "track_condition_adjustment",
    "surface_adjustment",
    "barrier_adjustment",
    "weight_adjustment",
    "field_size_adjustment",
    "parameter_status",
    "context_parameter_evidence_sha256",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


def sha256_payload(parts: list[Any]) -> str:
    payload = "\x1f".join(str(part if part is not None else "") for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def atomic_write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        with temporary_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        temporary_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    status = "BLOCKED_CONTEXT_PARAMETER_REGISTRY_UNAVAILABLE"
    evidence_sha = sha256_payload(
        [
            "EDGEIQ_CONTEXT_PARAMETER_REGISTRY_V1",
            "HEADER_ONLY",
            "NO_GOVERNED_EMPIRICAL_CONTEXT_PARAMETERS_AVAILABLE",
            BUILDER_VERSION,
            CONTRACT_VERSION,
        ]
    )

    atomic_write_csv(OUTPUT_PATH, FIELDS, rows)
    atomic_write_csv(
        SUMMARY_PATH,
        ["metric", "value"],
        [
            {"metric": "status", "value": status},
            {"metric": "registry_rows", "value": 0},
            {"metric": "governed_parameter_rows", "value": 0},
            {"metric": "adjustment_components_fabricated", "value": "NO"},
            {"metric": "parameter_coefficients_estimated", "value": "NO"},
            {"metric": "parameter_coefficients_defaulted", "value": "NO"},
            {"metric": "builder_version", "value": BUILDER_VERSION},
            {"metric": "contract_version", "value": CONTRACT_VERSION},
            {"metric": "built_at_utc", "value": BUILT_AT},
        ],
    )

    audit = {
        "audit_name": "edgeiq_context_parameter_registry_v1",
        "audited_at_utc": BUILT_AT,
        "status": status,
        "checks": {
            "registry_file_published": {"status": "PASS", "detail": str(OUTPUT_PATH)},
            "contract_header_published": {"status": "PASS", "detail": FIELDS},
            "no_fabricated_adjustments": {"status": "PASS", "detail": True},
            "no_default_parameters": {"status": "PASS", "detail": True},
            "no_empirical_coefficients_available": {"status": "PASS", "detail": True},
        },
        "counts": {
            "registry_rows": 0,
            "governed_parameter_rows": 0,
        },
        "evidence_sha256": evidence_sha,
        "builder_version": BUILDER_VERSION,
        "contract_version": CONTRACT_VERSION,
    }
    atomic_write_json(AUDIT_PATH, audit)

    REPORT_PATH.write_text(
        "\n".join(
            [
                "# EDGEIQ Context Parameter Registry V1",
                "",
                f"Built: {BUILT_AT}",
                "",
                f"Status: {status}",
                "",
                "This governed authority is intentionally header-only because no governed empirical context-parameter source was found in the repository.",
                "",
                "No distance, class, track, condition, surface, barrier, weight or field-size adjustment coefficients were invented, defaulted, inferred, interpolated or estimated.",
                "",
                "The header-only publication allows downstream builders to fail closed with PARAMETER_NOT_AVAILABLE instead of crashing on a missing canonical registry file.",
                "",
                "EPI remains blocked until governed empirical context parameters are authored or ingested with lineage.",
                "",
                f"Evidence SHA-256: {evidence_sha}",
            ]
        ),
        encoding="utf-8",
    )

    print(f"status={status}")
    print("registry_rows=0")
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
