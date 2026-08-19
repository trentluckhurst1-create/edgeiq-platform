
from __future__ import annotations

import csv
import hashlib
import json
import re
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

REPORT_MD = REPORT_DIR / "edgeiq_racingcom_first_loss_point_v1.md"
REPORT_JSON = REPORT_DIR / "edgeiq_racingcom_first_loss_point_v1.json"
PAYLOAD_CSV = REPORT_DIR / "edgeiq_racingcom_payload_content_profile_v1.csv"
IDENTITY_CSV = REPORT_DIR / "edgeiq_racingcom_payload_race_identity_v1.csv"

ACTIVE_FACTS = (
    REPO / "public" / "data" / "edgeiq_racingcom_runner_speed_fact_v1.csv",
    REPO / "public" / "data" / "edgeiq_racingcom_runner_sectional_fact_v1.csv",
    REPO / "public" / "data" / "edgeiq_racingcom_runner_split_fact_v1.csv",
    REPO / "public" / "data" / "edgeiq_racingcom_race_speed_summary_v1.csv",
)

DATE_PATTERNS = (
    re.compile(r"\b(20\d{2})[-_]?(\d{2})[-_]?(\d{2})\b"),
    re.compile(r"\b(\d{2})[-_](\d{2})[-_](20\d{2})\b"),
)

RACE_PATTERNS = (
    re.compile(r"(?:race|r)[-_ ]?0?(\d{1,2})", re.IGNORECASE),
    re.compile(r"raceNumber[\"']?\s*[:=]\s*[\"']?(\d{1,2})", re.IGNORECASE),
    re.compile(r"race_no[\"']?\s*[:=]\s*[\"']?(\d{1,2})", re.IGNORECASE),
)

TRACK_KEYS = (
    "track",
    "trackName",
    "venue",
    "venueName",
    "meetingName",
)

DATE_KEYS = (
    "meetingDate",
    "raceDate",
    "date",
    "meeting_date",
)

RACE_KEYS = (
    "raceNumber",
    "raceNo",
    "race_no",
)


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

    return path.read_text(encoding="utf-8", errors="replace")


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                return list(reader.fieldnames or []), [dict(row) for row in reader]
        except UnicodeDecodeError:
            continue

    raise UnicodeError(f"Unable to decode CSV: {path}")


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
            output = {}

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


def walk_json(value: Any) -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []

    def visit(current: Any) -> None:
        if isinstance(current, dict):
            for key, child in current.items():
                found.append((str(key), child))
                visit(child)

        elif isinstance(current, list):
            for child in current:
                visit(child)

    visit(value)
    return found


def first_key_value(
    flattened: list[tuple[str, Any]],
    keys: tuple[str, ...],
) -> str:
    wanted = {key.casefold() for key in keys}

    for key, value in flattened:
        if key.casefold() not in wanted:
            continue

        if isinstance(value, (dict, list)):
            continue

        result = clean(value)

        if result:
            return result

    return ""


def normalise_date(value: str) -> str:
    value = clean(value)

    if not value:
        return ""

    match = DATE_PATTERNS[0].search(value)

    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

    match = DATE_PATTERNS[1].search(value)

    if match:
        return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"

    return ""


def normalise_race_number(value: str) -> str:
    match = re.search(r"\d{1,2}", clean(value))

    if not match:
        return ""

    number = int(match.group(0))

    if number < 1 or number > 20:
        return ""

    return str(number)


def identity_from_filename(path: Path) -> tuple[str, str]:
    name = path.stem

    date_value = normalise_date(name)
    race_value = ""

    for pattern in RACE_PATTERNS:
        match = pattern.search(name)

        if match:
            race_value = normalise_race_number(match.group(1))
            break

    return date_value, race_value


