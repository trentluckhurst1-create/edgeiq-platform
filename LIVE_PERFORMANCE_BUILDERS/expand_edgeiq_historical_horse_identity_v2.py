from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path.cwd()

MASTER_PATH = ROOT / "public" / "data" / "edgeiq_canonical_horse_master_v2.csv"
MASTER_CANDIDATE_PATH = ROOT / "public" / "data" / "edgeiq_canonical_horse_master_v2_CANDIDATE.csv"
ALIAS_PATH = ROOT / "public" / "data" / "edgeiq_canonical_horse_alias_v2.csv"
ALIAS_CANDIDATE_PATH = ROOT / "public" / "data" / "edgeiq_canonical_horse_alias_v2_CANDIDATE.csv"

FAILURE_PATH = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
    / "historical-run-observation"
    / "edgeiq_historical_run_observation_v2_identity_failures.csv"
)

WAREHOUSE_BUILDER_PATH = (
    ROOT / "scripts" / "build_edgeiq_historical_run_observation_fact_v2.py"
)

DOC_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
    / "historical-horse-identity-expansion-v2"
)
AUDIT_JSON_PATH = DOC_DIR / "EDGEIQ_HISTORICAL_HORSE_IDENTITY_EXPANSION_V2_AUDIT.json"
AUDIT_MD_PATH = DOC_DIR / "EDGEIQ_HISTORICAL_HORSE_IDENTITY_EXPANSION_V2_AUDIT.md"
REGISTRATION_LEDGER_PATH = DOC_DIR / "edgeiq_historical_horse_identity_registration_v2.csv"
CONFLICT_LEDGER_PATH = DOC_DIR / "edgeiq_historical_horse_identity_conflicts_v2.csv"

BUILDER_VERSION = "EDGEIQ_CANONICAL_HORSE_MASTER_V2"
METHOD_VERSION = "HISTORICAL_IDENTITY_EXPANSION_V2"


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalise_name(value: Any) -> str:
    return " ".join(clean(value).upper().split())


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def evidence_hash(parts: list[str]) -> str:
    return sha256_text("|".join(clean(part) for part in parts))


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        return fields, [dict(row) for row in reader]


