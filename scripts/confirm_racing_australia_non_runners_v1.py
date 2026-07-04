from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TARGET_DATE = "2026-05-31"
TARGET_TRACK = "SANDOWN LAKESIDE"
TARGET_RACES = {str(number) for number in range(1, 9)}

CANDIDATE = DATA / "racing_australia_settlement_candidate_v1.csv"
RA_RAW = DATA / "racing_australia_sandown_2026_05_31_raw_results_v1.csv"
RA_NORMALISED = DATA / "racing_australia_sandown_2026_05_31_normalised_results_v1.csv"
SPORTSBET_FULL_DAY = DATA / "sportsbet_live_market_full_day_v5_2.csv"
CURRENT_PROJECTION = DATA / "edgeiq_current_field_projection_v5_2.csv"
RESULTS_TRUTH_LOOP = DATA / "edgeiq_results_truth_loop.csv"
PRICE_TRUTH = DATA / "edgeiq_price_truth_history_v1.csv"

CONFIRMATION_OUT = DATA / "racing_australia_non_runner_confirmation_v1.csv"
AUDIT_OUT = DATA / "racing_australia_non_runner_confirmation_v1_audit.csv"

DETAIL_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "classification",
    "settlement_safe",
    "settlement_blocker",
    "present_in_price_truth",
    "present_in_ra_final_results",
    "ra_raw_present",
    "present_in_sportsbet_full_day",
    "sportsbet_is_scratched",
    "sportsbet_runner_status",
    "sportsbet_selection_status",
    "sportsbet_status_code",
    "present_in_current_projection",
    "present_in_results_truth_loop",
    "truth_loop_result_status",
    "local_scratch_flag_found",
    "local_scratch_source",
    "local_non_runner_flag_found",
    "local_non_runner_source",
    "sources_checked",
    "evidence",
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


def row_key(date: object, track: object, race_no: object, horse_value: object, key_value: object = "") -> str:
    key = horse_key(key_value) or horse_key(horse_value)
    return "|".join([clean(date), normalise_track(track), clean_race_no(race_no), key])


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


def first_present(row: dict[str, str] | None, columns: list[str]) -> str:
    if not row:
        return ""
    for column in columns:
        value = clean(row.get(column))
        if value:
            return value
    return ""


def index_file(path: Path) -> dict[str, list[dict[str, str]]]:
    _, rows = read_csv(path)
    indexed: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        race_date = clean(row.get("race_date") or row.get("date") or row.get("snapshot_date"))
        track = normalise_track(row.get("track") or row.get("venue") or row.get("meeting_name"))
        race_no = clean_race_no(row.get("race_no") or row.get("race_number"))
        if race_date != TARGET_DATE or track != TARGET_TRACK or race_no not in TARGET_RACES:
            continue
        horse_value = first_present(row, ["horse", "horse_raw", "horse_rated", "runner", "selection_name"])
        key_value = first_present(row, ["horse_key", "_horse_key", "horse_match_key_v5_2"])
        if not horse_value and not key_value:
            continue
        indexed[row_key(race_date, track, race_no, horse_value, key_value)].append(row)
    return indexed


def load_unconfirmed_candidate_rows() -> list[dict[str, str]]:
    _, rows = read_csv(CANDIDATE)
    unconfirmed = [
        row
        for row in rows
        if clean(row.get("race_date")) == TARGET_DATE
        and normalise_track(row.get("track")) == TARGET_TRACK
        and clean_race_no(row.get("race_no")) in TARGET_RACES
        and clean(row.get("result_status")) == "NON_RUNNER_UNCONFIRMED"
    ]
    return sorted(unconfirmed, key=lambda row: (int(clean_race_no(row.get("race_no"))), horse_key(row.get("horse_key") or row.get("horse"))))


def candidate_sources() -> list[Path]:
    base = [
        SPORTSBET_FULL_DAY,
        CURRENT_PROJECTION,
        RESULTS_TRUTH_LOOP,
        PRICE_TRUTH,
        DATA / "edgeiq_vic_live_fields_synced.csv",
        DATA / "edgeiq_vic_scratchings_diagnostics.csv",
        DATA / "edgeiq_results_auto_settlement.csv",
        DATA / "race_card_active.csv",
        DATA / "race_card_report.csv",
        DATA / "rated_market_v2.csv",
        DATA / "edgeiq_market_truth_engine_v3.csv",
    ]
    discovered = list(DATA.glob("*scratch*.csv"))
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in base + discovered:
        if path.exists() and path not in seen:
            deduped.append(path)
            seen.add(path)
    return deduped


def value_truthy(value: object) -> bool:
    text = normalise_text(value)
    return text in {"TRUE", "YES", "Y", "1", "SCR", "SCRATCHED", "WITHDRAWN", "LATEWITHDRAWAL"}


def is_positive_scratch(row: dict[str, str]) -> tuple[bool, str]:
    for column in row:
        column_key = normalise_text(column)
        value = clean(row.get(column))
        value_key = normalise_text(value)
        if not value_key:
            continue
        if column_key in {"IS_SCRATCHED", "SCRATCHED"} and value_truthy(value):
            return True, f"{column}={value}"
        if "SCRATCH" in column_key and re.search(r"\bSCRATCH|SCRATCHED|LATE\s*SCR", value_key):
            return True, f"{column}={value}"
        if column_key in {"RUNNER_STATUS", "SELECTION_STATUS", "STATUS", "STATUS_CODE", "RESULT_STATUS"}:
            if re.search(r"\bSCRATCH|SCRATCHED|LATE\s*SCR", value_key):
                return True, f"{column}={value}"
    return False, ""


def is_positive_non_runner(row: dict[str, str]) -> tuple[bool, str]:
    for column in row:
        column_key = normalise_text(column)
        value = clean(row.get(column))
        value_key = normalise_text(value)
        if not value_key:
            continue
        if column_key in {"RUNNER_STATUS", "SELECTION_STATUS", "STATUS", "STATUS_CODE", "RESULT_STATUS", "MATCH_STATUS", "NOTES"} or "RUNNER" in column_key:
            if re.search(r"\bNON\s*RUNNER\b|\bWITHDRAWN\b|\bNOT\s*A\s*STARTER\b|\bDID\s*NOT\s*START\b|\bDNS\b", value_key):
                return True, f"{column}={value}"
    return False, ""


def source_evidence(path: Path, rows: list[dict[str, str]]) -> tuple[list[str], list[str], list[str]]:
    scratch_hits: list[str] = []
    non_runner_hits: list[str] = []
    compact_evidence: list[str] = []
    for row in rows:
        scratch_found, scratch_reason = is_positive_scratch(row)
        non_runner_found, non_runner_reason = is_positive_non_runner(row)
        if scratch_found:
            scratch_hits.append(f"{path.name}:{scratch_reason}")
        if non_runner_found:
            non_runner_hits.append(f"{path.name}:{non_runner_reason}")

        evidence_columns = [
            "is_scratched",
            "scratched",
            "scratch_status",
            "scratching_details",
            "runner_status",
            "selection_status",
            "status_code",
            "result_status",
            "market_status",
            "notes",
        ]
        values = []
        for column in evidence_columns:
            value = clean(row.get(column))
            if value:
                values.append(f"{column}={value}")
        if values:
            compact_evidence.append(f"{path.name}:" + "; ".join(values))
    return scratch_hits, non_runner_hits, compact_evidence


def classify(
    *,
    present_in_ra: bool,
    present_in_price_truth: bool,
    scratch_hits: list[str],
    non_runner_hits: list[str],
) -> tuple[str, str, str, str]:
    if scratch_hits:
        return "CONFIRMED_SCRATCHED", "TRUE", "", "Positive local scratching indicator found."
    if non_runner_hits:
        return "CONFIRMED_NON_RUNNER", "TRUE", "", "Positive local non-runner indicator found."
    if not present_in_ra and present_in_price_truth:
        return (
            "INFERRED_NON_RUNNER_FROM_RA_ABSENCE",
            "FALSE",
            "NEEDS_MANUAL_SCRATCHING_CONFIRMATION",
            "Runner is in price-truth/candidate field but absent from RA final result rows; no positive scratching or non-runner flag was found.",
        )
    return (
        "STILL_UNCONFIRMED",
        "FALSE",
        "NEEDS_MANUAL_SCRATCHING_CONFIRMATION",
        "No positive scratching/non-runner indicator and RA absence could not be safely interpreted.",
    )


def audit_row(section: str, metric: str, value: object, source_path: Path | str = "", notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "source_path": str(source_path),
        "notes": notes,
        "built_at": now_utc(),
    }


def build_confirmation_rows() -> tuple[list[dict[str, object]], list[Path]]:
    unconfirmed_rows = load_unconfirmed_candidate_rows()
    source_paths = candidate_sources()
    source_indexes = {path: index_file(path) for path in source_paths}
    ra_normalised_index = index_file(RA_NORMALISED)
    ra_raw_index = index_file(RA_RAW)
    sportsbet_index = index_file(SPORTSBET_FULL_DAY)
    projection_index = index_file(CURRENT_PROJECTION)
    truth_loop_index = index_file(RESULTS_TRUTH_LOOP)
    price_truth_index = index_file(PRICE_TRUTH)

    output_rows: list[dict[str, object]] = []
    for row in unconfirmed_rows:
        key = row_key(row.get("race_date"), row.get("track"), row.get("race_no"), row.get("horse"), row.get("horse_key"))
        sportsbet_rows = sportsbet_index.get(key, [])
        truth_loop_rows = truth_loop_index.get(key, [])
        scratch_hits: list[str] = []
        non_runner_hits: list[str] = []
        evidence: list[str] = []
        checked_sources: list[str] = []

        for path in source_paths:
            checked_sources.append(path.name)
            rows = source_indexes[path].get(key, [])
            local_scratch, local_non_runner, local_evidence = source_evidence(path, rows)
            scratch_hits.extend(local_scratch)
            non_runner_hits.extend(local_non_runner)
            evidence.extend(local_evidence)

        present_in_ra = key in ra_normalised_index
        present_in_price_truth = key in price_truth_index or bool(row)
        classification, settlement_safe, settlement_blocker, notes = classify(
            present_in_ra=present_in_ra,
            present_in_price_truth=present_in_price_truth,
            scratch_hits=scratch_hits,
            non_runner_hits=non_runner_hits,
        )

        sportsbet_first = sportsbet_rows[0] if sportsbet_rows else {}
        truth_loop_first = truth_loop_rows[0] if truth_loop_rows else {}
        output_rows.append(
            {
                "race_date": clean(row.get("race_date")),
                "track": normalise_track(row.get("track")),
                "race_no": clean_race_no(row.get("race_no")),
                "horse": clean(row.get("horse")),
                "horse_key": horse_key(row.get("horse_key")) or horse_key(row.get("horse")),
                "classification": classification,
                "settlement_safe": settlement_safe,
                "settlement_blocker": settlement_blocker,
                "present_in_price_truth": "TRUE" if present_in_price_truth else "FALSE",
                "present_in_ra_final_results": "TRUE" if present_in_ra else "FALSE",
                "ra_raw_present": "TRUE" if key in ra_raw_index else "FALSE",
                "present_in_sportsbet_full_day": "TRUE" if sportsbet_rows else "FALSE",
                "sportsbet_is_scratched": first_present(sportsbet_first, ["is_scratched"]),
                "sportsbet_runner_status": first_present(sportsbet_first, ["runner_status"]),
                "sportsbet_selection_status": first_present(sportsbet_first, ["selection_status"]),
                "sportsbet_status_code": first_present(sportsbet_first, ["status_code"]),
                "present_in_current_projection": "TRUE" if key in projection_index else "FALSE",
                "present_in_results_truth_loop": "TRUE" if truth_loop_rows else "FALSE",
                "truth_loop_result_status": first_present(truth_loop_first, ["result_status"]),
                "local_scratch_flag_found": "YES" if scratch_hits else "NO",
                "local_scratch_source": " | ".join(scratch_hits),
                "local_non_runner_flag_found": "YES" if non_runner_hits else "NO",
                "local_non_runner_source": " | ".join(non_runner_hits),
                "sources_checked": " | ".join(checked_sources),
                "evidence": " || ".join(evidence),
                "notes": notes,
            }
        )
    return output_rows, source_paths


