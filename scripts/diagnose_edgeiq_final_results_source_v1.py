from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PRICE_TRUTH = DATA / "edgeiq_price_truth_history_v1.csv"
OUTPUT = DATA / "edgeiq_final_results_source_diagnostic_v1.csv"
SUMMARY = DATA / "edgeiq_final_results_source_diagnostic_v1_summary.csv"

TARGET_DATE = "2026-05-31"
TARGET_TRACK = "SANDOWN LAKESIDE"
TARGET_RACES = {str(number) for number in range(1, 9)}

EXPLICIT_INPUTS = [
    DATA / "edgeiq_results_truth_loop.csv",
    DATA / "race_results.csv",
    DATA / "results_history.csv",
    DATA / "ra_horse_runs.csv",
    DATA / "horse_runs_ra.csv",
    DATA / "run_context.csv",
    PRICE_TRUTH,
]

FILENAME_TOKENS = [
    "result",
    "results",
    "finish",
    "placing",
    "position",
    "winner",
    "settlement",
    "truth",
    "sp",
    "starting_price",
]

DATE_COLUMNS = ["race_date", "date_k", "date", "run_date", "meeting_date", "event_date"]
TRACK_COLUMNS = ["track", "track_name", "meeting_name", "venue", "track_code"]
RACE_NO_COLUMNS = ["race_no", "race_k", "race_number", "race"]
HORSE_COLUMNS = ["horse", "horse_name", "runner", "runner_name", "selection_name"]
HORSE_KEY_COLUMNS = ["horse_key", "horse_k", "horse_clean", "canonical_runner_key"]
FINISH_COLUMNS = ["finish_position", "finish_pos_num", "finish_pos", "finish", "placing", "position"]
WINNER_COLUMNS = ["winner_flag", "won", "winner", "is_winner", "result"]
SP_COLUMNS = ["sp_num", "sp", "starting_price", "price", "price_raw", "starting_price_raw"]
STATUS_COLUMNS = ["result_status", "result", "result_resolution_status", "safe_for_model_validation"]

DERIVED_NON_RESULT_SOURCE_TOKENS = [
    "audit",
    "diagnostic",
    "summary",
    "health",
    "readiness",
    "dedupe",
    "pipeline_status",
    "snapshot_count_mismatch",
    "comparison",
    "overlay",
    "fair_prices",
    "sportsbet",
    "live_market",
    "market_tape",
    "terminal_feed",
    "meeting_universe",
    "race_fields",
    "speed_map",
]

DIAGNOSTIC_COLUMNS = [
    "file_path",
    "file_name",
    "row_count",
    "columns_found",
    "relevant_columns_found",
    "has_race_date",
    "race_date_column",
    "has_track",
    "track_column",
    "has_race_no",
    "race_no_column",
    "has_horse",
    "horse_column",
    "horse_key_column",
    "has_finish_position",
    "finish_position_column",
    "has_winner_flag",
    "winner_column",
    "has_sp",
    "sp_column",
    "status_column",
    "rows_matching_sandown_lakeside_2026_05_31",
    "rows_matching_r1_r8",
    "rows_matching_current_87_horses",
    "unique_current_horses_matched",
    "current_horse_rows_with_finish_position",
    "current_horse_rows_with_winner_flag",
    "current_horse_rows_with_sp",
    "final_settlement_ready_rows",
    "candidate_score",
    "source_status",
    "failure_reason",
    "built_at",
]

