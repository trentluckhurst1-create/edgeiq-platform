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

OUTPUT_PATH = (
    DATA
    / "edgeiq_epi_warehouse_release_manifest_v1.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_epi_warehouse_release_manifest_v1_contract.json"
)

WAREHOUSE_NAME = "EDGEIQ_CANONICAL_EPI_WAREHOUSE"
WAREHOUSE_VERSION = "1.0.0"
CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = (
    "edgeiq_epi_warehouse_release_manifest_v1.0.0"
)

RELEASE_DECISION = "EPI_WAREHOUSE_V1_RELEASED"
RECONCILIATION_DECISION = (
    "EPI_WAREHOUSE_V1_RECONCILED"
)
RELEASE_STATUS = (
    "GOVERNED_EPI_WAREHOUSE_RELEASE"
)

LAYERS = [
    {
        "sequence": 1,
        "name": "Race Entry EPI Fact V1",
        "base": "edgeiq_race_entry_epi_fact_v1",
        "spec": (
            "docs/performance-intelligence/"
            "EDGEIQ_RACE_ENTRY_EPI_FACT_V1_SPEC.md"
        ),
    },
    {
        "sequence": 2,
        "name": "Race EPI Distribution Fact V1",
        "base": "edgeiq_race_epi_distribution_fact_v1",
        "spec": (
            "docs/performance-intelligence/"
            "EDGEIQ_RACE_EPI_DISTRIBUTION_FACT_V1_SPEC.md"
        ),
    },
    {
        "sequence": 3,
        "name": "Race Entry EPI Relative Context Fact V1",
        "base": (
            "edgeiq_race_entry_epi_relative_context_fact_v1"
        ),
        "spec": (
            "docs/performance-intelligence/"
            "EDGEIQ_RACE_ENTRY_EPI_RELATIVE_CONTEXT_FACT_V1_SPEC.md"
        ),
    },
    {
        "sequence": 4,
        "name": "Race Entry EPI Ordering Fact V1",
        "base": "edgeiq_race_entry_epi_ordering_fact_v1",
        "spec": (
            "docs/performance-intelligence/"
            "EDGEIQ_RACE_ENTRY_EPI_ORDERING_FACT_V1_SPEC.md"
        ),
    },
    {
        "sequence": 5,
        "name": "Race EPI Ordering Summary Fact V1",
        "base": "edgeiq_race_epi_ordering_summary_fact_v1",
        "spec": (
            "docs/performance-intelligence/"
            "EDGEIQ_RACE_EPI_ORDERING_SUMMARY_FACT_V1_SPEC.md"
        ),
    },
    {
        "sequence": 6,
        "name": "Race Entry EPI Publication Snapshot Fact V1",
        "base": (
            "edgeiq_race_entry_epi_publication_snapshot_fact_v1"
        ),
        "spec": (
            "docs/performance-intelligence/"
            "EDGEIQ_RACE_ENTRY_EPI_PUBLICATION_SNAPSHOT_FACT_V1_SPEC.md"
        ),
    },
    {
        "sequence": 7,
        "name": "Race EPI Publication Snapshot Fact V1",
        "base": "edgeiq_race_epi_publication_snapshot_fact_v1",
        "spec": (
            "docs/performance-intelligence/"
            "EDGEIQ_RACE_EPI_PUBLICATION_SNAPSHOT_FACT_V1_SPEC.md"
        ),
    },
]


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
                ensure_ascii=False,
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


