from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
PUBLIC_DATA = ROOT / "public" / "data"
SRC_ROOT = ROOT / "src" / "edgeiq-os"
OUTPUT_ROOT = (
    ROOT
    / "docs"
    / "full-product-implementation"
    / "current-product-data-completion-v1"
)

TARGET_METRICS = {
    "epi": [
        "epi",
        "current_epi",
        "epi_today",
        "edgeiq",
        "performance_rating",
        "rating",
    ],
    "eri": [
        "eri",
        "current_eri",
        "race_eri",
        "race_strength",
    ],
    "early_speed": [
        "early_speed",
        "early_speed_rating",
        "speed_early",
        "map_speed",
        "pace_speed",
        "spd",
    ],
    "late_speed": [
        "late_speed",
        "late_speed_rating",
        "speed_late",
    ],
    "suitability": [
        "suitability",
        "suitability_rating",
        "today_suitability",
    ],
    "form_momentum": [
        "form_momentum",
        "momentum",
        "form_momentum_rating",
    ],
    "fair_price": [
        "fair_price",
        "edgeiq_price",
        "model_price",
        "assessed_price",
    ],
    "market_price": [
        "market_price",
        "fixed_win",
        "win_price",
        "market",
        "price",
    ],
    "edge": [
        "edge",
        "edge_percent",
        "edge_pct",
        "value_edge",
    ],
    "map": [
        "map_position",
        "settling_position",
        "predicted_position",
        "map_speed",
    ],
    "recent_form": [
        "last_5",
        "last5",
        "recent_form",
        "form",
        "recent_starts",
    ],
    "profile": [
        "career_starts",
        "career_wins",
        "career_places",
        "track_starts",
        "distance_starts",
    ],
    "sectionals": [
        "section_8_6",
        "section_6_4",
        "section_4_2",
        "section_2_f",
        "move_8_6",
        "move_6_4",
        "move_4_2",
        "move_2_f",
        "eight_six",
        "six_four",
        "four_two",
        "two_finish",
    ],
}

IDENTITY_CANDIDATES = {
    "meeting": [
        "canonical_meeting_key",
        "meeting_key",
        "meeting_id",
        "meeting",
        "track",
        "venue",
    ],
    "race": [
        "canonical_race_key",
        "race_key",
        "race_id",
        "race_no",
        "race_number",
    ],
    "runner": [
        "canonical_runner_key",
        "canonical_runner_id",
        "runner_key",
        "runner_id",
        "runner_number",
        "horse",
        "horse_name",
        "runner",
        "runner_name",
    ],
}

MISSING_STRINGS = {
    "",
    "-",
    "—",
    ".",
    "..",
    "...",
    "null",
    "none",
    "nan",
    "n/a",
    "na",
    "undefined",
    "unavailable",
    "not available",
    "pending",
}

DATA_FILE_HINTS = [
    "current",
    "three_day",
    "race",
    "field",
    "form",
    "performance",
    "epi",
    "eri",
    "speed",
    "suitability",
    "momentum",
    "market",
    "price",
    "edge",
    "map",
    "profile",
    "result",
    "sectional",
]


@dataclass
class FileSummary:
    path: str
    format: str
    size_bytes: int
    rows: int
    columns: int
    relevant_columns: list[str]
    identity_columns: list[str]
    metric_matches: dict[str, list[str]]
    parse_status: str
    parse_error: str


@dataclass
class FieldProfile:
    file: str
    field: str
    rows: int
    populated: int
    missing: int
    invalid_placeholder: int
    numeric: int
    distinct: int
    sample_values: list[str]


def normalise_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def is_missing(value: Any) -> bool:
    if value is None:
        return True

    if isinstance(value, float):
        return math.isnan(value)

    if isinstance(value, str):
        return value.strip().lower() in MISSING_STRINGS

    return False


def is_invalid_placeholder(value: Any) -> bool:
    if value is None:
        return False

    text = str(value).strip().lower()
    return text in {
        ".",
        "..",
        "...",
        "null",
        "none",
        "nan",
        "undefined",
    }


def numeric_value(value: Any) -> float | None:
    if is_missing(value):
        return None

    text = str(value).strip()
    text = text.replace("$", "").replace("%", "").replace(",", "")
    text = re.sub(r"\s*(kg|m)$", "", text, flags=re.I)

    try:
        parsed = float(text)
        if math.isfinite(parsed):
            return parsed
    except (TypeError, ValueError):
        return None

    return None


