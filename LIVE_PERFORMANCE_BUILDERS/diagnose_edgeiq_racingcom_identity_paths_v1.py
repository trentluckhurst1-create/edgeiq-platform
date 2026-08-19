
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

RAW_DIR = (
    REPO
    / "outputs"
    / "sectionals"
    / "raw"
    / "VIC"
    / "racingcom_full_payloads"
)

REPORT_DIR = (
    REPO
    / "docs"
    / "performance-intelligence"
    / "standard-time-investigation"
)

PATH_CSV = REPORT_DIR / "edgeiq_racingcom_identity_candidate_paths_v1.csv"
FILE_CSV = REPORT_DIR / "edgeiq_racingcom_identity_path_file_profile_v1.csv"
TOP_LEVEL_CSV = REPORT_DIR / "edgeiq_racingcom_top_level_schema_v1.csv"
REPORT_JSON = REPORT_DIR / "edgeiq_racingcom_identity_paths_v1.json"
REPORT_MD = REPORT_DIR / "edgeiq_racingcom_identity_paths_v1.md"

IDENTITY_KEY_TERMS = {
    "date": {
        "date",
        "meetingdate",
        "racedate",
        "meeting_date",
        "race_date",
        "eventdate",
        "event_date",
        "startdate",
    },
    "track": {
        "track",
        "trackname",
        "track_name",
        "venue",
        "venuename",
        "venue_name",
        "meetingname",
        "meeting_name",
        "course",
        "coursename",
    },
    "race_number": {
        "racenumber",
        "race_number",
        "raceno",
        "race_no",
        "racenum",
        "number",
    },
    "race_id": {
        "raceid",
        "race_id",
        "eventid",
        "event_id",
    },
    "meeting_id": {
        "meetingid",
        "meeting_id",
    },
    "url": {
        "url",
        "pageurl",
        "page_url",
        "canonicalurl",
        "canonical_url",
        "sourceurl",
        "source_url",
    },
}

SECTIONAL_KEY_TERMS = {
    "sectional",
    "sectionals",
    "splits",
    "split",
    "speed",
    "speeddata",
    "speed_data",
    "distance",
    "elapsedtime",
    "elapsed_time",
    "time",
    "runner",
    "runners",
    "horse",
    "horses",
}


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)

    return digest.hexdigest()


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fields: list[str] = []
    seen: set[str] = set()

    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fields.append(key)

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()

        for row in rows:
            output: dict[str, Any] = {}

            for key in fields:
                value = row.get(key, "")

                if isinstance(value, (dict, list, tuple)):
                    value = json.dumps(
                        value,
                        ensure_ascii=False,
                        sort_keys=True,
                    )

                output[key] = value

            writer.writerow(output)


def scalar_preview(value: Any, limit: int = 240) -> str:
    if isinstance(value, (dict, list)):
        return ""

    text = clean(value)
    text = text.replace("\r", " ").replace("\n", " ")

    if len(text) > limit:
        return text[:limit] + "..."

    return text


