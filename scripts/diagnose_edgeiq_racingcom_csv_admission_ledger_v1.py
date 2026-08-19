from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import importlib.util
import json
import sys
from typing import Any

import pandas as pd


APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_ROOT
PUBLIC_DATA = APP_ROOT / "public" / "data"
RAW_CACHE = (
    APP_ROOT
    / "outputs"
    / "sectionals"
    / "raw"
    / "VIC"
    / "racingcom_csv"
)
BUILDER_PATH = (
    APP_ROOT
    / "scripts"
    / "build_edgeiq_racingcom_csv_ingestion_v1.py"
)
INVESTIGATION_DIR = (
    APP_ROOT
    / "docs"
    / "performance-intelligence"
    / "standard-time-investigation"
)

DIAGNOSTICS_PATH = (
    PUBLIC_DATA / "edgeiq_racingcom_csv_ingestion_diagnostics_v1.csv"
)
INGESTION_PATH = (
    PUBLIC_DATA / "edgeiq_racingcom_csv_ingestion_v1.csv"
)

LEDGER_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_csv_cache_admission_ledger_v1.csv"
)
CANDIDATES_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_csv_candidate_population_v1.csv"
)
COLLISIONS_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_csv_cache_filename_collisions_v1.csv"
)
SUMMARY_JSON_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_csv_admission_ledger_v1.json"
)
REPORT_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_csv_admission_ledger_v1.md"
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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_builder_module():
    if not BUILDER_PATH.exists():
        raise FileNotFoundError(f"Builder not found: {BUILDER_PATH}")

    spec = importlib.util.spec_from_file_location(
        "edgeiq_racingcom_csv_builder_forensic_v1",
        BUILDER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to construct builder import specification.")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_diagnostics() -> dict[str, dict[str, str]]:
    if not DIAGNOSTICS_PATH.exists():
        return {}

    frame = pd.read_csv(
        DIAGNOSTICS_PATH,
        dtype=str,
        keep_default_na=False,
    )

    result: dict[str, dict[str, str]] = {}
    for row in frame.to_dict("records"):
        metric = clean(row.get("metric"))
        if not metric:
            continue
        result[metric] = {
            "value": clean(row.get("value")),
            "notes": clean(row.get("notes")),
        }
    return result


def read_existing_ingestion() -> pd.DataFrame:
    if not INGESTION_PATH.exists():
        return pd.DataFrame()

    return pd.read_csv(
        INGESTION_PATH,
        dtype=str,
        keep_default_na=False,
        low_memory=False,
    )


def cache_name_for_url(module, url: str) -> str:
    try:
        return module.cache_path_for_url(url).name
    except Exception:
        return ""


def candidate_population(module) -> pd.DataFrame:
    try:
        candidates = module.discover_candidates()
    except Exception as exc:
        return pd.DataFrame(
            [
                {
                    "candidate_discovery_error": (
                        f"{type(exc).__name__}: {exc}"
                    )
                }
            ]
        )

    if candidates is None:
        return pd.DataFrame()

    candidates = candidates.copy()

    for column in [
        "race_date",
        "track",
        "race_no",
        "speed_data_url",
        "csv_url",
        "discovery_method",
    ]:
        if column not in candidates.columns:
            candidates[column] = ""

    candidates["csv_url"] = candidates["csv_url"].map(clean)
    candidates["expected_cache_name"] = candidates["csv_url"].map(
        lambda value: cache_name_for_url(module, value)
        if value
        else ""
    )
    candidates["csv_url_has_value"] = candidates["csv_url"].map(
        lambda value: "YES" if value else "NO"
    )
    candidates["csv_url_ends_csv"] = candidates["csv_url"].map(
        lambda value: (
            "YES"
            if value.lower().split("?", 1)[0].endswith(".csv")
            else "NO"
        )
    )
    candidates["cache_file_exists"] = candidates[
        "expected_cache_name"
    ].map(
        lambda name: (
            "YES"
            if name and (RAW_CACHE / name).exists()
            else "NO"
        )
    )

    return candidates


def inspect_cache_file(module, path: Path) -> dict[str, Any]:
    row: dict[str, Any] = {
        "cache_file": path.name,
        "cache_path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": file_sha256(path),
        "readable_semicolon_csv": "NO",
        "record_count": 0,
        "first_row_column_count": 0,
        "first_row_preview": "",
        "parser_status": "",
        "parser_error": "",
        "parsed_runner_rows": 0,
        "parsed_race_date": "",
        "parsed_track": "",
        "parsed_race_no": "",
        "parsed_distance": "",
        "parsed_source_url": "",
        "distinct_horses": 0,
        "has_complete_race_identity": "NO",
    }

    records: list[list[str]] = []

    try:
        try:
            with path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as handle:
                records = list(csv.reader(handle, delimiter=";"))
        except UnicodeDecodeError:
            with path.open(
                "r",
                encoding="latin-1",
                newline="",
            ) as handle:
                records = list(csv.reader(handle, delimiter=";"))

        row["readable_semicolon_csv"] = "YES"
        row["record_count"] = len(records)

        if records:
            row["first_row_column_count"] = len(records[0])
            row["first_row_preview"] = " | ".join(
                clean(value) for value in records[0][:8]
            )[:1000]
    except Exception as exc:
        row["parser_status"] = "READ_ERROR"
        row["parser_error"] = f"{type(exc).__name__}: {exc}"
        return row

    source_url = f"{module.CLOUDFRONT_BASE}/{path.name}"

    try:
        parsed = module.parse_racingcom_csv(
            path,
            source_url,
            {},
        )
    except Exception as exc:
        row["parser_status"] = "PARSER_EXCEPTION"
        row["parser_error"] = f"{type(exc).__name__}: {exc}"
        return row

    if not parsed:
        row["parser_status"] = "ZERO_ROWS"
        return row

    row["parser_status"] = "PARSED"
    row["parsed_runner_rows"] = len(parsed)

    race_dates = sorted(
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
    source_urls = sorted(
        {
            clean(item.get("source_url"))
            for item in parsed
            if clean(item.get("source_url"))
        }
    )
    horses = {
        clean(item.get("horse_key"))
        for item in parsed
        if clean(item.get("horse_key"))
    }

    row["parsed_race_date"] = " | ".join(race_dates)
    row["parsed_track"] = " | ".join(tracks)
    row["parsed_race_no"] = " | ".join(race_numbers)
    row["parsed_distance"] = " | ".join(distances)
    row["parsed_source_url"] = " | ".join(source_urls)
    row["distinct_horses"] = len(horses)

    if (
        len(race_dates) == 1
        and len(tracks) == 1
        and len(race_numbers) == 1
        and race_dates[0]
        and tracks[0]
        and race_numbers[0]
    ):
        row["has_complete_race_identity"] = "YES"

    return row


def build_collision_ledger(
    candidates: pd.DataFrame,
) -> pd.DataFrame:
    if candidates.empty or "csv_url" not in candidates.columns:
        return pd.DataFrame(
            columns=[
                "expected_cache_name",
                "distinct_csv_urls",
                "candidate_rows",
                "csv_urls",
                "collision_status",
            ]
        )

    valid = candidates[
        candidates["csv_url"].map(bool)
        & candidates["expected_cache_name"].map(bool)
    ].copy()

    rows: list[dict[str, Any]] = []

    for cache_name, group in valid.groupby(
        "expected_cache_name",
        dropna=False,
    ):
        urls = sorted(set(group["csv_url"].map(clean)))
        rows.append(
            {
                "expected_cache_name": cache_name,
                "distinct_csv_urls": len(urls),
                "candidate_rows": len(group),
                "csv_urls": " | ".join(urls),
                "collision_status": (
                    "COLLISION"
                    if len(urls) > 1
                    else "UNIQUE"
                ),
            }
        )

    return pd.DataFrame(rows)


def unique_race_identities(
    ledger: pd.DataFrame,
) -> set[tuple[str, str, str]]:
    identities: set[tuple[str, str, str]] = set()

    if ledger.empty:
        return identities

    parsed = ledger[
        ledger["has_complete_race_identity"] == "YES"
    ]

    for row in parsed.to_dict("records"):
        identities.add(
            (
                clean(row.get("parsed_race_date")),
                clean(row.get("parsed_track")),
                clean(row.get("parsed_race_no")),
            )
        )

    return identities


def main() -> int:
    print("EDGEIQ Racing.com CSV Admission Ledger V1")
    print(f"Builder: {BUILDER_PATH}")
    print(f"Cache: {RAW_CACHE}")
    print()

    INVESTIGATION_DIR.mkdir(parents=True, exist_ok=True)

    module = load_builder_module()

    print("[1/5] Reading existing governed diagnostics...")
    diagnostics = read_diagnostics()
    ingestion = read_existing_ingestion()

    print("[2/5] Reconstructing candidate population...")
    candidates = candidate_population(module)
    candidates.to_csv(
        CANDIDATES_OUT,
        index=False,
        encoding="utf-8",
    )

    print("[3/5] Inspecting every cached CSV...")
    cache_files = (
        sorted(RAW_CACHE.glob("*.csv"))
        if RAW_CACHE.exists()
        else []
    )

    ledger_rows: list[dict[str, Any]] = []

    for index, cache_file in enumerate(cache_files, start=1):
        ledger_rows.append(
            inspect_cache_file(module, cache_file)
        )
        if index % 50 == 0:
            print(
                f"  Inspected {index}/{len(cache_files)} cached CSVs"
            )

    ledger = pd.DataFrame(ledger_rows)
    ledger.to_csv(
        LEDGER_OUT,
        index=False,
        encoding="utf-8",
    )

    print("[4/5] Testing cache filename collisions...")
    collisions = build_collision_ledger(candidates)
    collisions.to_csv(
        COLLISIONS_OUT,
        index=False,
        encoding="utf-8",
    )

    parser_status_counts = (
        Counter(ledger["parser_status"])
        if not ledger.empty
        else Counter()
    )

    identities = unique_race_identities(ledger)

    candidate_rows = len(candidates)
    candidate_error = ""

    if (
        not candidates.empty
        and "candidate_discovery_error" in candidates.columns
    ):
        candidate_error = clean(
            candidates.iloc[0].get(
                "candidate_discovery_error",
                "",
            )
        )

    if candidate_error:
        direct_candidate_rows = 0
        unique_csv_urls = 0
        csv_ending_urls = 0
        candidate_urls_cached = 0
    else:
        direct_candidate_rows = int(
            candidates["csv_url"].map(bool).sum()
        )
        unique_csv_urls = int(
            candidates.loc[
                candidates["csv_url"].map(bool),
                "csv_url",
            ].nunique()
        )
        csv_ending_urls = int(
            (
                candidates["csv_url_ends_csv"] == "YES"
            ).sum()
        )
        candidate_urls_cached = int(
            candidates.loc[
                candidates["csv_url"].map(bool)
                & (
                    candidates["cache_file_exists"]
                    == "YES"
                ),
                "csv_url",
            ].nunique()
        )

    collision_count = (
        int(
            (
                collisions["collision_status"]
                == "COLLISION"
            ).sum()
        )
        if not collisions.empty
        else 0
    )

    existing_ingestion_rows = len(ingestion)
    existing_ingestion_races = 0
    existing_ingestion_source_urls = 0

    required_identity_columns = {
        "race_date",
        "track",
        "race_no",
    }

    if (
        not ingestion.empty
        and required_identity_columns.issubset(
            ingestion.columns
        )
    ):
        existing_ingestion_races = len(
            ingestion[
                ["race_date", "track", "race_no"]
            ]
            .drop_duplicates()
        )

    if (
        not ingestion.empty
        and "source_url" in ingestion.columns
    ):
        existing_ingestion_source_urls = int(
            ingestion["source_url"]
            .map(clean)
            .replace("", pd.NA)
            .dropna()
            .nunique()
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
            "threshold_modified": False,
        },
        "builder_configuration": {
            "max_fetches": int(module.MAX_FETCHES),
            "raw_cache": str(RAW_CACHE),
        },
        "existing_diagnostics": diagnostics,
        "candidate_population": {
            "candidate_rows_reconstructed": candidate_rows,
            "candidate_discovery_error": candidate_error,
            "candidate_rows_with_csv_url": direct_candidate_rows,
            "unique_csv_urls": unique_csv_urls,
            "csv_urls_ending_dot_csv": csv_ending_urls,
            "unique_candidate_urls_with_existing_cache_file": (
                candidate_urls_cached
            ),
        },
        "cache_population": {
            "cache_files": len(cache_files),
            "unique_cache_hashes": (
                int(ledger["sha256"].nunique())
                if not ledger.empty
                else 0
            ),
            "parser_status_counts": dict(
                sorted(parser_status_counts.items())
            ),
            "parsed_cache_files": int(
                (ledger["parser_status"] == "PARSED").sum()
            )
            if not ledger.empty
            else 0,
            "zero_row_cache_files": int(
                (ledger["parser_status"] == "ZERO_ROWS").sum()
            )
            if not ledger.empty
            else 0,
            "parser_exception_files": int(
                (
                    ledger["parser_status"]
                    == "PARSER_EXCEPTION"
                ).sum()
            )
            if not ledger.empty
            else 0,
            "parsed_runner_rows_before_deduplication": int(
                ledger["parsed_runner_rows"].sum()
            )
            if not ledger.empty
            else 0,
            "complete_race_identities": len(identities),
        },
        "cache_filename_collisions": {
            "collision_names": collision_count,
            "maximum_urls_per_cache_name": (
                int(collisions["distinct_csv_urls"].max())
                if not collisions.empty
                else 0
            ),
        },
        "existing_ingestion_output": {
            "runner_rows": existing_ingestion_rows,
            "distinct_races": existing_ingestion_races,
            "distinct_source_urls": (
                existing_ingestion_source_urls
            ),
        },
    }

    print("[5/5] Writing forensic report...")

    SUMMARY_JSON_OUT.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    status_lines = "\n".join(
        f"- {key}: **{value}**"
        for key, value in sorted(
            parser_status_counts.items()
        )
    )

    if not status_lines:
        status_lines = "- No cache files inspected."

    diagnostics_lines = "\n".join(
        (
            f"- `{metric}`: **{item['value']}**"
            f" ? {item['notes']}"
        )
        for metric, item in diagnostics.items()
    )

    if not diagnostics_lines:
        diagnostics_lines = (
            "- Existing ingestion diagnostics were not found."
        )

    decision = "CSV_ADMISSION_EVIDENCE_CREATED"

    report = f"""# EDGEIQ Racing.com CSV Admission Ledger V1

Generated UTC: `{summary['generated_utc']}`

## Governance boundary

- Read-only forensic diagnostic.
- No network access performed.
- Production ingestion builder not executed.
- No cache file modified.
- No governed output modified.
- No fetch threshold modified.
- Existing builder functions reused only for local discovery and parsing.

## Proven builder boundary

- Configured `MAX_FETCHES`: **{module.MAX_FETCHES}**
- Existing diagnostic candidate rows: **{diagnostics.get('candidate_rows', {}).get('value', 'NOT_AVAILABLE')}**
- Existing diagnostic direct CSV candidates: **{diagnostics.get('direct_csv_candidates', {}).get('value', 'NOT_AVAILABLE')}**
- Existing ingestion runner rows: **{existing_ingestion_rows}**
- Existing ingestion distinct races: **{existing_ingestion_races}**
- Existing ingestion distinct source URLs: **{existing_ingestion_source_urls}**

## Reconstructed candidate population

- Candidate rows: **{candidate_rows}**
- Candidate discovery error: **{candidate_error or 'NONE'}**
- Candidate rows with CSV URL: **{direct_candidate_rows}**
- Unique CSV URLs: **{unique_csv_urls}**
- Candidate CSV URLs ending in `.csv`: **{csv_ending_urls}**
- Unique candidate URLs with an existing cache file: **{candidate_urls_cached}**

## Cache population

- Cached CSV files: **{len(cache_files)}**
- Unique cached contents: **{summary['cache_population']['unique_cache_hashes']}**
- Parsed cached files: **{summary['cache_population']['parsed_cache_files']}**
- Zero-row cached files: **{summary['cache_population']['zero_row_cache_files']}**
- Parser-exception files: **{summary['cache_population']['parser_exception_files']}**
- Parsed runner rows before output deduplication: **{summary['cache_population']['parsed_runner_rows_before_deduplication']}**
- Complete race identities represented in cache: **{len(identities)}**

### Parser statuses

{status_lines}

## Cache filename collision test

- Cache names representing multiple distinct URLs: **{collision_count}**
- Maximum distinct URLs sharing one cache name: **{summary['cache_filename_collisions']['maximum_urls_per_cache_name']}**

## Existing diagnostics

{diagnostics_lines}

## Decision

**{decision}**

The next governed decision must be based on the exact admission ledger. The fetch cap must not be changed until candidate coverage, cache coverage, parser rejection, cache collision, and race identity counts are established.

## Artifacts

- `{LEDGER_OUT.relative_to(APP_ROOT).as_posix()}`
- `{CANDIDATES_OUT.relative_to(APP_ROOT).as_posix()}`
- `{COLLISIONS_OUT.relative_to(APP_ROOT).as_posix()}`
- `{SUMMARY_JSON_OUT.relative_to(APP_ROOT).as_posix()}`
- `{REPORT_OUT.relative_to(APP_ROOT).as_posix()}`
"""

    REPORT_OUT.write_text(report, encoding="utf-8")

    print()
    print("COMPLETE")
    print(f"Report: {REPORT_OUT}")
    print(f"Ledger: {LEDGER_OUT}")
    print(f"Candidates: {CANDIDATES_OUT}")
    print(f"Collisions: {COLLISIONS_OUT}")
    print()
    print("KEY COUNTS")
    print(f"MAX_FETCHES: {module.MAX_FETCHES}")
    print(f"Candidate rows: {candidate_rows}")
    print(f"Unique CSV URLs: {unique_csv_urls}")
    print(f"Cache files: {len(cache_files)}")
    print(
        "Parsed cache files: "
        f"{summary['cache_population']['parsed_cache_files']}"
    )
    print(
        "Complete cached race identities: "
        f"{len(identities)}"
    )
    print(
        "Existing ingestion distinct races: "
        f"{existing_ingestion_races}"
    )
    print(f"Cache filename collisions: {collision_count}")
    print()
    print("DECISION")
    print(decision)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
