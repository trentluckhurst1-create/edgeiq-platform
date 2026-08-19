from __future__ import annotations

import ast
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any


BUILDER_RELATIVE = Path(
    "scripts/build_edgeiq_epi_workspace_terminal_feed_v1.py"
)

HISTORICAL_RELATIVE = Path(
    "public/data/edgeiq_historical_performance_rating_v6_1_research.csv"
)

FORM_GUIDE_RELATIVE = Path(
    "public/data/edgeiq_form_guide_enriched_v2.json"
)

CATALOG_RELATIVE = Path(
    "public/data/edgeiq_three_day_product_catalog_v1.json"
)

OUTPUT_RELATIVE = Path(
    "public/data/edgeiq_epi_workspace_terminal_feed_v1.csv"
)

OUTPUT_ROOT_RELATIVE = Path(
    "docs/runtime-data-wiring-audit-v1/phase-d3-epi-exact-build-logic"
)

TARGET_TERMS = (
    "current_epi",
    "field_avg",
    "rank",
    "diff",
    "start_",
    "historical",
    "rating",
    "epi",
    "horse",
    "runner",
    "race_date",
    "meeting_date",
    "track",
    "venue",
    "race_number",
    "race_no",
    "canonical",
    "lookup",
    "index",
    "history",
)


def safe_text(path: Path) -> str:
    return path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    )


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def json_records(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(safe_text(path))

    if isinstance(payload, list):
        return [
            row
            for row in payload
            if isinstance(row, dict)
        ]

    if not isinstance(payload, dict):
        return []

    candidates: list[list[dict[str, Any]]] = []

    def walk(value: Any) -> None:
        if isinstance(value, list):
            dict_rows = [
                item
                for item in value
                if isinstance(item, dict)
            ]

            if dict_rows:
                candidates.append(dict_rows)

            for item in value:
                walk(item)

        elif isinstance(value, dict):
            for child in value.values():
                walk(child)

    walk(payload)

    return max(candidates, key=len, default=[])


def extract_function_source(
    text: str,
    function_name: str,
) -> tuple[int, int, str]:
    tree = ast.parse(text)
    lines = text.splitlines()

    for node in ast.walk(tree):
        if (
            isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            )
            and node.name == function_name
        ):
            start = node.lineno
            end = getattr(node, "end_lineno", node.lineno)

            numbered = "\n".join(
                f"{number}: {lines[number - 1]}"
                for number in range(start, end + 1)
            )

            return start, end, numbered

    raise RuntimeError(
        f"Function not found: {function_name}"
    )


