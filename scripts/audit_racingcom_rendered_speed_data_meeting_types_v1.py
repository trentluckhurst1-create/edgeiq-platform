from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

NORMALISED = DATA / "racingcom_rendered_speed_data_normalised_v1.csv"
RAW = DATA / "racingcom_rendered_speed_data_raw_v1.csv"
HARVEST_AUDIT = DATA / "racingcom_rendered_speed_data_harvester_v1_audit.csv"

OUT = DATA / "racingcom_rendered_speed_data_meeting_types_v1.csv"
AUDIT_OUT = DATA / "racingcom_rendered_speed_data_meeting_types_v1_audit.csv"

OUT_COLUMNS = [
    "meeting_date",
    "track",
    "race_no",
    "source_url",
    "meeting_type",
    "is_thoroughbred_race",
    "is_trial",
    "is_jumpout",
    "is_picnic",
    "classification_reason",
]

AUDIT_COLUMNS = [
    "pages_audited",
    "thoroughbred_races",
    "trials",
    "jumpouts",
    "picnics",
    "unknown",
    "pct_thoroughbred_races",
    "final_status",
]

TRIAL_RE = re.compile(r"\btrials?\b", re.IGNORECASE)
JUMPOUT_RE = re.compile(r"\bjump\s*outs?\b|\bjumpouts?\b", re.IGNORECASE)
PICNIC_RE = re.compile(r"\bpicnics?\b", re.IGNORECASE)
PUBLIC_SPEED_RE = re.compile(
    r"^https://www\.racing\.com/form/\d{4}-\d{2}-\d{2}/[^/]+/race/\d+/speed-data(?:[?#].*)?$",
    re.IGNORECASE,
)


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    tmp.replace(path)


def race_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        clean(row.get("meeting_date")),
        clean(row.get("track")),
        clean(row.get("race_no")),
        clean(row.get("source_url")),
    )


def source_context() -> dict[tuple[str, str, str, str], dict[str, Any]]:
    races: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in read_csv(NORMALISED):
        key = race_key(row)
        if not any(key):
            continue
        record = races.setdefault(
            key,
            {
                "meeting_date": key[0],
                "track": key[1],
                "race_no": key[2],
                "source_url": key[3],
                "normalised_rows": 0,
                "raw_text": [],
                "headers": set(),
            },
        )
        record["normalised_rows"] += 1
    for row in read_csv(RAW):
        key = race_key(row)
        if not any(key):
            continue
        record = races.setdefault(
            key,
            {
                "meeting_date": key[0],
                "track": key[1],
                "race_no": key[2],
                "source_url": key[3],
                "normalised_rows": 0,
                "raw_text": [],
                "headers": set(),
            },
        )
        raw = clean(row.get("raw_row_text"))
        if raw:
            record["raw_text"].append(raw)
        header = clean(row.get("visible_column_headers"))
        if header:
            record["headers"].add(header)
    return races


def classify(record: dict[str, Any]) -> dict[str, str]:
    context = " ".join(
        [
            clean(record.get("meeting_date")),
            clean(record.get("track")),
            clean(record.get("race_no")),
            clean(record.get("source_url")),
            " ".join(sorted(record.get("headers") or [])),
            " ".join(record.get("raw_text") or [])[:5000],
        ]
    )
    if JUMPOUT_RE.search(context):
        return {
            "meeting_type": "JUMPOUT",
            "is_thoroughbred_race": "FALSE",
            "is_trial": "FALSE",
            "is_jumpout": "TRUE",
            "is_picnic": "FALSE",
            "classification_reason": "Excluded keyword detected: jumpout/jump out.",
        }
    if TRIAL_RE.search(context):
        return {
            "meeting_type": "TRIAL",
            "is_thoroughbred_race": "FALSE",
            "is_trial": "TRUE",
            "is_jumpout": "FALSE",
            "is_picnic": "FALSE",
            "classification_reason": "Excluded keyword detected: trial.",
        }
    if PICNIC_RE.search(context):
        return {
            "meeting_type": "PICNIC",
            "is_thoroughbred_race": "FALSE",
            "is_trial": "FALSE",
            "is_jumpout": "FALSE",
            "is_picnic": "TRUE",
            "classification_reason": "Excluded keyword detected: picnic.",
        }

    source_url = clean(record.get("source_url"))
    normalised_rows = int(record.get("normalised_rows") or 0)
    headers = " ".join(sorted(record.get("headers") or []))
    has_speed_headers = all(token in headers.upper() for token in ("POS / HORSE", "EARLY", "MID", "LATE", "PEAK", "AVG SPEED"))
    if PUBLIC_SPEED_RE.match(source_url) and normalised_rows > 0 and has_speed_headers:
        return {
            "meeting_type": "THOROUGHBRED_RACE",
            "is_thoroughbred_race": "TRUE",
            "is_trial": "FALSE",
            "is_jumpout": "FALSE",
            "is_picnic": "FALSE",
            "classification_reason": "Public Racing.com race speed-data URL with visible runner speed rows and no trial/jumpout/picnic keyword.",
        }

    return {
        "meeting_type": "UNKNOWN",
        "is_thoroughbred_race": "FALSE",
        "is_trial": "FALSE",
        "is_jumpout": "FALSE",
        "is_picnic": "FALSE",
        "classification_reason": "Insufficient meeting label evidence in rendered extraction.",
    }


