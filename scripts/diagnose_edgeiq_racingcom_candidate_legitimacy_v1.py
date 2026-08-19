from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INVESTIGATION_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "standard-time-investigation"
)

URL_LEDGER = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_url_admission_order_ledger_v1.csv"
)

HISTORICAL_SOURCES = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_historical_success_sources_v1.csv"
)

CALENDAR_SOURCE = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_racingcom_calendar_discovery_v1.csv"
)

PROBE_SOURCE = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_racingcom_completed_payload_probe_v1.csv"
)

LEDGER_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_candidate_legitimacy_ledger_v1.csv"
)

MEETING_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_candidate_meeting_profile_v1.csv"
)

COLUMN_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_source_column_inventory_v1.csv"
)

SUMMARY_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_candidate_legitimacy_v1.json"
)

REPORT_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_candidate_legitimacy_v1.md"
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


def integer(value: Any) -> int | None:
    text = clean(value)

    if not text:
        return None

    match = re.search(r"\d+", text)

    if not match:
        return None

    try:
        return int(match.group())
    except Exception:
        return None


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()

    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        low_memory=False,
    )


def normalise_track(value: Any) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "",
        clean(value).lower(),
    )


def source_column_inventory(
    named_frames: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for source_name, frame in named_frames.items():
        for column in frame.columns:
            values = frame[column].map(clean)

            non_empty = values[values.map(bool)]

            rows.append(
                {
                    "source": source_name,
                    "column": column,
                    "row_count": len(frame),
                    "non_empty_count": len(non_empty),
                    "distinct_non_empty": (
                        int(non_empty.nunique())
                        if not non_empty.empty
                        else 0
                    ),
                    "sample_values": " | ".join(
                        non_empty.drop_duplicates()
                        .head(8)
                        .tolist()
                    ),
                }
            )

    return pd.DataFrame(rows)


def likely_columns(
    frame: pd.DataFrame,
    patterns: list[str],
) -> list[str]:
    result = []

    for column in frame.columns:
        lowered = column.lower()

        if any(
            pattern in lowered
            for pattern in patterns
        ):
            result.append(column)

    return result


def evidence_rows(
    frame: pd.DataFrame,
    source_name: str,
) -> list[dict[str, Any]]:
    if frame.empty:
        return []

    date_columns = likely_columns(
        frame,
        ["date"],
    )

    track_columns = likely_columns(
        frame,
        [
            "track",
            "venue",
            "meeting",
        ],
    )

    race_number_columns = likely_columns(
        frame,
        [
            "raceno",
            "race_no",
            "racenumber",
            "race_number",
        ],
    )

    race_count_columns = likely_columns(
        frame,
        [
            "racecount",
            "race_count",
            "numberofraces",
            "number_of_races",
            "totalraces",
            "total_races",
        ],
    )

    rows = []

    for _, source_row in frame.iterrows():
        dates = [
            clean(source_row.get(column))
            for column in date_columns
            if clean(source_row.get(column))
        ]

        tracks = [
            clean(source_row.get(column))
            for column in track_columns
            if clean(source_row.get(column))
        ]

        race_numbers = [
            integer(source_row.get(column))
            for column in race_number_columns
        ]

        race_counts = [
            integer(source_row.get(column))
            for column in race_count_columns
        ]

        race_numbers = [
            value
            for value in race_numbers
            if value is not None
        ]

        race_counts = [
            value
            for value in race_counts
            if value is not None
        ]

        if not dates or not tracks:
            continue

        rows.append(
            {
                "source": source_name,
                "race_date": dates[0],
                "track": tracks[0],
                "track_key": normalise_track(tracks[0]),
                "evidenced_race_no": (
                    max(race_numbers)
                    if race_numbers
                    else None
                ),
                "declared_race_count": (
                    max(race_counts)
                    if race_counts
                    else None
                ),
            }
        )

    return rows


def main() -> int:
    print("EDGEIQ Racing.com Candidate Legitimacy V1")
    print()

    INVESTIGATION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    urls = read_csv(URL_LEDGER)
    historical = read_csv(HISTORICAL_SOURCES)
    calendar = read_csv(CALENDAR_SOURCE)
    probe = read_csv(PROBE_SOURCE)

    if urls.empty:
        raise RuntimeError(
            f"URL admission ledger is empty: {URL_LEDGER}"
        )

    print("[1/5] Inventorying discovery-source schemas...")

    inventory = source_column_inventory(
        {
            "calendar_discovery": calendar,
            "completed_payload_probe": probe,
        }
    )

    inventory.to_csv(
        COLUMN_OUT,
        index=False,
        encoding="utf-8",
    )

    print("[2/5] Extracting meeting-level race evidence...")

    evidence = []

    evidence.extend(
        evidence_rows(
            calendar,
            "calendar_discovery",
        )
    )

    evidence.extend(
        evidence_rows(
            probe,
            "completed_payload_probe",
        )
    )

    evidence_frame = pd.DataFrame(evidence)

    if not evidence_frame.empty:
        evidence_frame["race_date"] = (
            evidence_frame["race_date"].map(clean)
        )

    historical_urls = (
        set(historical["source_url"].map(clean))
        if (
            not historical.empty
            and "source_url" in historical.columns
        )
        else set()
    )

    print("[3/5] Classifying every candidate URL...")

    classified_rows = []

    for _, candidate in urls.iterrows():
        race_date = clean(
            candidate.get("race_date")
        )

        track = clean(
            candidate.get("track")
        )

        track_key = normalise_track(track)

        race_no = integer(
            candidate.get("race_no")
        )

        csv_url = clean(
            candidate.get("csv_url")
        )

        method = clean(
            candidate.get("discovery_method")
        )

        matching = (
            evidence_frame[
                (
                    evidence_frame["race_date"]
                    == race_date
                )
                & (
                    evidence_frame["track_key"]
                    == track_key
                )
            ]
            if not evidence_frame.empty
            else pd.DataFrame()
        )

        evidenced_numbers = []

        declared_counts = []

        if not matching.empty:
            evidenced_numbers = [
                int(value)
                for value in matching[
                    "evidenced_race_no"
                ].dropna()
            ]

            declared_counts = [
                int(value)
                for value in matching[
                    "declared_race_count"
                ].dropna()
            ]

        maximum_evidenced_race = (
            max(evidenced_numbers)
            if evidenced_numbers
            else None
        )

        declared_race_count = (
            max(declared_counts)
            if declared_counts
            else None
        )

        effective_limit = declared_race_count

        if effective_limit is None:
            effective_limit = maximum_evidenced_race

        direct_method = (
            "DIRECT" in method.upper()
        )

        historical_success = (
            csv_url in historical_urls
        )

        if historical_success:
            legitimacy = (
                "HISTORICALLY_FETCHED_AND_PARSED"
            )
        elif (
            race_no is not None
            and effective_limit is not None
            and race_no > effective_limit
        ):
            legitimacy = (
                "BEYOND_EVIDENCED_RACE_LIMIT"
            )
        elif direct_method:
            legitimacy = (
                "DIRECT_URL_NOT_HISTORICALLY_FETCHED"
            )
        elif effective_limit is not None:
            legitimacy = (
                "DERIVED_WITHIN_EVIDENCED_LIMIT"
            )
        else:
            legitimacy = (
                "DERIVED_WITHOUT_RACE_LIMIT_EVIDENCE"
            )

        classified_rows.append(
            {
                **candidate.to_dict(),
                "race_no_numeric": (
                    race_no
                    if race_no is not None
                    else ""
                ),
                "historical_fetch_success": (
                    "YES"
                    if historical_success
                    else "NO"
                ),
                "meeting_source_rows": len(matching),
                "maximum_evidenced_race_no": (
                    maximum_evidenced_race
                    if maximum_evidenced_race is not None
                    else ""
                ),
                "declared_race_count": (
                    declared_race_count
                    if declared_race_count is not None
                    else ""
                ),
                "effective_evidenced_race_limit": (
                    effective_limit
                    if effective_limit is not None
                    else ""
                ),
                "candidate_legitimacy": legitimacy,
            }
        )

    classified = pd.DataFrame(classified_rows)

    classified.to_csv(
        LEDGER_OUT,
        index=False,
        encoding="utf-8",
    )

    print("[4/5] Profiling candidate expansion by meeting...")

    meeting_rows = []

    group_columns = [
        "race_date",
        "track",
        "discovery_method",
    ]

    for keys, group in classified.groupby(
        group_columns,
        dropna=False,
        sort=False,
    ):
        date, track, method = keys

        numeric_races = [
            int(value)
            for value in group[
                "race_no_numeric"
            ]
            if clean(value)
        ]

        lexical_order = [
            int(value)
            for value in group[
                "race_no_numeric"
            ]
            if clean(value)
        ]

        numeric_sorted = sorted(numeric_races)

        lexical_bias = (
            lexical_order != numeric_sorted
        )

        meeting_rows.append(
            {
                "race_date": clean(date),
                "track": clean(track),
                "discovery_method": clean(method),
                "candidate_urls": len(group),
                "minimum_admission_position": int(
                    group[
                        "admission_position"
                    ].astype(int).min()
                ),
                "maximum_admission_position": int(
                    group[
                        "admission_position"
                    ].astype(int).max()
                ),
                "minimum_candidate_race": (
                    min(numeric_races)
                    if numeric_races
                    else ""
                ),
                "maximum_candidate_race": (
                    max(numeric_races)
                    if numeric_races
                    else ""
                ),
                "candidate_race_sequence": ",".join(
                    str(value)
                    for value in lexical_order
                ),
                "numeric_race_sequence": ",".join(
                    str(value)
                    for value in numeric_sorted
                ),
                "lexical_order_bias": (
                    "YES"
                    if lexical_bias
                    else "NO"
                ),
                "historical_successes": int(
                    (
                        group[
                            "historical_fetch_success"
                        ] == "YES"
                    ).sum()
                ),
                "beyond_evidenced_limit": int(
                    (
                        group[
                            "candidate_legitimacy"
                        ]
                        == "BEYOND_EVIDENCED_RACE_LIMIT"
                    ).sum()
                ),
                "derived_without_limit_evidence": int(
                    (
                        group[
                            "candidate_legitimacy"
                        ]
                        == "DERIVED_WITHOUT_RACE_LIMIT_EVIDENCE"
                    ).sum()
                ),
            }
        )

    meetings = pd.DataFrame(meeting_rows)

    meetings.to_csv(
        MEETING_OUT,
        index=False,
        encoding="utf-8",
    )

    print("[5/5] Writing governed report...")

    legitimacy_counts = Counter(
        classified["candidate_legitimacy"]
    )

    method_counts = Counter(
        classified["discovery_method"]
    )

    first_50 = classified[
        classified[
            "within_default_first_50"
        ] == "YES"
    ]

    first_50_legitimacy = Counter(
        first_50["candidate_legitimacy"]
    )

    lexical_bias_meetings = int(
        (
            meetings["lexical_order_bias"]
            == "YES"
        ).sum()
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
            "governed_output_modified": False,
        },
        "candidate_population": {
            "rows": len(classified),
            "meetings": len(meetings),
            "historical_success_urls": len(
                historical_urls
            ),
            "legitimacy_counts": dict(
                sorted(legitimacy_counts.items())
            ),
            "discovery_method_counts": dict(
                sorted(method_counts.items())
            ),
        },
        "first_50": {
            "rows": len(first_50),
            "legitimacy_counts": dict(
                sorted(
                    first_50_legitimacy.items()
                )
            ),
        },
        "ordering": {
            "meetings_with_lexical_race_order_bias": (
                lexical_bias_meetings
            ),
        },
    }

    decision = (
        "CANDIDATE_LEGITIMACY_EVIDENCE_CREATED"
    )

    summary["decision"] = decision

    SUMMARY_OUT.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    legitimacy_lines = "\n".join(
        f"- `{name}`: **{count}**"
        for name, count in sorted(
            legitimacy_counts.items()
        )
    )

    first_50_lines = "\n".join(
        f"- `{name}`: **{count}**"
        for name, count in sorted(
            first_50_legitimacy.items()
        )
    )

    method_lines = "\n".join(
        f"- `{name}`: **{count}**"
        for name, count in sorted(
            method_counts.items()
        )
    )

    report = f"""# EDGEIQ Racing.com Candidate Legitimacy V1

Generated UTC: `{summary['generated_utc']}`

## Governance boundary

- Read-only forensic diagnostic.
- No network access.
- Production ingestion builder not executed.
- No candidate, cache or governed output modified.

## Candidate population

- Candidate URLs: **{len(classified)}**
- Candidate meeting groups: **{len(meetings)}**
- Historically fetched and parsed URLs: **{len(historical_urls)}**

### Candidate legitimacy

{legitimacy_lines}

### Discovery methods

{method_lines}

## First-50 admission cohort

- URLs: **{len(first_50)}**

{first_50_lines}

## Ordering defect

- Meeting groups affected by lexical race-number ordering: **{lexical_bias_meetings}**

Lexical ordering produces sequences such as:

`1,10,11,12,2,3...`

rather than:

`1,2,3...10,11,12`

## Interpretation boundary

A meetcode-derived URL is not treated as proof that a CSV exists.

The strongest classes are:

1. `HISTORICALLY_FETCHED_AND_PARSED`
2. source-supported candidates inside an evidenced race limit
3. direct URLs not yet historically fetched
4. derived URLs without meeting race-limit evidence
5. candidates beyond an evidenced race limit

No production remediation has been applied.

## Decision

**{decision}**

## Artifacts

- `{LEDGER_OUT.relative_to(ROOT).as_posix()}`
- `{MEETING_OUT.relative_to(ROOT).as_posix()}`
- `{COLUMN_OUT.relative_to(ROOT).as_posix()}`
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
    print(f"Candidate ledger: {LEDGER_OUT}")
    print(f"Meeting profile: {MEETING_OUT}")
    print(f"Column inventory: {COLUMN_OUT}")
    print()
    print("KEY COUNTS")

    for name, count in sorted(
        legitimacy_counts.items()
    ):
        print(f"{name}: {count}")

    print(
        "Meetings with lexical ordering bias: "
        f"{lexical_bias_meetings}"
    )
    print()
    print("DECISION")
    print(decision)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