def profile_payload(path: Path) -> dict[str, Any]:
    text = read_text(path)
    content_hash = sha256_file(path)

    json_status = "NOT_JSON"
    json_type = ""
    date_value = ""
    track_value = ""
    race_value = ""
    extraction_source = ""

    try:
        payload = json.loads(text)
        json_status = "VALID_JSON"
        json_type = type(payload).__name__

        flattened = walk_json(payload)

        date_value = normalise_date(
            first_key_value(flattened, DATE_KEYS)
        )
        track_value = first_key_value(flattened, TRACK_KEYS)
        race_value = normalise_race_number(
            first_key_value(flattened, RACE_KEYS)
        )

        if date_value or track_value or race_value:
            extraction_source = "JSON_KEYS"

    except json.JSONDecodeError:
        payload = None

    filename_date, filename_race = identity_from_filename(path)

    if not date_value:
        date_value = filename_date

        if filename_date:
            extraction_source = (
                extraction_source + "|FILENAME_DATE"
            ).strip("|")

    if not race_value:
        race_value = filename_race

        if filename_race:
            extraction_source = (
                extraction_source + "|FILENAME_RACE"
            ).strip("|")

    lower = text.casefold()

    sectional_signals = {
        "has_sectional": "sectional" in lower,
        "has_speed": "speed" in lower,
        "has_distance": "distance" in lower,
        "has_runner": "runner" in lower or "horse" in lower,
        "has_race": "race" in lower,
        "has_time": "time" in lower,
        "has_200_marker": "200" in lower,
        "has_400_marker": "400" in lower,
        "has_600_marker": "600" in lower,
        "has_800_marker": "800" in lower,
    }

    signal_count = sum(
        1
        for value in sectional_signals.values()
        if value
    )

    race_identity = "|".join(
        part
        for part in (
            date_value,
            track_value.casefold(),
            race_value,
        )
        if part
    )

    return {
        "relative_path": path.relative_to(REPO).as_posix(),
        "file_name": path.name,
        "suffix": path.suffix.casefold(),
        "size_bytes": path.stat().st_size,
        "sha256": content_hash,
        "json_status": json_status,
        "json_type": json_type,
        "meeting_date": date_value,
        "track": track_value,
        "race_no": race_value,
        "race_identity": race_identity,
        "identity_complete": bool(
            date_value and track_value and race_value
        ),
        "identity_partial": bool(
            date_value or track_value or race_value
        ),
        "extraction_source": extraction_source,
        "sectional_signal_count": signal_count,
        **sectional_signals,
    }


def governed_reference_summary() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []

    for path in ACTIVE_FACTS:
        if not path.exists():
            output.append(
                {
                    "dataset": path.name,
                    "status": "NOT_FOUND",
                    "rows": 0,
                    "distinct_source_files": 0,
                }
            )
            continue

        columns, rows = read_csv(path)

        source_columns = [
            column
            for column in columns
            if any(
                token in column.casefold()
                for token in (
                    "source_file",
                    "source_path",
                    "payload",
                    "provenance",
                )
            )
        ]

        references = set()

        for row in rows:
            for column in source_columns:
                value = clean(row.get(column))

                if value:
                    references.add(value)

        output.append(
            {
                "dataset": path.name,
                "status": "FOUND",
                "rows": len(rows),
                "source_columns": source_columns,
                "distinct_source_files": len(references),
            }
        )

    return output