def read_csv_profile(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise RuntimeError(
                f"Missing CSV header: {path}"
            )

        return list(reader.fieldnames), list(reader)


def artifact_paths(
    layer: dict[str, object],
) -> dict[str, str]:
    base = text(layer["base"])

    return {
        "specification": text(layer["spec"]),
        "contract": (
            "contracts/performance-intelligence/"
            f"{base}_contract.json"
        ),
        "builder": (
            f"scripts/build_{base}.py"
        ),
        "auditor": (
            f"scripts/audit_{base}.py"
        ),
        "fact": (
            f"public/data/{base}.csv"
        ),
        "audit": (
            f"public/data/{base}_audit.json"
        ),
    }


def git_artifact_state(
    repository_path: str,
) -> tuple[bool, bool]:
    tracked_result = subprocess.run(
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
    )

    tracked = (
        tracked_result.returncode == 0
    )

    status_output = run_git(
        "status",
        "--porcelain",
        "--",
        repository_path,
    )

    clean = not status_output

    return tracked, clean


def require_unique(
    rows: list[dict[str, str]],
    fields: list[str],
    name: str,
) -> None:
    values = [
        tuple(
            text(row.get(field))
            for field in fields
        )
        for row in rows
    ]

    incomplete = [
        value
        for value in values
        if not all(value)
    ]

    if incomplete:
        raise RuntimeError(
            f"{name} has incomplete natural keys."
        )

    duplicates = [
        value
        for value, count in Counter(
            values
        ).items()
        if count != 1
    ]

    if duplicates:
        raise RuntimeError(
            f"{name} has duplicate natural keys: "
            f"{duplicates[:20]}"
        )


def main() -> None:
    contract = json.loads(
        CONTRACT_PATH.read_text(
            encoding="utf-8"
        )
    )

    source_git_head = run_git(
        "rev-parse",
        "HEAD",
    )

    source_git_branch = run_git(
        "rev-parse",
        "--abbrev-ref",
        "HEAD",
    )

    source_git_commit_timestamp = run_git(
        "show",
        "-s",
        "--format=%cI",
        "HEAD",
    )

    repository_root = run_git(
        "rev-parse",
        "--show-toplevel",
    )

    governed_layers: list[dict[str, object]] = []
    facts: dict[
        str,
        list[dict[str, str]],
    ] = {}

    all_artifact_evidence: list[str] = []

    for layer in LAYERS:
        base = text(layer["base"])
        paths = artifact_paths(layer)

        artifacts: list[dict[str, object]] = []

        for role, repository_path in paths.items():
            absolute_path = (
                ROOT
                / Path(repository_path)
            )

            if not absolute_path.exists():
                raise RuntimeError(
                    f"Missing required {role} artifact: "
                    f"{repository_path}"
                )

            tracked, clean = git_artifact_state(
                repository_path
            )

            if not tracked:
                raise RuntimeError(
                    f"Governed artifact is not tracked by Git: "
                    f"{repository_path}"
                )

            if not clean:
                raise RuntimeError(
                    f"Governed artifact is modified or staged: "
                    f"{repository_path}"
                )

            artifact_hash = sha256_file(
                absolute_path
            )

            artifact = {
                "artifact_role": role,
                "repository_path": repository_path,
                "size_bytes": (
                    absolute_path.stat().st_size
                ),
                "sha256": artifact_hash,
                "git_tracked": True,
                "git_clean": True,
            }

            artifacts.append(artifact)

            all_artifact_evidence.append(
                sha256_payload(
                    [
                        layer["sequence"],
                        base,
                        role,
                        repository_path,
                        artifact["size_bytes"],
                        artifact_hash,
                    ]
                )
            )

        contract_payload = json.loads(
            (
                ROOT
                / Path(paths["contract"])
            ).read_text(
                encoding="utf-8"
            )
        )

        expected_contract_name = (
            f"{base}"
        )

        if text(
            contract_payload.get(
                "contract_name"
            )
        ) != expected_contract_name:
            raise RuntimeError(
                f"Contract-name mismatch for {base}: "
                f"{contract_payload.get('contract_name')}"
            )

        audit_payload = json.loads(
            (
                ROOT
                / Path(paths["audit"])
            ).read_text(
                encoding="utf-8"
            )
        )

        audit_status = text(
            audit_payload.get("status")
        )

        if audit_status != "PASS":
            raise RuntimeError(
                f"Governed audit is not PASS for {base}: "
                f"{audit_status}"
            )

        fact_fields, fact_rows = read_csv_profile(
            ROOT
            / Path(paths["fact"])
        )

        facts[base] = fact_rows

        layer_evidence = sha256_payload(
            [
                layer["sequence"],
                layer["name"],
                base,
                expected_contract_name,
                len(fact_rows),
                len(fact_fields),
                audit_status,
                canonical_json(
                    audit_payload.get(
                        "counts",
                        {},
                    )
                ),
                *[
                    artifact["sha256"]
                    for artifact in artifacts
                ],
            ]
        )

        governed_layers.append(
            {
                "layer_sequence": (
                    layer["sequence"]
                ),
                "layer_name": (
                    layer["name"]
                ),
                "layer_base_name": base,
                "contract_name": (
                    expected_contract_name
                ),
                "fact_row_count": (
                    len(fact_rows)
                ),
                "fact_column_count": (
                    len(fact_fields)
                ),
                "audit_status": (
                    audit_status
                ),
                "audit_counts": (
                    audit_payload.get(
                        "counts",
                        {},
                    )
                ),
                "artifacts": artifacts,
                "layer_evidence_sha256": (
                    layer_evidence
                ),
            }
        )

    race_entry_fact = facts[
        "edgeiq_race_entry_epi_fact_v1"
    ]

    race_distribution = facts[
        "edgeiq_race_epi_distribution_fact_v1"
    ]

    relative_context = facts[
        "edgeiq_race_entry_epi_relative_context_fact_v1"
    ]

    ordering_fact = facts[
        "edgeiq_race_entry_epi_ordering_fact_v1"
    ]

    ordering_summary = facts[
        "edgeiq_race_epi_ordering_summary_fact_v1"
    ]

    runner_snapshot = facts[
        "edgeiq_race_entry_epi_publication_snapshot_fact_v1"
    ]

    race_snapshot = facts[
        "edgeiq_race_epi_publication_snapshot_fact_v1"
    ]

    required_non_empty_populations = {
        "race_entry_epi_fact": len(
            race_entry_fact
        ),
        "race_epi_distribution": len(
            race_distribution
        ),
        "race_entry_epi_relative_context": len(
            relative_context
        ),
        "race_entry_epi_ordering": len(
            ordering_fact
        ),
        "race_epi_ordering_summary": len(
            ordering_summary
        ),
        "race_entry_epi_publication_snapshot": len(
            runner_snapshot
        ),
        "race_epi_publication_snapshot": len(
            race_snapshot
        ),
    }

    empty_populations = {
        name: count
        for name, count
        in required_non_empty_populations.items()
        if count < 1
    }

    if empty_populations:
        raise RuntimeError(
            "EPI Warehouse V1 cannot be released with "
            "empty governed populations: "
            f"{empty_populations}"
        )

    require_unique(
        runner_snapshot,
        ["race_entry_id"],
        "Race Entry EPI Publication Snapshot",
    )

    require_unique(
        race_snapshot,
        [
            "race_id",
            "race_date",
        ],
        "Race EPI Publication Snapshot",
    )

    runner_entry_ids = {
        text(row.get("race_entry_id"))
        for row in runner_snapshot
    }

    entry_fact_ids = {
        text(row.get("race_entry_id"))
        for row in race_entry_fact
    }

    relative_entry_ids = {
        text(row.get("race_entry_id"))
        for row in relative_context
    }

    ordering_entry_ids = {
        text(row.get("race_entry_id"))
        for row in ordering_fact
    }

    if (
        runner_entry_ids
        != entry_fact_ids
        or runner_entry_ids
        != relative_entry_ids
        or runner_entry_ids
        != ordering_entry_ids
    ):
        raise RuntimeError(
            "Runner-level governed populations do not "
            "reconcile across the EPI chain."
        )

    distribution_races = {
        (
            text(row.get("race_id")),
            text(row.get("race_date")),
        )
        for row in race_distribution
    }

    summary_races = {
        (
            text(row.get("race_id")),
            text(row.get("race_date")),
        )
        for row in ordering_summary
    }

    snapshot_races = {
        (
            text(row.get("race_id")),
            text(row.get("race_date")),
        )
        for row in race_snapshot
    }

    runner_snapshot_races = {
        (
            text(row.get("race_id")),
            text(row.get("race_date")),
        )
        for row in runner_snapshot
    }

    if (
        distribution_races
        != summary_races
        or distribution_races
        != snapshot_races
        or distribution_races
        != runner_snapshot_races
    ):
        raise RuntimeError(
            "Race-level governed populations do not "
            "reconcile across the EPI chain."
        )

    runner_counts_by_race = Counter(
        (
            text(row.get("race_id")),
            text(row.get("race_date")),
        )
        for row in runner_snapshot
    )

    empty_publication_races = [
        race_key
        for race_key in snapshot_races
        if runner_counts_by_race[
            race_key
        ] < 1
    ]

    if empty_publication_races:
        raise RuntimeError(
            "Race publication snapshots exist without "
            "runner publication rows."
        )

    terminal_reconciliation = {
        "race_entry_fact_row_count": (
            len(race_entry_fact)
        ),
        "relative_context_row_count": (
            len(relative_context)
        ),
        "ordering_fact_row_count": (
            len(ordering_fact)
        ),
        "runner_publication_snapshot_row_count": (
            len(runner_snapshot)
        ),
        "race_distribution_row_count": (
            len(race_distribution)
        ),
        "ordering_summary_row_count": (
            len(ordering_summary)
        ),
        "race_publication_snapshot_row_count": (
            len(race_snapshot)
        ),
        "runner_publication_race_count": (
            len(runner_snapshot_races)
        ),
        "race_publication_race_count": (
            len(snapshot_races)
        ),
        "runner_population_reconciled": True,
        "race_population_reconciled": True,
        "runner_natural_keys_unique": True,
        "race_natural_keys_unique": True,
        "every_runner_race_has_race_snapshot": True,
        "every_race_snapshot_has_runner_population": True,
    }

    release_created_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    release_summary = {
        "governed_layer_count": (
            len(governed_layers)
        ),
        "artifact_count": sum(
            len(layer["artifacts"])
            for layer in governed_layers
        ),
        "passed_audit_count": sum(
            1
            for layer in governed_layers
            if layer["audit_status"] == "PASS"
        ),
        "tracked_artifact_count": sum(
            1
            for layer in governed_layers
            for artifact in layer["artifacts"]
            if artifact["git_tracked"]
        ),
        "clean_artifact_count": sum(
            1
            for layer in governed_layers
            for artifact in layer["artifacts"]
            if artifact["git_clean"]
        ),
        "source_fact_total_row_count": sum(
            int(layer["fact_row_count"])
            for layer in governed_layers
        ),
        "builder_version": (
            BUILDER_VERSION
        ),
    }

    release_identity_hash = sha256_payload(
        [
            CONTRACT_VERSION,
            WAREHOUSE_NAME,
            WAREHOUSE_VERSION,
            source_git_head,
            *[
                layer[
                    "layer_evidence_sha256"
                ]
                for layer in governed_layers
            ],
            sha256_text(
                canonical_json(
                    terminal_reconciliation
                )
            ),
            RELEASE_DECISION,
        ]
    )

    release_id = (
        "EPIWH1-"
        f"{release_identity_hash[:32].upper()}"
    )

    release_evidence = sha256_payload(
        [
            release_id,
            WAREHOUSE_NAME,
            WAREHOUSE_VERSION,
            CONTRACT_VERSION,
            source_git_head,
            source_git_branch,
            source_git_commit_timestamp,
            repository_root,
            *all_artifact_evidence,
            *[
                layer[
                    "layer_evidence_sha256"
                ]
                for layer in governed_layers
            ],
            canonical_json(
                terminal_reconciliation
            ),
            canonical_json(
                release_summary
            ),
            RELEASE_DECISION,
            RECONCILIATION_DECISION,
            RELEASE_STATUS,
        ]
    )

    manifest = {
        "epi_warehouse_release_id": (
            release_id
        ),
        "warehouse_name": (
            WAREHOUSE_NAME
        ),
        "warehouse_version": (
            WAREHOUSE_VERSION
        ),
        "manifest_contract_version": (
            CONTRACT_VERSION
        ),
        "release_created_at_utc": (
            release_created_at_utc
        ),
        "source_git": {
            "source_git_head": (
                source_git_head
            ),
            "source_git_branch": (
                source_git_branch
            ),
            "source_git_commit_timestamp": (
                source_git_commit_timestamp
            ),
            "repository_root": (
                repository_root
            ),
            "governed_source_artifacts_clean": (
                True
            ),
        },
        "governed_layers": (
            governed_layers
        ),
        "terminal_reconciliation": (
            terminal_reconciliation
        ),
        "release_summary": (
            release_summary
        ),
        "release_decision": (
            RELEASE_DECISION
        ),
        "reconciliation_decision": (
            RECONCILIATION_DECISION
        ),
        "release_status": (
            RELEASE_STATUS
        ),
        "epi_warehouse_release_evidence_sha256": (
            release_evidence
        ),
    }

    required_top_level_fields = contract[
        "required_top_level_fields"
    ]

    if list(manifest.keys()) != (
        required_top_level_fields
    ):
        raise RuntimeError(
            "Manifest top-level fields do not match "
            "the governed contract."
        )

    atomic_write_json(
        OUTPUT_PATH,
        manifest,
    )

    print(
        "EDGEIQ_EPI_WAREHOUSE_RELEASE_MANIFEST_V1_BUILD_PASS"
    )
    print(
        f"epi_warehouse_release_id={release_id}"
    )
    print(
        f"source_git_head={source_git_head}"
    )
    print(
        f"governed_layer_count={len(governed_layers)}"
    )
    print(
        f"artifact_count={release_summary['artifact_count']}"
    )
    print(
        f"passed_audit_count={release_summary['passed_audit_count']}"
    )
    print(
        "runner_publication_snapshot_rows="
        f"{len(runner_snapshot)}"
    )
    print(
        "race_publication_snapshot_rows="
        f"{len(race_snapshot)}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
