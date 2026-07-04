from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

NON_RUNNER_CONFIRMATION = DATA / "racing_australia_non_runner_confirmation_v1.csv"
SETTLEMENT_CANDIDATE = DATA / "racing_australia_settlement_candidate_v1.csv"
PRICE_TRUTH = DATA / "edgeiq_price_truth_history_v1.csv"

TEMPLATE_OUT = DATA / "manual_sandown_2026_05_31_scratching_confirmation_template_v1.csv"
AUDIT_OUT = DATA / "manual_sandown_2026_05_31_scratching_confirmation_template_v1_audit.csv"

TARGET_DATE = "2026-05-31"
TARGET_TRACK = "SANDOWN LAKESIDE"

ALLOWED_MANUAL_STATUSES = [
    "CONFIRMED_SCRATCHED",
    "CONFIRMED_NON_RUNNER",
    "CONFIRMED_STARTED_NO_RESULT",
    "STILL_UNCONFIRMED",
]

TEMPLATE_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "current_classification",
    "source_reason",
    "sportsbet_present",
    "ra_result_present",
    "manual_status",
    "manual_finish_position",
    "manual_won",
    "manual_starting_price",
    "manual_notes",
]

AUDIT_COLUMNS = ["section", "metric", "value", "source_path", "notes", "built_at"]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"}:
        return ""
    return text


def normalise_text(value: object) -> str:
    text = clean(value).upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def horse_key(value: object) -> str:
    return normalise_text(value).replace(" ", "")


def clean_race_no(value: object) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def target_key(row: dict[str, str]) -> str:
    return "|".join(
        [
            clean(row.get("race_date")),
            normalise_text(row.get("track")),
            clean_race_no(row.get("race_no")),
            horse_key(row.get("horse_key")) or horse_key(row.get("horse")),
        ]
    )


def load_candidate_keys() -> set[str]:
    _, rows = read_csv(SETTLEMENT_CANDIDATE)
    return {
        target_key(row)
        for row in rows
        if clean(row.get("result_status")) == "NON_RUNNER_UNCONFIRMED"
        and clean(row.get("race_date")) == TARGET_DATE
        and normalise_text(row.get("track")) == TARGET_TRACK
    }


def load_price_truth_keys() -> set[str]:
    _, rows = read_csv(PRICE_TRUTH)
    return {
        target_key(row)
        for row in rows
        if clean(row.get("race_date")) == TARGET_DATE
        and normalise_text(row.get("track")) == TARGET_TRACK
    }


def source_reason(row: dict[str, str]) -> str:
    parts = [
        f"classification={clean(row.get('classification'))}",
        f"settlement_blocker={clean(row.get('settlement_blocker'))}",
        f"ra_present={clean(row.get('present_in_ra_final_results'))}",
        f"sportsbet_present={clean(row.get('present_in_sportsbet_full_day'))}",
        f"sportsbet_scratched={clean(row.get('sportsbet_is_scratched'))}",
        f"sportsbet_status={clean(row.get('sportsbet_runner_status'))}",
    ]
    notes = clean(row.get("notes"))
    if notes:
        parts.append(f"notes={notes}")
    return " | ".join(part for part in parts if part and not part.endswith("="))


def build_template_rows() -> list[dict[str, object]]:
    _, rows = read_csv(NON_RUNNER_CONFIRMATION)
    candidate_keys = load_candidate_keys()
    price_truth_keys = load_price_truth_keys()
    template_rows: list[dict[str, object]] = []
    seen: set[str] = set()

    for row in rows:
        key = target_key(row)
        if key in seen:
            continue
        if key not in candidate_keys:
            continue
        if key not in price_truth_keys:
            continue
        template_rows.append(
            {
                "race_date": clean(row.get("race_date")),
                "track": clean(row.get("track")),
                "race_no": clean_race_no(row.get("race_no")),
                "horse": clean(row.get("horse")),
                "horse_key": horse_key(row.get("horse_key")) or horse_key(row.get("horse")),
                "current_classification": clean(row.get("classification")),
                "source_reason": source_reason(row),
                "sportsbet_present": clean(row.get("present_in_sportsbet_full_day")),
                "ra_result_present": clean(row.get("present_in_ra_final_results")),
                "manual_status": "STILL_UNCONFIRMED",
                "manual_finish_position": "",
                "manual_won": "",
                "manual_starting_price": "",
                "manual_notes": "",
            }
        )
        seen.add(key)

    return sorted(template_rows, key=lambda item: (int(str(item["race_no"])), str(item["horse_key"])))


def audit_row(section: str, metric: str, value: object, source_path: Path | str = "", notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "source_path": str(source_path),
        "notes": notes,
        "built_at": now_utc(),
    }


def build_audit(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    required_present = all(column in TEMPLATE_COLUMNS for column in TEMPLATE_COLUMNS)
    manual_status_counts = Counter(str(row.get("manual_status", "")) for row in rows)
    race_count = len({str(row.get("race_no", "")) for row in rows})
    runner_count = len({str(row.get("horse_key", "")) for row in rows})
    ready = bool(rows) and required_present and len(rows) == 16 and runner_count == 16

    audit = [
        audit_row("input", "non_runner_confirmation_source_exists", NON_RUNNER_CONFIRMATION.exists(), NON_RUNNER_CONFIRMATION),
        audit_row("input", "settlement_candidate_source_exists", SETTLEMENT_CANDIDATE.exists(), SETTLEMENT_CANDIDATE),
        audit_row("input", "price_truth_source_exists", PRICE_TRUTH.exists(), PRICE_TRUTH),
        audit_row("output", "template_rows", len(rows), TEMPLATE_OUT),
        audit_row("output", "races_represented", race_count, TEMPLATE_OUT),
        audit_row("output", "runners_represented", runner_count, TEMPLATE_OUT),
        audit_row("manual_defaults", "default_still_unconfirmed_count", manual_status_counts.get("STILL_UNCONFIRMED", 0), TEMPLATE_OUT),
        audit_row("schema", "required_manual_fields_present", "TRUE" if required_present else "FALSE", TEMPLATE_OUT, ",".join(TEMPLATE_COLUMNS)),
        audit_row("schema", "allowed_manual_status_values", " | ".join(ALLOWED_MANUAL_STATUSES), TEMPLATE_OUT),
        audit_row("status", "ready_for_manual_review", "TRUE" if ready else "FALSE", TEMPLATE_OUT),
    ]
    for race_no, count in sorted(Counter(str(row.get("race_no", "")) for row in rows).items(), key=lambda item: int(item[0])):
        audit.append(audit_row("race_count", f"R{race_no}", count, TEMPLATE_OUT))
    return audit


def main() -> None:
    rows = build_template_rows()
    audit_rows = build_audit(rows)

    write_csv(TEMPLATE_OUT, rows, TEMPLATE_COLUMNS)
    write_csv(AUDIT_OUT, audit_rows, AUDIT_COLUMNS)

    print("=" * 96)
    print("MANUAL SANDOWN SCRATCHING CONFIRMATION TEMPLATE V1 - REVIEW ONLY")
    print("=" * 96)
    for row in audit_rows:
        if row["section"] in {"output", "manual_defaults", "schema", "status"}:
            print(f"{row['section']},{row['metric']},{row['value']},{row['notes']}")
    print(f"wrote: {TEMPLATE_OUT}")
    print(f"wrote: {AUDIT_OUT}")
    print("=" * 96)


if __name__ == "__main__":
    main()