def render_markdown(report: dict[str, Any]) -> str:
    population = report["payload_population"]
    classifications = report["classification_counts"]

    lines = [
        "# EDGEIQ Racing.com First Loss Point V1",
        "",
        f"Generated UTC: `{report['generated_utc']}`",
        "",
        "## Governance boundary",
        "",
        "- Read-only forensic diagnostic.",
        "- Raw full-payload directory only.",
        "- No builder modified.",
        "- No governed output modified.",
        "- No threshold modified.",
        "- No benchmark data fabricated.",
        "",
        "## Raw payload population",
        "",
        f"- Files: **{population['files']}**",
        f"- Unique hashes: **{population['unique_hashes']}**",
        f"- Duplicate copies: **{population['duplicate_copies']}**",
        "",
        "## Structural classification",
        "",
    ]

    for key, value in sorted(classifications.items()):
        lines.append(f"- {key}: **{value}**")

    lines.extend(
        [
            "",
            "## Distinct extracted identities",
            "",
            f"- Complete race identities: "
            f"**{report['complete_race_identities']}**",
            f"- Partial race identities: "
            f"**{report['partial_race_identities']}**",
            f"- Payloads with no identity: "
            f"**{report['payloads_without_identity']}**",
            "",
            "## Governed facts",
            "",
        ]
    )

    for dataset in report["governed_references"]:
        lines.append(
            f"- `{dataset['dataset']}` ? "
            f"{dataset['status']} ? "
            f"rows={dataset['rows']} ? "
            f"distinct source files="
            f"{dataset['distinct_source_files']}"
        )

    lines.extend(
        [
            "",
            "## Preliminary interpretation",
            "",
        ]
    )

    complete_identities = report["complete_race_identities"]

    if complete_identities <= 39:
        lines.extend(
            [
                "**RAW_FILES_COLLAPSE_TO_NO_MORE_THAN_39_COMPLETE_RACE_IDENTITIES**",
                "",
                "The 602 files do not presently prove more than 39 races. "
                "They appear to include repeated captures or payload variants "
                "for the same race population.",
            ]
        )
    else:
        lines.extend(
            [
                "**RAW_FILES_CONTAIN_MORE_THAN_39_COMPLETE_RACE_IDENTITIES**",
                "",
                "The raw directory contains identifiable race evidence beyond "
                "the 39 governed races. The next diagnostic must execute the "
                "active parser against each unique payload and record exact "
                "admission or rejection reasons.",
            ]
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if not RAW_DIR.exists():
        raise FileNotFoundError(
            f"Raw payload directory not found: {RAW_DIR}"
        )

    print("EDGEIQ Racing.com First Loss Point V1")
    print(f"Raw directory: {RAW_DIR}")
    print("")

    paths = sorted(
        (
            path
            for path in RAW_DIR.rglob("*")
            if path.is_file()
        ),
        key=lambda path: path.as_posix().casefold(),
    )

    print(f"[1/4] Profiling {len(paths):,} raw files...")

    payload_rows: list[dict[str, Any]] = []

    for index, path in enumerate(paths, start=1):
        payload_rows.append(profile_payload(path))

        if index % 100 == 0:
            print(f"  Profiled {index:,}/{len(paths):,}")

    print("[2/4] Collapsing duplicate content...")
    unique_by_hash: dict[str, dict[str, Any]] = {}

    for row in payload_rows:
        unique_by_hash.setdefault(row["sha256"], row)

    unique_rows = list(unique_by_hash.values())

    print(f"Unique content payloads: {len(unique_rows):,}")

    complete_identities = {
        row["race_identity"]
        for row in unique_rows
        if row["identity_complete"]
    }

    partial_identities = {
        row["race_identity"]
        for row in unique_rows
        if row["identity_partial"]
        and not row["identity_complete"]
    }

    payloads_without_identity = sum(
        1
        for row in unique_rows
        if not row["identity_partial"]
    )

    classification_counts = Counter(
        (
            "VALID_JSON_COMPLETE_IDENTITY"
            if row["json_status"] == "VALID_JSON"
            and row["identity_complete"]
            else "VALID_JSON_PARTIAL_IDENTITY"
            if row["json_status"] == "VALID_JSON"
            and row["identity_partial"]
            else "VALID_JSON_NO_IDENTITY"
            if row["json_status"] == "VALID_JSON"
            else "NON_JSON_PARTIAL_IDENTITY"
            if row["identity_partial"]
            else "NON_JSON_NO_IDENTITY"
        )
        for row in unique_rows
    )

    print("[3/4] Reading governed source references...")
    governed_references = governed_reference_summary()

    report = {
        "diagnostic": "EDGEIQ_RACINGCOM_FIRST_LOSS_POINT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "raw_directory": str(RAW_DIR),
        "governance": {
            "read_only": True,
            "builders_modified": False,
            "governed_outputs_modified": False,
            "thresholds_modified": False,
            "fabricated_data": False,
        },
        "payload_population": {
            "files": len(payload_rows),
            "unique_hashes": len(unique_rows),
            "duplicate_copies": len(payload_rows) - len(unique_rows),
        },
        "classification_counts": dict(
            sorted(classification_counts.items())
        ),
        "complete_race_identities": len(complete_identities),
        "partial_race_identities": len(partial_identities),
        "payloads_without_identity": payloads_without_identity,
        "governed_references": governed_references,
    }

    identity_rows = [
        {
            "race_identity": identity,
            "meeting_date": next(
                (
                    row["meeting_date"]
                    for row in unique_rows
                    if row["race_identity"] == identity
                ),
                "",
            ),
            "track": next(
                (
                    row["track"]
                    for row in unique_rows
                    if row["race_identity"] == identity
                ),
                "",
            ),
            "race_no": next(
                (
                    row["race_no"]
                    for row in unique_rows
                    if row["race_identity"] == identity
                ),
                "",
            ),
            "unique_payload_count": sum(
                1
                for row in unique_rows
                if row["race_identity"] == identity
            ),
            "file_copy_count": sum(
                1
                for row in payload_rows
                if row["race_identity"] == identity
            ),
        }
        for identity in sorted(complete_identities)
    ]

    print("[4/4] Writing deterministic forensic artifacts...")

    write_csv(PAYLOAD_CSV, payload_rows)
    write_csv(IDENTITY_CSV, identity_rows)

    REPORT_JSON.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    REPORT_MD.write_text(
        render_markdown(report),
        encoding="utf-8",
    )

    print("")
    print("COMPLETE")
    print(f"Report: {REPORT_MD}")
    print(f"Payload profile: {PAYLOAD_CSV}")
    print(f"Race identities: {IDENTITY_CSV}")
    print("")
    print("DECISION")

    if len(complete_identities) > 39:
        print("RAW_FILES_CONTAIN_MORE_THAN_39_COMPLETE_RACE_IDENTITIES")
    else:
        print("RAW_FILES_COLLAPSE_TO_NO_MORE_THAN_39_COMPLETE_RACE_IDENTITIES")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
