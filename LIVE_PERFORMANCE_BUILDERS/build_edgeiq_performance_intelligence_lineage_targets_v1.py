from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path.cwd().resolve()

PROGRAM_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "restart-v1"
)

BASELINE_JSON = (
    PROGRAM_ROOT
    / "edgeiq_performance_intelligence_restart_baseline_v1.json"
)

INVENTORY_CSV = (
    PROGRAM_ROOT
    / "edgeiq_performance_intelligence_restart_inventory_v1.csv"
)

OUTPUT_JSON = (
    PROGRAM_ROOT
    / "edgeiq_performance_intelligence_lineage_targets_v1.json"
)

OUTPUT_CSV = (
    PROGRAM_ROOT
    / "edgeiq_performance_intelligence_lineage_targets_v1.csv"
)

OUTPUT_MD = (
    PROGRAM_ROOT
    / "EDGEIQ_PERFORMANCE_INTELLIGENCE_LINEAGE_TARGETS_V1.md"
)

EXPECTED_TARGET_COUNT = 2

STARTED = time.monotonic()


def log(message: str) -> None:
    elapsed = time.monotonic() - STARTED
    print(
        f"[{elapsed:7.2f}s] {message}",
        flush=True,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Required JSON file is missing: "
            f"{path.relative_to(ROOT).as_posix()}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )


def read_inventory() -> dict[str, dict[str, str]]:
    if not INVENTORY_CSV.is_file():
        raise FileNotFoundError(
            "Unit 001 inventory CSV is missing."
        )

    inventory: dict[str, dict[str, str]] = {}

    with INVENTORY_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            relative_path = row.get(
                "relative_path",
                "",
            ).strip()

            if relative_path:
                inventory[relative_path] = row

    return inventory


def main() -> int:
    log("PI_RESTART_UNIT_002A START")

    baseline = read_json(BASELINE_JSON)
    inventory = read_inventory()

    if baseline.get("verdict") != "PASS":
        raise RuntimeError(
            "Unit 001 baseline verdict is not PASS."
        )

    summary = baseline.get("summary", {})

    if summary.get("important_zero_row_count") != 2:
        raise RuntimeError(
            "Unit 001 did not report exactly two "
            "important zero-row outputs."
        )

    important_paths = baseline.get(
        "important_path_status",
        [],
    )

    targets: list[dict[str, Any]] = []

    for item in important_paths:
        status = str(
            item.get("csv_status", "")
        ).strip()

        if status not in {
            "HEADER_ONLY",
            "EMPTY_FILE",
        }:
            continue

        relative_path = str(
            item.get("relative_path", "")
        ).strip()

        if not relative_path:
            raise RuntimeError(
                "Zero-row target has no path."
            )

        absolute_path = ROOT / relative_path

        if not absolute_path.is_file():
            raise FileNotFoundError(
                f"Zero-row target is missing: "
                f"{relative_path}"
            )

        inventory_row = inventory.get(
            relative_path
        )

        if inventory_row is None:
            raise RuntimeError(
                f"Zero-row target is absent from "
                f"Unit 001 inventory: {relative_path}"
            )

        inventory_status = inventory_row.get(
            "csv_status",
            "",
        )

        if inventory_status != status:
            raise RuntimeError(
                f"Status mismatch for {relative_path}: "
                f"baseline={status}, "
                f"inventory={inventory_status}"
            )

        data_rows_raw = inventory_row.get(
            "csv_data_rows",
            "",
        )

        data_rows = (
            int(data_rows_raw)
            if str(data_rows_raw).strip()
            else 0
        )

        if data_rows != 0:
            raise RuntimeError(
                f"Target is not zero-row: "
                f"{relative_path}"
            )

        targets.append(
            {
                "target_number": 0,
                "relative_path": relative_path,
                "csv_status": status,
                "csv_data_rows": data_rows,
                "csv_columns": int(
                    inventory_row.get(
                        "csv_columns",
                        "0",
                    )
                    or 0
                ),
                "size_bytes": int(
                    inventory_row.get(
                        "size_bytes",
                        "0",
                    )
                    or 0
                ),
                "category": inventory_row.get(
                    "category",
                    "",
                ),
                "modified_utc": inventory_row.get(
                    "modified_utc",
                    "",
                ),
                "sha256": sha256_file(
                    absolute_path
                ),
                "investigation_status": (
                    "PENDING_BUILDER_TRACE"
                ),
            }
        )

    targets.sort(
        key=lambda row: row["relative_path"]
    )

    for index, target in enumerate(
        targets,
        start=1,
    ):
        target["target_number"] = index

    if len(targets) != EXPECTED_TARGET_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_TARGET_COUNT} "
            f"zero-row targets, found "
            f"{len(targets)}."
        )

    fieldnames = [
        "target_number",
        "relative_path",
        "csv_status",
        "csv_data_rows",
        "csv_columns",
        "size_bytes",
        "category",
        "modified_utc",
        "sha256",
        "investigation_status",
    ]

    with OUTPUT_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(targets)

    payload = {
        "program": (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE"
        ),
        "unit": "PI_RESTART_UNIT_002A",
        "name": (
            "Zero-Row Canonical Lineage Targets"
        ),
        "version": "V1",
        "generated_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "verdict": "PASS",
        "governance": {
            "engine_logic_changed": False,
            "thresholds_changed": False,
            "source_data_changed": False,
            "warehouse_data_changed": False,
            "runtime_data_changed": False,
            "react_changed": False,
        },
        "source_evidence": {
            "baseline_json": (
                BASELINE_JSON
                .relative_to(ROOT)
                .as_posix()
            ),
            "inventory_csv": (
                INVENTORY_CSV
                .relative_to(ROOT)
                .as_posix()
            ),
            "baseline_commit": (
                summary.get(
                    "current_head_short",
                    "",
                )
            ),
        },
        "summary": {
            "expected_target_count": (
                EXPECTED_TARGET_COUNT
            ),
            "identified_target_count": (
                len(targets)
            ),
            "header_only_target_count": sum(
                target["csv_status"]
                == "HEADER_ONLY"
                for target in targets
            ),
            "empty_file_target_count": sum(
                target["csv_status"]
                == "EMPTY_FILE"
                for target in targets
            ),
            "next_action": (
                "TRACE_TARGET_001_PRODUCING_BUILDER"
            ),
            "runtime_seconds": round(
                time.monotonic() - STARTED,
                3,
            ),
        },
        "targets": targets,
    }

    OUTPUT_JSON.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    markdown = [
        "# EDGEIQ Performance Intelligence Lineage Targets V1",
        "",
        "## Verdict",
        "",
        "**PASS**",
        "",
        (
            "This unit identifies the exact canonical "
            "zero-row outputs discovered by Restart Unit 001."
        ),
        "",
        "No builder, threshold, source dataset, warehouse,",
        "runtime dataset or React file was changed.",
        "",
        "## Identified Targets",
        "",
        (
            "| Target | Canonical output | Status | "
            "Rows | Columns | Size bytes |"
        ),
        "|---:|---|---|---:|---:|---:|",
    ]

    for target in targets:
        markdown.append(
            f"| {target['target_number']} "
            f"| `{target['relative_path']}` "
            f"| {target['csv_status']} "
            f"| {target['csv_data_rows']} "
            f"| {target['csv_columns']} "
            f"| {target['size_bytes']} |"
        )

    markdown.extend(
        [
            "",
            "## Governed Next Action",
            "",
            "**TRACE_TARGET_001_PRODUCING_BUILDER**",
            "",
            (
                "The next unit must identify the exact "
                "producer, orchestrator and declared inputs "
                "for Target 001."
            ),
            "",
            (
                "No repair is authorised until the first "
                "proven upstream collapse point is identified."
            ),
            "",
        ]
    )

    OUTPUT_MD.write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    log("PI_RESTART_UNIT_002A VERDICT=PASS")
    log(
        "IDENTIFIED_TARGET_COUNT="
        f"{len(targets)}"
    )

    for target in targets:
        log(
            f"TARGET_{target['target_number']:03d}="
            f"{target['relative_path']}"
        )

    log(
        "NEXT_ACTION="
        "TRACE_TARGET_001_PRODUCING_BUILDER"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log("PI_RESTART_UNIT_002A VERDICT=FAIL")
        print(
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)
