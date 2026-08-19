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

PHASE05_PROTOTYPES = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase0_5"
)

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase0_7"
)

PROTOTYPE_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase0_7"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase0_7"
)

PROGRESS_INTERVAL = 100_000
SAMPLE_LIMIT = 100

TRACK_PREFIXES = (
    "BET365 ",
    "LADBROKES ",
    "SPORTSBET ",
    "APIA M ",
    "APIAM ",
    "TAB ",
    "THE ",
)

TRACK_SUFFIXES = (
    " RACECOURSE",
    " RACING CLUB",
)

TRACK_ALIAS_MAP = {
    "APIAMBENDIGO": "BENDIGO",
    "BET365BENDIGO": "BENDIGO",
    "BENDIGO": "BENDIGO",

    "BET365BALLARAT": "BALLARAT",
    "BALLARAT": "BALLARAT",

    "BALLARATSYN": "BALLARATSYNTHETIC",
    "BALLARATSYNTH": "BALLARATSYNTHETIC",
    "BALLARATSYNTHETIC": "BALLARATSYNTHETIC",
    "BET365BALLARATSYNTHETIC": "BALLARATSYNTHETIC",

    "GEELONGSYN": "GEELONGSYNTHETIC",
    "GEELONGSYNTH": "GEELONGSYNTHETIC",
    "GEELONGSYNTHETIC": "GEELONGSYNTHETIC",
    "BET365GEELONGSYNTHETIC": "GEELONGSYNTHETIC",

    "PAKENHAMSYN": "PAKENHAMSYNTHETIC",
    "PAKENHAMSYNTH": "PAKENHAMSYNTHETIC",
    "PAKENHAMSYNTHETIC": "PAKENHAMSYNTHETIC",
    "SPORTSBETPAKENHAMSYNTHETIC": "PAKENHAMSYNTHETIC",

    "PAKENHAM": "PAKENHAM",
    "SPORTSBETPAKENHAM": "PAKENHAM",

    "CAULFIELDHEATH": "CAULFIELDHEATH",
    "CAULFIELD": "CAULFIELD",

    "SANDOWNHILLSIDE": "SANDOWNHILLSIDE",
    "SANDOWNLAKESIDE": "SANDOWNLAKESIDE",
    "SANDOWN": "SANDOWN",

    "FLEMINGTON": "FLEMINGTON",
    "CRANBOURNE": "CRANBOURNE",
    "MORNINGTON": "MORNINGTON",
    "MOONEEVALLEY": "MOONEEVALLEY",
}

