from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

RESULTS = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_historical_results_warehouse_v2_graphql.csv"
)

SECTIONALS = (
    ROOT
    / "public"
    / "data"
    / "racingcom_sectional_warehouse_v2.csv"
)

PHASE05 = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase0_5"
)

PHASE07 = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase0_7"
)

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase0_8"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase0_8"
)

PROTOTYPE_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase0_8"
)

PROGRESS_INTERVAL = 100_000
SAMPLE_LIMIT = 250

AUTOMATIC_PROMOTION_METHODS = {
    "DATE_TRACK_RACE_HORSE_NORMALISED",
}

CONDITIONAL_PROMOTION_METHODS = {
    "DATE_TRACK_HORSE_NORMALISED",
    "DATE_RACE_HORSE_NORMALISED",
}

RESEARCH_ONLY_METHODS = {
    "DATE_HORSE_ONLY_UNIQUE",
}

TRACK_ALIAS_OVERRIDES = {
    "PARKHILLSIDE": "SANDOWNHILLSIDE",
    "PARKLAKESIDE": "SANDOWNLAKESIDE",
    "PARKKILMORE": "KILMORE",
    "LADBROKESPARKHILLSIDE": "SANDOWNHILLSIDE",
    "LADBROKESPARKLAKESIDE": "SANDOWNLAKESIDE",
    "SANDOWNPARKHILLSIDE": "SANDOWNHILLSIDE",
    "SANDOWNPARKLAKESIDE": "SANDOWNLAKESIDE",
    "PAKENHAMSYN": "PAKENHAMSYNTHETIC",
    "BALLARATSYN": "BALLARATSYNTHETIC",
    "GEELONGSYN": "GEELONGSYNTHETIC",
}

COUNTRY_SUFFIX_PATTERN = re.compile(
    r"\s*(?:\((?:AUS|NZ|IRE|GB|USA|FR|JPN|SAF|ARG|BRZ|GER|CAN|CHI|URU|ITY|SWE|DEN|SIN|HK)\)\s*)+$",
    re.IGNORECASE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalise_date(value: Any) -> str:
    text = clean(value)

    if not text:
        return ""

    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
    )

    for fmt in formats:
        try:
            return datetime.strptime(
                text[:10],
                fmt,
            ).strftime("%Y-%m-%d")
        except ValueError:
            continue

    match = re.match(
        r"^(\d{4}-\d{2}-\d{2})",
        text,
    )

    return match.group(1) if match else ""


def normalise_integer(value: Any) -> str:
    text = clean(value)

    if not text:
        return ""

    try:
        value_float = float(text)
    except ValueError:
        match = re.search(r"\d+", text)
        return match.group(0) if match else ""

    if not value_float.is_integer():
        return ""

    return str(int(value_float))


def base_key(value: Any) -> str:
    return re.sub(
        r"[^A-Z0-9]+",
        "",
        clean(value).upper(),
    )


def normalise_track(value: Any) -> str:
    key = base_key(value)

    prefixes = (
        "BET365",
        "LADBROKES",
        "SPORTSBET",
        "APIAM",
        "TAB",
    )

    for prefix in prefixes:
        if key.startswith(prefix):
            key = key[len(prefix):]
            break

    if key in TRACK_ALIAS_OVERRIDES:
        return TRACK_ALIAS_OVERRIDES[key]

    aliases = {
        "BENDIGO": "BENDIGO",
        "BALLARATSYNTH": "BALLARATSYNTHETIC",
        "BALLARATSYNTHETIC": "BALLARATSYNTHETIC",
        "GEELONGSYNTH": "GEELONGSYNTHETIC",
        "GEELONGSYNTHETIC": "GEELONGSYNTHETIC",
        "PAKENHAMSYNTH": "PAKENHAMSYNTHETIC",
        "PAKENHAMSYNTHETIC": "PAKENHAMSYNTHETIC",
    }

    return aliases.get(key, key)


def normalise_horse(value: Any) -> str:
    text = clean(value).upper()
    text = COUNTRY_SUFFIX_PATTERN.sub(
        "",
        text,
    )
    return re.sub(
        r"[^A-Z0-9]+",
        "",
        text,
    )