def build_audit(rows: list[dict[str, object]], source_paths: list[Path]) -> list[dict[str, object]]:
    classifications = Counter(str(row.get("classification", "")) for row in rows)
    settlement_safe_count = sum(1 for row in rows if str(row.get("settlement_safe")) == "TRUE")
    settlement_blocked_count = len(rows) - settlement_safe_count
    positive_scratch_source_count = len(
        {
            part.split(":", 1)[0]
            for row in rows
            for part in str(row.get("local_scratch_source", "")).split(" | ")
            if part
        }
    )
    if rows and settlement_blocked_count == 0:
        recommendation = "READY_TO_BUILD_SETTLEMENT_WITH_NON_RUNNER_STATUS"
    else:
        recommendation = "NEEDS_MANUAL_SCRATCHING_CONFIRMATION"

    audit = [
        audit_row("input", "unconfirmed_input_rows", len(rows), CANDIDATE),
        audit_row("classification", "confirmed_scratched_count", classifications.get("CONFIRMED_SCRATCHED", 0), CONFIRMATION_OUT),
        audit_row("classification", "confirmed_non_runner_count", classifications.get("CONFIRMED_NON_RUNNER", 0), CONFIRMATION_OUT),
        audit_row("classification", "inferred_ra_absence_count", classifications.get("INFERRED_NON_RUNNER_FROM_RA_ABSENCE", 0), CONFIRMATION_OUT),
        audit_row("classification", "still_unconfirmed_count", classifications.get("STILL_UNCONFIRMED", 0), CONFIRMATION_OUT),
        audit_row("sources", "sources_checked", len(source_paths), "", " | ".join(str(path) for path in source_paths)),
        audit_row("sources", "positive_scratching_source_count", positive_scratch_source_count, CONFIRMATION_OUT),
        audit_row("settlement", "settlement_safe_count", settlement_safe_count, CONFIRMATION_OUT),
        audit_row("settlement", "settlement_blocked_count", settlement_blocked_count, CONFIRMATION_OUT),
        audit_row("recommendation", "recommendation", recommendation, AUDIT_OUT),
    ]
    for classification, count in sorted(classifications.items()):
        audit.append(audit_row("classification_count", classification, count, CONFIRMATION_OUT))
    for race_no, count in sorted(Counter(str(row.get("race_no")) for row in rows).items(), key=lambda item: int(item[0])):
        audit.append(audit_row("race_count", f"R{race_no}", count, CONFIRMATION_OUT))
    return audit


def main() -> None:
    rows, sources = build_confirmation_rows()
    audit_rows = build_audit(rows, sources)

    write_csv(CONFIRMATION_OUT, rows, DETAIL_COLUMNS)
    write_csv(AUDIT_OUT, audit_rows, AUDIT_COLUMNS)

    print("=" * 96)
    print("RACING AUSTRALIA NON-RUNNER CONFIRMATION V1 - REVIEW ONLY")
    print("=" * 96)
    for row in audit_rows:
        if row["section"] in {"input", "classification", "sources", "settlement", "recommendation"}:
            print(f"{row['section']},{row['metric']},{row['value']},{row['notes']}")
    print(f"wrote: {CONFIRMATION_OUT}")
    print(f"wrote: {AUDIT_OUT}")
    print("=" * 96)


if __name__ == "__main__":
    main()
