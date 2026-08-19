from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import importlib.util
import json
import re
import sys
from typing import Any

import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

BUILDER_PATH = (
    REPOSITORY_ROOT
    / "scripts"
    / "build_edgeiq_racingcom_csv_ingestion_v1.py"
)

PUBLIC_DATA = REPOSITORY_ROOT / "public" / "data"

INGESTION_PATH = (
    PUBLIC_DATA
    / "edgeiq_racingcom_csv_ingestion_v1.csv"
)

DIAGNOSTICS_PATH = (
    PUBLIC_DATA
    / "edgeiq_racingcom_csv_ingestion_diagnostics_v1.csv"
)

INVESTIGATION_DIR = (
    REPOSITORY_ROOT
    / "docs"
    / "performance-intelligence"
    / "standard-time-investigation"
)

URL_LEDGER_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_url_admission_order_ledger_v1.csv"
)

HISTORICAL_SOURCES_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_historical_success_sources_v1.csv"
)

FIRST_50_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_first_50_url_cohort_v1.csv"
)

SUMMARY_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_url_admission_order_v1.json"
)

REPORT_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_url_admission_order_v1.md"
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


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "edgeiq_racingcom_url_order_forensic_v1",
        BUILDER_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to load Racing.com ingestion builder."
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return module


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()

    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        low_memory=False,
    )


def read_metric(
    diagnostics: pd.DataFrame,
    metric: str,
) -> str:
    if diagnostics.empty:
        return ""

    if not {"metric", "value"}.issubset(
        diagnostics.columns
    ):
        return ""

    matches = diagnostics[
        diagnostics["metric"].map(clean) == metric
    ]

    if matches.empty:
        return ""

    return clean(matches.iloc[0]["value"])


def url_filename(url: str) -> str:
    try:
        return Path(
            urlparse(url).path
        ).name
    except Exception:
        return ""


def url_host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def filename_identity(
    filename: str,
) -> tuple[str, str]:
    text = clean(filename)

    match = re.fullmatch(
        r"(\d+)_([0-9]+)\.csv",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return "", ""

    return match.group(1), match.group(2)


def reconstruct_candidates(
    module,
) -> pd.DataFrame:
    candidates = module.discover_candidates()

    if candidates is None or candidates.empty:
        return pd.DataFrame()

    frame = candidates.copy()

    required = [
        "race_date",
        "track",
        "race_no",
        "speed_data_url",
        "csv_url",
        "discovery_method",
    ]

    for column in required:
        if column not in frame.columns:
            frame[column] = ""

    for column in required:
        frame[column] = frame[column].map(clean)

    frame = frame[
        frame["csv_url"].map(bool)
    ].copy()

    frame = frame.drop_duplicates(
        subset=["csv_url"],
        keep="first",
    ).reset_index(drop=True)

    frame.insert(
        0,
        "admission_position",
        range(1, len(frame) + 1),
    )

    frame["within_default_first_50"] = frame[
        "admission_position"
    ].map(
        lambda value: (
            "YES"
            if int(value) <= int(module.MAX_FETCHES)
            else "NO"
        )
    )

    frame["url_host"] = frame[
        "csv_url"
    ].map(url_host)

    frame["url_filename"] = frame[
        "csv_url"
    ].map(url_filename)

    identities = frame[
        "url_filename"
    ].map(filename_identity)

    frame["cloudfront_race_id"] = identities.map(
        lambda item: item[0]
    )

    frame["cloudfront_race_suffix"] = identities.map(
        lambda item: item[1]
    )

    frame["filename_matches_expected_pattern"] = (
        frame["cloudfront_race_id"].map(bool)
    ).map(
        lambda value: "YES" if value else "NO"
    )

    return frame


def historical_sources(
    ingestion: pd.DataFrame,
    url_ledger: pd.DataFrame,
) -> pd.DataFrame:
    columns = [
        "source_url",
        "ingestion_runner_rows",
        "ingestion_race_date",
        "ingestion_track",
        "ingestion_race_no",
        "ingestion_distance",
        "current_candidate_present",
        "current_admission_position",
        "within_current_first_50",
        "current_candidate_race_date",
        "current_candidate_track",
        "current_candidate_race_no",
        "current_discovery_method",
        "url_host",
        "url_filename",
        "cloudfront_race_id",
        "cloudfront_race_suffix",
    ]

    if (
        ingestion.empty
        or "source_url" not in ingestion.columns
    ):
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, Any]] = []

    for source_url, group in ingestion.groupby(
        ingestion["source_url"].map(clean),
        dropna=False,
    ):
        source_url = clean(source_url)

        if not source_url:
            continue

        match = url_ledger[
            url_ledger["csv_url"] == source_url
        ]

        current = (
            match.iloc[0].to_dict()
            if not match.empty
            else {}
        )

        def values(column: str) -> str:
            if column not in group.columns:
                return ""

            return " | ".join(
                sorted(
                    {
                        clean(value)
                        for value in group[column]
                        if clean(value)
                    }
                )
            )

        filename = url_filename(source_url)
        race_id, suffix = filename_identity(filename)

        rows.append(
            {
                "source_url": source_url,
                "ingestion_runner_rows": len(group),
                "ingestion_race_date": values(
                    "race_date"
                ),
                "ingestion_track": values("track"),
                "ingestion_race_no": values(
                    "race_no"
                ),
                "ingestion_distance": values(
                    "distance"
                ),
                "current_candidate_present": (
                    "YES" if current else "NO"
                ),
                "current_admission_position": clean(
                    current.get(
                        "admission_position",
                        "",
                    )
                ),
                "within_current_first_50": clean(
                    current.get(
                        "within_default_first_50",
                        "",
                    )
                ),
                "current_candidate_race_date": clean(
                    current.get("race_date", "")
                ),
                "current_candidate_track": clean(
                    current.get("track", "")
                ),
                "current_candidate_race_no": clean(
                    current.get("race_no", "")
                ),
                "current_discovery_method": clean(
                    current.get(
                        "discovery_method",
                        "",
                    )
                ),
                "url_host": url_host(source_url),
                "url_filename": filename,
                "cloudfront_race_id": race_id,
                "cloudfront_race_suffix": suffix,
            }
        )

    return pd.DataFrame(rows, columns=columns)