def term_lines(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for line_number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        lowered = line.lower()
        matched = [
            term
            for term in TARGET_TERMS
            if term.lower() in lowered
        ]

        if not matched:
            continue

        rows.append(
            {
                "line_number": line_number,
                "matched_terms": " | ".join(matched),
                "source_line": line.rstrip(),
            }
        )

    return rows


def schema_profile(
    path: Path,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    columns = sorted(
        {
            str(key)
            for row in rows[:5000]
            for key in row.keys()
        }
    )

    return {
        "path": path.as_posix(),
        "row_count": len(rows),
        "column_count": len(columns),
        "columns": " | ".join(columns),
    }


def key_value_samples(
    dataset_name: str,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    key_terms = (
        "horse",
        "runner",
        "horse_name",
        "runner_name",
        "horse_code",
        "runner_code",
        "race_date",
        "meeting_date",
        "date",
        "track",
        "venue",
        "race_number",
        "race_no",
        "epi",
        "rating",
        "performance_rating",
        "rank",
    )

    columns = sorted(
        {
            str(key)
            for row in rows[:5000]
            for key in row.keys()
        }
    )

    selected = [
        column
        for column in columns
        if any(
            term in column.lower()
            for term in key_terms
        )
    ]

    output: list[dict[str, Any]] = []

    for column in selected:
        values = [
            str(row.get(column, "") or "").strip()
            for row in rows
        ]

        populated = [
            value
            for value in values
            if value
            and value.lower() not in {
                "none",
                "null",
                "nan",
                "n/a",
                "na",
            }
        ]

        output.append(
            {
                "dataset": dataset_name,
                "column": column,
                "row_count": len(rows),
                "populated_count": len(populated),
                "population_rate": (
                    round(len(populated) / len(rows), 6)
                    if rows
                    else 0
                ),
                "sample_values": " | ".join(
                    sorted(set(populated))[:12]
                ),
            }
        )

    return output


def main() -> int:
    root = Path.cwd().resolve()

    builder_path = root / BUILDER_RELATIVE
    historical_path = root / HISTORICAL_RELATIVE
    form_guide_path = root / FORM_GUIDE_RELATIVE
    catalog_path = root / CATALOG_RELATIVE
    output_path = root / OUTPUT_RELATIVE
    output_root = root / OUTPUT_ROOT_RELATIVE

    output_root.mkdir(parents=True, exist_ok=True)

    required = (
        builder_path,
        historical_path,
        form_guide_path,
        catalog_path,
        output_path,
    )

    missing = [
        path
        for path in required
        if not path.exists()
    ]

    if missing:
        for path in missing:
            print(
                f"ERROR missing: {path}",
                file=sys.stderr,
            )
        return 2

    builder_text = safe_text(builder_path)

    build_start, build_end, build_source = (
        extract_function_source(
            builder_text,
            "build",
        )
    )

    print("=== EPI EXACT BUILD LOGIC ===", flush=True)
    print(
        f"build_function_lines={build_start}-{build_end}",
        flush=True,
    )

    (
        output_root
        / "EDGEIQ_EPI_EXACT_BUILD_FUNCTION_V1.txt"
    ).write_text(
        build_source + "\n",
        encoding="utf-8",
    )

    relevant_lines = term_lines(builder_text)

    write_csv(
        output_root
        / "EDGEIQ_EPI_EXACT_BUILD_RELEVANT_LINES_V1.csv",
        relevant_lines,
        [
            "line_number",
            "matched_terms",
            "source_line",
        ],
    )

    historical_rows = load_csv(historical_path)
    output_rows = load_csv(output_path)
    form_rows = json_records(form_guide_path)
    catalog_rows = json_records(catalog_path)

    schemas = [
        schema_profile(
            HISTORICAL_RELATIVE,
            historical_rows,
        ),
        schema_profile(
            FORM_GUIDE_RELATIVE,
            form_rows,
        ),
        schema_profile(
            CATALOG_RELATIVE,
            catalog_rows,
        ),
        schema_profile(
            OUTPUT_RELATIVE,
            output_rows,
        ),
    ]

    write_csv(
        output_root
        / "EDGEIQ_EPI_EXACT_SOURCE_SCHEMAS_V1.csv",
        schemas,
        [
            "path",
            "row_count",
            "column_count",
            "columns",
        ],
    )

    samples: list[dict[str, Any]] = []

    samples.extend(
        key_value_samples(
            "historical_performance",
            historical_rows,
        )
    )
    samples.extend(
        key_value_samples(
            "form_guide",
            form_rows,
        )
    )
    samples.extend(
        key_value_samples(
            "three_day_catalog",
            catalog_rows,
        )
    )
    samples.extend(
        key_value_samples(
            "epi_output",
            output_rows,
        )
    )

    write_csv(
        output_root
        / "EDGEIQ_EPI_EXACT_KEY_COLUMN_POPULATION_V1.csv",
        samples,
        [
            "dataset",
            "column",
            "row_count",
            "populated_count",
            "population_rate",
            "sample_values",
        ],
    )

    print("\n=== BUILD FUNCTION SOURCE ===", flush=True)
    print(build_source, flush=True)

    print("\n=== SOURCE SCHEMAS ===", flush=True)

    for schema in schemas:
        print(
            f"{schema['path']} "
            f"rows={schema['row_count']} "
            f"columns={schema['column_count']}",
            flush=True,
        )
        print(
            f"  {schema['columns']}",
            flush=True,
        )

    print("\n=== KEY COLUMN POPULATION ===", flush=True)

    for row in samples:
        print(
            f"{row['dataset']}::{row['column']} "
            f"{row['populated_count']}/{row['row_count']} "
            f"rate={row['population_rate']} "
            f"samples={row['sample_values']}",
            flush=True,
        )

    summary = {
        "audit_id": "EDGEIQ_EPI_EXACT_BUILD_LOGIC_V1",
        "builder": BUILDER_RELATIVE.as_posix(),
        "build_start_line": build_start,
        "build_end_line": build_end,
        "historical_rows": len(historical_rows),
        "form_guide_rows": len(form_rows),
        "catalog_rows": len(catalog_rows),
        "output_rows": len(output_rows),
        "relevant_builder_lines": len(relevant_lines),
        "key_column_profiles": len(samples),
        "status": "EVIDENCE_CAPTURED",
    }

    (
        output_root
        / "EDGEIQ_EPI_EXACT_BUILD_LOGIC_V1_SUMMARY.json"
    ).write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n=== PHASE D3 COMPLETE ===", flush=True)
    print(
        json.dumps(summary, indent=2),
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())