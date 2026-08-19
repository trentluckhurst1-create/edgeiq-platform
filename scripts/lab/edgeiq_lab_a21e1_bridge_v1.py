from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "edgeiq.lab.a21e1.v1"
BRIDGE_VERSION = "1.1"

RESEARCH_ROOT = Path(r"C:\EDGEIQ_RESEARCH_DAN_O\betting_model")

ENGINE = (
    RESEARCH_ROOT
    / "scripts"
    / "model_100c7a21e1_user_analysis_engine.py"
)

WAREHOUSE = (
    RESEARCH_ROOT
    / "outputs"
    / "model_100c7a21d_canonical_next_generation_research_warehouse.csv"
)

SCHEMA = (
    RESEARCH_ROOT
    / "outputs"
    / "model_100c7a21d_canonical_schema.csv"
)

PUBLISHED_FIELD_ROLES = (
    RESEARCH_ROOT
    / "outputs"
    / "model_100c7a21e1_user_analysis_field_roles.csv"
)

PUBLISHED_FILTER_CATALOG = (
    RESEARCH_ROOT
    / "outputs"
    / "model_100c7a21e1_filter_catalog.csv"
)

EXPECTED_WAREHOUSE_SHA256 = (
    "610d13cf9526bb9a6e45d1e02858f334"
    "520bd7628ce1bc186480f1b9d7a42300"
)

CHUNK_SIZE = 25000

DEFAULT_QUALIFIER_PREVIEW_LIMIT = 200
MAX_QUALIFIER_PREVIEW_LIMIT = 1000


