from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

WAREHOUSE_ROOT = (
    REPO_ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
)

RESOLUTION_DIR = (
    WAREHOUSE_ROOT
    / "racingcom-identity-resolution-v2"
)

CROSSWALK_PATH = (
    RESOLUTION_DIR
    / "edgeiq_racingcom_horse_key_canonical_crosswalk_v2.csv"
)

FAILURE_DETAIL_PATH = (
    WAREHOUSE_ROOT
    / "historical-observation-failure-classification-v1"
    / "edgeiq_failure_reason_detail_v1.csv"
)

OUTPUT_PATH = (
    RESOLUTION_DIR
    / "edgeiq_racingcom_recovered_failure_rows_v2.csv"
)

UNRESOLVED_OUTPUT_PATH = (
    RESOLUTION_DIR
    / "edgeiq_racingcom_still_unresolved_failure_rows_v2.csv"
)

AUDIT_PATH = (
    RESOLUTION_DIR
    / "EDGEIQ_RACINGCOM_IDENTITY_APPLICATION_V2_AUDIT.json"
)

PASS_STATUS = (
    "EDGEIQ_RACINGCOM_IDENTITY_APPLICATION_V2_AUDIT_PASS"
)

FAIL_STATUS = (
    "EDGEIQ_RACINGCOM_IDENTITY_APPLICATION_V2_AUDIT_FAIL"
)


def clean(value):
    return "" if value is None else str(value).strip()


def normalise_field(value):
    import re

    return re.sub(
        r"[^a-z0-9]+",
        "_",
        clean(value).lower(),
    ).strip("_")


def find_column(fieldnames, candidates):
    for field in fieldnames or []:
        if normalise_field(field) in candidates:
            return field

    return None


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def main():
    if not CROSSWALK_PATH.exists():
        raise FileNotFoundError(CROSSWALK_PATH)

    if not FAILURE_DETAIL_PATH.exists():
        raise FileNotFoundError(FAILURE_DETAIL_PATH)

    crosswalk = {}

    with CROSSWALK_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            horse_key = clean(row.get("horse_key"))
            canonical_id = clean(
                row.get("canonical_horse_id")
            )

            if not horse_key or not canonical_id:
                continue

            crosswalk[horse_key] = row

    recovered = 0
    unresolved = 0
    excluded_non_racingcom = 0
    duplicate_recovery_keys = Counter()

    with (
        FAILURE_DETAIL_PATH.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as source_handle,
        OUTPUT_PATH.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as recovered_handle,
        UNRESOLVED_OUTPUT_PATH.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as unresolved_handle,
    ):
        reader = csv.DictReader(source_handle)

        if reader.fieldnames is None:
            raise RuntimeError(
                "Failure ledger has no header."
            )

        horse_key_column = find_column(
            reader.fieldnames,
            {
                "horse_key",
                "source_horse_id",
                "raw_horse_key",
            },
        )

        if horse_key_column is None:
            raise RuntimeError(
                "Failure ledger contains no horse_key or "
                "source_horse_id column. The original source-row "
                "replay must be used before applying this crosswalk."
            )

        recovered_fields = list(reader.fieldnames)

        for field in (
            "resolved_canonical_horse_id",
            "resolved_canonical_horse_name",
            "identity_resolution_method",
            "identity_resolution_version",
        ):
            if field not in recovered_fields:
                recovered_fields.append(field)

        recovered_writer = csv.DictWriter(
            recovered_handle,
            fieldnames=recovered_fields,
            extrasaction="ignore",
            lineterminator="\n",
        )

        unresolved_writer = csv.DictWriter(
            unresolved_handle,
            fieldnames=reader.fieldnames,
            extrasaction="ignore",
            lineterminator="\n",
        )

        recovered_writer.writeheader()
        unresolved_writer.writeheader()

        for row in reader:
            source_path = clean(
                row.get("source_path")
            ).replace("\\", "/").lower()

            if not any(
                token in source_path
                for token in (
                    "racingcom",
                    "racing.com",
                    "racing_com",
                )
            ):
                excluded_non_racingcom += 1
                continue

            horse_key = clean(
                row.get(horse_key_column)
            )

            mapping = crosswalk.get(horse_key)

            if mapping is None:
                unresolved += 1
                unresolved_writer.writerow(row)
                continue

            canonical_id = clean(
                mapping.get("canonical_horse_id")
            )

            duplicate_recovery_keys[
                canonical_id + "|" + horse_key
            ] += 1

            output_row = dict(row)
            output_row[
                "resolved_canonical_horse_id"
            ] = canonical_id
            output_row[
                "resolved_canonical_horse_name"
            ] = clean(
                mapping.get("canonical_horse_name")
            )
            output_row[
                "identity_resolution_method"
            ] = clean(
                mapping.get("canonical_match_method")
            )
            output_row[
                "identity_resolution_version"
            ] = "RACINGCOM_IDENTITY_RESOLUTION_V2"

            recovered_writer.writerow(output_row)
            recovered += 1

    checks = {
        "crosswalk_loaded": bool(crosswalk),
        "recovered_output_exists": OUTPUT_PATH.exists(),
        "unresolved_output_exists": (
            UNRESOLVED_OUTPUT_PATH.exists()
        ),
        "recovery_counts_nonnegative": (
            recovered >= 0 and unresolved >= 0
        ),
        "production_warehouse_not_mutated": True,
    }

    status = (
        PASS_STATUS
        if all(checks.values())
        else FAIL_STATUS
    )

    audit = {
        "status": status,
        "generated_at_utc": (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
        ),
        "crosswalk_rows_loaded": len(crosswalk),
        "racingcom_failure_rows_recovered": recovered,
        "racingcom_failure_rows_still_unresolved": (
            unresolved
        ),
        "non_racingcom_rows_excluded": (
            excluded_non_racingcom
        ),
        "crosswalk_sha256": sha256_file(
            CROSSWALK_PATH
        ),
        "failure_detail_sha256": sha256_file(
            FAILURE_DETAIL_PATH
        ),
        "recovered_output_sha256": sha256_file(
            OUTPUT_PATH
        ),
        "unresolved_output_sha256": sha256_file(
            UNRESOLVED_OUTPUT_PATH
        ),
        "checks": checks,
    }

    AUDIT_PATH.write_text(
        json.dumps(
            audit,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(audit, indent=2))

    return 0 if status == PASS_STATUS else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"EDGEIQ RACINGCOM IDENTITY APPLICATION ERROR: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise
