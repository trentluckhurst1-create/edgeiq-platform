from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "public" / "data"

V2_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "racingcom-ingestion-v2"
)

INVESTIGATION_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "standard-time-investigation"
)

CALENDAR_SOURCE = (
    DATA
    / "edgeiq_racingcom_calendar_discovery_v1.csv"
)

COMPLETED_SOURCE = (
    DATA
    / "edgeiq_racingcom_completed_payload_probe_v1.csv"
)

RACE_CONTRACT = (
    V2_DIR
    / "edgeiq_racingcom_race_discovery_contract_v2.csv"
)

LEDGER_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_upstream_race_evidence_ledger_v1.csv"
)

MEETING_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_upstream_meeting_expansion_v1.csv"
)

OVERLAP_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_upstream_source_overlap_v1.csv"
)

COLUMN_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_upstream_source_columns_v1.csv"
)

AUDIT_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_upstream_race_evidence_audit_v1.csv"
)

SUMMARY_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_upstream_race_evidence_v1.json"
)

REPORT_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_upstream_race_evidence_v1.md"
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


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()

    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
        on_bad_lines="skip",
        low_memory=False,
    )


def date_key(value: Any) -> str:
    text = clean(value)

    if not text:
        return ""

    parsed = pd.to_datetime(
        text,
        errors="coerce",
    )

    if pd.isna(parsed):
        match = re.search(
            r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b",
            text,
        )

        if not match:
            return ""

        year, month, day = match.groups()

        return (
            f"{int(year):04d}-"
            f"{int(month):02d}-"
            f"{int(day):02d}"
        )

    return parsed.strftime("%Y-%m-%d")


def race_no(value: Any) -> int | None:
    text = clean(value)

    if not text:
        return None

    match = re.search(r"\d+", text)

    if not match:
        return None

    number = int(match.group())

    return number if number > 0 else None


def race_no_from_url(value: Any) -> int | None:
    match = re.search(
        r"/race/(\d+)(?:/|$)",
        clean(value),
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    return int(match.group(1))


def track_key(value: Any) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "",
        clean(value).lower(),
    )


def first_value(
    row: pd.Series,
    names: list[str],
) -> str:
    lower_map = {
        column.lower(): column
        for column in row.index
    }

    for name in names:
        column = lower_map.get(
            name.lower()
        )

        if not column:
            continue

        value = clean(row.get(column))

        if value:
            return value

    return ""


def first_matching_column(
    row: pd.Series,
    terms: list[str],
) -> tuple[str, str]:
    for column in row.index:
        lowered = column.lower()

        if not any(
            term in lowered
            for term in terms
        ):
            continue

        value = clean(row.get(column))

        if value:
            return column, value

    return "", ""


def inspect_source(
    frame: pd.DataFrame,
    source_name: str,
    source_path: Path,
    current_date: pd.Timestamp,
) -> list[dict[str, Any]]:
    rows = []

    if frame.empty:
        return rows

    for index, row in frame.iterrows():
        date_column, raw_date = (
            first_matching_column(
                row,
                ["race_date", "meeting_date", "date"],
            )
        )

        track_column, raw_track = (
            first_matching_column(
                row,
                ["track", "venue", "meeting"],
            )
        )

        race_column, raw_race = (
            first_matching_column(
                row,
                [
                    "race_no",
                    "race_number",
                    "raceno",
                    "racenumber",
                ],
            )
        )

        url_column, raw_url = (
            first_matching_column(
                row,
                [
                    "speed_data_url",
                    "race_url",
                    "page_url",
                    "url",
                ],
            )
        )

        race_from_column = race_no(
            raw_race
        )

        race_from_url = race_no_from_url(
            raw_url
        )

        effective_race = (
            race_from_column
            or race_from_url
        )

        race_date = date_key(raw_date)
        parsed_date = pd.to_datetime(
            race_date,
            errors="coerce",
        )

        if race_from_column is not None:
            evidence_origin = (
                "EXPLICIT_RACE_COLUMN"
            )
        elif race_from_url is not None:
            evidence_origin = (
                "URL_DERIVED_ONLY"
            )
        else:
            evidence_origin = (
                "NO_RACE_EVIDENCE"
            )

        rows.append(
            {
                "source_name": source_name,
                "source_file": (
                    source_path
                    .relative_to(ROOT)
                    .as_posix()
                ),
                "source_row_number": (
                    int(index) + 2
                ),
                "race_date": race_date,
                "future_dated": (
                    "YES"
                    if pd.notna(parsed_date)
                    and parsed_date > current_date
                    else "NO"
                ),
                "track": raw_track,
                "track_key": track_key(
                    raw_track
                ),
                "race_no_column": (
                    race_column
                ),
                "race_no_raw": raw_race,
                "race_no_from_column": (
                    race_from_column
                    if race_from_column is not None
                    else ""
                ),
                "url_column": url_column,
                "source_url": raw_url,
                "race_no_from_url": (
                    race_from_url
                    if race_from_url is not None
                    else ""
                ),
                "effective_race_no": (
                    effective_race
                    if effective_race is not None
                    else ""
                ),
                "race_evidence_origin": (
                    evidence_origin
                ),
                "date_column": date_column,
                "track_column": track_column,
            }
        )

    return rows