def count_values(
    frame: pd.DataFrame,
    column: str,
) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}

    counter = Counter(
        clean(value) or "<EMPTY>"
        for value in frame[column]
    )

    return dict(sorted(counter.items()))


def main() -> int:
    print("EDGEIQ Racing.com URL Admission Order V1")
    print()

    INVESTIGATION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    module = load_builder()

    print("[1/4] Reconstructing current URL ordering...")
    ledger = reconstruct_candidates(module)

    ledger.to_csv(
        URL_LEDGER_OUT,
        index=False,
        encoding="utf-8",
    )

    first_50 = ledger[
        ledger["within_default_first_50"] == "YES"
    ].copy()

    first_50.to_csv(
        FIRST_50_OUT,
        index=False,
        encoding="utf-8",
    )

    print("[2/4] Reading historical ingestion sources...")
    ingestion = read_csv(INGESTION_PATH)
    diagnostics = read_csv(DIAGNOSTICS_PATH)

    historical = historical_sources(
        ingestion,
        ledger,
    )

    historical.to_csv(
        HISTORICAL_SOURCES_OUT,
        index=False,
        encoding="utf-8",
    )

    print("[3/4] Comparing current and historical populations...")

    current_urls = set(
        ledger["csv_url"]
    ) if not ledger.empty else set()

    historical_urls = set(
        historical["source_url"]
    ) if not historical.empty else set()

    historical_present = (
        int(
            (
                historical[
                    "current_candidate_present"
                ] == "YES"
            ).sum()
        )
        if not historical.empty
        else 0
    )

    historical_in_first_50 = (
        int(
            (
                historical[
                    "within_current_first_50"
                ] == "YES"
            ).sum()
        )
        if not historical.empty
        else 0
    )

    historical_positions = []

    if not historical.empty:
        for value in historical[
            "current_admission_position"
        ]:
            text = clean(value)
            if text.isdigit():
                historical_positions.append(
                    int(text)
                )

    historical_candidate_count = read_metric(
        diagnostics,
        "unique_csv_urls",
    )

    try:
        historical_candidate_count_int = int(
            historical_candidate_count
        )
    except Exception:
        historical_candidate_count_int = 0

    current_candidate_count = len(ledger)

    candidate_count_delta = (
        current_candidate_count
        - historical_candidate_count_int
        if historical_candidate_count_int
        else None
    )

    first_50_dates = count_values(
        first_50,
        "race_date",
    )

    first_50_tracks = count_values(
        first_50,
        "track",
    )

    first_50_methods = count_values(
        first_50,
        "discovery_method",
    )

    first_50_hosts = count_values(
        first_50,
        "url_host",
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
        "builder": {
            "max_fetches": int(module.MAX_FETCHES),
        },
        "historical_run": {
            "run_timestamp_utc": read_metric(
                diagnostics,
                "run_timestamp_utc",
            ),
            "candidate_rows": read_metric(
                diagnostics,
                "candidate_rows",
            ),
            "direct_csv_candidates": read_metric(
                diagnostics,
                "direct_csv_candidates",
            ),
            "unique_csv_urls": (
                historical_candidate_count
            ),
            "fetch_attempts": read_metric(
                diagnostics,
                "fetch_attempts",
            ),
            "csvs_fetched_or_cached": read_metric(
                diagnostics,
                "csvs_fetched_or_cached",
            ),
            "csv_fetch_failures": read_metric(
                diagnostics,
                "csv_fetch_failures",
            ),
            "csvs_parsed": read_metric(
                diagnostics,
                "csvs_parsed",
            ),
            "rows_parsed": read_metric(
                diagnostics,
                "rows_parsed",
            ),
        },
        "current_population": {
            "unique_csv_urls": current_candidate_count,
            "first_50_rows": len(first_50),
            "distinct_hosts": (
                int(ledger["url_host"].nunique())
                if not ledger.empty
                else 0
            ),
            "distinct_race_dates": (
                int(ledger["race_date"].nunique())
                if not ledger.empty
                else 0
            ),
            "distinct_tracks": (
                int(ledger["track"].nunique())
                if not ledger.empty
                else 0
            ),
            "expected_filename_pattern_count": (
                int(
                    (
                        ledger[
                            "filename_matches_expected_pattern"
                        ] == "YES"
                    ).sum()
                )
                if not ledger.empty
                else 0
            ),
        },
        "population_drift": {
            "historical_unique_urls": (
                historical_candidate_count_int
            ),
            "current_unique_urls": (
                current_candidate_count
            ),
            "current_minus_historical": (
                candidate_count_delta
            ),
        },
        "historical_success_sources": {
            "distinct_source_urls": (
                len(historical_urls)
            ),
            "present_in_current_candidates": (
                historical_present
            ),
            "absent_from_current_candidates": (
                len(historical_urls)
                - historical_present
            ),
            "within_current_first_50": (
                historical_in_first_50
            ),
            "minimum_current_position": (
                min(historical_positions)
                if historical_positions
                else None
            ),
            "maximum_current_position": (
                max(historical_positions)
                if historical_positions
                else None
            ),
        },
        "first_50_profile": {
            "dates": first_50_dates,
            "tracks": first_50_tracks,
            "discovery_methods": first_50_methods,
            "hosts": first_50_hosts,
        },
        "url_set_counts": {
            "current_urls": len(current_urls),
            "historical_success_urls": (
                len(historical_urls)
            ),
            "historical_success_urls_still_current": (
                len(
                    current_urls
                    & historical_urls
                )
            ),
        },
    }

    if len(historical_urls) != 8:
        decision = (
            "HISTORICAL_SOURCE_COUNT_MISMATCH"
        )
    elif historical_present == 8:
        decision = (
            "HISTORICAL_SUCCESS_URLS_RECONSTRUCTED"
        )
    elif historical_present > 0:
        decision = (
            "HISTORICAL_SUCCESS_URLS_PARTIALLY_RECONSTRUCTED"
        )
    else:
        decision = (
            "HISTORICAL_SUCCESS_URLS_NOT_IN_CURRENT_POPULATION"
        )

    summary["decision"] = decision

    SUMMARY_OUT.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("[4/4] Writing governed report...")

    historical_table_lines = []

    for row in historical.to_dict("records"):
        historical_table_lines.append(
            "| "
            + " | ".join(
                [
                    clean(row.get("url_filename")),
                    clean(
                        row.get(
                            "ingestion_race_date"
                        )
                    ),
                    clean(
                        row.get(
                            "ingestion_track"
                        )
                    ),
                    clean(
                        row.get(
                            "ingestion_race_no"
                        )
                    ),
                    clean(
                        row.get(
                            "ingestion_runner_rows"
                        )
                    ),
                    clean(
                        row.get(
                            "current_candidate_present"
                        )
                    ),
                    clean(
                        row.get(
                            "current_admission_position"
                        )
                    ),
                    clean(
                        row.get(
                            "within_current_first_50"
                        )
                    ),
                ]
            )
            + " |"
        )

    if not historical_table_lines:
        historical_table_lines = [
            "| No historical sources found |  |  |  |  |  |  |  |"
        ]

    report = f"""# EDGEIQ Racing.com URL Admission Order V1

Generated UTC: `{summary['generated_utc']}`

## Governance boundary

- Read-only diagnostic.
- No network access.
- Production builder not executed.
- No cache or governed output modified.
- Current candidate ordering reconstructed through the existing discovery function.

## Historical run evidence

- Run timestamp: **{summary['historical_run']['run_timestamp_utc'] or 'NOT_AVAILABLE'}**
- Historical unique CSV URLs: **{summary['historical_run']['unique_csv_urls'] or 'NOT_AVAILABLE'}**
- Fetch attempts: **{summary['historical_run']['fetch_attempts'] or 'NOT_AVAILABLE'}**
- CSVs fetched or cached: **{summary['historical_run']['csvs_fetched_or_cached'] or 'NOT_AVAILABLE'}**
- Fetch failures: **{summary['historical_run']['csv_fetch_failures'] or 'NOT_AVAILABLE'}**
- CSVs parsed: **{summary['historical_run']['csvs_parsed'] or 'NOT_AVAILABLE'}**
- Runner rows parsed: **{summary['historical_run']['rows_parsed'] or 'NOT_AVAILABLE'}**

## Current candidate population

- Unique CSV URLs: **{current_candidate_count}**
- Default admission cap: **{module.MAX_FETCHES}**
- URLs in current first cohort: **{len(first_50)}**
- Distinct dates: **{summary['current_population']['distinct_race_dates']}**
- Distinct tracks: **{summary['current_population']['distinct_tracks']}**
- URLs matching the expected `raceid_suffix.csv` pattern: **{summary['current_population']['expected_filename_pattern_count']}**

## Candidate-population drift

- Historical unique URLs: **{historical_candidate_count_int or 'NOT_AVAILABLE'}**
- Current unique URLs: **{current_candidate_count}**
- Current minus historical: **{candidate_count_delta if candidate_count_delta is not None else 'NOT_AVAILABLE'}**

## Historical successful sources

- Historical distinct source URLs: **{len(historical_urls)}**
- Still present in current candidates: **{historical_present}**
- Missing from current candidates: **{len(historical_urls) - historical_present}**
- Currently positioned inside first 50: **{historical_in_first_50}**
- Minimum current admission position: **{min(historical_positions) if historical_positions else 'NOT_AVAILABLE'}**
- Maximum current admission position: **{max(historical_positions) if historical_positions else 'NOT_AVAILABLE'}**

| CSV | Ingestion date | Ingestion track | Race | Runners | Current candidate | Current position | Current first 50 |
|---|---:|---|---:|---:|---|---:|---|
{chr(10).join(historical_table_lines)}

## Interpretation boundary

This diagnostic does not assume that current HTTP status matches the May 2026 run.

It establishes only:

1. the deterministic candidate ordering currently produced by the builder;
2. whether the eight historically successful source URLs remain discoverable;
3. whether those historical successes are concentrated within the builder's first 50 admission positions;
4. whether the candidate population has drifted since the historical run.

## Decision

**{decision}**

## Artifacts

- `{URL_LEDGER_OUT.relative_to(REPOSITORY_ROOT).as_posix()}`
- `{FIRST_50_OUT.relative_to(REPOSITORY_ROOT).as_posix()}`
- `{HISTORICAL_SOURCES_OUT.relative_to(REPOSITORY_ROOT).as_posix()}`
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
    print(f"URL ledger: {URL_LEDGER_OUT}")
    print(
        "Historical sources: "
        f"{HISTORICAL_SOURCES_OUT}"
    )
    print()
    print("KEY COUNTS")
    print(
        "Historical unique URLs: "
        f"{historical_candidate_count_int}"
    )
    print(
        "Current unique URLs: "
        f"{current_candidate_count}"
    )
    print(
        "Historical successful sources: "
        f"{len(historical_urls)}"
    )
    print(
        "Historical sources still current: "
        f"{historical_present}"
    )
    print(
        "Historical sources in current first 50: "
        f"{historical_in_first_50}"
    )
    print()
    print("DECISION")
    print(decision)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