def load_csv(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        fields = [str(field) for field in (reader.fieldnames or [])]
        rows = [dict(row) for row in reader]
    return rows, fields


def flatten_json_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    preferred_keys = [
        "rows",
        "records",
        "runners",
        "data",
        "items",
        "facts",
        "meetings",
        "races",
        "results",
    ]

    for key in preferred_keys:
        value = payload.get(key)
        if isinstance(value, list) and any(isinstance(item, dict) for item in value):
            records = [item for item in value if isinstance(item, dict)]

            if key == "meetings":
                expanded: list[dict[str, Any]] = []
                for meeting in records:
                    races = meeting.get("races")
                    if isinstance(races, list):
                        for race in races:
                            if not isinstance(race, dict):
                                continue
                            runners = race.get("runners")
                            if isinstance(runners, list):
                                for runner in runners:
                                    if not isinstance(runner, dict):
                                        continue
                                    merged = {
                                        **{
                                            f"meeting_{k}": v
                                            for k, v in meeting.items()
                                            if k != "races"
                                        },
                                        **{
                                            f"race_{k}": v
                                            for k, v in race.items()
                                            if k != "runners"
                                        },
                                        **runner,
                                    }
                                    expanded.append(merged)
                            else:
                                expanded.append(
                                    {
                                        **{
                                            f"meeting_{k}": v
                                            for k, v in meeting.items()
                                            if k != "races"
                                        },
                                        **race,
                                    }
                                )
                if expanded:
                    return expanded

            return records

    candidate_lists: list[list[dict[str, Any]]] = []

    def visit(value: Any) -> None:
        if isinstance(value, list):
            dict_rows = [item for item in value if isinstance(item, dict)]
            if dict_rows:
                candidate_lists.append(dict_rows)
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            for child in value.values():
                visit(child)

    visit(payload)

    if not candidate_lists:
        return [payload]

    return max(candidate_lists, key=len)


def load_json(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    rows = flatten_json_records(payload)
    fields = sorted(
        {
            str(key)
            for row in rows
            for key in row.keys()
        }
    )
    return rows, fields


def locate_data_files() -> list[Path]:
    paths: list[Path] = []

    if not PUBLIC_DATA.exists():
        return paths

    for path in PUBLIC_DATA.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {".csv", ".json"}:
            continue

        lowered = path.name.lower()

        if any(hint in lowered for hint in DATA_FILE_HINTS):
            paths.append(path)

    return sorted(paths)


def match_fields(fields: Iterable[str]) -> tuple[dict[str, list[str]], list[str]]:
    normalised = {field: normalise_key(field) for field in fields}

    matches: dict[str, list[str]] = {}

    for metric, candidates in TARGET_METRICS.items():
        candidate_keys = {normalise_key(candidate) for candidate in candidates}
        metric_fields: list[str] = []

        for field, field_key in normalised.items():
            if (
                field_key in candidate_keys
                or any(
                    field_key.endswith("_" + candidate)
                    or field_key.startswith(candidate + "_")
                    for candidate in candidate_keys
                )
            ):
                metric_fields.append(field)

        matches[metric] = sorted(set(metric_fields))

    identity_fields: list[str] = []
    identity_keys = {
        normalise_key(candidate)
        for values in IDENTITY_CANDIDATES.values()
        for candidate in values
    }

    for field, field_key in normalised.items():
        if (
            field_key in identity_keys
            or any(
                field_key.endswith("_" + identity_key)
                for identity_key in identity_keys
            )
        ):
            identity_fields.append(field)

    return matches, sorted(set(identity_fields))


def profile_fields(
    file_path: Path,
    rows: list[dict[str, Any]],
    matched_fields: Iterable[str],
) -> list[FieldProfile]:
    profiles: list[FieldProfile] = []

    for field in sorted(set(matched_fields)):
        values = [row.get(field) for row in rows]
        populated_values = [value for value in values if not is_missing(value)]
        invalid_count = sum(is_invalid_placeholder(value) for value in values)
        numeric_count = sum(numeric_value(value) is not None for value in populated_values)
        distinct_values = {
            str(value).strip()
            for value in populated_values
        }

        profiles.append(
            FieldProfile(
                file=str(file_path.relative_to(ROOT)),
                field=field,
                rows=len(values),
                populated=len(populated_values),
                missing=len(values) - len(populated_values),
                invalid_placeholder=invalid_count,
                numeric=numeric_count,
                distinct=len(distinct_values),
                sample_values=sorted(distinct_values)[:8],
            )
        )

    return profiles


def find_react_mappings() -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    if not SRC_ROOT.exists():
        return findings

    label_patterns = {
        "epi": r"\bEPI\b",
        "eri": r"\bERI\b",
        "early_speed": r"EARLY\s*SPEED|\bSPD\b",
        "late_speed": r"LATE\s*SPEED",
        "suitability": r"SUITAB",
        "form_momentum": r"FORM\s*MOMENTUM",
        "fair_price": r"EDGEIQ\s*PRICE|\bFAIR\b",
        "market_price": r"\bMARKET\b",
        "edge": r"\bEDGE\b",
        "sectionals": r"\b8-6\b|\b6-4\b|\b4-2\b|\b2-F\b",
    }

    property_pattern = re.compile(
        r"\b("
        + "|".join(
            sorted(
                {
                    candidate
                    for candidates in TARGET_METRICS.values()
                    for candidate in candidates
                },
                key=len,
                reverse=True,
            )
        )
        + r")\b",
        flags=re.I,
    )

    for path in sorted(SRC_ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".tsx", ".ts"}:
            continue

        text = path.read_text(encoding="utf-8", errors="replace")
        relative = str(path.relative_to(ROOT))

        labels = [
            label
            for label, pattern in label_patterns.items()
            if re.search(pattern, text, flags=re.I)
        ]

        properties = sorted(
            {
                match.group(1)
                for match in property_pattern.finditer(text)
            }
        )

        if not labels and not properties:
            continue

        findings.append(
            {
                "path": relative,
                "labels": labels,
                "properties": properties,
                "uses_table": "<table" in text,
                "text_align_center_hits": len(
                    re.findall(r"text-align\s*:\s*center", text, flags=re.I)
                ),
                "missing_glyph_hits": len(
                    re.findall(
                        r"""["'`](?:\.|-|—|Unavailable|Not available)["'`]""",
                        text,
                        flags=re.I,
                    )
                ),
            }
        )

    return findings


def identity_value(
    row: dict[str, Any],
    candidates: list[str],
) -> str:
    normalised_lookup = {
        normalise_key(key): value
        for key, value in row.items()
    }

    for candidate in candidates:
        key = normalise_key(candidate)
        value = normalised_lookup.get(key)

        if not is_missing(value):
            return str(value).strip()

    return ""


def build_runner_identity(row: dict[str, Any]) -> tuple[str, str, str]:
    meeting = identity_value(row, IDENTITY_CANDIDATES["meeting"])
    race = identity_value(row, IDENTITY_CANDIDATES["race"])
    runner = identity_value(row, IDENTITY_CANDIDATES["runner"])

    return meeting, race, runner


def build_cross_file_conflicts(
    file_rows: dict[str, list[dict[str, Any]]],
    file_metric_fields: dict[str, dict[str, list[str]]],
) -> list[dict[str, Any]]:
    value_index: dict[
        tuple[str, str, str, str],
        list[tuple[str, str, str]],
    ] = defaultdict(list)

    for file_name, rows in file_rows.items():
        metric_fields = file_metric_fields[file_name]

        for row in rows:
            meeting, race, runner = build_runner_identity(row)

            if not race or not runner:
                continue

            for metric, fields in metric_fields.items():
                for field in fields:
                    value = row.get(field)

                    if is_missing(value):
                        continue

                    numeric = numeric_value(value)
                    comparable = (
                        f"{numeric:.6f}"
                        if numeric is not None
                        else str(value).strip().lower()
                    )

                    value_index[
                        (meeting.lower(), race.lower(), runner.lower(), metric)
                    ].append((file_name, field, comparable))

    conflicts: list[dict[str, Any]] = []

    for key, entries in value_index.items():
        unique_values = sorted({entry[2] for entry in entries})

        if len(unique_values) <= 1:
            continue

        meeting, race, runner, metric = key

        conflicts.append(
            {
                "meeting": meeting,
                "race": race,
                "runner": runner,
                "metric": metric,
                "values": unique_values,
                "sources": [
                    {
                        "file": file_name,
                        "field": field,
                        "value": value,
                    }
                    for file_name, field, value in entries
                ],
            }
        )

    return conflicts


def duplicate_identity_findings(
    file_rows: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    for file_name, rows in file_rows.items():
        counts: Counter[tuple[str, str, str]] = Counter()

        for row in rows:
            identity = build_runner_identity(row)

            if all(identity):
                counts[identity] += 1

        for identity, count in counts.items():
            if count <= 1:
                continue

            findings.append(
                {
                    "file": file_name,
                    "meeting": identity[0],
                    "race": identity[1],
                    "runner": identity[2],
                    "count": count,
                }
            )

    return findings


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames: list[str] = []
    seen: set[str] = set()

    for row in rows:
        for key in row.keys():
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            serialised = {
                key: (
                    json.dumps(value, ensure_ascii=False)
                    if isinstance(value, (list, dict))
                    else value
                )
                for key, value in row.items()
            }
            writer.writerow(serialised)


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    data_files = locate_data_files()

    file_summaries: list[FileSummary] = []
    field_profiles: list[FieldProfile] = []
    file_rows: dict[str, list[dict[str, Any]]] = {}
    file_metric_fields: dict[str, dict[str, list[str]]] = {}

    for path in data_files:
        relative = str(path.relative_to(ROOT))

        try:
            if path.suffix.lower() == ".csv":
                rows, fields = load_csv(path)
                file_format = "CSV"
            else:
                rows, fields = load_json(path)
                file_format = "JSON"

            metric_matches, identity_fields = match_fields(fields)
            relevant_fields = sorted(
                {
                    field
                    for matched in metric_matches.values()
                    for field in matched
                }
            )

            file_rows[relative] = rows
            file_metric_fields[relative] = metric_matches

            file_summaries.append(
                FileSummary(
                    path=relative,
                    format=file_format,
                    size_bytes=path.stat().st_size,
                    rows=len(rows),
                    columns=len(fields),
                    relevant_columns=relevant_fields,
                    identity_columns=identity_fields,
                    metric_matches=metric_matches,
                    parse_status="PASS",
                    parse_error="",
                )
            )

            field_profiles.extend(
                profile_fields(
                    path,
                    rows,
                    relevant_fields,
                )
            )

        except Exception as exc:
            file_summaries.append(
                FileSummary(
                    path=relative,
                    format=path.suffix.upper().lstrip("."),
                    size_bytes=path.stat().st_size,
                    rows=0,
                    columns=0,
                    relevant_columns=[],
                    identity_columns=[],
                    metric_matches={metric: [] for metric in TARGET_METRICS},
                    parse_status="FAIL",
                    parse_error=f"{type(exc).__name__}: {exc}",
                )
            )

    react_mappings = find_react_mappings()
    conflicts = build_cross_file_conflicts(file_rows, file_metric_fields)
    duplicates = duplicate_identity_findings(file_rows)

    metric_coverage: list[dict[str, Any]] = []

    for metric in TARGET_METRICS:
        matching_profiles = [
            profile
            for profile in field_profiles
            if profile.field in {
                field
                for summary in file_summaries
                for field in summary.metric_matches.get(metric, [])
            }
        ]

        metric_coverage.append(
            {
                "metric": metric,
                "source_fields": len(matching_profiles),
                "rows_examined": sum(profile.rows for profile in matching_profiles),
                "populated": sum(profile.populated for profile in matching_profiles),
                "missing": sum(profile.missing for profile in matching_profiles),
                "invalid_placeholders": sum(
                    profile.invalid_placeholder
                    for profile in matching_profiles
                ),
                "files": sorted({profile.file for profile in matching_profiles}),
            }
        )

    suspicious_profiles = [
        asdict(profile)
        for profile in field_profiles
        if (
            profile.invalid_placeholder > 0
            or (
                profile.rows > 0
                and profile.missing > 0
                and profile.populated > 0
            )
        )
    ]

    summary = {
        "status": "PASS",
        "files_scanned": len(file_summaries),
        "files_parsed": sum(
            summary.parse_status == "PASS"
            for summary in file_summaries
        ),
        "files_failed": sum(
            summary.parse_status != "PASS"
            for summary in file_summaries
        ),
        "field_profiles": len(field_profiles),
        "suspicious_field_profiles": len(suspicious_profiles),
        "react_files_with_metric_mappings": len(react_mappings),
        "cross_file_conflicts": len(conflicts),
        "duplicate_runner_identity_findings": len(duplicates),
    }

    payload = {
        "summary": summary,
        "metric_coverage": metric_coverage,
        "file_summaries": [asdict(item) for item in file_summaries],
        "field_profiles": [asdict(item) for item in field_profiles],
        "suspicious_field_profiles": suspicious_profiles,
        "react_mappings": react_mappings,
        "cross_file_conflicts": conflicts,
        "duplicate_identity_findings": duplicates,
    }

    json_path = OUTPUT_ROOT / "EDGEIQ_CURRENT_PRODUCT_DATA_COMPLETION_V1_AUDIT.json"
    md_path = OUTPUT_ROOT / "EDGEIQ_CURRENT_PRODUCT_DATA_COMPLETION_V1_AUDIT.md"
    file_csv_path = OUTPUT_ROOT / "EDGEIQ_CURRENT_PRODUCT_DATA_FILES_V1.csv"
    field_csv_path = OUTPUT_ROOT / "EDGEIQ_CURRENT_PRODUCT_FIELD_PROFILES_V1.csv"
    conflict_csv_path = OUTPUT_ROOT / "EDGEIQ_CURRENT_PRODUCT_CROSS_FILE_CONFLICTS_V1.csv"
    react_csv_path = OUTPUT_ROOT / "EDGEIQ_CURRENT_PRODUCT_REACT_MAPPINGS_V1.csv"

    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    write_csv(
        file_csv_path,
        [asdict(item) for item in file_summaries],
    )

    write_csv(
        field_csv_path,
        [asdict(item) for item in field_profiles],
    )

    write_csv(
        conflict_csv_path,
        conflicts,
    )

    write_csv(
        react_csv_path,
        react_mappings,
    )

    markdown: list[str] = [
        "# EDGEIQ Current Product Data Completion V1 Audit",
        "",
        "## Status",
        "",
        "PASS",
        "",
        "## Summary",
        "",
    ]

    for key, value in summary.items():
        markdown.append(f"- **{key}**: {value}")

    markdown.extend(
        [
            "",
            "## Metric Coverage",
            "",
            "| Metric | Source Fields | Rows Examined | Populated | Missing | Invalid Placeholders |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )

    for row in metric_coverage:
        markdown.append(
            f"| {row['metric']} | {row['source_fields']} | "
            f"{row['rows_examined']} | {row['populated']} | "
            f"{row['missing']} | {row['invalid_placeholders']} |"
        )

    markdown.extend(
        [
            "",
            "## Highest-Priority Findings",
            "",
        ]
    )

    if conflicts:
        markdown.append(
            f"- Cross-file metric conflicts requiring investigation: {len(conflicts)}"
        )
    else:
        markdown.append("- Cross-file metric conflicts: 0")

    if duplicates:
        markdown.append(
            f"- Duplicate runner identity findings: {len(duplicates)}"
        )
    else:
        markdown.append("- Duplicate runner identity findings: 0")

    invalid_total = sum(
        profile.invalid_placeholder
        for profile in field_profiles
    )

    markdown.append(
        f"- Invalid punctuation/null placeholder cells: {invalid_total}"
    )

    markdown.append(
        f"- Suspicious partially populated fields: {len(suspicious_profiles)}"
    )

    markdown.extend(
        [
            "",
            "## Next Step",
            "",
            "Use this audit to generate the deterministic feed and presentation repair.",
            "No calculations or source data were changed by this audit.",
            "",
        ]
    )

    md_path.write_text("\n".join(markdown), encoding="utf-8")

    print(
        json.dumps(
            {
                **summary,
                "json": str(json_path),
                "markdown": str(md_path),
                "files_csv": str(file_csv_path),
                "fields_csv": str(field_csv_path),
                "conflicts_csv": str(conflict_csv_path),
                "react_csv": str(react_csv_path),
            },
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