KEY_STRATEGIES = (
    {
        "name": "DATE_TRACK_RACE_HORSE_NORMALISED",
        "components": (
            "race_date",
            "track",
            "race_number",
            "horse",
        ),
        "strength": "STRONG",
    },
    {
        "name": "DATE_TRACK_HORSE_NORMALISED",
        "components": (
            "race_date",
            "track",
            "horse",
        ),
        "strength": "CONDITIONAL",
    },
    {
        "name": "DATE_RACE_HORSE_NORMALISED",
        "components": (
            "race_date",
            "race_number",
            "horse",
        ),
        "strength": "CONDITIONAL",
    },
    {
        "name": "DATE_HORSE_ONLY_UNIQUE",
        "components": (
            "race_date",
            "horse",
        ),
        "strength": "FALLBACK_UNIQUE_ONLY",
    },
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
        number = float(text)
    except ValueError:
        match = re.search(
            r"\d+",
            text,
        )
        return (
            str(int(match.group(0)))
            if match
            else ""
        )

    if not number.is_integer():
        return ""

    return str(int(number))


def normalise_horse(value: Any) -> str:
    text = clean(value).upper()

    text = re.sub(
        r"\((?:AUS|NZ|IRE|GB|USA|FR|JPN|SAF|ARG|BRZ|GER|CAN|CHI|URU|ITY|SWE|DEN|SIN|HK)\)",
        "",
        text,
    )

    text = re.sub(
        r"\b(?:AUS|NZ|IRE|GB|USA|FR|JPN|SAF|ARG|BRZ|GER|CAN|CHI|URU|ITY|SWE|DEN|SIN|HK)\b$",
        "",
        text,
    )

    text = re.sub(
        r"[^A-Z0-9]+",
        "",
        text,
    )

    return text


def base_track_key(value: Any) -> str:
    text = clean(value).upper()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    for prefix in TRACK_PREFIXES:
        if text.startswith(prefix):
            text = text[
                len(prefix):
            ]
            break

    for suffix in TRACK_SUFFIXES:
        if text.endswith(suffix):
            text = text[
                :-len(suffix)
            ]
            break

    return re.sub(
        r"[^A-Z0-9]+",
        "",
        text,
    )


def normalise_track(value: Any) -> str:
    raw_key = re.sub(
        r"[^A-Z0-9]+",
        "",
        clean(value).upper(),
    )

    if raw_key in TRACK_ALIAS_MAP:
        return TRACK_ALIAS_MAP[
            raw_key
        ]

    base_key = base_track_key(value)

    if base_key in TRACK_ALIAS_MAP:
        return TRACK_ALIAS_MAP[
            base_key
        ]

    return base_key


def first(
    row: dict[str, str],
    fields: tuple[str, ...],
) -> str:
    for field in fields:
        value = clean(
            row.get(field)
        )

        if value:
            return value

    return ""


def results_values(
    row: dict[str, str],
) -> dict[str, str]:
    return {
        "race_date": normalise_date(
            row.get("race_date")
        ),
        "track": normalise_track(
            row.get("track")
        ),
        "race_number": normalise_integer(
            row.get("race_no")
        ),
        "horse": normalise_horse(
            row.get("horse")
        ),
    }


def sectional_values(
    row: dict[str, str],
) -> dict[str, str]:
    return {
        "race_date": normalise_date(
            row.get("meeting_date")
        ),
        "track": normalise_track(
            row.get("track")
        ),
        "race_number": normalise_integer(
            row.get("race_no")
        ),
        "horse": normalise_horse(
            row.get("horse_name")
        ),
    }


def key_from_values(
    values: dict[str, str],
    components: tuple[str, ...],
) -> str:
    parts = []

    for component in components:
        value = values.get(
            component,
            "",
        )

        if not value:
            return ""

        parts.append(value)

    return "|".join(parts)


def latest_performance_identity() -> Path:
    candidates = sorted(
        PHASE05_PROTOTYPES.glob(
            "edgeiq_canonical_performance_identity_prototype_v0_1_*.csv"
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not candidates:
        raise FileNotFoundError(
            "Phase 0.5 performance identity prototype was not found."
        )

    return candidates[0]


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        path.write_text(
            "",
            encoding="utf-8",
        )
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


def build_performance_lookup(
    identity_path: Path,
) -> dict[
    tuple[
        str,
        str,
        str,
        str,
    ],
    list[str],
]:
    lookup: dict[
        tuple[
            str,
            str,
            str,
            str,
        ],
        list[str],
    ] = defaultdict(list)

    with identity_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "IDENTITY_LOOKUP_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            performance_id = clean(
                row.get(
                    "performance_id"
                )
            )

            if not performance_id:
                continue

            values = {
                "race_date": normalise_date(
                    row.get(
                        "race_date"
                    )
                ),
                "track": normalise_track(
                    row.get(
                        "track"
                    )
                ),
                "race_number": (
                    normalise_integer(
                        row.get(
                            "race_number"
                        )
                    )
                ),
                "horse": normalise_horse(
                    row.get(
                        "horse_name"
                    )
                ),
            }

            key = (
                values["race_date"],
                values["track"],
                values["race_number"],
                values["horse"],
            )

            lookup[key].append(
                performance_id
            )

    return lookup


def build_result_strategy_indexes() -> tuple[
    dict[str, Counter[str]],
    dict[
        str,
        dict[str, str],
    ],
]:
    counts = {
        strategy["name"]: Counter()
        for strategy in KEY_STRATEGIES
    }

    unique_performance = {
        strategy["name"]: {}
        for strategy in KEY_STRATEGIES
    }

    identity_path = (
        latest_performance_identity()
    )

    performance_lookup = (
        build_performance_lookup(
            identity_path
        )
    )

    with RESULTS.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "RESULT_INDEX_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            values = results_values(row)

            full_key = (
                values["race_date"],
                values["track"],
                values["race_number"],
                values["horse"],
            )

            performance_ids = (
                performance_lookup.get(
                    full_key,
                    [],
                )
            )

            performance_id = (
                performance_ids[0]
                if len(
                    set(
                        performance_ids
                    )
                ) == 1
                else ""
            )

            for strategy in (
                KEY_STRATEGIES
            ):
                key = key_from_values(
                    values,
                    strategy[
                        "components"
                    ],
                )

                if not key:
                    continue

                name = strategy["name"]
                counts[name][key] += 1

                if (
                    performance_id
                    and key not in
                    unique_performance[
                        name
                    ]
                ):
                    unique_performance[
                        name
                    ][key] = (
                        performance_id
                    )

    for strategy in KEY_STRATEGIES:
        name = strategy["name"]

        unique_performance[name] = {
            key: performance_id
            for key, performance_id
            in unique_performance[
                name
            ].items()
            if counts[name][key] == 1
        }

    return (
        counts,
        unique_performance,
    )


def audit_track_aliases() -> list[
    dict[str, Any]
]:
    result_tracks = Counter()
    sectional_tracks = Counter()

    with RESULTS.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        for row in reader:
            raw = clean(
                row.get("track")
            )

            if raw:
                result_tracks[raw] += 1

    with SECTIONALS.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        for row in reader:
            raw = clean(
                row.get("track")
            )

            if raw:
                sectional_tracks[
                    raw
                ] += 1

    rows = []

    for raw_track, count in sorted(
        result_tracks.items()
    ):
        canonical = normalise_track(
            raw_track
        )

        sectional_variants = [
            value
            for value
            in sectional_tracks
            if normalise_track(
                value
            ) == canonical
        ]

        rows.append(
            {
                "source": "RESULTS",
                "raw_track": raw_track,
                "canonical_track": (
                    canonical
                ),
                "rows": count,
                "matching_sectional_variants": (
                    " | ".join(
                        sorted(
                            sectional_variants
                        )
                    )
                ),
            }
        )

    for raw_track, count in sorted(
        sectional_tracks.items()
    ):
        canonical = normalise_track(
            raw_track
        )

        result_variants = [
            value
            for value
            in result_tracks
            if normalise_track(
                value
            ) == canonical
        ]

        rows.append(
            {
                "source": "SECTIONALS",
                "raw_track": raw_track,
                "canonical_track": (
                    canonical
                ),
                "rows": count,
                "matching_result_variants": (
                    " | ".join(
                        sorted(
                            result_variants
                        )
                    )
                ),
            }
        )

    return rows


def build_linkage_prototype(
    counts: dict[
        str,
        Counter[str],
    ],
    unique_performance: dict[
        str,
        dict[str, str],
    ],
    output_path: Path,
) -> dict[str, Any]:
    status_counts = Counter()
    method_counts = Counter()
    unlinked_reason_counts = (
        Counter()
    )
    unlinked_samples: list[
        dict[str, Any]
    ] = []

    source_rows = 0
    linked_rows = 0
    ambiguous_rows = 0
    unlinked_rows = 0

    fields = [
        "sectional_source_row",
        "performance_id",
        "link_status",
        "link_method",
        "link_strength",
        "race_date",
        "raw_track",
        "canonical_track",
        "race_number",
        "raw_horse",
        "canonical_horse",
        "unlinked_reason",
    ]

    with SECTIONALS.open(
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

        for source_row, row in enumerate(
            reader,
            start=2,
        ):
            source_rows += 1

            if (
                source_rows == 1
                or source_rows
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "GOVERNED_LINK_PROGRESS="
                    f"{source_rows}",
                    flush=True,
                )

            values = sectional_values(
                row
            )

            performance_id = ""
            link_status = "UNLINKED"
            link_method = "NONE"
            link_strength = ""
            unlinked_reason = (
                "NO_UNIQUE_MATCH"
            )

            encountered_ambiguity = (
                False
            )

            for strategy in (
                KEY_STRATEGIES
            ):
                name = strategy["name"]
                key = key_from_values(
                    values,
                    strategy[
                        "components"
                    ],
                )

                if not key:
                    continue

                result_count = counts[
                    name
                ].get(
                    key,
                    0,
                )

                if result_count == 1:
                    candidate_id = (
                        unique_performance[
                            name
                        ].get(
                            key,
                            "",
                        )
                    )

                    if candidate_id:
                        performance_id = (
                            candidate_id
                        )
                        link_status = (
                            "LINKED"
                        )
                        link_method = name
                        link_strength = (
                            strategy[
                                "strength"
                            ]
                        )
                        unlinked_reason = ""
                        break

                elif result_count > 1:
                    encountered_ambiguity = (
                        True
                    )

            if performance_id:
                linked_rows += 1
            elif encountered_ambiguity:
                link_status = (
                    "AMBIGUOUS"
                )
                unlinked_reason = (
                    "MULTIPLE_RESULT_"
                    "PERFORMANCES"
                )
                ambiguous_rows += 1
            else:
                unlinked_rows += 1

            status_counts[
                link_status
            ] += 1
            method_counts[
                link_method
            ] += 1

            if unlinked_reason:
                unlinked_reason_counts[
                    unlinked_reason
                ] += 1

            writer.writerow(
                {
                    "sectional_source_row": (
                        source_row
                    ),
                    "performance_id": (
                        performance_id
                    ),
                    "link_status": (
                        link_status
                    ),
                    "link_method": (
                        link_method
                    ),
                    "link_strength": (
                        link_strength
                    ),
                    "race_date": (
                        values[
                            "race_date"
                        ]
                    ),
                    "raw_track": clean(
                        row.get("track")
                    ),
                    "canonical_track": (
                        values["track"]
                    ),
                    "race_number": (
                        values[
                            "race_number"
                        ]
                    ),
                    "raw_horse": clean(
                        row.get(
                            "horse_name"
                        )
                    ),
                    "canonical_horse": (
                        values["horse"]
                    ),
                    "unlinked_reason": (
                        unlinked_reason
                    ),
                }
            )

            if (
                not performance_id
                and len(
                    unlinked_samples
                ) < SAMPLE_LIMIT
            ):
                unlinked_samples.append(
                    {
                        "race_date": (
                            values[
                                "race_date"
                            ]
                        ),
                        "raw_track": clean(
                            row.get(
                                "track"
                            )
                        ),
                        "canonical_track": (
                            values[
                                "track"
                            ]
                        ),
                        "race_number": (
                            values[
                                "race_number"
                            ]
                        ),
                        "raw_horse": (
                            clean(
                                row.get(
                                    "horse_name"
                                )
                            )
                        ),
                        "canonical_horse": (
                            values[
                                "horse"
                            ]
                        ),
                        "status": (
                            link_status
                        ),
                        "reason": (
                            unlinked_reason
                        ),
                    }
                )

    return {
        "source_rows": source_rows,
        "linked_rows": linked_rows,
        "linked_pct": (
            round(
                linked_rows
                / source_rows
                * 100,
                4,
            )
            if source_rows
            else 0.0
        ),
        "ambiguous_rows": (
            ambiguous_rows
        ),
        "unlinked_rows": (
            unlinked_rows
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
        "unlinked_reason_counts": dict(
            sorted(
                unlinked_reason_counts.items()
            )
        ),
        "unlinked_samples": (
            unlinked_samples
        ),
    }


def build_strategy_summary(
    counts: dict[
        str,
        Counter[str],
    ],
    unique_performance: dict[
        str,
        dict[str, str],
    ],
) -> list[dict[str, Any]]:
    rows = []

    for strategy in KEY_STRATEGIES:
        name = strategy["name"]
        counter = counts[name]

        rows.append(
            {
                "strategy_name": name,
                "strength": (
                    strategy[
                        "strength"
                    ]
                ),
                "components": (
                    " | ".join(
                        strategy[
                            "components"
                        ]
                    )
                ),
                "result_keys": len(
                    counter
                ),
                "unique_result_keys": sum(
                    1
                    for count
                    in counter.values()
                    if count == 1
                ),
                "ambiguous_result_keys": sum(
                    1
                    for count
                    in counter.values()
                    if count > 1
                ),
                "keys_with_performance_id": (
                    len(
                        unique_performance[
                            name
                        ]
                    )
                ),
            }
        )

    return rows


def markdown_report(
    summary: dict[str, Any],
) -> str:
    linkage = summary[
        "linkage"
    ]

    lines = [
        "# EDGEiQ Performance Intelligence",
        "## Phase 0.7 Governed Sectional Linkage Prototype",
        "",
        f"Generated UTC: `{summary['generated_utc']}`",
        "",
        "## Result",
        "",
        f"- Sectional rows: **{linkage['source_rows']:,}**",
        f"- Linked: **{linkage['linked_rows']:,}**",
        f"- Linked percentage: **{linkage['linked_pct']}%**",
        f"- Ambiguous: **{linkage['ambiguous_rows']:,}**",
        f"- Unlinked: **{linkage['unlinked_rows']:,}**",
        "",
        "## Governance",
        "",
        "Automatic linkage is permitted only where a normalised key resolves to exactly one result performance.",
        "",
        "The preferred key order is:",
        "",
        "1. Date + canonical track + race number + canonical horse.",
        "2. Date + canonical track + canonical horse, unique only.",
        "3. Date + race number + canonical horse, unique only.",
        "4. Date + canonical horse, unique only.",
        "",
        "Ambiguous rows remain unresolved.",
        "",
        "No production data was modified.",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    PROTOTYPE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    ARCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    output_path = (
        PROTOTYPE_DIR
        / f"edgeiq_governed_sectional_performance_linkage_v0_1_{run_id}.csv"
    )
    track_alias_path = (
        ARCH_DIR
        / "edgeiq_track_alias_normalisation_v0_1.csv"
    )
    strategy_path = (
        ARCH_DIR
        / "edgeiq_sectional_linkage_strategy_v0_1.csv"
    )
    summary_path = (
        AUDIT_DIR
        / f"edgeiq_performance_intelligence_phase0_7_summary_{run_id}.json"
    )
    latest_path = (
        AUDIT_DIR
        / "edgeiq_performance_intelligence_phase0_7_latest.json"
    )
    report_path = (
        AUDIT_DIR
        / f"EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE0_7_REPORT_{run_id}.md"
    )
    unlinked_path = (
        AUDIT_DIR
        / f"edgeiq_phase0_7_unlinked_samples_{run_id}.csv"
    )

    print(
        "PHASE0_7_BUILD_RESULT_INDEX_START",
        flush=True,
    )

    (
        counts,
        unique_performance,
    ) = build_result_strategy_indexes()

    strategy_rows = (
        build_strategy_summary(
            counts,
            unique_performance,
        )
    )

    write_csv(
        strategy_path,
        strategy_rows,
    )

    print(
        "PHASE0_7_TRACK_ALIAS_AUDIT_START",
        flush=True,
    )

    track_rows = audit_track_aliases()

    write_csv(
        track_alias_path,
        track_rows,
    )

    print(
        "PHASE0_7_GOVERNED_LINKAGE_START",
        flush=True,
    )

    linkage = build_linkage_prototype(
        counts,
        unique_performance,
        output_path,
    )

    write_csv(
        unlinked_path,
        linkage[
            "unlinked_samples"
        ],
    )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 0.7 Governed Sectional "
            "Performance Linkage Prototype"
        ),
        "generated_utc": utc_now(),
        "production_data_modified": False,
        "normalisation_rules": {
            "race_number": (
                "Numeric race identifiers are "
                "normalised from values such as "
                "1.0 and 1 to integer text 1."
            ),
            "track": (
                "Sponsor prefixes and known "
                "synthetic-course aliases are "
                "normalised before matching."
            ),
            "horse": (
                "Punctuation, spaces and trailing "
                "country suffixes are normalised."
            ),
        },
        "strategy_order": [
            strategy["name"]
            for strategy
            in KEY_STRATEGIES
        ],
        "strategy_summary": (
            strategy_rows
        ),
        "linkage": linkage,
        "canonical_status": (
            "PROTOTYPE_LINKAGE_NOT_PROMOTED"
        ),
        "promotion_rule": (
            "Only rows linked by a unique "
            "deterministic result key may be "
            "eligible for canonical migration."
        ),
        "next_stage": (
            "Phase 0.8 validate linked evidence, "
            "diagnose remaining unlinked rows, "
            "and design canonical horse aliases"
        ),
        "outputs": {
            "linkage_prototype": str(
                output_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "track_aliases": str(
                track_alias_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "strategy": str(
                strategy_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "unlinked_samples": str(
                unlinked_path.relative_to(
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
        "PHASE0_7_GOVERNED_SECTIONAL_"
        "LINKAGE_PROTOTYPE_PASS",
        flush=True,
    )
    print(
        f"LINKAGE={output_path}",
        flush=True,
    )
    print(
        f"TRACK_ALIASES={track_alias_path}",
        flush=True,
    )
    print(
        f"STRATEGY={strategy_path}",
        flush=True,
    )
    print(
        f"UNLINKED={unlinked_path}",
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
