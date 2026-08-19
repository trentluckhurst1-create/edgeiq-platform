from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
from typing import Any

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve()
REPOSITORY_ROOT = SCRIPT_PATH.parents[1]

BUILDER_PATH = (
    REPOSITORY_ROOT
    / "scripts"
    / "build_edgeiq_racingcom_csv_ingestion_v1.py"
)

INTENDED_CACHE = (
    REPOSITORY_ROOT
    / "outputs"
    / "sectionals"
    / "raw"
    / "VIC"
    / "racingcom_csv"
)

INVESTIGATION_DIR = (
    REPOSITORY_ROOT
    / "docs"
    / "performance-intelligence"
    / "standard-time-investigation"
)

LEDGER_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_cache_root_escape_ledger_v1.csv"
)

SUMMARY_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_cache_root_escape_v1.json"
)

REPORT_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_cache_root_escape_v1.md"
)


def clean(value: Any) -> str:
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def load_builder():
    if not BUILDER_PATH.exists():
        raise FileNotFoundError(
            f"Builder not found: {BUILDER_PATH}"
        )

    spec = importlib.util.spec_from_file_location(
        "edgeiq_racingcom_builder_root_forensic_v1",
        BUILDER_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to create builder import specification."
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return module


def inventory_cache(
    module,
    cache_root: Path,
    cache_classification: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    files = (
        sorted(cache_root.rglob("*"))
        if cache_root.exists()
        else []
    )

    files = [
        path
        for path in files
        if path.is_file()
    ]

    for path in files:
        row: dict[str, Any] = {
            "cache_classification": cache_classification,
            "cache_root": str(cache_root),
            "file_name": path.name,
            "file_path": str(path),
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "modified_utc": datetime.fromtimestamp(
                path.stat().st_mtime,
                tz=timezone.utc,
            ).isoformat(),
            "sha256": sha256_file(path),
            "parser_status": "NOT_CSV",
            "parser_error": "",
            "parsed_runner_rows": 0,
            "race_date": "",
            "track": "",
            "race_no": "",
            "distance": "",
            "distinct_horses": 0,
            "complete_race_identity": "NO",
        }

        if path.suffix.lower() != ".csv":
            rows.append(row)
            continue

        source_url = (
            f"{module.CLOUDFRONT_BASE}/{path.name}"
        )

        try:
            parsed = module.parse_racingcom_csv(
                path,
                source_url,
                {},
            )
        except Exception as exc:
            row["parser_status"] = "PARSER_EXCEPTION"
            row["parser_error"] = (
                f"{type(exc).__name__}: {exc}"
            )
            rows.append(row)
            continue

        if not parsed:
            row["parser_status"] = "ZERO_ROWS"
            rows.append(row)
            continue

        row["parser_status"] = "PARSED"
        row["parsed_runner_rows"] = len(parsed)

        dates = sorted(
            {
                clean(item.get("race_date"))
                for item in parsed
                if clean(item.get("race_date"))
            }
        )

        tracks = sorted(
            {
                clean(item.get("track"))
                for item in parsed
                if clean(item.get("track"))
            }
        )

        race_numbers = sorted(
            {
                clean(item.get("race_no"))
                for item in parsed
                if clean(item.get("race_no"))
            }
        )

        distances = sorted(
            {
                clean(item.get("distance"))
                for item in parsed
                if clean(item.get("distance"))
            }
        )

        horses = {
            clean(item.get("horse_key"))
            for item in parsed
            if clean(item.get("horse_key"))
        }

        row["race_date"] = " | ".join(dates)
        row["track"] = " | ".join(tracks)
        row["race_no"] = " | ".join(race_numbers)
        row["distance"] = " | ".join(distances)
        row["distinct_horses"] = len(horses)

        if (
            len(dates) == 1
            and len(tracks) == 1
            and len(race_numbers) == 1
            and dates[0]
            and tracks[0]
            and race_numbers[0]
        ):
            row["complete_race_identity"] = "YES"

        rows.append(row)

    return rows


def distinct_races(
    ledger: pd.DataFrame,
    classification: str,
) -> int:
    if ledger.empty:
        return 0

    subset = ledger[
        (ledger["cache_classification"] == classification)
        & (ledger["complete_race_identity"] == "YES")
    ].copy()

    if subset.empty:
        return 0

    return len(
        subset[
            [
                "race_date",
                "track",
                "race_no",
            ]
        ].drop_duplicates()
    )


def main() -> int:
    print("EDGEIQ Racing.com Cache Root Escape V1")
    print()

    INVESTIGATION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    module = load_builder()

    builder_app_root = Path(module.APP_ROOT).resolve()
    builder_project_root = Path(
        module.PROJECT_ROOT
    ).resolve()
    builder_cache = Path(module.RAW_CACHE).resolve()
    intended_cache = INTENDED_CACHE.resolve()

    print(f"Repository root: {REPOSITORY_ROOT}")
    print(f"Builder APP_ROOT: {builder_app_root}")
    print(
        "Builder PROJECT_ROOT: "
        f"{builder_project_root}"
    )
    print(f"Builder RAW_CACHE: {builder_cache}")
    print(f"Intended RAW_CACHE: {intended_cache}")
    print()

    root_escape = (
        builder_project_root != REPOSITORY_ROOT.resolve()
    )

    cache_mismatch = (
        builder_cache != intended_cache
    )

    try:
        builder_cache.relative_to(
            REPOSITORY_ROOT.resolve()
        )
        builder_cache_inside_repository = True
    except ValueError:
        builder_cache_inside_repository = False

    rows: list[dict[str, Any]] = []

    print("[1/3] Inspecting builder-resolved cache...")
    rows.extend(
        inventory_cache(
            module,
            builder_cache,
            "BUILDER_RESOLVED",
        )
    )

    if builder_cache != intended_cache:
        print("[2/3] Inspecting intended repository cache...")
        rows.extend(
            inventory_cache(
                module,
                intended_cache,
                "INTENDED_REPOSITORY",
            )
        )
    else:
        print(
            "[2/3] Builder and intended cache paths match."
        )

    ledger = pd.DataFrame(rows)

    ledger_columns = [
        "cache_classification",
        "cache_root",
        "file_name",
        "file_path",
        "extension",
        "size_bytes",
        "modified_utc",
        "sha256",
        "parser_status",
        "parser_error",
        "parsed_runner_rows",
        "race_date",
        "track",
        "race_no",
        "distance",
        "distinct_horses",
        "complete_race_identity",
    ]

    if ledger.empty:
        ledger = pd.DataFrame(columns=ledger_columns)
    else:
        ledger = ledger.reindex(columns=ledger_columns)

    ledger.to_csv(
        LEDGER_OUT,
        index=False,
        encoding="utf-8",
    )

    print("[3/3] Writing governed evidence report...")

    builder_rows = ledger[
        ledger["cache_classification"]
        == "BUILDER_RESOLVED"
    ]

    intended_rows = ledger[
        ledger["cache_classification"]
        == "INTENDED_REPOSITORY"
    ]

    builder_csv_rows = builder_rows[
        builder_rows["extension"] == ".csv"
    ]

    intended_csv_rows = intended_rows[
        intended_rows["extension"] == ".csv"
    ]

    builder_parsed = builder_csv_rows[
        builder_csv_rows["parser_status"] == "PARSED"
    ]

    intended_parsed = intended_csv_rows[
        intended_csv_rows["parser_status"] == "PARSED"
    ]

    escaped_runner_rows = (
        int(builder_parsed["parsed_runner_rows"].sum())
        if not builder_parsed.empty
        else 0
    )

    intended_runner_rows = (
        int(intended_parsed["parsed_runner_rows"].sum())
        if not intended_parsed.empty
        else 0
    )

    builder_statuses = (
        Counter(builder_csv_rows["parser_status"])
        if not builder_csv_rows.empty
        else Counter()
    )

    intended_statuses = (
        Counter(intended_csv_rows["parser_status"])
        if not intended_csv_rows.empty
        else Counter()
    )

    builder_distinct_races = distinct_races(
        ledger,
        "BUILDER_RESOLVED",
    )

    intended_distinct_races = distinct_races(
        ledger,
        "INTENDED_REPOSITORY",
    )

    duplicate_hashes_across_roots = 0

    if (
        not builder_csv_rows.empty
        and not intended_csv_rows.empty
    ):
        escaped_hashes = set(
            builder_csv_rows["sha256"]
        )
        intended_hashes = set(
            intended_csv_rows["sha256"]
        )
        duplicate_hashes_across_roots = len(
            escaped_hashes & intended_hashes
        )

    summary = {
        "generated_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "governance": {
            "read_only": True,
            "network_access_performed": False,
            "production_builder_executed": False,
            "builder_modified": False,
            "cache_modified": False,
            "governed_output_modified": False,
        },
        "resolved_paths": {
            "repository_root": str(
                REPOSITORY_ROOT.resolve()
            ),
            "builder_app_root": str(builder_app_root),
            "builder_project_root": str(
                builder_project_root
            ),
            "builder_raw_cache": str(builder_cache),
            "intended_raw_cache": str(
                intended_cache
            ),
        },
        "path_findings": {
            "project_root_matches_repository": (
                not root_escape
            ),
            "cache_path_matches_intended": (
                not cache_mismatch
            ),
            "builder_cache_inside_repository": (
                builder_cache_inside_repository
            ),
        },
        "builder_resolved_cache": {
            "all_files": len(builder_rows),
            "csv_files": len(builder_csv_rows),
            "unique_csv_contents": (
                int(builder_csv_rows["sha256"].nunique())
                if not builder_csv_rows.empty
                else 0
            ),
            "parser_statuses": dict(
                sorted(builder_statuses.items())
            ),
            "parsed_csv_files": len(builder_parsed),
            "parsed_runner_rows": escaped_runner_rows,
            "distinct_races": builder_distinct_races,
        },
        "intended_repository_cache": {
            "all_files": len(intended_rows),
            "csv_files": len(intended_csv_rows),
            "unique_csv_contents": (
                int(intended_csv_rows["sha256"].nunique())
                if not intended_csv_rows.empty
                else 0
            ),
            "parser_statuses": dict(
                sorted(intended_statuses.items())
            ),
            "parsed_csv_files": len(intended_parsed),
            "parsed_runner_rows": intended_runner_rows,
            "distinct_races": intended_distinct_races,
        },
        "cross_root_duplicate_hashes": (
            duplicate_hashes_across_roots
        ),
    }

    if (
        root_escape
        and cache_mismatch
        and not builder_cache_inside_repository
    ):
        decision = "CACHE_ROOT_ESCAPE_CONFIRMED"
    elif cache_mismatch:
        decision = "CACHE_PATH_MISMATCH_CONFIRMED"
    else:
        decision = "CACHE_ROOT_MATCHES_REPOSITORY"

    summary["decision"] = decision

    SUMMARY_OUT.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    builder_status_lines = "\n".join(
        f"- `{name}`: **{count}**"
        for name, count in sorted(
            builder_statuses.items()
        )
    )

    if not builder_status_lines:
        builder_status_lines = "- No CSV files found."

    intended_status_lines = "\n".join(
        f"- `{name}`: **{count}**"
        for name, count in sorted(
            intended_statuses.items()
        )
    )

    if not intended_status_lines:
        intended_status_lines = "- No CSV files found."

    report = f"""# EDGEIQ Racing.com Cache Root Escape V1

Generated UTC: `{summary['generated_utc']}`

## Governance boundary

- Read-only forensic diagnostic.
- No network access.
- Production builder not executed.
- Builder not modified.
- Cache files not modified or moved.
- Governed outputs not modified.

## Path resolution

- Repository root: `{REPOSITORY_ROOT.resolve()}`
- Builder `APP_ROOT`: `{builder_app_root}`
- Builder `PROJECT_ROOT`: `{builder_project_root}`
- Builder `RAW_CACHE`: `{builder_cache}`
- Intended repository cache: `{intended_cache}`

## Path findings

- `PROJECT_ROOT` matches repository: **{not root_escape}**
- Builder cache matches intended cache: **{not cache_mismatch}**
- Builder cache is inside repository: **{builder_cache_inside_repository}**

## Builder-resolved cache

- All files: **{len(builder_rows)}**
- CSV files: **{len(builder_csv_rows)}**
- Unique CSV contents: **{summary['builder_resolved_cache']['unique_csv_contents']}**
- Parsed CSV files: **{len(builder_parsed)}**
- Parsed runner rows: **{escaped_runner_rows}**
- Complete distinct races: **{builder_distinct_races}**

### Parser statuses

{builder_status_lines}

## Intended repository cache

- All files: **{len(intended_rows)}**
- CSV files: **{len(intended_csv_rows)}**
- Unique CSV contents: **{summary['intended_repository_cache']['unique_csv_contents']}**
- Parsed CSV files: **{len(intended_parsed)}**
- Parsed runner rows: **{intended_runner_rows}**
- Complete distinct races: **{intended_distinct_races}**

### Parser statuses

{intended_status_lines}

## Cross-root comparison

- Duplicate CSV contents across both roots: **{duplicate_hashes_across_roots}**

## Architectural interpretation

The production builder derives `PROJECT_ROOT` from `Path(__file__).resolve().parents[3]`.

For a builder stored under the repository `scripts` directory, this resolves above the EDGEIQ repository. Any output path derived from that value is therefore capable of escaping the governed repository boundary.

No remediation has been applied in this diagnostic.

## Decision

**{decision}**

## Artifacts

- `{LEDGER_OUT.relative_to(REPOSITORY_ROOT).as_posix()}`
- `{SUMMARY_OUT.relative_to(REPOSITORY_ROOT).as_posix()}`
- `{REPORT_OUT.relative_to(REPOSITORY_ROOT).as_posix()}`
"""

    REPORT_OUT.write_text(
        report,
        encoding="utf-8",
    )

    print()
    print("COMPLETE")
    print(f"Report: {REPORT_OUT}")
    print(f"Ledger: {LEDGER_OUT}")
    print()
    print("KEY COUNTS")
    print(
        "Builder PROJECT_ROOT: "
        f"{builder_project_root}"
    )
    print(f"Builder cache: {builder_cache}")
    print(f"Intended cache: {intended_cache}")
    print(
        "Builder cache CSV files: "
        f"{len(builder_csv_rows)}"
    )
    print(
        "Builder cache parsed files: "
        f"{len(builder_parsed)}"
    )
    print(
        "Builder cache parsed runner rows: "
        f"{escaped_runner_rows}"
    )
    print(
        "Builder cache distinct races: "
        f"{builder_distinct_races}"
    )
    print(
        "Intended cache CSV files: "
        f"{len(intended_csv_rows)}"
    )
    print()
    print("DECISION")
    print(decision)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