def write_csv_atomic(
    path: Path,
    fields: list[str],
    rows: list[dict[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with temporary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    temporary_path.replace(path)


def load_source_system_classifier():
    spec = importlib.util.spec_from_file_location(
        "edgeiq_historical_run_observation_builder_v2",
        WAREHOUSE_BUILDER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Unable to load warehouse builder: {WAREHOUSE_BUILDER_PATH}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    classifier = getattr(module, "source_system_from_path", None)
    if not callable(classifier):
        raise RuntimeError(
            "The historical warehouse builder does not expose "
            "source_system_from_path(). The repair will not guess source systems."
        )

    return classifier


def call_classifier(classifier, source_path: str) -> str:
    attempts = (source_path, Path(source_path))

    for argument in attempts:
        try:
            result = clean(classifier(argument)).upper()
            if result:
                return result
        except (TypeError, AttributeError):
            continue

    raise RuntimeError(
        f"Warehouse source-system classifier returned no value for: {source_path}"
    )


def require_files() -> None:
    required = (
        MASTER_PATH,
        ALIAS_PATH,
        FAILURE_PATH,
        WAREHOUSE_BUILDER_PATH,
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(
            "REQUIRED FILES MISSING:\n" + "\n".join(f"- {path}" for path in missing)
        )


def main() -> None:
    require_files()
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    classifier = load_source_system_classifier()

    master_fields, master_rows = read_csv(MASTER_PATH)
    alias_fields, alias_rows = read_csv(ALIAS_PATH)

    required_master_fields = {
        "canonical_horse_id",
        "canonical_horse_name",
        "normalised_horse_name",
        "primary_source_system",
        "primary_source_horse_id",
        "date_of_birth",
        "sex",
        "sire",
        "dam",
        "country",
        "horse_status",
        "source_record_count",
        "source_file_count",
        "identity_resolution_status",
        "identity_resolution_method",
        "horse_master_builder_version",
        "horse_master_method_version",
        "canonical_horse_evidence_sha256",
    }
    required_alias_fields = {
        "canonical_horse_id",
        "source_system",
        "source_horse_id",
        "source_horse_name",
        "normalised_horse_name",
        "source_path",
        "source_row_number",
        "source_row_evidence_sha256",
        "alias_builder_version",
        "alias_method_version",
        "alias_evidence_sha256",
    }

    missing_master_fields = sorted(required_master_fields - set(master_fields))
    missing_alias_fields = sorted(required_alias_fields - set(alias_fields))
    if missing_master_fields:
        raise SystemExit(f"MASTER SCHEMA MISMATCH: {missing_master_fields}")
    if missing_alias_fields:
        raise SystemExit(f"ALIAS SCHEMA MISMATCH: {missing_alias_fields}")

    master_by_id: dict[str, dict[str, str]] = {}
    for row in master_rows:
        canonical_id = clean(row.get("canonical_horse_id"))
        if not canonical_id:
            raise SystemExit("MASTER AUDIT FAIL: blank canonical_horse_id")
        if canonical_id in master_by_id:
            raise SystemExit(
                f"MASTER AUDIT FAIL: duplicate canonical_horse_id {canonical_id}"
            )
        master_by_id[canonical_id] = row

    alias_key_to_canonical: dict[tuple[str, str], str] = {}
    for row in alias_rows:
        system = clean(row.get("source_system")).upper()
        source_id = clean(row.get("source_horse_id"))
        canonical_id = clean(row.get("canonical_horse_id"))
        if not system or not source_id or not canonical_id:
            continue

        key = (system, source_id)
        prior = alias_key_to_canonical.get(key)
        if prior and prior != canonical_id:
            raise SystemExit(
                "ALIAS AUDIT FAIL: existing source identity maps to multiple "
                f"canonical horses: {key} -> {prior}, {canonical_id}"
            )
        alias_key_to_canonical[key] = canonical_id

    observed: dict[tuple[str, str], dict[str, Any]] = {}
    scan_rows = 0
    rows_without_source_id = 0

    with FAILURE_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        failure_fields = set(reader.fieldnames or [])
        required_failure_fields = {
            "source_path",
            "source_row_number",
            "source_horse_id",
            "source_horse_name",
            "source_row_evidence_sha256",
        }
        missing_failure_fields = sorted(required_failure_fields - failure_fields)
        if missing_failure_fields:
            raise SystemExit(
                f"FAILURE LEDGER SCHEMA MISMATCH: {missing_failure_fields}"
            )

        for scan_rows, row in enumerate(reader, start=1):
            source_id = clean(row.get("source_horse_id"))
            if not source_id:
                rows_without_source_id += 1
                continue

            source_path = clean(row.get("source_path"))
            source_system = call_classifier(classifier, source_path)
            key = (source_system, source_id)
            source_name = clean(row.get("source_horse_name"))

            item = observed.get(key)
            if item is None:
                observed[key] = {
                    "source_system": source_system,
                    "source_horse_id": source_id,
                    "source_horse_name": source_name,
                    "source_path": source_path,
                    "source_row_number": clean(row.get("source_row_number")),
                    "source_row_evidence_sha256": clean(
                        row.get("source_row_evidence_sha256")
                    ),
                    "source_paths": {source_path} if source_path else set(),
                    "source_record_count": 1,
                    "name_conflicts": set(),
                }
            else:
                item["source_record_count"] = int(item["source_record_count"]) + 1
                if source_path:
                    item["source_paths"].add(source_path)

                existing_name = clean(item.get("source_horse_name"))
                if not existing_name and source_name:
                    item["source_horse_name"] = source_name
                    item["source_path"] = source_path
                    item["source_row_number"] = clean(row.get("source_row_number"))
                    item["source_row_evidence_sha256"] = clean(
                        row.get("source_row_evidence_sha256")
                    )
                elif (
                    existing_name
                    and source_name
                    and normalise_name(existing_name) != normalise_name(source_name)
                ):
                    item["name_conflicts"].add(source_name)

            if scan_rows % 500_000 == 0:
                print(
                    "Identity expansion scan: "
                    f"{scan_rows:,} failure rows; "
                    f"{len(observed):,} unique source identities",
                    flush=True,
                )

    new_master_rows: list[dict[str, str]] = []
    new_alias_rows: list[dict[str, str]] = []
    registration_rows: list[dict[str, str]] = []
    conflict_rows: list[dict[str, str]] = []

    existing_identities_retained = 0
    source_id_only_registrations = 0
    named_registrations = 0

    for key in sorted(observed):
        source_system, source_id = key
        item = observed[key]

        existing_canonical = alias_key_to_canonical.get(key)
        if existing_canonical:
            existing_identities_retained += 1
            continue

        canonical_id = f"HORSE|{source_system}|{source_id}"
        source_name = clean(item.get("source_horse_name"))
        name_conflicts = sorted(item.get("name_conflicts") or set())

        if canonical_id in master_by_id:
            canonical_row = master_by_id[canonical_id]
            canonical_name = clean(canonical_row.get("canonical_horse_name"))
            resolution_status = clean(
                canonical_row.get("identity_resolution_status")
            ) or "RESOLVED_EXACT_SOURCE_ID"
        else:
            canonical_name = source_name
            if canonical_name:
                named_registrations += 1
                resolution_status = "RESOLVED_EXACT_SOURCE_ID"
                horse_status = "HISTORICAL"
            else:
                source_id_only_registrations += 1
                resolution_status = "SOURCE_ID_ONLY"
                horse_status = "HISTORICAL_ID_ONLY"

            master_evidence = evidence_hash(
                [
                    canonical_id,
                    canonical_name,
                    source_system,
                    source_id,
                    clean(item.get("source_path")),
                    clean(item.get("source_row_number")),
                    clean(item.get("source_row_evidence_sha256")),
                    METHOD_VERSION,
                ]
            )

            master_row = {field: "" for field in master_fields}
            master_row.update(
                {
                    "canonical_horse_id": canonical_id,
                    "canonical_horse_name": canonical_name,
                    "normalised_horse_name": normalise_name(canonical_name),
                    "primary_source_system": source_system,
                    "primary_source_horse_id": source_id,
                    "horse_status": horse_status,
                    "source_record_count": str(item["source_record_count"]),
                    "source_file_count": str(len(item["source_paths"])),
                    "identity_resolution_status": resolution_status,
                    "identity_resolution_method": (
                        "EXACT_SOURCE_SYSTEM_AND_SOURCE_HORSE_ID"
                    ),
                    "horse_master_builder_version": BUILDER_VERSION,
                    "horse_master_method_version": METHOD_VERSION,
                    "canonical_horse_evidence_sha256": master_evidence,
                }
            )
            master_rows.append(master_row)
            master_by_id[canonical_id] = master_row
            new_master_rows.append(master_row)

        alias_evidence = evidence_hash(
            [
                canonical_id,
                source_system,
                source_id,
                source_name,
                clean(item.get("source_path")),
                clean(item.get("source_row_number")),
                clean(item.get("source_row_evidence_sha256")),
                METHOD_VERSION,
            ]
        )

        alias_row = {field: "" for field in alias_fields}
        alias_row.update(
            {
                "canonical_horse_id": canonical_id,
                "source_system": source_system,
                "source_horse_id": source_id,
                "source_horse_name": source_name,
                "normalised_horse_name": normalise_name(source_name),
                "source_path": clean(item.get("source_path")),
                "source_row_number": clean(item.get("source_row_number")),
                "source_row_evidence_sha256": clean(
                    item.get("source_row_evidence_sha256")
                ),
                "alias_builder_version": BUILDER_VERSION,
                "alias_method_version": METHOD_VERSION,
                "alias_evidence_sha256": alias_evidence,
            }
        )
        alias_rows.append(alias_row)
        new_alias_rows.append(alias_row)
        alias_key_to_canonical[key] = canonical_id

        registration_rows.append(
            {
                "canonical_horse_id": canonical_id,
                "source_system": source_system,
                "source_horse_id": source_id,
                "source_horse_name": source_name,
                "identity_resolution_status": (
                    "RESOLVED_EXACT_SOURCE_ID" if source_name else "SOURCE_ID_ONLY"
                ),
                "source_record_count": str(item["source_record_count"]),
                "source_file_count": str(len(item["source_paths"])),
                "representative_source_path": clean(item.get("source_path")),
                "representative_source_row_number": clean(
                    item.get("source_row_number")
                ),
                "representative_source_row_evidence_sha256": clean(
                    item.get("source_row_evidence_sha256")
                ),
                "registration_evidence_sha256": evidence_hash(
                    [
                        canonical_id,
                        source_system,
                        source_id,
                        source_name,
                        str(item["source_record_count"]),
                        str(len(item["source_paths"])),
                        METHOD_VERSION,
                    ]
                ),
            }
        )

        if name_conflicts:
            conflict_rows.append(
                {
                    "source_system": source_system,
                    "source_horse_id": source_id,
                    "selected_source_horse_name": source_name,
                    "conflicting_source_horse_names": " | ".join(name_conflicts),
                    "conflict_resolution": (
                        "IDENTITY PRESERVED BY EXACT SOURCE ID; "
                        "NO NAME-BASED MERGE PERFORMED"
                    ),
                }
            )

    master_rows.sort(key=lambda row: clean(row.get("canonical_horse_id")))
    alias_rows.sort(
        key=lambda row: (
            clean(row.get("source_system")),
            clean(row.get("source_horse_id")),
            clean(row.get("source_path")),
            clean(row.get("source_row_number")),
        )
    )

    # Final integrity checks before replacing production files.
    final_master_ids = [clean(row.get("canonical_horse_id")) for row in master_rows]
    if len(final_master_ids) != len(set(final_master_ids)):
        raise SystemExit(
            "FINAL AUDIT FAIL: duplicate canonical_horse_id after expansion"
        )

    final_alias_map: dict[tuple[str, str], str] = {}
    for row in alias_rows:
        key = (
            clean(row.get("source_system")).upper(),
            clean(row.get("source_horse_id")),
        )
        canonical_id = clean(row.get("canonical_horse_id"))
        if not key[0] or not key[1] or not canonical_id:
            continue
        prior = final_alias_map.get(key)
        if prior and prior != canonical_id:
            raise SystemExit(
                f"FINAL AUDIT FAIL: alias conflict {key}: {prior} vs {canonical_id}"
            )
        final_alias_map[key] = canonical_id

    unresolved_observed_keys = [
        key for key in observed if key not in final_alias_map
    ]
    if unresolved_observed_keys:
        raise SystemExit(
            "FINAL AUDIT FAIL: "
            f"{len(unresolved_observed_keys):,} observed source identities "
            "remain without aliases"
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = DOC_DIR / "backups" / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MASTER_PATH, backup_dir / MASTER_PATH.name)
    shutil.copy2(ALIAS_PATH, backup_dir / ALIAS_PATH.name)

    write_csv_atomic(MASTER_PATH, master_fields, master_rows)
    write_csv_atomic(MASTER_CANDIDATE_PATH, master_fields, master_rows)
    write_csv_atomic(ALIAS_PATH, alias_fields, alias_rows)
    write_csv_atomic(ALIAS_CANDIDATE_PATH, alias_fields, alias_rows)

    registration_fields = [
        "canonical_horse_id",
        "source_system",
        "source_horse_id",
        "source_horse_name",
        "identity_resolution_status",
        "source_record_count",
        "source_file_count",
        "representative_source_path",
        "representative_source_row_number",
        "representative_source_row_evidence_sha256",
        "registration_evidence_sha256",
    ]
    conflict_fields = [
        "source_system",
        "source_horse_id",
        "selected_source_horse_name",
        "conflicting_source_horse_names",
        "conflict_resolution",
    ]
    write_csv_atomic(
        REGISTRATION_LEDGER_PATH,
        registration_fields,
        registration_rows,
    )
    write_csv_atomic(CONFLICT_LEDGER_PATH, conflict_fields, conflict_rows)

    audit = {
        "status": (
            "EDGEIQ_HISTORICAL_HORSE_IDENTITY_EXPANSION_V2_AUDIT_PASS"
        ),
        "failure_rows_scanned": scan_rows,
        "failure_rows_without_source_horse_id": rows_without_source_id,
        "unique_source_identities_observed": len(observed),
        "existing_source_identities_retained": existing_identities_retained,
        "new_master_identities_registered": len(new_master_rows),
        "new_aliases_registered": len(new_alias_rows),
        "new_named_identities": named_registrations,
        "new_source_id_only_identities": source_id_only_registrations,
        "source_name_conflicts_preserved": len(conflict_rows),
        "horse_master_rows_after_expansion": len(master_rows),
        "horse_alias_rows_after_expansion": len(alias_rows),
        "unresolved_observed_source_identities_after_expansion": 0,
        "backup_directory": str(backup_dir),
        "governance": {
            "warehouse_source_system_classifier_reused": True,
            "exact_source_system_and_source_id_keys_only": True,
            "fuzzy_matching_used": False,
            "name_based_merging_used": False,
            "missing_horse_names_invented": False,
            "source_name_conflicts_preserved": True,
        },
    }

    AUDIT_JSON_PATH.write_text(
        json.dumps(audit, indent=2) + "\n",
        encoding="utf-8",
    )

    AUDIT_MD_PATH.write_text(
        "# EDGEIQ Historical Horse Identity Expansion V2 Audit\n\n"
        f"Status: `{audit['status']}`\n\n"
        "## Results\n\n"
        f"- Failure rows scanned: `{scan_rows:,}`\n"
        f"- Rows without source horse ID: `{rows_without_source_id:,}`\n"
        f"- Unique source identities observed: `{len(observed):,}`\n"
        f"- Existing source identities retained: "
        f"`{existing_identities_retained:,}`\n"
        f"- New master identities registered: `{len(new_master_rows):,}`\n"
        f"- New aliases registered: `{len(new_alias_rows):,}`\n"
        f"- New named identities: `{named_registrations:,}`\n"
        f"- New source-ID-only identities: "
        f"`{source_id_only_registrations:,}`\n"
        f"- Source-name conflicts preserved: `{len(conflict_rows):,}`\n"
        f"- Horse Master rows after expansion: `{len(master_rows):,}`\n"
        f"- Horse Alias rows after expansion: `{len(alias_rows):,}`\n"
        "- Unresolved observed source identities after expansion: `0`\n\n"
        "## Governance\n\n"
        "- Exact source system plus exact source horse ID is the identity key.\n"
        "- The warehouse builder's source-system classifier is reused.\n"
        "- No fuzzy matching is used.\n"
        "- No name-only merging is used.\n"
        "- Missing horse names remain blank and are labelled `SOURCE_ID_ONLY`.\n"
        "- Conflicting source names are preserved in the conflict ledger.\n",
        encoding="utf-8",
    )

    print(json.dumps(audit, indent=2), flush=True)


if __name__ == "__main__":
    main()