def latest_file(
    directory: Path,
    pattern: str,
) -> Path:
    candidates = sorted(
        directory.glob(pattern),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not candidates:
        raise FileNotFoundError(
            f"No file matched {pattern}"
        )

    return candidates[0]


def write_json(
    path: Path,
    payload: Any,
) -> None:
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fields: list[str] = []

    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)


def build_performance_lookup(
    identity_path: Path,
) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}

    with identity_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            if (
                row_number == 1
                or row_number % PROGRESS_INTERVAL == 0
            ):
                print(
                    f"PERFORMANCE_LOOKUP_PROGRESS={row_number}",
                    flush=True,
                )

            performance_id = clean(
                row.get("performance_id")
            )

            if not performance_id:
                continue

            lookup[performance_id] = {
                "race_date": normalise_date(
                    row.get("race_date")
                ),
                "track": normalise_track(
                    row.get("track")
                ),
                "race_number": normalise_integer(
                    row.get("race_number")
                ),
                "horse": normalise_horse(
                    row.get("horse_name")
                ),
                "raw_track": clean(
                    row.get("track")
                ),
                "raw_horse": clean(
                    row.get("horse_name")
                ),
                "provider_race_id": clean(
                    row.get("provider_race_id")
                ),
                "provider_runner_id": clean(
                    row.get("provider_runner_id")
                ),
            }

    return lookup


def build_result_diagnostic_indexes() -> dict[str, Any]:
    indexes = {
        "date": Counter(),
        "date_track": Counter(),
        "date_horse": Counter(),
        "date_track_race": Counter(),
        "date_track_race_horse": Counter(),
        "date_race_horse": Counter(),
        "date_track_horse": Counter(),
    }

    horses_by_date_track_race: dict[
        tuple[str, str, str],
        set[str],
    ] = defaultdict(set)

    tracks_by_date_race_horse: dict[
        tuple[str, str, str],
        set[str],
    ] = defaultdict(set)

    races_by_date_track_horse: dict[
        tuple[str, str, str],
        set[str],
    ] = defaultdict(set)

    with RESULTS.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            if (
                row_number == 1
                or row_number % PROGRESS_INTERVAL == 0
            ):
                print(
                    f"RESULT_DIAGNOSTIC_PROGRESS={row_number}",
                    flush=True,
                )

            race_date = normalise_date(
                row.get("race_date")
            )
            track = normalise_track(
                row.get("track")
            )
            race_number = normalise_integer(
                row.get("race_no")
            )
            horse = normalise_horse(
                row.get("horse")
            )

            if race_date:
                indexes["date"][race_date] += 1

            if race_date and track:
                indexes["date_track"][
                    f"{race_date}|{track}"
                ] += 1

            if race_date and horse:
                indexes["date_horse"][
                    f"{race_date}|{horse}"
                ] += 1

            if race_date and track and race_number:
                indexes["date_track_race"][
                    f"{race_date}|{track}|{race_number}"
                ] += 1

            if (
                race_date
                and track
                and race_number
                and horse
            ):
                indexes["date_track_race_horse"][
                    f"{race_date}|{track}|{race_number}|{horse}"
                ] += 1

                horses_by_date_track_race[
                    (
                        race_date,
                        track,
                        race_number,
                    )
                ].add(horse)

            if race_date and race_number and horse:
                indexes["date_race_horse"][
                    f"{race_date}|{race_number}|{horse}"
                ] += 1

                tracks_by_date_race_horse[
                    (
                        race_date,
                        race_number,
                        horse,
                    )
                ].add(track)

            if race_date and track and horse:
                indexes["date_track_horse"][
                    f"{race_date}|{track}|{horse}"
                ] += 1

                races_by_date_track_horse[
                    (
                        race_date,
                        track,
                        horse,
                    )
                ].add(race_number)

    return {
        "indexes": indexes,
        "horses_by_date_track_race": (
            horses_by_date_track_race
        ),
        "tracks_by_date_race_horse": (
            tracks_by_date_race_horse
        ),
        "races_by_date_track_horse": (
            races_by_date_track_horse
        ),
    }


def classify_link_method(
    method: str,
) -> tuple[str, bool]:
    if method in AUTOMATIC_PROMOTION_METHODS:
        return (
            "AUTO_PROMOTION_ELIGIBLE",
            True,
        )

    if method in CONDITIONAL_PROMOTION_METHODS:
        return (
            "CONDITIONAL_VALIDATION_REQUIRED",
            False,
        )

    if method in RESEARCH_ONLY_METHODS:
        return (
            "RESEARCH_ONLY_NOT_PROMOTABLE",
            False,
        )

    return (
        "UNLINKED_OR_AMBIGUOUS",
        False,
    )


