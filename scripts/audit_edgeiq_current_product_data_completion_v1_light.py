from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
PUBLIC_DATA = ROOT / "public" / "data"
OUTPUT_ROOT = (
    ROOT
    / "docs"
    / "full-product-implementation"
    / "current-product-data-completion-v1-light"
)

MAX_ROWS_PER_FILE = 5_000
MAX_JSON_BYTES = 25 * 1024 * 1024
MAX_FILES = 150

INCLUDE_TERMS = (
    "current",
    "three_day",
    "terminal",
    "workspace",
    "race_field",
    "form_guide",
    "market",
    "pricing",
    "edge",
    "map",
    "epi",
    "eri",
    "speed",
    "suitability",
    "momentum",
    "profile",
)

EXCLUDE_TERMS = (
    "warehouse",
    "performance_fact",
    "runner_lengths",
    "lengths_v_standard_fact",
    "historical",
    "raw_",
    "archive",
    "backup",
)

METRIC_ALIASES = {
    "epi": ("epi", "current_epi", "epi_today", "performance_rating"),
    "eri": ("eri", "current_eri", "race_strength"),
    "early_speed": ("early_speed", "early_speed_rating", "map_speed", "spd"),
    "late_speed": ("late_speed", "late_speed_rating"),
    "suitability": ("suitability", "suitability_rating"),
    "form_momentum": ("form_momentum", "momentum"),
    "fair_price": ("fair_price", "edgeiq_price", "model_price"),
    "market_price": ("market_price", "fixed_win", "win_price"),
    "edge": ("edge", "edge_percent", "edge_pct"),
    "recent_form": ("recent_form", "last_5", "last5"),
    "sectionals": (
        "section_8_6",
        "section_6_4",
        "section_4_2",
        "section_2_f",
        "move_8_6",
        "move_6_4",
        "move_4_2",
        "move_2_f",
    ),
}

MISSING_VALUES = {
    "",
    "-",
    "—",
    ".",
    "..",
    "...",
    "null",
    "none",
    "nan",
    "undefined",
    "unavailable",
    "not available",
}


def normalise(value: Any) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(value).strip().lower(),
    ).strip("_")


def is_missing(value: Any) -> bool:
    if value is None:
        return True

    if isinstance(value, float):
        return math.isnan(value)

    return str(value).strip().lower() in MISSING_VALUES


def locate_files() -> list[Path]:
    files: list[Path] = []

    for path in PUBLIC_DATA.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {".csv", ".json"}:
            continue

        name = path.name.lower()

        if not any(term in name for term in INCLUDE_TERMS):
            continue

        if any(term in name for term in EXCLUDE_TERMS):
            continue

        if path.suffix.lower() == ".json" and path.stat().st_size > MAX_JSON_BYTES:
            continue

        files.append(path)

    return sorted(files)[:MAX_FILES]


def identify_metrics(fields: list[str]) -> dict[str, list[str]]:
    normalised_fields = {
        field: normalise(field)
        for field in fields
    }

    result: dict[str, list[str]] = {}

    for metric, aliases in METRIC_ALIASES.items():
        aliases_normalised = {normalise(alias) for alias in aliases}

        matches = [
            field
            for field, field_key in normalised_fields.items()
            if field_key in aliases_normalised
            or any(
                field_key.endswith("_" + alias)
                or field_key.startswith(alias + "_")
                for alias in aliases_normalised
            )
        ]

        result[metric] = sorted(set(matches))

    return result


def inspect_csv(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])

        for index, row in enumerate(reader):
            if index >= MAX_ROWS_PER_FILE:
                break
            rows.append(dict(row))

    return fields, rows


def find_record_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [
            item for item in payload[:MAX_ROWS_PER_FILE]
            if isinstance(item, dict)
        ]

    if not isinstance(payload, dict):
        return []

    for key in (
        "rows",
        "records",
        "runners",
        "items",
        "data",
        "facts",
        "results",
    ):
        value = payload.get(key)
        if isinstance(value, list):
            return [
                item for item in value[:MAX_ROWS_PER_FILE]
                if isinstance(item, dict)
            ]

    # Do not recursively flatten huge nested meeting catalogues here.
    return [payload]


def inspect_json(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    payload = json.loads(
        path.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )
    )

    rows = find_record_list(payload)

    fields = sorted({
        str(key)
        for row in rows
        for key in row.keys()
    })

    return fields, rows