def configure_utf8() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)

        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(
                encoding="utf-8",
                errors="replace",
            )


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def require_file(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError(
            f"Required LAB dependency not found: {path}"
        )


def read_csv(
    path: Path,
) -> list[dict[str, str]]:
    if not path.is_file():
        return []

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def read_csv_preview(
    path: Path,
    limit: int,
) -> tuple[list[dict[str, str]], int]:

    if not path.is_file():
        return [], 0

    preview: list[dict[str, str]] = []
    total = 0

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:

        reader = csv.DictReader(handle)

        for row in reader:
            total += 1

            if len(preview) < limit:
                preview.append(row)

    return preview, total


def truthy(value: Any) -> bool:
    return str(value or "").strip().upper() == "TRUE"


def filter_catalog_lookup() -> dict[str, dict[str, str]]:
    require_file(PUBLISHED_FILTER_CATALOG)

    rows = read_csv(
        PUBLISHED_FILTER_CATALOG
    )

    lookup: dict[str, dict[str, str]] = {}

    for row in rows:
        canonical = str(
            row.get("normalized_column")
            or row.get("column")
            or ""
        ).strip()

        physical = str(
            row.get("column")
            or ""
        ).strip()

        if canonical:
            lookup[canonical.lower()] = row

        if physical:
            lookup[physical.lower()] = row

    return lookup


def validate_filter_fields(
    filters: list[dict[str, Any]],
) -> None:

    lookup = filter_catalog_lookup()

    for index, item in enumerate(filters):

        field = str(
            item.get("field", "")
        ).strip()

        if not field:
            raise RuntimeError(
                f"filters[{index}] has no field."
            )

        row = lookup.get(
            field.lower()
        )

        if row is None:
            raise RuntimeError(
                f"Filter field is not present in the "
                f"governed A21E1 catalog: {field}"
            )

        if not truthy(
            row.get("filter_allowed")
        ):
            reason = str(
                row.get("reason", "NOT_ALLOWED")
            ).strip()

            raise RuntimeError(
                f"Filter field is not permitted by "
                f"A21E1 governance: {field}. "
                f"Reason={reason}"
            )


def validate_query(
    raw_query: Any,
) -> dict[str, Any]:

    if not isinstance(
        raw_query,
        dict,
    ):
        raise RuntimeError(
            "LAB query must be a JSON object."
        )

    name = str(
        raw_query.get("name", "")
    ).strip()

    if not name:
        raise RuntimeError(
            "LAB query requires a name."
        )

    splits = raw_query.get(
        "splits",
        ["TRAIN"],
    )

    filters = raw_query.get(
        "filters",
        [],
    )

    breakdowns = raw_query.get(
        "breakdowns",
        [],
    )

    if not isinstance(
        splits,
        list,
    ):
        raise RuntimeError(
            "splits must be an array."
        )

    if not isinstance(
        filters,
        list,
    ):
        raise RuntimeError(
            "filters must be an array."
        )

    if not isinstance(
        breakdowns,
        list,
    ):
        raise RuntimeError(
            "breakdowns must be an array."
        )

    clean_filters: list[
        dict[str, Any]
    ] = []

    for index, item in enumerate(
        filters
    ):

        if not isinstance(
            item,
            dict,
        ):
            raise RuntimeError(
                f"filters[{index}] must "
                f"be an object."
            )

        for key in (
            "field",
            "operator",
            "value",
        ):
            if key not in item:
                raise RuntimeError(
                    f"filters[{index}] "
                    f"is missing {key}."
                )

        clean_filters.append(
            {
                "field": str(
                    item["field"]
                ).strip(),

                "operator": str(
                    item["operator"]
                ).strip(),

                "value": item["value"],
            }
        )

    validate_filter_fields(
        clean_filters
    )

    return {
        "name": name,

        "splits": [
            str(value).strip()
            for value in splits
        ],

        "filters": clean_filters,

        "breakdowns": [
            str(value).strip()
            for value in breakdowns
        ],
    }


def normalize_request(
    payload: Any,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
]:

    if not isinstance(
        payload,
        dict,
    ):
        raise RuntimeError(
            "LAB request must be "
            "a JSON object."
        )

    if isinstance(
        payload.get("query"),
        dict,
    ):
        raw_query = payload["query"]

        options = payload.get(
            "options",
            {},
        )

        if not isinstance(
            options,
            dict,
        ):
            raise RuntimeError(
                "options must be "
                "a JSON object."
            )
    else:
        raw_query = payload
        options = {}

    query = validate_query(
        raw_query
    )

    raw_limit = options.get(
        "qualifying_runner_limit",
        DEFAULT_QUALIFIER_PREVIEW_LIMIT,
    )

    try:
        preview_limit = int(
            raw_limit
        )
    except Exception as exc:
        raise RuntimeError(
            "qualifying_runner_limit "
            "must be an integer."
        ) from exc

    preview_limit = max(
        0,
        min(
            preview_limit,
            MAX_QUALIFIER_PREVIEW_LIMIT,
        ),
    )

    normalized_options = {
        "qualifying_runner_limit":
            preview_limit,

        "include_catalog":
            bool(
                options.get(
                    "include_catalog",
                    False,
                )
            ),

        "include_field_roles":
            bool(
                options.get(
                    "include_field_roles",
                    False,
                )
            ),
    }

    return (
        query,
        normalized_options,
    )


def audit_dict(
    audit_lines: list[str],
) -> dict[str, str]:

    result: dict[str, str] = {}

    for line in audit_lines:
        if "=" not in line:
            continue

        key, value = line.split(
            "=",
            1,
        )

        result[
            key.strip()
        ] = value.strip()

    return result


def describe() -> dict[str, Any]:
    require_file(
        PUBLISHED_FIELD_ROLES
    )

    require_file(
        PUBLISHED_FILTER_CATALOG
    )

    roles = read_csv(
        PUBLISHED_FIELD_ROLES
    )

    catalog = read_csv(
        PUBLISHED_FILTER_CATALOG
    )

    allowed = [
        row
        for row in catalog
        if truthy(
            row.get("filter_allowed")
        )
    ]

    blocked = [
        row
        for row in roles
        if not truthy(
            row.get("filter_allowed")
        )
    ]

    return {
        "status": "PASS",

        "contract_version":
            CONTRACT_VERSION,

        "bridge_version":
            BRIDGE_VERSION,

        "mode": "DESCRIBE",

        "generated_at":
            utc_now(),

        "engine": {
            "id": "A21E1",
            "name": (
                "Governed User "
                "Analysis Engine V1"
            ),
        },

        "warehouse": {
            "sha256":
                EXPECTED_WAREHOUSE_SHA256,

            "rows_from_governed_audit":
                700039,

            "columns_from_governed_audit":
                602,
        },

        "catalog": {
            "filterable_count":
                len(allowed),

            "field_role_count":
                len(roles),

            "filterable_fields":
                allowed,

            "blocked_field_count":
                len(blocked),
        },

        "limits": {
            "default_qualifier_preview":
                DEFAULT_QUALIFIER_PREVIEW_LIMIT,

            "maximum_qualifier_preview":
                MAX_QUALIFIER_PREVIEW_LIMIT,
        },
    }


def run_analysis(
    query: dict[str, Any],
    options: dict[str, Any],
) -> dict[str, Any]:

    for path in (
        ENGINE,
        WAREHOUSE,
        SCHEMA,
    ):
        require_file(path)

    preview_limit = int(
        options[
            "qualifying_runner_limit"
        ]
    )

    with tempfile.TemporaryDirectory(
        prefix="edgeiq_lab_a21e1_"
    ) as temp_name:

        temp = Path(
            temp_name
        )

        query_path = (
            temp
            / "query.json"
        )

        role_path = (
            temp
            / "field_roles.csv"
        )

        catalog_path = (
            temp
            / "filter_catalog.csv"
        )

        overall_path = (
            temp
            / "overall.csv"
        )

        breakdown_path = (
            temp
            / "breakdowns.csv"
        )

        qualifier_path = (
            temp
            / "qualifying_runners.csv"
        )

        audit_path = (
            temp
            / "audit.txt"
        )

        query_path.write_text(
            json.dumps(
                query,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        command = [
            sys.executable,
            "-X",
            "utf8",
            str(ENGINE),

            str(WAREHOUSE),
            str(SCHEMA),

            str(role_path),
            str(catalog_path),

            str(query_path),

            str(overall_path),
            str(breakdown_path),
            str(qualifier_path),

            str(audit_path),

            EXPECTED_WAREHOUSE_SHA256,
            str(CHUNK_SIZE),
        ]

        child_env = os.environ.copy()

        child_env[
            "PYTHONUTF8"
        ] = "1"

        child_env[
            "PYTHONIOENCODING"
        ] = "utf-8"

        process = subprocess.run(
            command,

            cwd=str(
                RESEARCH_ROOT
            ),

            env=child_env,

            capture_output=True,

            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if process.returncode != 0:
            raise RuntimeError(
                "A21E1 governed analysis "
                "failed.\n"
                f"EXIT_CODE="
                f"{process.returncode}\n"
                f"STDOUT:\n"
                f"{process.stdout}\n"
                f"STDERR:\n"
                f"{process.stderr}"
            )

        if not audit_path.is_file():
            raise RuntimeError(
                "A21E1 completed "
                "without an audit."
            )

        audit_text = (
            audit_path.read_text(
                encoding="utf-8-sig",
                errors="replace",
            )
        )

        audit_lines = (
            audit_text.splitlines()
        )

        audit = audit_dict(
            audit_lines
        )

        if (
            audit.get("VERDICT")
            !=
            "PASS_GOVERNED_USER_ANALYSIS_ENGINE_V1"
        ):
            raise RuntimeError(
                "A21E1 governance "
                "verdict did not pass.\n"
                + audit_text
            )

        if (
            audit.get(
                "FINAL_HOLDOUT_ROWS_SEEN"
            )
            != "0"
        ):
            raise RuntimeError(
                "A21E1 exposed "
                "final holdout rows."
            )

        if (
            audit.get(
                "HARD_FAILURES"
            )
            != "NONE"
        ):
            raise RuntimeError(
                "A21E1 reported "
                "hard failures."
            )

        qualifier_preview, qualifier_total = (
            read_csv_preview(
                qualifier_path,
                preview_limit,
            )
        )

        response: dict[str, Any] = {
            "status": "PASS",

            "contract_version":
                CONTRACT_VERSION,

            "bridge_version":
                BRIDGE_VERSION,

            "generated_at":
                utc_now(),

            "engine": {
                "id": "A21E1",

                "name": (
                    "Governed User "
                    "Analysis Engine V1"
                ),
            },

            "query": query,

            "options": options,

            "overall":
                read_csv(
                    overall_path
                ),

            "breakdowns":
                read_csv(
                    breakdown_path
                ),

            "qualifying_runners": {
                "total":
                    qualifier_total,

                "returned":
                    len(
                        qualifier_preview
                    ),

                "limit":
                    preview_limit,

                "rows":
                    qualifier_preview,
            },

            "governance": {
                "warehouse_sha256":
                    audit.get(
                        "CANONICAL_WAREHOUSE_SHA256"
                    ),

                "warehouse_rows_read":
                    audit.get(
                        "WAREHOUSE_ROWS_READ"
                    ),

                "warehouse_columns":
                    audit.get(
                        "WAREHOUSE_COLUMNS"
                    ),

                "filterable_fields":
                    audit.get(
                        "FILTERABLE_FIELDS"
                    ),

                "final_holdout_rows_seen":
                    audit.get(
                        "FINAL_HOLDOUT_ROWS_SEEN"
                    ),

                "hard_failures":
                    audit.get(
                        "HARD_FAILURES"
                    ),

                "verdict":
                    audit.get(
                        "VERDICT"
                    ),
            },

            "audit":
                audit_lines,
        }

        if options[
            "include_catalog"
        ]:
            response[
                "filter_catalog"
            ] = read_csv(
                catalog_path
            )

        if options[
            "include_field_roles"
        ]:
            response[
                "field_roles"
            ] = read_csv(
                role_path
            )

        return response


def emit(
    payload: dict[str, Any],
    *,
    stderr: bool = False,
) -> None:

    target = (
        sys.stderr
        if stderr
        else sys.stdout
    )

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        file=target,
    )


def main() -> int:
    configure_utf8()

    if (
        len(sys.argv) == 2
        and sys.argv[1]
        == "--describe"
    ):
        try:
            emit(
                describe()
            )

            return 0

        except Exception as exc:
            emit(
                {
                    "status": "ERROR",
                    "contract_version":
                        CONTRACT_VERSION,
                    "error": str(exc),
                },
                stderr=True,
            )

            return 1

    if len(sys.argv) != 2:
        emit(
            {
                "status": "ERROR",

                "contract_version":
                    CONTRACT_VERSION,

                "error": (
                    "Usage: "
                    "edgeiq_lab_a21e1_bridge_v1.py "
                    "--describe | <request.json>"
                ),
            },
            stderr=True,
        )

        return 2

    request_path = Path(
        sys.argv[1]
    )

    if not request_path.is_file():
        emit(
            {
                "status": "ERROR",

                "contract_version":
                    CONTRACT_VERSION,

                "error": (
                    "Request file not found: "
                    f"{request_path}"
                ),
            },
            stderr=True,
        )

        return 2

    try:
        payload = json.loads(
            request_path.read_text(
                encoding="utf-8-sig",
                errors="replace",
            )
        )

        query, options = (
            normalize_request(
                payload
            )
        )

        result = run_analysis(
            query,
            options,
        )

        emit(
            result
        )

        return 0

    except Exception as exc:
        emit(
            {
                "status": "ERROR",

                "contract_version":
                    CONTRACT_VERSION,

                "error": str(exc),
            },
            stderr=True,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