def validate_existing_links(
    linkage_path: Path,
    performance_lookup: dict[
        str,
        dict[str, str],
    ],
    validation_path: Path,
) -> dict[str, Any]:
    status_counts = Counter()
    method_counts = Counter()
    validation_counts = Counter()
    promotion_counts = Counter()

    mismatch_samples: list[dict[str, Any]] = []

    source_rows = 0
    linked_rows = 0
    exact_validated_rows = 0
    invalid_rows = 0

    fields = [
        "sectional_source_row",
        "performance_id",
        "link_status",
        "link_method",
        "promotion_class",
        "automatic_promotion_eligible",
        "validation_state",
        "sectional_race_date",
        "result_race_date",
        "sectional_track",
        "result_track",
        "sectional_race_number",
        "result_race_number",
        "sectional_horse",
        "result_horse",
        "date_match",
        "track_match",
        "race_number_match",
        "horse_match",
    ]

    with linkage_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as source_handle, validation_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as output_handle:
        reader = csv.DictReader(
            source_handle
        )
        writer = csv.DictWriter(
            output_handle,
            fieldnames=fields,
        )
        writer.writeheader()

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            source_rows += 1

            if (
                row_number == 1
                or row_number % PROGRESS_INTERVAL == 0
            ):
                print(
                    f"LINK_VALIDATION_PROGRESS={row_number}",
                    flush=True,
                )

            performance_id = clean(
                row.get("performance_id")
            )
            link_status = clean(
                row.get("link_status")
            )
            link_method = clean(
                row.get("link_method")
            )

            status_counts[link_status] += 1
            method_counts[link_method] += 1

            (
                promotion_class,
                automatic_eligible,
            ) = classify_link_method(
                link_method
            )

            promotion_counts[
                promotion_class
            ] += 1

            sectional_date = normalise_date(
                row.get("race_date")
            )
            sectional_track = normalise_track(
                row.get("canonical_track")
                or row.get("raw_track")
            )
            sectional_race_number = (
                normalise_integer(
                    row.get("race_number")
                )
            )
            sectional_horse = normalise_horse(
                row.get("canonical_horse")
                or row.get("raw_horse")
            )

            result = performance_lookup.get(
                performance_id
            )

            validation_state = (
                "NOT_LINKED"
            )
            result_date = ""
            result_track = ""
            result_race_number = ""
            result_horse = ""

            date_match = False
            track_match = False
            race_match = False
            horse_match = False

            if performance_id and result:
                linked_rows += 1

                result_date = result[
                    "race_date"
                ]
                result_track = result[
                    "track"
                ]
                result_race_number = result[
                    "race_number"
                ]
                result_horse = result[
                    "horse"
                ]

                date_match = (
                    sectional_date
                    == result_date
                )
                track_match = (
                    sectional_track
                    == result_track
                )
                race_match = (
                    sectional_race_number
                    == result_race_number
                )
                horse_match = (
                    sectional_horse
                    == result_horse
                )

                required_checks = {
                    "DATE_TRACK_RACE_HORSE_NORMALISED": (
                        date_match
                        and track_match
                        and race_match
                        and horse_match
                    ),
                    "DATE_TRACK_HORSE_NORMALISED": (
                        date_match
                        and track_match
                        and horse_match
                    ),
                    "DATE_RACE_HORSE_NORMALISED": (
                        date_match
                        and race_match
                        and horse_match
                    ),
                    "DATE_HORSE_ONLY_UNIQUE": (
                        date_match
                        and horse_match
                    ),
                }

                if required_checks.get(
                    link_method,
                    False,
                ):
                    validation_state = (
                        "VALIDATED"
                    )
                    exact_validated_rows += 1
                else:
                    validation_state = (
                        "VALIDATION_MISMATCH"
                    )
                    invalid_rows += 1

                    if (
                        len(mismatch_samples)
                        < SAMPLE_LIMIT
                    ):
                        mismatch_samples.append(
                            {
                                "performance_id": (
                                    performance_id
                                ),
                                "link_method": (
                                    link_method
                                ),
                                "sectional_date": (
                                    sectional_date
                                ),
                                "result_date": (
                                    result_date
                                ),
                                "sectional_track": (
                                    sectional_track
                                ),
                                "result_track": (
                                    result_track
                                ),
                                "sectional_race_number": (
                                    sectional_race_number
                                ),
                                "result_race_number": (
                                    result_race_number
                                ),
                                "sectional_horse": (
                                    sectional_horse
                                ),
                                "result_horse": (
                                    result_horse
                                ),
                            }
                        )

            elif performance_id:
                validation_state = (
                    "PERFORMANCE_ID_NOT_FOUND"
                )
                invalid_rows += 1

            validation_counts[
                validation_state
            ] += 1

            writer.writerow(
                {
                    "sectional_source_row": (
                        clean(
                            row.get(
                                "sectional_source_row"
                            )
                        )
                    ),
                    "performance_id": (
                        performance_id
                    ),
                    "link_status": link_status,
                    "link_method": link_method,
                    "promotion_class": (
                        promotion_class
                    ),
                    "automatic_promotion_eligible": (
                        automatic_eligible
                    ),
                    "validation_state": (
                        validation_state
                    ),
                    "sectional_race_date": (
                        sectional_date
                    ),
                    "result_race_date": (
                        result_date
                    ),
                    "sectional_track": (
                        sectional_track
                    ),
                    "result_track": (
                        result_track
                    ),
                    "sectional_race_number": (
                        sectional_race_number
                    ),
                    "result_race_number": (
                        result_race_number
                    ),
                    "sectional_horse": (
                        sectional_horse
                    ),
                    "result_horse": (
                        result_horse
                    ),
                    "date_match": date_match,
                    "track_match": track_match,
                    "race_number_match": (
                        race_match
                    ),
                    "horse_match": (
                        horse_match
                    ),
                }
            )

    return {
        "source_rows": source_rows,
        "linked_rows": linked_rows,
        "validated_rows": (
            exact_validated_rows
        ),
        "validation_mismatch_rows": (
            invalid_rows
        ),
        "validated_pct_of_linked": (
            round(
                exact_validated_rows
                / linked_rows
                * 100,
                4,
            )
            if linked_rows
            else 0.0
        ),
        "status_counts": dict(
            sorted(
                status_counts.items()
            )
        ),
        "method_counts": dict(
            sorted(
                method_counts.items()
            )
        ),
        "validation_counts": dict(
            sorted(
                validation_counts.items()
            )
        ),
        "promotion_counts": dict(
            sorted(
                promotion_counts.items()
            )
        ),
        "mismatch_samples": (
            mismatch_samples
        ),
    }


