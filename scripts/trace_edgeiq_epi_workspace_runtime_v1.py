from __future__ import annotations

import csv
import hashlib
import importlib.util
import inspect
import json
import sys
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_ID = "EDGEIQ_EPI_WORKSPACE_RUNTIME_TRACE_V1"

BUILDER_PATH = Path(
    "scripts/build_edgeiq_epi_workspace_terminal_feed_v1.py"
)

FEED_PATH = Path(
    "public/data/edgeiq_epi_workspace_terminal_feed_v1.csv"
)

OUTPUT_ROOT = Path(
    "docs/runtime-data-wiring-audit-v1/phase-d5-epi-runtime-trace"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def safe_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
    except Exception:
        return repr(value)


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def populated(value: Any) -> bool:
    return clean(value) not in {
        "",
        "None",
        "null",
        "NULL",
        "nan",
        "NaN",
    }


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fields: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def load_builder(path: Path):
    spec = importlib.util.spec_from_file_location(
        "edgeiq_epi_workspace_runtime_target",
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Unable to create module specification for {path}"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return module


def analyse_feed(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "exists": False,
            "rows": 0,
            "columns": [],
            "population": {},
        }

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        columns = list(reader.fieldnames or [])

    target_columns = (
        "current_epi",
        "rank",
        "field_avg",
        "diff",
        "peak_last_10",
        "average_last_10",
        "governed_trend",
    )

    population = {}

    for column in target_columns:
        if column not in columns:
            population[column] = {
                "present": False,
                "populated": 0,
                "blank": len(rows),
            }
            continue

        count = sum(
            1
            for row in rows
            if populated(row.get(column))
        )

        population[column] = {
            "present": True,
            "populated": count,
            "blank": len(rows) - count,
        }

    return {
        "exists": True,
        "rows": len(rows),
        "columns": columns,
        "population": population,
    }


def classify_trace(row: dict[str, Any]) -> str:
    if row["runner_argument_type"] != "dict":
        return "NON_DICTIONARY_ARGUMENT"

    if row["runner_key_count"] == 0:
        return "EMPTY_RUNNER_DICTIONARY"

    if not row["epi_key_present"]:
        if row["rating_key_present"]:
            return "EPI_MISSING_RATING_FALLBACK_PRESENT"
        return "EPI_AND_RATING_MISSING"

    if row["epi_type"] == "dict":
        if not row["epi_value_key_present"]:
            return "EPI_OBJECT_MISSING_VALUE_KEY"

        if not row["epi_value_populated"]:
            return "EPI_OBJECT_VALUE_BLANK"

    elif not row["epi_raw_populated"]:
        return "EPI_SCALAR_BLANK"

    if row["returned_value_populated"]:
        return "CURRENT_EPI_RETURNED"

    return "EPI_PRESENT_BUT_HELPER_RETURNED_NONE"


def main() -> int:
    root = Path.cwd().resolve()
    builder_path = root / BUILDER_PATH
    feed_path = root / FEED_PATH
    output_root = root / OUTPUT_ROOT

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(f"=== {AUDIT_ID} ===", flush=True)
    print(f"builder={builder_path}", flush=True)
    print(f"feed={feed_path}", flush=True)

    if not builder_path.exists():
        raise FileNotFoundError(
            f"Canonical builder not found: {builder_path}"
        )

    builder_hash_before = sha256_file(builder_path)
    feed_hash_before = sha256_file(feed_path)
    feed_before = analyse_feed(feed_path)

    print("\n[1/5] Loading canonical builder...", flush=True)

    module = load_builder(builder_path)

    if not hasattr(module, "current_epi_value"):
        raise AttributeError(
            "Canonical builder does not define current_epi_value()."
        )

    if not hasattr(module, "build"):
        raise AttributeError(
            "Canonical builder does not define build()."
        )

    original_current_epi_value = module.current_epi_value
    build_signature = str(inspect.signature(module.build))

    print(
        f"build_signature={build_signature}",
        flush=True,
    )
    print(
        f"current_epi_value_signature="
        f"{inspect.signature(original_current_epi_value)}",
        flush=True,
    )

    trace_rows: list[dict[str, Any]] = []
    call_number = 0

    def traced_current_epi_value(
        runner: Any,
    ) -> float | None:
        nonlocal call_number
        call_number += 1

        runner_is_dict = isinstance(runner, dict)
        keys = (
            sorted(str(key) for key in runner.keys())
            if runner_is_dict
            else []
        )

        epi_present = (
            "epi" in runner
            if runner_is_dict
            else False
        )
        rating_present = (
            "rating" in runner
            if runner_is_dict
            else False
        )

        epi_raw = (
            runner.get("epi")
            if runner_is_dict
            else None
        )
        rating_raw = (
            runner.get("rating")
            if runner_is_dict
            else None
        )

        epi_is_dict = isinstance(epi_raw, dict)
        epi_value_present = (
            "value" in epi_raw
            if epi_is_dict
            else False
        )
        epi_value = (
            epi_raw.get("value")
            if epi_is_dict
            else None
        )

        runner_name = ""

        if runner_is_dict:
            runner_name = clean(
                runner.get("runnerName")
                or runner.get("runner_name")
                or runner.get("horse")
                or runner.get("name")
            )

        exception_type = ""
        exception_message = ""

        try:
            returned = original_current_epi_value(
                runner
            )
        except Exception as exc:
            returned = None
            exception_type = type(exc).__name__
            exception_message = str(exc)

        row = {
            "call_number": call_number,
            "runner_name": runner_name,
            "runner_argument_type": type(runner).__name__,
            "runner_key_count": len(keys),
            "runner_keys": " | ".join(keys),
            "epi_key_present": epi_present,
            "epi_type": type(epi_raw).__name__,
            "epi_raw_populated": populated(epi_raw),
            "epi_raw_json": safe_json(epi_raw),
            "epi_value_key_present": epi_value_present,
            "epi_value_type": type(epi_value).__name__,
            "epi_value_populated": populated(epi_value),
            "epi_value": clean(epi_value),
            "rating_key_present": rating_present,
            "rating_type": type(rating_raw).__name__,
            "rating_raw_populated": populated(rating_raw),
            "rating_raw_json": safe_json(rating_raw),
            "returned_value_populated": populated(returned),
            "returned_value": clean(returned),
            "exception_type": exception_type,
            "exception_message": exception_message,
        }

        row["classification"] = classify_trace(row)
        trace_rows.append(row)

        return returned

    module.current_epi_value = traced_current_epi_value

    print(
        "\n[2/5] Running canonical build with in-memory trace...",
        flush=True,
    )

    build_exception = None
    build_result = None

    try:
        build_result = module.build()
    except Exception as exc:
        build_exception = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }

    module.current_epi_value = original_current_epi_value

    print(
        f"runtime_calls_captured={len(trace_rows)}",
        flush=True,
    )

    print(
        "\n[3/5] Analysing trace classifications...",
        flush=True,
    )

    classifications = Counter(
        row["classification"]
        for row in trace_rows
    )

    returned_count = sum(
        1
        for row in trace_rows
        if row["returned_value_populated"]
    )

    epi_key_count = sum(
        1
        for row in trace_rows
        if row["epi_key_present"]
    )

    epi_value_count = sum(
        1
        for row in trace_rows
        if row["epi_value_populated"]
    )

    empty_runner_count = sum(
        1
        for row in trace_rows
        if row["classification"]
        == "EMPTY_RUNNER_DICTIONARY"
    )

    missing_epi_and_rating_count = sum(
        1
        for row in trace_rows
        if row["classification"]
        == "EPI_AND_RATING_MISSING"
    )

    helper_failure_count = sum(
        1
        for row in trace_rows
        if row["classification"]
        == "EPI_PRESENT_BUT_HELPER_RETURNED_NONE"
    )

    print(
        json.dumps(
            dict(classifications),
            indent=2,
        ),
        flush=True,
    )

    print(
        "\n[4/5] Analysing rebuilt output...",
        flush=True,
    )

    feed_after = analyse_feed(feed_path)
    feed_hash_after = sha256_file(feed_path)
    builder_hash_after = sha256_file(builder_path)

    current_epi_population = (
        feed_after
        .get("population", {})
        .get("current_epi", {})
        .get("populated", 0)
    )

    if build_exception:
        verdict = "BUILD_EXECUTION_FAILED"

    elif not trace_rows:
        verdict = "NO_CURRENT_EPI_RUNTIME_CALLS_CAPTURED"

    elif empty_runner_count == len(trace_rows):
        verdict = "FORM_RUNNER_LOOKUP_RETURNED_EMPTY_DICTIONARIES"

    elif (
        missing_epi_and_rating_count
        == len(trace_rows)
    ):
        verdict = "MATCHED_RUNTIME_OBJECTS_LACK_EPI_AND_RATING"

    elif (
        epi_value_count > 0
        and returned_count == 0
    ):
        verdict = "HELPER_RUNTIME_CONVERSION_FAILURE"

    elif (
        returned_count > 0
        and current_epi_population == 0
    ):
        verdict = "VALUES_EXIST_AT_HELPER_BUT_ARE_LOST_DOWNSTREAM"

    elif current_epi_population > 0:
        verdict = "CURRENT_EPI_NOW_POPULATED"

    elif epi_key_count == 0:
        verdict = "RUNTIME_FORM_RUNNERS_DO_NOT_CONTAIN_EPI_KEY"

    else:
        verdict = "MIXED_RUNTIME_STATE_REQUIRES_ROW_REVIEW"

    print(
        f"verdict={verdict}",
        flush=True,
    )

    print(
        "\n[5/5] Writing governed evidence...",
        flush=True,
    )

    trace_fields = [
        "call_number",
        "runner_name",
        "classification",
        "runner_argument_type",
        "runner_key_count",
        "runner_keys",
        "epi_key_present",
        "epi_type",
        "epi_raw_populated",
        "epi_raw_json",
        "epi_value_key_present",
        "epi_value_type",
        "epi_value_populated",
        "epi_value",
        "rating_key_present",
        "rating_type",
        "rating_raw_populated",
        "rating_raw_json",
        "returned_value_populated",
        "returned_value",
        "exception_type",
        "exception_message",
    ]

    write_csv(
        output_root
        / f"{AUDIT_ID}_ALL_CALLS.csv",
        trace_rows,
        trace_fields,
    )

    write_csv(
        output_root
        / f"{AUDIT_ID}_NON_RETURNING_CALLS.csv",
        [
            row
            for row in trace_rows
            if not row["returned_value_populated"]
        ],
        trace_fields,
    )

    write_csv(
        output_root
        / f"{AUDIT_ID}_RETURNING_CALLS.csv",
        [
            row
            for row in trace_rows
            if row["returned_value_populated"]
        ],
        trace_fields,
    )

    classification_rows = [
        {
            "classification": name,
            "count": count,
        }
        for name, count in sorted(
            classifications.items()
        )
    ]

    write_csv(
        output_root
        / f"{AUDIT_ID}_CLASSIFICATIONS.csv",
        classification_rows,
        [
            "classification",
            "count",
        ],
    )

    summary = {
        "audit_id": AUDIT_ID,
        "generated_at_utc": utc_now(),
        "builder_path": BUILDER_PATH.as_posix(),
        "builder_signature": build_signature,
        "builder_sha256_before": builder_hash_before,
        "builder_sha256_after": builder_hash_after,
        "builder_unchanged": (
            builder_hash_before
            == builder_hash_after
        ),
        "feed_path": FEED_PATH.as_posix(),
        "feed_sha256_before": feed_hash_before,
        "feed_sha256_after": feed_hash_after,
        "feed_before": feed_before,
        "feed_after": feed_after,
        "build_result": safe_json(build_result),
        "build_exception": build_exception,
        "runtime_calls": len(trace_rows),
        "runner_arguments_with_epi_key": epi_key_count,
        "runner_arguments_with_populated_epi_value": epi_value_count,
        "helper_returned_numeric_value": returned_count,
        "empty_runner_dictionaries": empty_runner_count,
        "missing_epi_and_rating": missing_epi_and_rating_count,
        "epi_present_but_helper_returned_none": helper_failure_count,
        "classifications": dict(
            classifications
        ),
        "verdict": verdict,
        "status": (
            "EVIDENCE_CAPTURED"
            if not build_exception
            else "BUILD_FAILED"
        ),
    }

    (
        output_root
        / f"{AUDIT_ID}_SUMMARY.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    report_lines = [
        f"# {AUDIT_ID}",
        "",
        f"- Generated UTC: `{summary['generated_at_utc']}`",
        f"- Verdict: **{verdict}**",
        f"- Builder unchanged: `{summary['builder_unchanged']}`",
        f"- Runtime calls: `{len(trace_rows)}`",
        f"- Arguments containing `epi`: `{epi_key_count}`",
        f"- Populated `epi.value`: `{epi_value_count}`",
        f"- Numeric helper returns: `{returned_count}`",
        f"- Empty runner dictionaries: `{empty_runner_count}`",
        f"- Missing both `epi` and `rating`: `{missing_epi_and_rating_count}`",
        f"- Output `current_epi` populated: `{current_epi_population}`",
        "",
        "## Classifications",
        "",
    ]

    for name, count in sorted(
        classifications.items()
    ):
        report_lines.append(
            f"- `{name}`: `{count}`"
        )

    (
        output_root
        / f"{AUDIT_ID}_REPORT.md"
    ).write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8",
    )

    print("\n=== PHASE D5 COMPLETE ===")
    print(
        json.dumps(
            {
                "status": summary["status"],
                "verdict": verdict,
                "runtime_calls": len(trace_rows),
                "epi_key_count": epi_key_count,
                "epi_value_count": epi_value_count,
                "helper_returned_count": returned_count,
                "current_epi_output_populated": (
                    current_epi_population
                ),
                "builder_unchanged": summary[
                    "builder_unchanged"
                ],
            },
            indent=2,
        )
    )

    if build_exception:
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())