def walk_json(
    value: Any,
    path: str = "$",
    depth: int = 0,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"

            rows.append(
                {
                    "json_path": child_path,
                    "key": str(key),
                    "value_type": type(child).__name__,
                    "value_preview": scalar_preview(child),
                    "depth": depth + 1,
                }
            )

            rows.extend(
                walk_json(
                    child,
                    child_path,
                    depth + 1,
                )
            )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"

            rows.extend(
                walk_json(
                    child,
                    child_path,
                    depth + 1,
                )
            )

    return rows


def classify_key(key: str) -> list[str]:
    folded = key.casefold()
    categories: list[str] = []

    for category, terms in IDENTITY_KEY_TERMS.items():
        if folded in terms:
            categories.append(category)

    return categories


def top_level_description(payload: Any) -> tuple[str, list[str]]:
    if isinstance(payload, dict):
        return "dict", sorted(str(key) for key in payload.keys())

    if isinstance(payload, list):
        item_types = sorted(
            {
                type(item).__name__
                for item in payload[:100]
            }
        )
        return "list", item_types

    return type(payload).__name__, []


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if not RAW_DIR.exists():
        raise FileNotFoundError(
            f"Raw directory not found: {RAW_DIR}"
        )

    print("EDGEIQ Racing.com Identity Paths V1")
    print(f"Raw directory: {RAW_DIR}")
    print("")

    all_paths = sorted(
        (
            path
            for path in RAW_DIR.rglob("*")
            if path.is_file()
        ),
        key=lambda path: path.as_posix().casefold(),
    )

    unique_paths: list[Path] = []
    seen_hashes: set[str] = set()

    for path in all_paths:
        digest = sha256_file(path)

        if digest in seen_hashes:
            continue

        seen_hashes.add(digest)
        unique_paths.append(path)

    print(f"Raw files: {len(all_paths):,}")
    print(f"Unique contents: {len(unique_paths):,}")
    print("")

    candidate_rows: list[dict[str, Any]] = []
    file_rows: list[dict[str, Any]] = []
    top_level_rows: list[dict[str, Any]] = []

    valid_json_count = 0
    invalid_json_count = 0

    path_counts: Counter[tuple[str, str, str]] = Counter()
    path_file_counts: defaultdict[
        tuple[str, str, str],
        set[str],
    ] = defaultdict(set)

    print("[1/3] Inspecting exact JSON paths...")

    for index, path in enumerate(unique_paths, start=1):
        relative = path.relative_to(REPO).as_posix()
        digest = sha256_file(path)
        text = read_text(path)

        try:
            payload = json.loads(text)
            valid_json_count += 1
        except json.JSONDecodeError as exc:
            invalid_json_count += 1

            file_rows.append(
                {
                    "relative_path": relative,
                    "sha256": digest,
                    "json_status": "INVALID_JSON",
                    "json_error": (
                        f"{exc.msg}; line={exc.lineno}; "
                        f"column={exc.colno}"
                    ),
                    "root_type": "",
                    "top_level_keys": "",
                    "candidate_identity_path_count": 0,
                    "sectional_key_path_count": 0,
                }
            )
            continue

        root_type, top_level_keys = top_level_description(payload)
        walked = walk_json(payload)

        identity_path_count = 0
        sectional_path_count = 0

        for row in walked:
            key = clean(row["key"])
            folded_key = key.casefold()
            categories = classify_key(key)

            if any(
                term in folded_key
                for term in SECTIONAL_KEY_TERMS
            ):
                sectional_path_count += 1

            for category in categories:
                identity_path_count += 1

                candidate = {
                    "relative_path": relative,
                    "sha256": digest,
                    "category": category,
                    "json_path": row["json_path"],
                    "key": key,
                    "depth": row["depth"],
                    "value_type": row["value_type"],
                    "value_preview": row["value_preview"],
                }

                candidate_rows.append(candidate)

                count_key = (
                    category,
                    row["json_path"],
                    row["value_type"],
                )

                path_counts[count_key] += 1
                path_file_counts[count_key].add(relative)

        file_rows.append(
            {
                "relative_path": relative,
                "sha256": digest,
                "json_status": "VALID_JSON",
                "json_error": "",
                "root_type": root_type,
                "top_level_keys": "|".join(top_level_keys),
                "candidate_identity_path_count": identity_path_count,
                "sectional_key_path_count": sectional_path_count,
            }
        )

        top_level_rows.append(
            {
                "relative_path": relative,
                "sha256": digest,
                "root_type": root_type,
                "top_level_schema": "|".join(top_level_keys),
                "top_level_item_count": (
                    len(payload)
                    if isinstance(payload, (dict, list))
                    else 0
                ),
            }
        )

        if index % 50 == 0:
            print(
                f"  Inspected {index:,}/{len(unique_paths):,}"
            )

    print("[2/3] Aggregating candidate identity paths...")

    aggregated_paths: list[dict[str, Any]] = []

    for key, occurrences in path_counts.items():
        category, json_path, value_type = key

        examples: list[str] = []

        for row in candidate_rows:
            if (
                row["category"] == category
                and row["json_path"] == json_path
                and row["value_type"] == value_type
            ):
                preview = clean(row["value_preview"])

                if preview and preview not in examples:
                    examples.append(preview)

                if len(examples) >= 8:
                    break

        aggregated_paths.append(
            {
                "category": category,
                "json_path": json_path,
                "value_type": value_type,
                "occurrences": occurrences,
                "distinct_files": len(
                    path_file_counts[key]
                ),
                "depth": json_path.count(".")
                + json_path.count("["),
                "example_values": examples,
            }
        )

    aggregated_paths.sort(
        key=lambda row: (
            row["category"],
            int(row["depth"]),
            -int(row["distinct_files"]),
            row["json_path"],
        )
    )

    top_level_schema_counts = Counter(
        (
            row["root_type"],
            row["top_level_schema"],
        )
        for row in top_level_rows
    )

    top_level_summary = [
        {
            "root_type": root_type,
            "top_level_schema": schema,
            "unique_payload_count": count,
        }
        for (root_type, schema), count
        in top_level_schema_counts.most_common()
    ]

    report = {
        "diagnostic": "EDGEIQ_RACINGCOM_IDENTITY_PATHS_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "raw_directory": str(RAW_DIR),
        "governance": {
            "read_only": True,
            "builders_modified": False,
            "governed_outputs_modified": False,
            "thresholds_modified": False,
            "fabricated_data": False,
        },
        "population": {
            "raw_files": len(all_paths),
            "unique_contents": len(unique_paths),
            "valid_json_unique_contents": valid_json_count,
            "invalid_json_unique_contents": invalid_json_count,
        },
        "candidate_path_count": len(aggregated_paths),
        "candidate_occurrence_count": len(candidate_rows),
        "top_level_schema_count": len(top_level_summary),
    }

    print("[3/3] Writing forensic artifacts...")

    write_csv(PATH_CSV, aggregated_paths)
    write_csv(FILE_CSV, file_rows)
    write_csv(TOP_LEVEL_CSV, top_level_summary)

    REPORT_JSON.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    markdown = [
        "# EDGEIQ Racing.com Identity Paths V1",
        "",
        f"Generated UTC: `{report['generated_utc']}`",
        "",
        "## Governance boundary",
        "",
        "- Read-only forensic diagnostic.",
        "- Exact JSON paths recorded.",
        "- No first-key recursive identity inference.",
        "- No builder modified.",
        "- No governed output modified.",
        "- No threshold modified.",
        "- No benchmark data fabricated.",
        "",
        "## Population",
        "",
        f"- Raw files: **{len(all_paths)}**",
        f"- Unique contents: **{len(unique_paths)}**",
        f"- Valid JSON unique contents: "
        f"**{valid_json_count}**",
        f"- Invalid JSON unique contents: "
        f"**{invalid_json_count}**",
        f"- Candidate identity paths: "
        f"**{len(aggregated_paths)}**",
        f"- Candidate identity occurrences: "
        f"**{len(candidate_rows)}**",
        f"- Distinct top-level schemas: "
        f"**{len(top_level_summary)}**",
        "",
        "## Decision",
        "",
        "**IDENTITY_PATH_EVIDENCE_CREATED**",
        "",
        "Race identities must now be selected only from paths "
        "demonstrated to represent the captured meeting and race. "
        "Horse-history dates, surface values, nested previous-start "
        "records, and generic number fields must not be treated as "
        "capture-level race identity.",
        "",
        "## Artifacts",
        "",
        f"- `{PATH_CSV.relative_to(REPO).as_posix()}`",
        f"- `{FILE_CSV.relative_to(REPO).as_posix()}`",
        f"- `{TOP_LEVEL_CSV.relative_to(REPO).as_posix()}`",
        f"- `{REPORT_JSON.relative_to(REPO).as_posix()}`",
    ]

    REPORT_MD.write_text(
        "\n".join(markdown) + "\n",
        encoding="utf-8",
    )

    print("")
    print("COMPLETE")
    print(f"Report: {REPORT_MD}")
    print(f"Candidate paths: {PATH_CSV}")
    print(f"File profiles: {FILE_CSV}")
    print(f"Top-level schemas: {TOP_LEVEL_CSV}")
    print("")
    print("DECISION")
    print("IDENTITY_PATH_EVIDENCE_CREATED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