def diagnose_unlinked_rows(
    linkage_path: Path,
    diagnostics: dict[str, Any],
    output_path: Path,
) -> dict[str, Any]:
    indexes = diagnostics["indexes"]

    reason_counts = Counter()
    track_counts = Counter()
    date_counts = Counter()
    date_track_counts = Counter()

    candidate_alias_rows: list[
        dict[str, Any]
    ] = []

    unlinked_rows = 0

    with linkage_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            if clean(
                row.get("link_status")
            ) == "LINKED":
                continue

            unlinked_rows += 1

            race_date = normalise_date(
                row.get("race_date")
            )
            track = normalise_track(
                row.get("canonical_track")
                or row.get("raw_track")
            )
            race_number = normalise_integer(
                row.get("race_number")
            )
            horse = normalise_horse(
                row.get("canonical_horse")
                or row.get("raw_horse")
            )

            date_key = race_date
            date_track_key = (
                f"{race_date}|{track}"
            )
            date_horse_key = (
                f"{race_date}|{horse}"
            )
            date_track_race_key = (
                f"{race_date}|{track}|"
                f"{race_number}"
            )
            full_key = (
                f"{race_date}|{track}|"
                f"{race_number}|{horse}"
            )

            reason = "UNKNOWN"

            if not indexes["date"].get(
                date_key
            ):
                reason = (
                    "RESULT_DATE_NOT_PRESENT"
                )

            elif not indexes[
                "date_horse"
            ].get(date_horse_key):
                reason = (
                    "HORSE_NOT_PRESENT_ON_DATE"
                )

            elif not indexes[
                "date_track"
            ].get(date_track_key):
                reason = (
                    "TRACK_ALIAS_OR_RESULT_"
                    "VENUE_MISMATCH"
                )

            elif not indexes[
                "date_track_race"
            ].get(
                date_track_race_key
            ):
                reason = (
                    "RACE_NUMBER_OR_MEETING_"
                    "STRUCTURE_MISMATCH"
                )

            elif not indexes[
                "date_track_race_horse"
            ].get(full_key):
                reason = (
                    "HORSE_NAME_OR_IDENTITY_"
                    "MISMATCH_WITHIN_RACE"
                )

            else:
                reason = (
                    "DUPLICATE_OR_AMBIGUOUS_"
                    "RESULT_EVIDENCE"
                )

            reason_counts[reason] += 1
            track_counts[track] += 1
            date_counts[race_date] += 1
            date_track_counts[
                date_track_key
            ] += 1

            if (
                len(candidate_alias_rows)
                < 10_000
            ):
                candidate_result_tracks = sorted(
                    diagnostics[
                        "tracks_by_date_race_horse"
                    ].get(
                        (
                            race_date,
                            race_number,
                            horse,
                        ),
                        set(),
                    )
                )

                candidate_result_races = sorted(
                    diagnostics[
                        "races_by_date_track_horse"
                    ].get(
                        (
                            race_date,
                            track,
                            horse,
                        ),
                        set(),
                    )
                )

                candidate_horses = sorted(
                    diagnostics[
                        "horses_by_date_track_race"
                    ].get(
                        (
                            race_date,
                            track,
                            race_number,
                        ),
                        set(),
                    )
                )

                candidate_alias_rows.append(
                    {
                        "race_date": race_date,
                        "raw_track": clean(
                            row.get("raw_track")
                        ),
                        "canonical_track": track,
                        "race_number": (
                            race_number
                        ),
                        "raw_horse": clean(
                            row.get("raw_horse")
                        ),
                        "canonical_horse": (
                            horse
                        ),
                        "diagnostic_reason": (
                            reason
                        ),
                        "candidate_result_tracks": (
                            " | ".join(
                                candidate_result_tracks
                            )
                        ),
                        "candidate_result_race_numbers": (
                            " | ".join(
                                candidate_result_races
                            )
                        ),
                        "candidate_horses_in_race": (
                            " | ".join(
                                candidate_horses[
                                    :50
                                ]
                            )
                        ),
                        "automatic_resolution_allowed": (
                            False
                        ),
                    }
                )

    write_csv(
        output_path,
        candidate_alias_rows,
    )

    return {
        "unlinked_rows": unlinked_rows,
        "reason_counts": dict(
            sorted(
                reason_counts.items()
            )
        ),
        "top_tracks": [
            {
                "track": track,
                "rows": count,
            }
            for track, count
            in track_counts.most_common(50)
        ],
        "top_dates": [
            {
                "date": date,
                "rows": count,
            }
            for date, count
            in date_counts.most_common(50)
        ],
        "top_date_tracks": [
            {
                "date_track": key,
                "rows": count,
            }
            for key, count
            in date_track_counts.most_common(
                100
            )
        ],
    }


