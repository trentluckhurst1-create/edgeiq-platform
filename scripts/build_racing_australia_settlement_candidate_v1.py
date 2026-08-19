from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TARGET_DATE = "2026-05-31"
TARGET_TRACK = "SANDOWN LAKESIDE"
TARGET_RACES = {str(number) for number in range(1, 9)}

PRICE_TRUTH = DATA / "edgeiq_price_truth_history_v1.csv"
RA_NORMALISED = DATA / "racing_australia_sandown_2026_05_31_normalised_results_v1.csv"
RA_UNMATCHED = DATA / "racing_australia_unmatched_results_v1.csv"

CANDIDATE_OUT = DATA / "racing_australia_settlement_candidate_v1.csv"
AUDIT_OUT = DATA / "racing_australia_settlement_candidate_v1_audit.csv"

CANDIDATE_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "finish_position",
    "won",
    "starting_price",
    "result_status",
    "settlement_blocker",
    "result_source",
    "match_status",
    "notes",
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
    text = text.replace("&", " AND ")
    text = re.sub(r"['`]", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def horse_key(value: object) -> str:
    return normalise_text(value).replace(" ", "")


def normalise_track(value: object) -> str:
    track = normalise_text(value)
    track = re.sub(r"\bSPORTS\s*BET\b", "SPORTSBET", track)
    track = re.sub(r"\bVIC\b|\bPROFESSIONAL\b|\bMETRO\b|\bTAB\b|\bMEETING\b", " ", track)
    track = re.sub(r"\bMELBOURNE\b|\bRACING\b|\bCLUB\b", " ", track)
    track = re.sub(r"\s+", " ", track).strip()
    if "SANDOWN" in track and "LAKESIDE" in track:
        return TARGET_TRACK
    if track.startswith("SPORTSBET "):
        track = track.replace("SPORTSBET ", "", 1)
    return track


def clean_race_no(value: object) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def candidate_key(date: object, track: object, race_no: object, horse_value: object, key_value: object = "") -> str:
    key = horse_key(key_value) or horse_key(horse_value)
    return "|".join([clean(date), normalise_track(track), clean_race_no(race_no), key])


def numeric_finish(value: object) -> bool:
    return bool(re.fullmatch(r"\d+", clean(value)))


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


def load_truth_targets() -> list[dict[str, str]]:
    columns, rows = read_csv(PRICE_TRUTH)
    required = {"race_date", "track", "race_no", "horse", "horse_key"}
    missing = sorted(required.difference(columns))
    if missing:
        raise ValueError(f"{PRICE_TRUTH} missing required columns: {missing}")

    targets_by_key: dict[str, dict[str, str]] = {}
    for row in rows:
        race_date = clean(row.get("race_date"))
        track = normalise_track(row.get("track"))
        race_no = clean_race_no(row.get("race_no"))
        if race_date != TARGET_DATE or track != TARGET_TRACK or race_no not in TARGET_RACES:
            continue
        key = candidate_key(race_date, track, race_no, row.get("horse"), row.get("horse_key"))
        targets_by_key[key] = {
            "race_date": race_date,
            "track": TARGET_TRACK,
            "race_no": race_no,
            "horse": clean(row.get("horse")),
            "horse_key": horse_key(row.get("horse_key")) or horse_key(row.get("horse")),
        }
    return sorted(targets_by_key.values(), key=lambda row: (int(row["race_no"]), row["horse_key"]))


def index_ra_results() -> dict[str, list[dict[str, str]]]:
    _, rows = read_csv(RA_NORMALISED)
    indexed: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        key = candidate_key(row.get("race_date"), row.get("track"), row.get("race_no"), row.get("horse"), row.get("horse_key"))
        indexed.setdefault(key, []).append(row)
    return indexed


def index_unmatched_diagnostic() -> dict[str, dict[str, str]]:
    _, rows = read_csv(RA_UNMATCHED)
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        key = candidate_key(row.get("race_date"), row.get("track"), row.get("race_no"), row.get("horse"), row.get("horse_key"))
        indexed[key] = row
    return indexed


def make_final_row(target: dict[str, str], ra_row: dict[str, str]) -> dict[str, object]:
    finish_position = clean(ra_row.get("finish_position"))
    won = "TRUE" if finish_position == "1" else "FALSE"
    return {
        "race_date": target["race_date"],
        "track": target["track"],
        "race_no": target["race_no"],
        "horse": target["horse"],
        "horse_key": target["horse_key"],
        "finish_position": finish_position,
        "won": won,
        "starting_price": clean(ra_row.get("starting_price")),
        "result_status": "FINAL",
        "settlement_blocker": "",
        "result_source": "RACING_AUSTRALIA",
        "match_status": "MATCHED_RA_NUMERIC_FINISH",
        "notes": "Numeric Racing Australia finish position captured; candidate only, not written to price truth.",
    }


def make_failed_to_finish_row(target: dict[str, str], ra_row: dict[str, str], diagnostic: dict[str, str]) -> dict[str, object]:
    finish_marker = clean(diagnostic.get("ra_finish_raw")) or "FF"
    return {
        "race_date": target["race_date"],
        "track": target["track"],
        "race_no": target["race_no"],
        "horse": target["horse"],
        "horse_key": target["horse_key"],
        "finish_position": finish_marker,
        "won": "FALSE",
        "starting_price": clean(ra_row.get("starting_price")) or clean(diagnostic.get("ra_starting_price")),
        "result_status": "FAILED_TO_FINISH",
        "settlement_blocker": "",
        "result_source": "RACING_AUSTRALIA",
        "match_status": "MATCHED_RA_FAILED_TO_FINISH",
        "notes": "Racing Australia row has non-numeric finish marker; treated as terminal failed-to-finish in candidate only.",
    }


def make_confirmed_scratched_row(target: dict[str, str], diagnostic: dict[str, str]) -> dict[str, object]:
    return {
        "race_date": target["race_date"],
        "track": target["track"],
        "race_no": target["race_no"],
        "horse": target["horse"],
        "horse_key": target["horse_key"],
        "finish_position": "SCR",
        "won": "FALSE",
        "starting_price": "",
        "result_status": "CONFIRMED_SCRATCHED",
        "settlement_blocker": "",
        "result_source": clean(diagnostic.get("scratching_indicator_source")) or "LOCAL_SCRATCHING_INDICATOR",
        "match_status": "RA_ABSENT_CONFIRMED_SCRATCHED",
        "notes": "RA result row absent and positive local scratching indicator exists; candidate only.",
    }


def make_unconfirmed_non_runner_row(target: dict[str, str], diagnostic: dict[str, str]) -> dict[str, object]:
    return {
        "race_date": target["race_date"],
        "track": target["track"],
        "race_no": target["race_no"],
        "horse": target["horse"],
        "horse_key": target["horse_key"],
        "finish_position": "",
        "won": "",
        "starting_price": "",
        "result_status": "NON_RUNNER_UNCONFIRMED",
        "settlement_blocker": "NEEDS_SCRATCHING_CONFIRMATION",
        "result_source": "RACING_AUSTRALIA_ABSENT_WITH_DIAGNOSTIC",
        "match_status": "UNMATCHED_RA_RESULT",
        "notes": clean(diagnostic.get("settlement_blocking_reason")) or "RA result row absent; no safe terminal status available.",
    }


def make_unresolved_row(target: dict[str, str], diagnostic: dict[str, str] | None = None) -> dict[str, object]:
    return {
        "race_date": target["race_date"],
        "track": target["track"],
        "race_no": target["race_no"],
        "horse": target["horse"],
        "horse_key": target["horse_key"],
        "finish_position": "",
        "won": "",
        "starting_price": clean((diagnostic or {}).get("ra_starting_price")),
        "result_status": "RESULT_UNRESOLVED",
        "settlement_blocker": "RESULT_REVIEW_REQUIRED",
        "result_source": "RACING_AUSTRALIA_DIAGNOSTIC",
        "match_status": "UNRESOLVED_SETTLEMENT_STATUS",
        "notes": clean((diagnostic or {}).get("settlement_blocking_reason")) or "No safe settlement candidate rule matched.",
    }


def build_candidate_row(
    target: dict[str, str],
    ra_rows: list[dict[str, str]],
    diagnostic: dict[str, str] | None,
) -> dict[str, object]:
    if ra_rows:
        ra_row = ra_rows[0]
        if numeric_finish(ra_row.get("finish_position")):
            return make_final_row(target, ra_row)
        if diagnostic and clean(diagnostic.get("classification")) == "FAILED_TO_FINISH_OR_NO_FINISH":
            return make_failed_to_finish_row(target, ra_row, diagnostic)
        return make_unresolved_row(target, diagnostic)

    if diagnostic and clean(diagnostic.get("classification")) == "LIKELY_NON_RUNNER":
        return make_unconfirmed_non_runner_row(target, diagnostic)
    if diagnostic and clean(diagnostic.get("classification")) == "LIKELY_SCRATCHED" and clean(diagnostic.get("scratch_indicator_found")) == "YES":
        return make_confirmed_scratched_row(target, diagnostic)
    return make_unresolved_row(target, diagnostic)


def audit_row(section: str, metric: str, value: object, source_path: Path | str = "", notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "source_path": str(source_path),
        "notes": notes,
        "built_at": now_utc(),
    }


def build_audit(candidate_rows: list[dict[str, object]], targets: list[dict[str, str]]) -> list[dict[str, object]]:
    status_counts = Counter(str(row.get("result_status", "")) for row in candidate_rows)
    blocker_counts = Counter(str(row.get("settlement_blocker", "")) for row in candidate_rows if clean(row.get("settlement_blocker")))
    race_count = len({str(row.get("race_no", "")) for row in candidate_rows})
    runner_count = len({candidate_key(row.get("race_date"), row.get("track"), row.get("race_no"), row.get("horse"), row.get("horse_key")) for row in candidate_rows})
    winner_flags_populated = sum(1 for row in candidate_rows if clean(row.get("won")))
    sp_populated = sum(1 for row in candidate_rows if clean(row.get("starting_price")))
    safe_statuses = {"FINAL", "FAILED_TO_FINISH", "CONFIRMED_SCRATCHED"}
    settlement_ready = bool(candidate_rows) and all(str(row.get("result_status")) in safe_statuses for row in candidate_rows)
    if len(candidate_rows) != 87 or runner_count != 87:
        recommendation = "SETTLEMENT_CANDIDATE_FAILED"
    elif any(row.get("settlement_blocker") == "NEEDS_SCRATCHING_CONFIRMATION" for row in candidate_rows):
        recommendation = "NEEDS_SCRATCHING_CONFIRMATION"
    elif settlement_ready:
        recommendation = "READY_FOR_SETTLEMENT_IF_NON_RUNNERS_CONFIRMED"
    else:
        recommendation = "SETTLEMENT_CANDIDATE_FAILED"

    rows = [
        audit_row("input", "target_truth_runners", len(targets), PRICE_TRUTH),
        audit_row("input", "ra_normalised_source", RA_NORMALISED.exists(), RA_NORMALISED),
        audit_row("input", "unmatched_diagnostic_source", RA_UNMATCHED.exists(), RA_UNMATCHED),
        audit_row("output", "candidate_rows", len(candidate_rows), CANDIDATE_OUT),
        audit_row("output", "races", race_count, CANDIDATE_OUT),
        audit_row("output", "runners", runner_count, CANDIDATE_OUT),
        audit_row("status", "final_numeric_finish_rows", status_counts.get("FINAL", 0), CANDIDATE_OUT),
        audit_row("status", "failed_to_finish_rows", status_counts.get("FAILED_TO_FINISH", 0), CANDIDATE_OUT),
        audit_row("status", "non_runner_unconfirmed_rows", status_counts.get("NON_RUNNER_UNCONFIRMED", 0), CANDIDATE_OUT),
        audit_row("fields", "winner_flags_populated", winner_flags_populated, CANDIDATE_OUT),
        audit_row("fields", "sp_populated", sp_populated, CANDIDATE_OUT),
        audit_row("blockers", "settlement_blockers", sum(blocker_counts.values()), CANDIDATE_OUT),
        audit_row("status", "settlement_ready", "TRUE" if settlement_ready else "FALSE", CANDIDATE_OUT),
        audit_row("recommendation", "recommendation", recommendation, AUDIT_OUT),
    ]
    for status, count in sorted(status_counts.items()):
        rows.append(audit_row("result_status_count", status, count, CANDIDATE_OUT))
    for blocker, count in sorted(blocker_counts.items()):
        rows.append(audit_row("settlement_blocker_count", blocker, count, CANDIDATE_OUT))
    for race_no, count in sorted(Counter(str(row["race_no"]) for row in candidate_rows).items(), key=lambda item: int(item[0])):
        rows.append(audit_row("race_count", f"R{race_no}", count, CANDIDATE_OUT))
    return rows


def main() -> None:
    targets = load_truth_targets()
    ra_index = index_ra_results()
    diagnostic_index = index_unmatched_diagnostic()

    candidate_rows: list[dict[str, object]] = []
    for target in targets:
        key = candidate_key(target["race_date"], target["track"], target["race_no"], target["horse"], target["horse_key"])
        candidate_rows.append(build_candidate_row(target, ra_index.get(key, []), diagnostic_index.get(key)))

    duplicate_keys = [
        key
        for key, count in Counter(
            candidate_key(row.get("race_date"), row.get("track"), row.get("race_no"), row.get("horse"), row.get("horse_key"))
            for row in candidate_rows
        ).items()
        if count > 1
    ]
    if duplicate_keys:
        raise ValueError(f"Settlement candidate produced duplicate runner keys: {duplicate_keys[:10]}")

    audit_rows = build_audit(candidate_rows, targets)

    write_csv(CANDIDATE_OUT, candidate_rows, CANDIDATE_COLUMNS)
    write_csv(AUDIT_OUT, audit_rows, AUDIT_COLUMNS)

    print("=" * 96)
    print("RACING AUSTRALIA SETTLEMENT CANDIDATE V1 - REVIEW ONLY")
    print("=" * 96)
    for row in audit_rows:
        if row["section"] in {"output", "status", "fields", "blockers", "recommendation"}:
            print(f"{row['section']},{row['metric']},{row['value']},{row['notes']}")
    print(f"wrote: {CANDIDATE_OUT}")
    print(f"wrote: {AUDIT_OUT}")
    print("=" * 96)


if __name__ == "__main__":
    main()
