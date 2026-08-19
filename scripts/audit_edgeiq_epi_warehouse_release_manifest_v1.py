from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

MANIFEST_PATH = (
    DATA
    / "edgeiq_epi_warehouse_release_manifest_v1.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_epi_warehouse_release_manifest_v1_contract.json"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_epi_warehouse_release_manifest_v1_audit.json"
)

EXPECTED_RELEASE_DECISION = (
    "EPI_WAREHOUSE_V1_RELEASED"
)
EXPECTED_RECONCILIATION_DECISION = (
    "EPI_WAREHOUSE_V1_RECONCILED"
)
EXPECTED_RELEASE_STATUS = (
    "GOVERNED_EPI_WAREHOUSE_RELEASE"
)


def text(value: object) -> str:
    return str(
        value if value is not None else ""
    ).strip()


def sha256_text(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def sha256_payload(
    parts: Iterable[object],
) -> str:
    return sha256_text(
        "\x1f".join(
            text(part)
            for part in parts
        )
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def run_git(
    *arguments: str,
) -> str:
    completed = subprocess.run(
        [
            "git",
            *arguments,
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if completed.returncode != 0:
        raise RuntimeError(
            "Git command failed: "
            f"git {' '.join(arguments)}\n"
            f"{completed.stderr}"
        )

    return completed.stdout.strip()


def atomic_write_json(
    path: Path,
    payload: dict,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )

    os.close(descriptor)
    temporary_path = Path(temporary_name)

    try:
        temporary_path.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def read_csv_rows(
    path: Path,
) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return list(
            csv.DictReader(handle)
        )


def main() -> None:
    checks: dict[str, dict[str, object]] = {}

    def check(
        name: str,
        passed: bool,
        detail: object,
    ) -> None:
        checks[name] = {
            "status": (
                "PASS"
                if passed
                else "FAIL"
            ),
            "detail": detail,
        }

    missing_paths = [
        str(path.relative_to(ROOT))
        for path in [
            MANIFEST_PATH,
            CONTRACT_PATH,
        ]
        if not path.exists()
    ]

    check(
        "required_files_exist",
        not missing_paths,
        missing_paths,
    )

    if missing_paths:
        payload = {
            "audit_name": (
                "edgeiq_epi_warehouse_release_manifest_v1"
            ),
            "audit_version": "1.0.0",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(
            AUDIT_PATH,
            payload,
        )

        raise SystemExit(
            "EDGEIQ_EPI_WAREHOUSE_RELEASE_MANIFEST_V1_AUDIT_FAIL"
        )

    contract = json.loads(
        CONTRACT_PATH.read_text(
            encoding="utf-8"
        )
    )

    manifest = json.loads(
        MANIFEST_PATH.read_text(
            encoding="utf-8"
        )
    )

    check(
        "top_level_fields_exact",
        set(manifest.keys())
        == set(
            contract[
                "required_top_level_fields"
            ]
        ),
        {
            "actual": list(
                manifest.keys()
            ),
            "expected": contract[
                "required_top_level_fields"
            ],
        },
    )

    layers = manifest.get(
        "governed_layers",
        [],
    )

    check(
        "required_layer_count",
        len(layers)
        == contract[
            "required_layer_count"
        ],
        len(layers),
    )

    layer_field_errors: list[str] = []
    artifact_field_errors: list[str] = []
    artifact_hash_errors: list[str] = []
    artifact_git_errors: list[str] = []
    audit_errors: list[str] = []
    contract_errors: list[str] = []
    row_count_errors: list[str] = []
    layer_evidence_errors: list[str] = []

    all_artifact_evidence: list[str] = []

    for layer in layers:
        base = text(
            layer.get(
                "layer_base_name"
            )
        )

        if set(layer.keys()) != set(
            contract[
                "required_layer_fields"
            ]
        ):
            layer_field_errors.append(
                base
            )

        artifacts = layer.get(
            "artifacts",
            [],
        )

        if len(artifacts) != contract[
            "required_artifact_count_per_layer"
        ]:
            artifact_field_errors.append(
                f"{base}:artifact_count"
            )

        artifact_hashes: list[str] = []

        role_paths: dict[str, Path] = {}

        for artifact in artifacts:
            if set(
                artifact.keys()
            ) != set(
                contract[
                    "required_artifact_fields"
                ]
            ):
                artifact_field_errors.append(
                    f"{base}:artifact_fields"
                )

            role = text(
                artifact.get(
                    "artifact_role"
                )
            )

            repository_path = text(
                artifact.get(
                    "repository_path"
                )
            )

            absolute_path = (
                ROOT
                / Path(repository_path)
            )

            role_paths[role] = absolute_path

            if not absolute_path.exists():
                artifact_hash_errors.append(
                    f"{base}:{role}:missing"
                )
                continue

            actual_size = (
                absolute_path.stat().st_size
            )

            actual_hash = sha256_file(
                absolute_path
            )

            if actual_size != artifact.get(
                "size_bytes"
            ):
                artifact_hash_errors.append(
                    f"{base}:{role}:size"
                )

            if actual_hash != text(
                artifact.get("sha256")
            ):
                artifact_hash_errors.append(
                    f"{base}:{role}:sha256"
                )

            artifact_hashes.append(
                actual_hash
            )

            tracked = subprocess.run(
                [
                    "git",
                    "ls-files",
                    "--error-unmatch",
                    "--",
                    repository_path,
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            ).returncode == 0

            clean = not run_git(
                "status",
                "--porcelain",
                "--",
                repository_path,
            )

            if (
                artifact.get(
                    "git_tracked"
                )
                is not True
                or not tracked
            ):
                artifact_git_errors.append(
                    f"{base}:{role}:tracked"
                )

            if (
                artifact.get(
                    "git_clean"
                )
                is not True
                or not clean
            ):
                artifact_git_errors.append(
                    f"{base}:{role}:clean"
                )

            all_artifact_evidence.append(
                sha256_payload(
                    [
                        layer.get(
                            "layer_sequence"
                        ),
                        base,
                        role,
                        repository_path,
                        actual_size,
                        actual_hash,
                    ]
                )
            )

        contract_path = role_paths.get(
            "contract"
        )

        audit_path = role_paths.get(
            "audit"
        )

        fact_path = role_paths.get(
            "fact"
        )

        if contract_path and contract_path.exists():
            source_contract = json.loads(
                contract_path.read_text(
                    encoding="utf-8"
                )
            )

            if text(
                source_contract.get(
                    "contract_name"
                )
            ) != text(
                layer.get(
                    "contract_name"
                )
            ):
                contract_errors.append(
                    base
                )

        if audit_path and audit_path.exists():
            source_audit = json.loads(
                audit_path.read_text(
                    encoding="utf-8"
                )
            )

            if text(
                source_audit.get("status")
            ) != "PASS":
                audit_errors.append(
                    base
                )

            if source_audit.get(
                "counts",
                {},
            ) != layer.get(
                "audit_counts",
                {},
            ):
                audit_errors.append(
                    f"{base}:counts"
                )

        if fact_path and fact_path.exists():
            with fact_path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as handle:
                reader = csv.DictReader(
                    handle
                )

                fields = list(
                    reader.fieldnames
                    or []
                )

                rows = list(reader)

            if len(rows) != layer.get(
                "fact_row_count"
            ):
                row_count_errors.append(
                    f"{base}:rows"
                )

            if len(fields) != layer.get(
                "fact_column_count"
            ):
                row_count_errors.append(
                    f"{base}:columns"
                )

        expected_layer_evidence = sha256_payload(
            [
                layer.get(
                    "layer_sequence"
                ),
                layer.get(
                    "layer_name"
                ),
                base,
                layer.get(
                    "contract_name"
                ),
                layer.get(
                    "fact_row_count"
                ),
                layer.get(
                    "fact_column_count"
                ),
                layer.get(
                    "audit_status"
                ),
                canonical_json(
                    layer.get(
                        "audit_counts",
                        {},
                    )
                ),
                *artifact_hashes,
            ]
        )

        if expected_layer_evidence != text(
            layer.get(
                "layer_evidence_sha256"
            )
        ):
            layer_evidence_errors.append(
                base
            )

    check(
        "layer_fields_exact",
        not layer_field_errors,
        layer_field_errors,
    )

    check(
        "artifact_fields_exact",
        not artifact_field_errors,
        artifact_field_errors,
    )

    check(
        "artifact_hashes_and_sizes_valid",
        not artifact_hash_errors,
        artifact_hash_errors,
    )

    check(
        "governed_artifacts_tracked_and_clean",
        not artifact_git_errors,
        artifact_git_errors,
    )

    check(
        "source_audits_pass_and_match",
        not audit_errors,
        audit_errors,
    )

    check(
        "source_contracts_match",
        not contract_errors,
        contract_errors,
    )

    check(
        "fact_profiles_match",
        not row_count_errors,
        row_count_errors,
    )

    check(
        "layer_evidence_valid",
        not layer_evidence_errors,
        layer_evidence_errors,
    )

    release_summary = manifest.get(
        "release_summary",
        {},
    )

    check(
        "release_summary_counts_valid",
        (
            release_summary.get(
                "governed_layer_count"
            )
            == len(layers)
            and release_summary.get(
                "artifact_count"
            )
            == sum(
                len(
                    layer.get(
                        "artifacts",
                        [],
                    )
                )
                for layer in layers
            )
            and release_summary.get(
                "passed_audit_count"
            )
            == len(layers)
            and release_summary.get(
                "tracked_artifact_count"
            )
            == sum(
                len(
                    layer.get(
                        "artifacts",
                        [],
                    )
                )
                for layer in layers
            )
            and release_summary.get(
                "clean_artifact_count"
            )
            == sum(
                len(
                    layer.get(
                        "artifacts",
                        [],
                    )
                )
                for layer in layers
            )
        ),
        release_summary,
    )

    reconciliation = manifest.get(
        "terminal_reconciliation",
        {},
    )

    reconciliation_flags = [
        "runner_population_reconciled",
        "race_population_reconciled",
        "runner_natural_keys_unique",
        "race_natural_keys_unique",
        "every_runner_race_has_race_snapshot",
        "every_race_snapshot_has_runner_population",
    ]

    check(
        "terminal_reconciliation_flags_pass",
        all(
            reconciliation.get(field)
            is True
            for field in reconciliation_flags
        ),
        {
            field: reconciliation.get(
                field
            )
            for field in reconciliation_flags
        },
    )

    runner_snapshot_path = (
        DATA
        / "edgeiq_race_entry_epi_publication_snapshot_fact_v1.csv"
    )

    race_snapshot_path = (
        DATA
        / "edgeiq_race_epi_publication_snapshot_fact_v1.csv"
    )

    runner_rows = read_csv_rows(
        runner_snapshot_path
    )

    race_rows = read_csv_rows(
        race_snapshot_path
    )

    runner_ids = [
        text(row.get("race_entry_id"))
        for row in runner_rows
    ]

    race_keys = [
        (
            text(row.get("race_id")),
            text(row.get("race_date")),
        )
        for row in race_rows
    ]

    runner_race_keys = {
        (
            text(row.get("race_id")),
            text(row.get("race_date")),
        )
        for row in runner_rows
    }

    check(
        "terminal_publication_populations_non_empty",
        (
            len(runner_rows) > 0
            and len(race_rows) > 0
            and len(runner_race_keys) > 0
        ),
        {
            "runner_rows": len(
                runner_rows
            ),
            "race_rows": len(
                race_rows
            ),
            "runner_race_keys": len(
                runner_race_keys
            ),
        },
    )

    check(
        "terminal_natural_keys_reverified",
        (
            len(runner_ids)
            == len(set(runner_ids))
            and len(race_keys)
            == len(set(race_keys))
            and set(race_keys)
            == runner_race_keys
        ),
        {
            "runner_rows": len(
                runner_rows
            ),
            "unique_runner_ids": len(
                set(runner_ids)
            ),
            "race_rows": len(
                race_rows
            ),
            "unique_race_keys": len(
                set(race_keys)
            ),
            "runner_race_keys": len(
                runner_race_keys
            ),
        },
    )

    expected_governance = {
        "release_decision": (
            EXPECTED_RELEASE_DECISION
        ),
        "reconciliation_decision": (
            EXPECTED_RECONCILIATION_DECISION
        ),
        "release_status": (
            EXPECTED_RELEASE_STATUS
        ),
    }

    governance_errors: list[str] = []

    for field, expected in expected_governance.items():
        if text(
            manifest.get(field)
        ) != expected:
            governance_errors.append(
                field
            )

    check(
        "release_governance_exact",
        not governance_errors,
        governance_errors,
    )

    source_git = manifest.get(
        "source_git",
        {},
    )

    source_git_head = text(
        source_git.get(
            "source_git_head"
        )
    )

    check(
        "source_git_commit_exists",
        bool(
            run_git(
                "cat-file",
                "-t",
                source_git_head,
            )
            == "commit"
        ),
        source_git_head,
    )

    expected_release_identity_hash = sha256_payload(
        [
            manifest.get(
                "manifest_contract_version"
            ),
            manifest.get(
                "warehouse_name"
            ),
            manifest.get(
                "warehouse_version"
            ),
            source_git_head,
            *[
                layer.get(
                    "layer_evidence_sha256"
                )
                for layer in layers
            ],
            sha256_text(
                canonical_json(
                    reconciliation
                )
            ),
            manifest.get(
                "release_decision"
            ),
        ]
    )

    expected_release_id = (
        "EPIWH1-"
        f"{expected_release_identity_hash[:32].upper()}"
    )

    check(
        "release_identity_deterministic",
        text(
            manifest.get(
                "epi_warehouse_release_id"
            )
        )
        == expected_release_id,
        {
            "actual": manifest.get(
                "epi_warehouse_release_id"
            ),
            "expected": expected_release_id,
        },
    )

    expected_release_evidence = sha256_payload(
        [
            expected_release_id,
            manifest.get(
                "warehouse_name"
            ),
            manifest.get(
                "warehouse_version"
            ),
            manifest.get(
                "manifest_contract_version"
            ),
            source_git_head,
            source_git.get(
                "source_git_branch"
            ),
            source_git.get(
                "source_git_commit_timestamp"
            ),
            source_git.get(
                "repository_root"
            ),
            *all_artifact_evidence,
            *[
                layer.get(
                    "layer_evidence_sha256"
                )
                for layer in layers
            ],
            canonical_json(
                reconciliation
            ),
            canonical_json(
                release_summary
            ),
            manifest.get(
                "release_decision"
            ),
            manifest.get(
                "reconciliation_decision"
            ),
            manifest.get(
                "release_status"
            ),
        ]
    )

    check(
        "release_evidence_deterministic",
        text(
            manifest.get(
                "epi_warehouse_release_evidence_sha256"
            )
        )
        == expected_release_evidence,
        {
            "actual": manifest.get(
                "epi_warehouse_release_evidence_sha256"
            ),
            "expected": (
                expected_release_evidence
            ),
        },
    )

    failed_checks = [
        name
        for name, result in checks.items()
        if result["status"] != "PASS"
    ]

    status = (
        "PASS"
        if not failed_checks
        else "FAIL"
    )

    payload = {
        "audit_name": (
            "edgeiq_epi_warehouse_release_manifest_v1"
        ),
        "audit_version": "1.0.0",
        "audited_at_utc": (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "status": status,
        "counts": {
            "governed_layer_count": (
                len(layers)
            ),
            "artifact_count": sum(
                len(
                    layer.get(
                        "artifacts",
                        [],
                    )
                )
                for layer in layers
            ),
            "passed_audit_count": sum(
                1
                for layer in layers
                if layer.get(
                    "audit_status"
                )
                == "PASS"
            ),
            "runner_publication_snapshot_rows": (
                len(runner_rows)
            ),
            "race_publication_snapshot_rows": (
                len(race_rows)
            ),
            "runner_publication_race_count": (
                len(runner_race_keys)
            ),
        },
        "release": {
            "epi_warehouse_release_id": (
                manifest.get(
                    "epi_warehouse_release_id"
                )
            ),
            "warehouse_name": (
                manifest.get(
                    "warehouse_name"
                )
            ),
            "warehouse_version": (
                manifest.get(
                    "warehouse_version"
                )
            ),
            "source_git_head": (
                source_git_head
            ),
            "release_decision": (
                manifest.get(
                    "release_decision"
                )
            ),
            "release_status": (
                manifest.get(
                    "release_status"
                )
            ),
        },
        "failed_checks": (
            failed_checks
        ),
        "checks": checks,
    }

    atomic_write_json(
        AUDIT_PATH,
        payload,
    )

    if status != "PASS":
        print(
            json.dumps(
                payload,
                indent=2,
            )
        )

        raise SystemExit(
            "EDGEIQ_EPI_WAREHOUSE_RELEASE_MANIFEST_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_EPI_WAREHOUSE_RELEASE_MANIFEST_V1_AUDIT_PASS"
    )
    print(
        "epi_warehouse_release_id="
        f"{manifest['epi_warehouse_release_id']}"
    )
    print(
        f"governed_layer_count={len(layers)}"
    )
    print(
        "artifact_count="
        f"{payload['counts']['artifact_count']}"
    )
    print(
        "passed_audit_count="
        f"{payload['counts']['passed_audit_count']}"
    )
    print(
        "runner_publication_snapshot_rows="
        f"{len(runner_rows)}"
    )
    print(
        "race_publication_snapshot_rows="
        f"{len(race_rows)}"
    )
    print(
        f"audit_output={AUDIT_PATH}"
    )


if __name__ == "__main__":
    main()