def final_status(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "UNABLE_TO_CLASSIFY"
    non_race = [row for row in rows if row["meeting_type"] in {"TRIAL", "JUMPOUT", "PICNIC"}]
    if non_race:
        return "NON_RACE_MEETINGS_DETECTED"
    unknown = [row for row in rows if row["meeting_type"] == "UNKNOWN"]
    thoroughbred = [row for row in rows if row["meeting_type"] == "THOROUGHBRED_RACE"]
    if unknown and thoroughbred:
        return "MIXED_MEETING_TYPES_FOUND"
    if thoroughbred and len(thoroughbred) == len(rows):
        return "ALL_VALID_THOROUGHBRED_RACES"
    return "UNABLE_TO_CLASSIFY"


def pct(numerator: int, denominator: int) -> str:
    if not denominator:
        return "0"
    return f"{(numerator / denominator) * 100:.2f}"


def main() -> None:
    _harvest_audit_rows = read_csv(HARVEST_AUDIT)
    races = source_context()
    output_rows: list[dict[str, str]] = []
    for key in sorted(races):
        record = races[key]
        classification = classify(record)
        output_rows.append(
            {
                "meeting_date": clean(record.get("meeting_date")),
                "track": clean(record.get("track")),
                "race_no": clean(record.get("race_no")),
                "source_url": clean(record.get("source_url")),
                **classification,
            }
        )

    counts = {
        "thoroughbred_races": sum(1 for row in output_rows if row["meeting_type"] == "THOROUGHBRED_RACE"),
        "trials": sum(1 for row in output_rows if row["meeting_type"] == "TRIAL"),
        "jumpouts": sum(1 for row in output_rows if row["meeting_type"] == "JUMPOUT"),
        "picnics": sum(1 for row in output_rows if row["meeting_type"] == "PICNIC"),
        "unknown": sum(1 for row in output_rows if row["meeting_type"] == "UNKNOWN"),
    }
    audit_row = {
        "pages_audited": len(output_rows),
        **counts,
        "pct_thoroughbred_races": pct(counts["thoroughbred_races"], len(output_rows)),
        "final_status": final_status(output_rows),
    }

    write_csv(OUT, output_rows, OUT_COLUMNS)
    write_csv(AUDIT_OUT, [audit_row], AUDIT_COLUMNS)

    print(f"[racingcom_meeting_types_v1] pages_audited={len(output_rows)}")
    print(
        "[racingcom_meeting_types_v1] "
        f"thoroughbred={counts['thoroughbred_races']} trials={counts['trials']} "
        f"jumpouts={counts['jumpouts']} picnics={counts['picnics']} unknown={counts['unknown']}"
    )
    print(f"[racingcom_meeting_types_v1] final_status={audit_row['final_status']}")
    print(f"[racingcom_meeting_types_v1] wrote {OUT.relative_to(ROOT)}")
    print(f"[racingcom_meeting_types_v1] wrote {AUDIT_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