def build_promotion_manifest(
    validation_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    counts = Counter()
    eligible_rows = 0

    fields = [
        "sectional_source_row",
        "performance_id",
        "link_method",
        "validation_state",
        "promotion_state",
        "promotion_reason",
        "linkage_version",
        "generated_at",
    ]

    generated_at = utc_now()

    with validation_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as source_handle, output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as output_handle:
        reader = csv.DictReader(
            source_handle
        )
        writer = csv.DictWriter(
            output_handle,
            fieldnames=fields,
        )
        writer.writeheader()

        for row in reader:
            method = clean(
                row.get("link_method")
            )
            validation_state = clean(
                row.get(
                    "validation_state"
                )
            )

            promotion_state = (
                "NOT_ELIGIBLE"
            )
            promotion_reason = (
                "LINK_NOT_STRONG_ENOUGH"
            )

            if (
                validation_state
                == "VALIDATED"
                and method
                in AUTOMATIC_PROMOTION_METHODS
            ):
                promotion_state = (
                    "ELIGIBLE_FOR_CANONICAL_"
                    "MIGRATION_REVIEW"
                )
                promotion_reason = (
                    "VALIDATED_STRONG_"
                    "DETERMINISTIC_KEY"
                )
                eligible_rows += 1

            elif (
                validation_state
                == "VALIDATED"
                and method
                in CONDITIONAL_PROMOTION_METHODS
            ):
                promotion_state = (
                    "REQUIRES_SECONDARY_"
                    "EVIDENCE_REVIEW"
                )
                promotion_reason = (
                    "VALIDATED_CONDITIONAL_KEY"
                )

            elif (
                validation_state
                == "VALIDATED"
                and method
                in RESEARCH_ONLY_METHODS
            ):
                promotion_state = (
                    "RESEARCH_ONLY"
                )
                promotion_reason = (
                    "DATE_HORSE_ONLY_KEY"
                )

            elif (
                validation_state
                != "VALIDATED"
            ):
                promotion_reason = (
                    validation_state
                )

            counts[promotion_state] += 1

            writer.writerow(
                {
                    "sectional_source_row": (
                        clean(
                            row.get(
                                "sectional_source_row"
                            )
                        )
                    ),
                    "performance_id": clean(
                        row.get(
                            "performance_id"
                        )
                    ),
                    "link_method": method,
                    "validation_state": (
                        validation_state
                    ),
                    "promotion_state": (
                        promotion_state
                    ),
                    "promotion_reason": (
                        promotion_reason
                    ),
                    "linkage_version": (
                        "SECTIONAL_LINKAGE_V0_1"
                    ),
                    "generated_at": (
                        generated_at
                    ),
                }
            )

    return {
        "eligible_rows": eligible_rows,
        "promotion_state_counts": dict(
            sorted(
                counts.items()
            )
        ),
    }


def architecture_markdown() -> str:
    return """# EDGEiQ Sectional Linkage Governance V0.1

## Automatic promotion

Only the following linkage may become automatically eligible for canonical migration review:

`DATE_TRACK_RACE_HORSE_NORMALISED`

It must also pass direct validation against the selected canonical performance record.

## Conditional linkage

The following may be retained as linkage evidence but require secondary evidence before canonical promotion:

- `DATE_TRACK_HORSE_NORMALISED`
- `DATE_RACE_HORSE_NORMALISED`

Secondary evidence may include:

- provider runner identity
- provider race identity
- official race distance
- official finish position
- trainer
- jockey
- barrier
- official sectional payload reference

## Research-only linkage

`DATE_HORSE_ONLY_UNIQUE`

This method may support research and gap analysis but must not automatically create canonical sectional evidence.

## Unresolved evidence

Rows remain unresolved when:

- no result date exists
- the horse is absent from the result date
- the track cannot be reconciled
- the race number differs
- the horse identity differs within the same race
- multiple candidate performances remain

No fuzzy name match or alias candidate may be automatically promoted.
"""


def markdown_report(
    summary: dict[str, Any],
) -> str:
    validation = summary[
        "link_validation"
    ]
    diagnosis = summary[
        "unlinked_diagnosis"
    ]
    promotion = summary[
        "promotion_manifest"
    ]

    lines = [
        "# EDGEiQ Performance Intelligence",
        "## Phase 0.8 Sectional Link Validation and Residual Diagnosis",
        "",
        f"Generated UTC: `{summary['generated_utc']}`",
        "",
        "## Link validation",
        "",
        f"- Linked rows checked: **{validation['linked_rows']:,}**",
        f"- Validated rows: **{validation['validated_rows']:,}**",
        f"- Validation rate: **{validation['validated_pct_of_linked']}%**",
        f"- Validation mismatches: **{validation['validation_mismatch_rows']:,}**",
        "",
        "## Canonical migration eligibility",
        "",
        f"- Strong deterministic rows eligible for migration review: **{promotion['eligible_rows']:,}**",
        "",
        "## Residual unlinked evidence",
        "",
        f"- Unlinked or ambiguous rows diagnosed: **{diagnosis['unlinked_rows']:,}**",
        "",
        "| Reason | Rows |",
        "|---|---:|",
    ]

    for reason, count in diagnosis[
        "reason_counts"
    ].items():
        lines.append(
            f"| {reason} | {count} |"
        )

    lines.extend(
        [
            "",
            "## Permanent rule",
            "",
            "No horse alias, track alias, race-number correction or fuzzy match is automatically promoted from this diagnosis.",
            "",
            "All residual rows remain preserved with their diagnostic reason.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    ARCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    PROTOTYPE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    identity_path = latest_file(
        PHASE05,
        "edgeiq_canonical_performance_identity_prototype_v0_1_*.csv",
    )

    linkage_path = latest_file(
        PHASE07,
        "edgeiq_governed_sectional_performance_linkage_v0_1_*.csv",
    )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    validation_path = (
        PROTOTYPE_DIR
        / f"edgeiq_sectional_link_validation_v0_1_{run_id}.csv"
    )

    residual_path = (
        AUDIT_DIR
        / f"edgeiq_sectional_residual_diagnosis_v0_1_{run_id}.csv"
    )

    promotion_path = (
        PROTOTYPE_DIR
        / f"edgeiq_sectional_migration_manifest_v0_1_{run_id}.csv"
    )

    summary_path = (
        AUDIT_DIR
        / f"edgeiq_performance_intelligence_phase0_8_summary_{run_id}.json"
    )

    latest_path = (
        AUDIT_DIR
        / "edgeiq_performance_intelligence_phase0_8_latest.json"
    )

    report_path = (
        AUDIT_DIR
        / f"EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE0_8_REPORT_{run_id}.md"
    )

    architecture_path = (
        ARCH_DIR
        / "EDGEIQ_SECTIONAL_LINKAGE_GOVERNANCE_V0_1.md"
    )

    architecture_path.write_text(
        architecture_markdown(),
        encoding="utf-8",
    )

    print(
        "PHASE0_8_BUILD_PERFORMANCE_LOOKUP_START",
        flush=True,
    )

    performance_lookup = (
        build_performance_lookup(
            identity_path
        )
    )

    print(
        "PHASE0_8_VALIDATE_EXISTING_LINKS_START",
        flush=True,
    )

    validation_summary = (
        validate_existing_links(
            linkage_path,
            performance_lookup,
            validation_path,
        )
    )

    print(
        "PHASE0_8_BUILD_RESULT_DIAGNOSTICS_START",
        flush=True,
    )

    diagnostic_indexes = (
        build_result_diagnostic_indexes()
    )

    print(
        "PHASE0_8_DIAGNOSE_RESIDUALS_START",
        flush=True,
    )

    residual_summary = (
        diagnose_unlinked_rows(
            linkage_path,
            diagnostic_indexes,
            residual_path,
        )
    )

    print(
        "PHASE0_8_BUILD_PROMOTION_MANIFEST_START",
        flush=True,
    )

    promotion_summary = (
        build_promotion_manifest(
            validation_path,
            promotion_path,
        )
    )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 0.8 Sectional Link Validation "
            "and Residual Diagnosis"
        ),
        "generated_utc": utc_now(),
        "production_data_modified": False,
        "identity_source": str(
            identity_path.relative_to(ROOT)
        ).replace("\\", "/"),
        "linkage_source": str(
            linkage_path.relative_to(ROOT)
        ).replace("\\", "/"),
        "link_validation": (
            validation_summary
        ),
        "unlinked_diagnosis": (
            residual_summary
        ),
        "promotion_manifest": (
            promotion_summary
        ),
        "canonical_status": (
            "VALIDATED_LINKAGE_PROTOTYPE_"
            "NOT_YET_MIGRATED"
        ),
        "next_stage": (
            "Phase 0.9 immutable canonical "
            "sectional evidence migration prototype"
        ),
        "outputs": {
            "validation": str(
                validation_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "residual_diagnosis": str(
                residual_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "migration_manifest": str(
                promotion_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "governance_specification": str(
                architecture_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
        },
    }

    write_json(
        summary_path,
        summary,
    )
    write_json(
        latest_path,
        summary,
    )

    report_path.write_text(
        markdown_report(summary),
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE0_8_SECTIONAL_LINK_"
        "VALIDATION_PASS",
        flush=True,
    )
    print(
        f"VALIDATION={validation_path}",
        flush=True,
    )
    print(
        f"RESIDUALS={residual_path}",
        flush=True,
    )
    print(
        f"MIGRATION_MANIFEST={promotion_path}",
        flush=True,
    )
    print(
        f"GOVERNANCE={architecture_path}",
        flush=True,
    )
    print(
        f"SUMMARY={summary_path}",
        flush=True,
    )
    print(
        f"REPORT={report_path}",
        flush=True,
    )


if __name__ == "__main__":
    main()