SUMMARY_COLUMNS = [
    "section",
    "metric",
    "value",
    "source_path",
    "notes",
    "built_at",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def has_text(value: object) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and text.lower() != "nan"


def norm(value: object) -> str:
    if not has_text(value):
        return ""
    return " ".join(str(value).upper().strip().split())


def key_text(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", norm(value))


def horse_key(value: object) -> str:
    if not has_text(value):
        return ""
    text = re.sub(r"\([^)]*\)", "", str(value))
    return key_text(text)


def clean_race_no(value: object) -> str:
    if not has_text(value):
        return ""
    text = str(value).strip()
    text = text[:-2] if text.endswith(".0") else text
    match = re.search(r"\d+", text)
    return str(int(match.group(0))) if match else ""


def parse_date(value: object) -> str:
    if not has_text(value):
        return ""
    text = str(value).strip()
    iso_match = re.match(r"^(\d{4}-\d{2}-\d{2})", text)
    if iso_match:
        return iso_match.group(1)
    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%d%b%y",
        "%d%b%Y",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def parse_number(value: object) -> str:
    if not has_text(value):
        return ""
    text = str(value).strip()
    if text.upper() in {"SCR", "SCRATCHED", "PENDING", "N/A", "NA", "-"}:
        return ""
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return ""
    number = float(match.group(0))
    return str(int(number)) if number.is_integer() else f"{number:.4f}".rstrip("0").rstrip(".")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_header(path: Path) -> list[str]:
    try:
        with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
            reader = csv.reader(handle)
            return next(reader, [])
    except OSError:
        return []


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def first_existing(columns: Iterable[str], candidates: list[str]) -> str:
    lower_to_real = {column.lower(): column for column in columns}
    for candidate in candidates:
        real = lower_to_real.get(candidate.lower())
        if real:
            return real
    return ""


def relevant_columns(columns: list[str]) -> list[str]:
    relevant_tokens = {
        *DATE_COLUMNS,
        *TRACK_COLUMNS,
        *RACE_NO_COLUMNS,
        *HORSE_COLUMNS,
        *HORSE_KEY_COLUMNS,
        *FINISH_COLUMNS,
        *WINNER_COLUMNS,
        *SP_COLUMNS,
        *STATUS_COLUMNS,
    }
    relevant: list[str] = []
    for column in columns:
        lower = column.lower()
        if lower in relevant_tokens or any(token in lower for token in FILENAME_TOKENS):
            relevant.append(column)
    return relevant


def load_target_horses() -> tuple[set[str], dict[str, set[str]], int]:
    if not PRICE_TRUTH.exists():
        raise FileNotFoundError(f"Missing price truth history: {PRICE_TRUTH}")
    columns, rows = read_rows(PRICE_TRUTH)
    required = {"race_date", "track", "race_no", "horse", "horse_key"}
    missing = sorted(required.difference(columns))
    if missing:
        raise ValueError(f"Price truth history missing required columns: {missing}")

    target_keys: set[str] = set()
    race_to_horses: dict[str, set[str]] = {race: set() for race in TARGET_RACES}
    for row in rows:
        if (
            parse_date(row.get("race_date", "")) == TARGET_DATE
            and key_text(row.get("track", "")) == key_text(TARGET_TRACK)
            and clean_race_no(row.get("race_no", "")) in TARGET_RACES
        ):
            key = horse_key(row.get("horse_key", "")) or horse_key(row.get("horse", ""))
            race = clean_race_no(row.get("race_no", ""))
            if key:
                target_keys.add(key)
                race_to_horses.setdefault(race, set()).add(key)
    return target_keys, race_to_horses, len(target_keys)


def candidate_by_filename(path: Path) -> bool:
    name = path.name.lower()
    return any(token in name for token in FILENAME_TOKENS)


def candidate_by_header(columns: list[str]) -> bool:
    lower_columns = [column.lower() for column in columns]
    return any(
        any(token in column for token in FILENAME_TOKENS)
        for column in lower_columns
    )


def derived_non_result_source_reason(path: Path) -> str:
    name = path.name.lower()
    if path == PRICE_TRUTH:
        return "Price truth history is the settlement target, not an independent final-results source."
    if path.name.lower() == OUTPUT.name.lower() or path.name.lower() == SUMMARY.name.lower():
        return "This diagnostic output is not an independent final-results source."
    for token in DERIVED_NON_RESULT_SOURCE_TOKENS:
        if token in name:
            return f"Derived/research file contains token '{token}', so it is audited but excluded from final-source ranking."
    return ""


def discover_candidate_files() -> tuple[list[Path], list[Path]]:
    found: list[Path] = []
    missing: list[Path] = []

    for path in EXPLICIT_INPUTS:
        if path.exists():
            found.append(path)
        else:
            missing.append(path)

    for path in DATA.glob("*.csv"):
        if path in found:
            continue
        columns = read_header(path)
        if candidate_by_filename(path) or candidate_by_header(columns):
            found.append(path)

    return sorted(found, key=lambda item: item.name.lower()), missing


def infer_won(finish_position: str, winner_raw: str, horse: str) -> str:
    if finish_position == "1":
        return "TRUE"
    winner_text = norm(winner_raw)
    if winner_text in {"YES", "TRUE", "WON", "WIN", "WINNER", "1"}:
        return "TRUE"
    if winner_text in {"NO", "FALSE", "LOST", "LOSE", "0"}:
        return "FALSE"
    if winner_text and horse and horse_key(winner_text) == horse_key(horse):
        return "TRUE"
    if finish_position:
        return "FALSE"
    return ""


def diagnose_file(
    path: Path,
    target_horses: set[str],
    race_to_horses: dict[str, set[str]],
    expected_target_horses: int,
) -> dict[str, object]:
    try:
        columns, rows = read_rows(path)
    except Exception as exc:  # noqa: BLE001 - diagnostic should report source read failures.
        return {
            "file_path": rel(path),
            "file_name": path.name,
            "row_count": 0,
            "columns_found": "",
            "relevant_columns_found": "",
            "has_race_date": "FALSE",
            "race_date_column": "",
            "has_track": "FALSE",
            "track_column": "",
            "has_race_no": "FALSE",
            "race_no_column": "",
            "has_horse": "FALSE",
            "horse_column": "",
            "horse_key_column": "",
            "has_finish_position": "FALSE",
            "finish_position_column": "",
            "has_winner_flag": "FALSE",
            "winner_column": "",
            "has_sp": "FALSE",
            "sp_column": "",
            "status_column": "",
            "rows_matching_sandown_lakeside_2026_05_31": 0,
            "rows_matching_r1_r8": 0,
            "rows_matching_current_87_horses": 0,
            "unique_current_horses_matched": 0,
            "current_horse_rows_with_finish_position": 0,
            "current_horse_rows_with_winner_flag": 0,
            "current_horse_rows_with_sp": 0,
            "final_settlement_ready_rows": 0,
            "candidate_score": 0,
            "source_status": "LOAD_ERROR",
            "failure_reason": str(exc),
            "built_at": now_utc(),
        }

    date_col = first_existing(columns, DATE_COLUMNS)
    track_col = first_existing(columns, TRACK_COLUMNS)
    race_no_col = first_existing(columns, RACE_NO_COLUMNS)
    horse_col = first_existing(columns, HORSE_COLUMNS)
    horse_key_col = first_existing(columns, HORSE_KEY_COLUMNS)
    finish_col = first_existing(columns, FINISH_COLUMNS)
    winner_col = first_existing(columns, WINNER_COLUMNS)
    sp_col = first_existing(columns, SP_COLUMNS)
    status_col = first_existing(columns, STATUS_COLUMNS)
    derived_reason = derived_non_result_source_reason(path)

    has_key_schema = bool(date_col and track_col and race_no_col and (horse_col or horse_key_col))

    sandown_rows = 0
    r1_r8_rows = 0
    current_rows = 0
    current_unique_horses: set[str] = set()
    finish_rows = 0
    winner_rows = 0
    sp_rows = 0
    settlement_ready_rows = 0

    if has_key_schema:
        for row in rows:
            race_date = parse_date(row.get(date_col, ""))
            track_key = key_text(row.get(track_col, ""))
            race_no = clean_race_no(row.get(race_no_col, ""))
            if race_date == TARGET_DATE and track_key == key_text(TARGET_TRACK):
                sandown_rows += 1
                if race_no in TARGET_RACES:
                    r1_r8_rows += 1
                    raw_horse = row.get(horse_col, "") if horse_col else row.get(horse_key_col, "")
                    key = horse_key(row.get(horse_key_col, "")) if horse_key_col else ""
                    if not key:
                        key = horse_key(raw_horse)
                    race_specific_match = key in race_to_horses.get(race_no, set())
                    broad_horse_match = key in target_horses
                    if race_specific_match or broad_horse_match:
                        current_rows += 1
                        if key:
                            current_unique_horses.add(key)
                        finish = parse_number(row.get(finish_col, "")) if finish_col else ""
                        winner = infer_won(finish, row.get(winner_col, "") if winner_col else "", raw_horse)
                        sp = parse_number(row.get(sp_col, "")) if sp_col else ""
                        finish_rows += 1 if has_text(finish) else 0
                        winner_rows += 1 if has_text(winner) else 0
                        sp_rows += 1 if has_text(sp) else 0
                        settlement_ready_rows += 1 if has_text(finish) and has_text(winner) else 0

    if derived_reason:
        source_status = "DERIVED_OR_REFERENCE_FILE_NOT_FINAL_SOURCE"
        failure_reason = derived_reason
    elif not has_key_schema:
        source_status = "NOT_MATCHABLE"
        failure_reason = "Missing date/track/race/horse key fields."
    elif current_rows == 0:
        source_status = "NO_TARGET_MATCH"
        if sandown_rows == 0:
            failure_reason = "No rows for 2026-05-31 Sandown Lakeside."
        elif r1_r8_rows == 0:
            failure_reason = "Rows match date/track but not races R1-R8."
        else:
            failure_reason = "Rows match target race context but not current 87 horse keys."
    elif settlement_ready_rows >= expected_target_horses:
        source_status = "FINAL_RESULTS_SOURCE_FOUND"
        failure_reason = ""
    elif finish_rows or winner_rows:
        source_status = "RESULTS_SOURCE_NEEDS_NORMALISATION"
        failure_reason = "Some final fields exist, but coverage is incomplete for the current 87 horses."
    elif sp_rows:
        source_status = "SP_ONLY_PARTIAL_SOURCE"
        failure_reason = "Matches current horses but has SP only; finish positions and winner flags are blank."
    else:
        source_status = "PENDING_OR_BLANK_RESULT_FIELDS"
        failure_reason = "Matches current horses but final result fields are blank."

    raw_candidate_score = (
        settlement_ready_rows * 1000
        + finish_rows * 100
        + winner_rows * 100
        + sp_rows * 10
        + current_rows
        + r1_r8_rows
    )
    candidate_score = 0 if derived_reason else raw_candidate_score

    return {
        "file_path": rel(path),
        "file_name": path.name,
        "row_count": len(rows),
        "columns_found": "|".join(columns),
        "relevant_columns_found": "|".join(relevant_columns(columns)),
        "has_race_date": "TRUE" if bool(date_col) else "FALSE",
        "race_date_column": date_col,
        "has_track": "TRUE" if bool(track_col) else "FALSE",
        "track_column": track_col,
        "has_race_no": "TRUE" if bool(race_no_col) else "FALSE",
        "race_no_column": race_no_col,
        "has_horse": "TRUE" if bool(horse_col or horse_key_col) else "FALSE",
        "horse_column": horse_col,
        "horse_key_column": horse_key_col,
        "has_finish_position": "TRUE" if bool(finish_col) else "FALSE",
        "finish_position_column": finish_col,
        "has_winner_flag": "TRUE" if bool(winner_col) else "FALSE",
        "winner_column": winner_col,
        "has_sp": "TRUE" if bool(sp_col) else "FALSE",
        "sp_column": sp_col,
        "status_column": status_col,
        "rows_matching_sandown_lakeside_2026_05_31": sandown_rows,
        "rows_matching_r1_r8": r1_r8_rows,
        "rows_matching_current_87_horses": current_rows,
        "unique_current_horses_matched": len(current_unique_horses),
        "current_horse_rows_with_finish_position": finish_rows,
        "current_horse_rows_with_winner_flag": winner_rows,
        "current_horse_rows_with_sp": sp_rows,
        "final_settlement_ready_rows": settlement_ready_rows,
        "candidate_score": candidate_score,
        "source_status": source_status,
        "failure_reason": failure_reason,
        "built_at": now_utc(),
    }


def summary_row(
    section: str,
    metric: str,
    value: object,
    source_path: str = "",
    notes: str = "",
) -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "source_path": source_path,
        "notes": notes,
        "built_at": now_utc(),
    }


def build_summary(
    diagnostics: list[dict[str, object]],
    missing_inputs: list[Path],
    target_horse_count: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    rankable = [
        row
        for row in diagnostics
        if row["source_status"] != "DERIVED_OR_REFERENCE_FILE_NOT_FINAL_SOURCE"
    ]
    sorted_candidates = sorted(
        rankable,
        key=lambda row: (
            int(row["final_settlement_ready_rows"]),
            int(row["current_horse_rows_with_finish_position"]),
            int(row["current_horse_rows_with_winner_flag"]),
            int(row["unique_current_horses_matched"]),
            int(row["candidate_score"]),
        ),
        reverse=True,
    )
    best = sorted_candidates[0] if sorted_candidates else {}

    final_sources = [row for row in rankable if row["source_status"] == "FINAL_RESULTS_SOURCE_FOUND"]
    normalisation_sources = [
        row for row in rankable if row["source_status"] == "RESULTS_SOURCE_NEEDS_NORMALISATION"
    ]
    sp_only_sources = [row for row in rankable if row["source_status"] == "SP_ONLY_PARTIAL_SOURCE"]

    if final_sources:
        status = "FINAL_RESULTS_SOURCE_FOUND"
        recommendation = final_sources[0]["file_path"]
        reason = "A source matched the current 87 horses with finish positions and winner flags."
    elif normalisation_sources:
        status = "RESULTS_SOURCE_NEEDS_NORMALISATION"
        recommendation = normalisation_sources[0]["file_path"]
        reason = "At least one source has partial final result fields but not complete settlement coverage."
    else:
        status = "NO_FINAL_RESULTS_SOURCE"
        recommendation = best.get("file_path", "")
        if sp_only_sources:
            reason = "Best matched sources provide SP only; finish positions and winner flags remain blank."
        elif best:
            reason = str(best.get("failure_reason", "No candidate source produced final settlement fields."))
        else:
            reason = "No candidate result files found."

    rows.extend(
        [
            summary_row("target", "target_date", TARGET_DATE),
            summary_row("target", "target_track", TARGET_TRACK),
            summary_row("target", "target_races", "R1-R8"),
            summary_row("target", "current_unique_horses", target_horse_count, rel(PRICE_TRUTH)),
            summary_row("discovery", "candidate_result_files_discovered", len(diagnostics)),
            summary_row("discovery", "rankable_result_source_candidates", len(rankable)),
            summary_row("discovery", "explicit_inputs_missing", len(missing_inputs)),
            summary_row("status", "status", status),
            summary_row("recommendation", "best_source_recommendation", recommendation),
            summary_row("recommendation", "reason_current_sources_are_failing", reason),
        ]
    )

    for path in missing_inputs:
        rows.append(summary_row("missing_input", path.name, "MISSING", str(path)))

    for source_status, count in sorted(
        {
            status_name: sum(1 for row in diagnostics if row["source_status"] == status_name)
            for status_name in {row["source_status"] for row in diagnostics}
        }.items()
    ):
        rows.append(summary_row("source_status_counts", source_status, count))

    if best:
        for metric in [
            "file_path",
            "row_count",
            "rows_matching_sandown_lakeside_2026_05_31",
            "rows_matching_r1_r8",
            "rows_matching_current_87_horses",
            "unique_current_horses_matched",
            "current_horse_rows_with_finish_position",
            "current_horse_rows_with_winner_flag",
            "current_horse_rows_with_sp",
            "final_settlement_ready_rows",
            "source_status",
            "failure_reason",
        ]:
            rows.append(summary_row("best_candidate", metric, best.get(metric, ""), str(best.get("file_path", ""))))

    top_candidates = sorted_candidates[:25]
    for rank, row in enumerate(top_candidates, start=1):
        rows.append(
            summary_row(
                "top_candidates",
                str(rank),
                row["file_path"],
                str(row["file_path"]),
                (
                    f"status={row['source_status']}; rows={row['row_count']}; "
                    f"sandown={row['rows_matching_sandown_lakeside_2026_05_31']}; "
                    f"r1_r8={row['rows_matching_r1_r8']}; current={row['rows_matching_current_87_horses']}; "
                    f"finish={row['current_horse_rows_with_finish_position']}; "
                    f"winner={row['current_horse_rows_with_winner_flag']}; sp={row['current_horse_rows_with_sp']}"
                ),
            )
        )

    return rows


def main() -> None:
    target_horses, race_to_horses, target_horse_count = load_target_horses()
    candidate_files, missing_inputs = discover_candidate_files()
    diagnostics = [
        diagnose_file(path, target_horses, race_to_horses, target_horse_count)
        for path in candidate_files
    ]
    summary = build_summary(diagnostics, missing_inputs, target_horse_count)

    write_csv(OUTPUT, diagnostics, DIAGNOSTIC_COLUMNS)
    write_csv(SUMMARY, summary, SUMMARY_COLUMNS)

    print("=" * 96)
    print("EDGEIQ FINAL RESULTS SOURCE DIAGNOSTIC V1 - NO SETTLEMENT")
    print("=" * 96)
    print(f"wrote: {OUTPUT}")
    print(f"wrote: {SUMMARY}")
    print("")
    for row in summary:
        if row["section"] in {"target", "discovery", "status", "recommendation", "best_candidate"}:
            print(f"{row['section']},{row['metric']},{row['value']},{row['notes']}")
    print("=" * 96)


if __name__ == "__main__":
    main()