def main() -> int:
    print(
        "EDGEIQ Racing.com Upstream Race Evidence V1"
    )
    print()

    INVESTIGATION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    current_date = pd.Timestamp(
        datetime.now().date()
    )

    print("[1/6] Reading upstream sources...")

    calendar = read_csv(
        CALENDAR_SOURCE
    )

    completed = read_csv(
        COMPLETED_SOURCE
    )

    race_contract = read_csv(
        RACE_CONTRACT
    )

    print(
        f"Calendar rows: {len(calendar)}"
    )
    print(
        f"Completed rows: {len(completed)}"
    )
    print(
        f"V2 race-contract rows: "
        f"{len(race_contract)}"
    )

    print("[2/6] Inventorying source columns...")

    column_rows = []

    for source_name, path, frame in [
        (
            "CALENDAR_DISCOVERY_V1",
            CALENDAR_SOURCE,
            calendar,
        ),
        (
            "COMPLETED_PAYLOAD_PROBE_V1",
            COMPLETED_SOURCE,
            completed,
        ),
    ]:
        for position, column in enumerate(
            frame.columns,
            start=1,
        ):
            nonblank = int(
                frame[column]
                .map(clean)
                .map(bool)
                .sum()
            )

            unique_nonblank = int(
                frame.loc[
                    frame[column]
                    .map(clean)
                    .map(bool),
                    column,
                ]
                .map(clean)
                .nunique()
            )

            column_rows.append(
                {
                    "source_name": source_name,
                    "source_file": (
                        path
                        .relative_to(ROOT)
                        .as_posix()
                    ),
                    "column_position": position,
                    "column_name": column,
                    "rows": len(frame),
                    "nonblank_rows": nonblank,
                    "unique_nonblank_values": (
                        unique_nonblank
                    ),
                }
            )

    columns = pd.DataFrame(
        column_rows
    )

    columns.to_csv(
        COLUMN_OUT,
        index=False,
        encoding="utf-8",
    )

    print("[3/6] Classifying race evidence origin...")

    ledger_rows = []

    ledger_rows.extend(
        inspect_source(
            calendar,
            "CALENDAR_DISCOVERY_V1",
            CALENDAR_SOURCE,
            current_date,
        )
    )

    ledger_rows.extend(
        inspect_source(
            completed,
            "COMPLETED_PAYLOAD_PROBE_V1",
            COMPLETED_SOURCE,
            current_date,
        )
    )

    ledger = pd.DataFrame(
        ledger_rows
    )

    ledger = ledger.sort_values(
        [
            "race_date",
            "track_key",
            "effective_race_no",
            "source_name",
            "source_row_number",
        ],
        ascending=[
            False,
            True,
            True,
            True,
            True,
        ],
    ).reset_index(drop=True)

    ledger.to_csv(
        LEDGER_OUT,
        index=False,
        encoding="utf-8",
    )

    print("[4/6] Profiling meeting expansions...")

    valid = ledger[
        ledger["effective_race_no"]
        .map(clean)
        .map(bool)
    ].copy()

    valid["race_no_numeric"] = (
        pd.to_numeric(
            valid["effective_race_no"],
            errors="coerce",
        )
    )

    meeting_rows = []

    for (
        source_name,
        race_date,
        meeting_track_key,
    ), group in valid.groupby(
        [
            "source_name",
            "race_date",
            "track_key",
        ],
        dropna=False,
    ):
        race_numbers = sorted(
            {
                int(value)
                for value in group[
                    "race_no_numeric"
                ].dropna()
            }
        )

        explicit_count = int(
            (
                group["race_evidence_origin"]
                == "EXPLICIT_RACE_COLUMN"
            ).sum()
        )

        url_only_count = int(
            (
                group["race_evidence_origin"]
                == "URL_DERIVED_ONLY"
            ).sum()
        )

        future_count = int(
            (
                group["future_dated"]
                == "YES"
            ).sum()
        )

        meeting_rows.append(
            {
                "source_name": source_name,
                "race_date": race_date,
                "track": clean(
                    group.iloc[0]["track"]
                ),
                "track_key": meeting_track_key,
                "source_rows": len(group),
                "distinct_races": len(
                    race_numbers
                ),
                "minimum_race_no": (
                    min(race_numbers)
                    if race_numbers
                    else ""
                ),
                "maximum_race_no": (
                    max(race_numbers)
                    if race_numbers
                    else ""
                ),
                "race_sequence": ",".join(
                    str(value)
                    for value in race_numbers
                ),
                "exact_1_to_12_pattern": (
                    "YES"
                    if race_numbers
                    == list(range(1, 13))
                    else "NO"
                ),
                "explicit_race_column_rows": (
                    explicit_count
                ),
                "url_derived_only_rows": (
                    url_only_count
                ),
                "future_dated_rows": (
                    future_count
                ),
                "all_future_dated": (
                    "YES"
                    if future_count == len(group)
                    else "NO"
                ),
            }
        )

    meetings = pd.DataFrame(
        meeting_rows
    )

    meetings = meetings.sort_values(
        [
            "race_date",
            "track_key",
            "source_name",
        ],
        ascending=[
            False,
            True,
            True,
        ],
    ).reset_index(drop=True)

    meetings.to_csv(
        MEETING_OUT,
        index=False,
        encoding="utf-8",
    )

    print("[5/6] Measuring source overlap...")

    overlap_source = valid.copy()

    overlap_source["canonical_key"] = (
        overlap_source["race_date"]
        + "|"
        + overlap_source["track_key"]
        + "|"
        + overlap_source[
            "race_no_numeric"
        ]
        .fillna(-1)
        .astype(int)
        .astype(str)
    )

    overlap_rows = []

    for canonical_key, group in (
        overlap_source.groupby(
            "canonical_key"
        )
    ):
        sources = sorted(
            set(group["source_name"])
        )

        overlap_rows.append(
            {
                "canonical_key": (
                    canonical_key
                ),
                "race_date": (
                    group.iloc[0]["race_date"]
                ),
                "track": (
                    group.iloc[0]["track"]
                ),
                "race_no": int(
                    group.iloc[0][
                        "race_no_numeric"
                    ]
                ),
                "source_count": len(
                    sources
                ),
                "sources": ",".join(
                    sources
                ),
                "independently_present_in_both": (
                    "YES"
                    if len(sources) > 1
                    else "NO"
                ),
                "source_row_count": len(
                    group
                ),
            }
        )

    overlap = pd.DataFrame(
        overlap_rows
    )

    overlap = overlap.sort_values(
        [
            "race_date",
            "track",
            "race_no",
        ],
        ascending=[
            False,
            True,
            True,
        ],
    ).reset_index(drop=True)

    overlap.to_csv(
        OVERLAP_OUT,
        index=False,
        encoding="utf-8",
    )

    print("[6/6] Writing audit and decision...")

    origin_counts = Counter(
        ledger["race_evidence_origin"]
    )

    exact_twelve_meetings = int(
        (
            meetings[
                "exact_1_to_12_pattern"
            ]
            == "YES"
        ).sum()
    )

    future_rows = int(
        (
            ledger["future_dated"]
            == "YES"
        ).sum()
    )

    future_exact_twelve = int(
        (
            (
                meetings[
                    "exact_1_to_12_pattern"
                ]
                == "YES"
            )
            & (
                meetings[
                    "all_future_dated"
                ]
                == "YES"
            )
        ).sum()
    )

    both_source_races = int(
        (
            overlap[
                "independently_present_in_both"
            ]
            == "YES"
        ).sum()
    )

    url_only_rows = int(
        (
            ledger[
                "race_evidence_origin"
            ]
            == "URL_DERIVED_ONLY"
        ).sum()
    )

    explicit_rows = int(
        (
            ledger[
                "race_evidence_origin"
            ]
            == "EXPLICIT_RACE_COLUMN"
        ).sum()
    )

    if (
        future_exact_twelve > 0
        or url_only_rows > 0
    ):
        decision = (
            "UPSTREAM_RACE_EVIDENCE_"
            "REQUIRES_REMEDIATION"
        )
    else:
        decision = (
            "UPSTREAM_RACE_EVIDENCE_"
            "SUPPORTED"
        )

    audit_rows = [
        {
            "check": (
                "source_files_present"
            ),
            "status": (
                "PASS"
                if CALENDAR_SOURCE.exists()
                and COMPLETED_SOURCE.exists()
                else "FAIL"
            ),
            "actual": (
                f"calendar={CALENDAR_SOURCE.exists()}; "
                f"completed={COMPLETED_SOURCE.exists()}"
            ),
            "expected": "Both source files present",
        },
        {
            "check": (
                "future_source_rows"
            ),
            "status": (
                "REVIEW"
                if future_rows > 0
                else "PASS"
            ),
            "actual": str(future_rows),
            "expected": (
                "Future rows must not be treated "
                "as completed race evidence"
            ),
        },
        {
            "check": (
                "url_derived_only_race_rows"
            ),
            "status": (
                "REVIEW"
                if url_only_rows > 0
                else "PASS"
            ),
            "actual": str(url_only_rows),
            "expected": (
                "Race existence supported by "
                "explicit race-level source evidence"
            ),
        },
        {
            "check": (
                "future_exact_1_to_12_meetings"
            ),
            "status": (
                "REVIEW"
                if future_exact_twelve > 0
                else "PASS"
            ),
            "actual": str(
                future_exact_twelve
            ),
            "expected": "0",
        },
        {
            "check": (
                "source_overlap"
            ),
            "status": "INFO",
            "actual": str(
                both_source_races
            ),
            "expected": (
                "Independent overlap measured, "
                "not assumed"
            ),
        },
        {
            "check": (
                "production_modified"
            ),
            "status": "PASS",
            "actual": "NO",
            "expected": "NO",
        },
        {
            "check": (
                "network_access"
            ),
            "status": "PASS",
            "actual": "NO",
            "expected": "NO",
        },
    ]

    audit = pd.DataFrame(
        audit_rows
    )

    audit.to_csv(
        AUDIT_OUT,
        index=False,
        encoding="utf-8",
    )

    summary = {
        "generated_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "current_date_used": (
            current_date.strftime(
                "%Y-%m-%d"
            )
        ),
        "governance": {
            "read_only": True,
            "network_access_performed": False,
            "production_files_modified": False,
            "v2_contracts_modified": False,
        },
        "source_rows": {
            "calendar": len(calendar),
            "completed": len(completed),
            "total": len(ledger),
        },
        "evidence_origin_counts": dict(
            sorted(origin_counts.items())
        ),
        "meeting_findings": {
            "meeting_source_groups": len(
                meetings
            ),
            "exact_1_to_12_patterns": (
                exact_twelve_meetings
            ),
            "future_exact_1_to_12_patterns": (
                future_exact_twelve
            ),
        },
        "date_findings": {
            "future_source_rows": (
                future_rows
            ),
        },
        "overlap_findings": {
            "canonical_races_present_in_both_sources": (
                both_source_races
            ),
        },
        "explicit_race_column_rows": (
            explicit_rows
        ),
        "url_derived_only_rows": (
            url_only_rows
        ),
        "decision": decision,
    }

    SUMMARY_OUT.write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )

    origin_lines = "\n".join(
        f"- `{name}`: **{count}**"
        for name, count in sorted(
            origin_counts.items()
        )
    )

    report = f"""# EDGEIQ Racing.com Upstream Race Evidence V1

Generated UTC: `{summary['generated_utc']}`

## Governance boundary

- Read-only forensic diagnostic.
- No network access.
- No production builder executed.
- No V1 or V2 contract modified.
- No cache modified.

## Source population

- Calendar rows: **{len(calendar)}**
- Completed-probe rows: **{len(completed)}**
- Combined source rows: **{len(ledger)}**

## Race evidence origin

{origin_lines}

## Date findings

- Future-dated source rows: **{future_rows}**

Future-dated rows cannot constitute completed-race evidence.

## Meeting expansion findings

- Source meeting groups: **{len(meetings)}**
- Exact race sequence `1?12`: **{exact_twelve_meetings}**
- Future meetings with exact sequence `1?12`: **{future_exact_twelve}**

## Source independence

- Canonical races appearing in both source files: **{both_source_races}**

Presence in both sources does not automatically prove independence if one source was generated from the other. This diagnostic records overlap only.

## Interpretation

An explicit race number in a source column is stronger than a race number recovered solely from a URL.

A future race page URL is scheduling or construction evidence, not completed-race or CSV-existence evidence.

The V2 foundation correctly avoided generating CSV URLs, but its source-admission classification must be tightened if upstream files contain constructed race pages.

## Decision

**{decision}**

## Artifacts

- `{LEDGER_OUT.relative_to(ROOT).as_posix()}`
- `{MEETING_OUT.relative_to(ROOT).as_posix()}`
- `{OVERLAP_OUT.relative_to(ROOT).as_posix()}`
- `{COLUMN_OUT.relative_to(ROOT).as_posix()}`
- `{AUDIT_OUT.relative_to(ROOT).as_posix()}`
- `{SUMMARY_OUT.relative_to(ROOT).as_posix()}`
- `{REPORT_OUT.relative_to(ROOT).as_posix()}`
"""

    REPORT_OUT.write_text(
        report,
        encoding="utf-8",
    )

    print()
    print("COMPLETE")
    print(f"Report: {REPORT_OUT}")
    print(f"Evidence ledger: {LEDGER_OUT}")
    print(f"Meeting profile: {MEETING_OUT}")
    print(f"Source overlap: {OVERLAP_OUT}")
    print(f"Column inventory: {COLUMN_OUT}")
    print(f"Audit: {AUDIT_OUT}")
    print()
    print("KEY COUNTS")
    print(
        "Explicit race-column rows: "
        f"{explicit_rows}"
    )
    print(
        "URL-derived-only rows: "
        f"{url_only_rows}"
    )
    print(
        "Future source rows: "
        f"{future_rows}"
    )
    print(
        "Exact 1-12 meeting groups: "
        f"{exact_twelve_meetings}"
    )
    print(
        "Future exact 1-12 groups: "
        f"{future_exact_twelve}"
    )
    print(
        "Races present in both sources: "
        f"{both_source_races}"
    )
    print()
    print("DECISION")
    print(decision)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