def profile_metric(
    rows: list[dict[str, Any]],
    fields: list[str],
) -> dict[str, int]:
    populated = 0
    missing = 0
    invalid_placeholder = 0

    for row in rows:
        for field in fields:
            value = row.get(field)

            if is_missing(value):
                missing += 1

                if str(value).strip().lower() in {
                    ".",
                    "..",
                    "...",
                    "null",
                    "undefined",
                    "nan",
                }:
                    invalid_placeholder += 1
            else:
                populated += 1

    return {
        "populated": populated,
        "missing": missing,
        "invalid_placeholders": invalid_placeholder,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fields: list[str] = []
    seen: set[str] = set()

    for row in rows:
        for key in row:
            if key not in seen:
                fields.append(key)
                seen.add(key)

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()

        for row in rows:
            writer.writerow({
                key: (
                    json.dumps(value, ensure_ascii=False)
                    if isinstance(value, (dict, list))
                    else value
                )
                for key, value in row.items()
            })


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    files = locate_files()

    print(
        f"Found {len(files)} lightweight current-product files.",
        flush=True,
    )

    file_rows: list[dict[str, Any]] = []
    metric_totals: dict[str, Counter[str]] = {
        metric: Counter()
        for metric in METRIC_ALIASES
    }

    for position, path in enumerate(files, start=1):
        relative = str(path.relative_to(ROOT))

        print(
            f"[{position}/{len(files)}] Inspecting {relative}",
            flush=True,
        )

        try:
            if path.suffix.lower() == ".csv":
                fields, rows = inspect_csv(path)
            else:
                fields, rows = inspect_json(path)

            matches = identify_metrics(fields)

            matched_metrics = {
                metric: metric_fields
                for metric, metric_fields in matches.items()
                if metric_fields
            }

            for metric, metric_fields in matched_metrics.items():
                profile = profile_metric(rows, metric_fields)
                metric_totals[metric].update(profile)

            file_rows.append({
                "path": relative,
                "size_mb": round(path.stat().st_size / 1024 / 1024, 2),
                "sample_rows": len(rows),
                "columns": len(fields),
                "metrics": matched_metrics,
                "status": "PASS",
                "error": "",
            })

        except Exception as exc:
            file_rows.append({
                "path": relative,
                "size_mb": round(path.stat().st_size / 1024 / 1024, 2),
                "sample_rows": 0,
                "columns": 0,
                "metrics": {},
                "status": "FAIL",
                "error": f"{type(exc).__name__}: {exc}",
            })

    metric_rows: list[dict[str, Any]] = []

    for metric, totals in metric_totals.items():
        metric_rows.append({
            "metric": metric,
            "populated": totals["populated"],
            "missing": totals["missing"],
            "invalid_placeholders": totals["invalid_placeholders"],
        })

    summary = {
        "status": "PASS",
        "files_discovered": len(files),
        "files_passed": sum(row["status"] == "PASS" for row in file_rows),
        "files_failed": sum(row["status"] == "FAIL" for row in file_rows),
        "maximum_rows_sampled_per_file": MAX_ROWS_PER_FILE,
        "large_historical_files_skipped": True,
    }

    payload = {
        "summary": summary,
        "metric_coverage": metric_rows,
        "files": file_rows,
    }

    json_path = OUTPUT_ROOT / "EDGEIQ_CURRENT_PRODUCT_DATA_COMPLETION_V1_LIGHT.json"
    csv_path = OUTPUT_ROOT / "EDGEIQ_CURRENT_PRODUCT_DATA_COMPLETION_V1_LIGHT.csv"
    md_path = OUTPUT_ROOT / "EDGEIQ_CURRENT_PRODUCT_DATA_COMPLETION_V1_LIGHT.md"

    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    write_csv(csv_path, file_rows)

    markdown = [
        "# EDGEIQ Current Product Data Completion V1 — Lightweight Audit",
        "",
        "## Summary",
        "",
        f"- Files discovered: {summary['files_discovered']}",
        f"- Files passed: {summary['files_passed']}",
        f"- Files failed: {summary['files_failed']}",
        f"- Maximum sampled rows per file: {MAX_ROWS_PER_FILE}",
        "- Large warehouse and historical fact files were deliberately skipped.",
        "",
        "## Metric Coverage",
        "",
        "| Metric | Populated | Missing | Invalid placeholders |",
        "|---|---:|---:|---:|",
    ]

    for row in metric_rows:
        markdown.append(
            f"| {row['metric']} | {row['populated']} | "
            f"{row['missing']} | {row['invalid_placeholders']} |"
        )

    md_path.write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                **summary,
                "json": str(json_path),
                "csv": str(csv_path),
                "markdown": str(md_path),
            },
            separators=(",", ":"),
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
