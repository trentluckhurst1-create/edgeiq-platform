from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUTPUTS = ROOT / "outputs"

TRUTH_HISTORY = DATA / "edgeiq_price_truth_history_v1.csv"
TRUTH_LOOP = DATA / "edgeiq_results_truth_loop.csv"
OUTPUT = DATA / "edgeiq_price_truth_result_readiness_v1.csv"
SUMMARY = DATA / "edgeiq_price_truth_result_readiness_v1_summary.csv"

EXPLICIT_SOURCE_PATHS = [
    TRUTH_LOOP,
    DATA / "race_results.csv",
    DATA / "results_history.csv",
    DATA / "ra_horse_runs.csv",
    DATA / "horse_runs_ra.csv",
]

KNOWN_EXTRA_SOURCE_NAMES = [
    "edgeiq_canonical_results_truth_v1.csv",
    "results_history_clean.csv",
    "edgeiq_results_master.csv",
    "master_result_events.csv",
    "ra_calendar_official_results.csv",
    "edgeiq_ra_historical_results_harvest_v1.csv",
    "edgeiq_official_results_backfill_v1.csv",
    "edgeiq_results_auto_settlement.csv",
    "edgeiq_market_truth_engine_v3.csv",
    "edgeiq_result_reconciliation.csv",
    "results_enriched.csv",
    "results_audit.csv",
    "results_race_detail.csv",
    "results_review.csv",
    "results_tab_feed.csv",
    "rated_results_history.csv",
    "edgeiq_settlement_board.csv",
]

OUTPUT_SOURCE_NAMES = [
    "run_context.csv",
    "run_context_FIXED.csv",
    "ra_horse_runs.csv",
    "horse_runs_ra.csv",
]

SOURCE_PRIORITY = {
    "edgeiq_canonical_results_truth_v1.csv": 1,
    "results_history_clean.csv": 2,
    "results_history.csv": 3,
    "race_results.csv": 4,
    "master_result_events.csv": 5,
    "ra_calendar_official_results.csv": 6,
    "edgeiq_ra_historical_results_harvest_v1.csv": 7,
    "edgeiq_official_results_backfill_v1.csv": 8,
    "results_enriched.csv": 9,
    "results_audit.csv": 10,
    "edgeiq_results_auto_settlement.csv": 11,
    "edgeiq_results_truth_loop.csv": 90,
    "horse_runs_ra.csv": 100,
    "ra_horse_runs.csv": 101,
    "run_context.csv": 102,
    "run_context_FIXED.csv": 103,
}

DATE_COLUMNS = ["race_date", "date_k", "date", "run_date", "meeting_date", "event_date"]
TRACK_COLUMNS = ["track", "track_name", "meeting_name", "venue", "track_code"]
RACE_NO_COLUMNS = ["race_no", "race_k", "race_number", "race"]
HORSE_KEY_COLUMNS = ["horse_key", "horse_k", "horse_clean", "canonical_runner_key"]
HORSE_COLUMNS = ["horse", "horse_name", "runner", "runner_name", "selection_name"]
FINISH_COLUMNS = ["finish_position", "finish_pos_num", "finish_pos", "finish", "placing", "position"]
WIN_COLUMNS = ["winner_flag", "won", "winner", "is_winner", "result"]
SP_COLUMNS = ["sp_num", "sp", "starting_price", "price", "price_raw", "starting_price_raw"]
STATUS_COLUMNS = ["result_status", "result", "result_resolution_status", "safe_for_model_validation"]

TRUTH_REQUIRED_COLUMNS = {
    "snapshot_timestamp",
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
}

READINESS_COLUMNS = [
    "snapshot_timestamp",
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "truth_match_key",
    "truth_result_status",
    "truth_finish_position",
    "truth_won",
    "truth_starting_price",
    "result_readiness_status",
    "match_method",
    "matched_source_count",
    "matched_row_count",
    "matched_sources",
    "duplicate_result_matches",
    "duplicate_sources",
    "ambiguous_result_match_flag",
    "best_result_source",
    "best_result_status",
    "best_finish_position",
    "best_won",
    "best_starting_price",
    "finish_position_populated_flag",
    "winner_flag_populated_flag",
    "sp_populated_flag",
    "readiness_reason",
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


def clean_race_no(value: object) -> str:
    if not has_text(value):
        return ""
    text = str(value).strip()
    text = text[:-2] if text.endswith(".0") else text
    match = re.search(r"\d+", text)
    return str(int(match.group(0))) if match else ""


def parse_numeric(value: object) -> str:
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


def bool_text(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def first_existing(columns: Iterable[str], candidates: list[str]) -> str:
    lower_to_real = {column.lower(): column for column in columns}
    for candidate in candidates:
        real = lower_to_real.get(candidate.lower())
        if real:
            return real
    return ""


def source_priority(source_id: str) -> int:
    return SOURCE_PRIORITY.get(Path(source_id).name, 200)


def source_id(path: Path) -> str:
    return rel(path)


def should_exclude_discovered(path: Path) -> bool:
    name = path.name.lower()
    if name in {
        TRUTH_HISTORY.name.lower(),
        OUTPUT.name.lower(),
        SUMMARY.name.lower(),
    }:
        return True
    blocked_tokens = [
        "audit",
        "diagnostic",
        "summary",
        "health",
        "readiness",
        "dedupe",
        "comparison",
        "overlay",
        "fair_prices",
        "snapshot",
    ]
    return any(token in name for token in blocked_tokens)


def discover_sources() -> tuple[list[Path], list[Path]]:
    found: list[Path] = []
    missing: list[Path] = []

    for path in EXPLICIT_SOURCE_PATHS:
        if path.exists():
            found.append(path)
        else:
            missing.append(path)

    for name in KNOWN_EXTRA_SOURCE_NAMES:
        path = DATA / name
        if path.exists() and path not in found and not should_exclude_discovered(path):
            found.append(path)

    for path in DATA.glob("*.csv"):
        name = path.name.lower()
        if (
            ("result" in name or "settlement" in name or "truth_loop" in name)
            and path not in found
            and not should_exclude_discovered(path)
        ):
            found.append(path)

    if OUTPUTS.exists():
        for name in OUTPUT_SOURCE_NAMES:
            for path in OUTPUTS.rglob(name):
                if path.exists() and path not in found and not should_exclude_discovered(path):
                    found.append(path)

    return found, missing


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def truth_key(row: dict[str, str]) -> str:
    return "|".join(
        [
            parse_date(row.get("race_date", "")),
            key_text(row.get("track", "")),
            clean_race_no(row.get("race_no", "")),
            key_text(row.get("horse_key", "")) or key_text(row.get("horse", "")),
        ]
    )


def source_key(row: dict[str, str]) -> str:
    return "|".join(
        [
            row["race_date"],
            key_text(row["track"]),
            clean_race_no(row["race_no"]),
            key_text(row["horse_key"]) or key_text(row["horse"]),
        ]
    )


def infer_won(finish_position: str, winner_raw: str, horse: str) -> str:
    if finish_position == "1":
        return "TRUE"
    winner_text = norm(winner_raw)
    if winner_text in {"YES", "TRUE", "WON", "WIN", "WINNER", "1"}:
        return "TRUE"
    if winner_text in {"NO", "FALSE", "LOST", "LOSE", "0"}:
        return "FALSE"
    if winner_text and horse and key_text(winner_text) == key_text(horse):
        return "TRUE"
    if finish_position:
        return "FALSE"
    return ""


def source_signature(row: dict[str, str]) -> str:
    return "|".join(
        [
            row.get("finish_position", ""),
            row.get("won", ""),
            row.get("starting_price", ""),
        ]
    )


def load_truth_history() -> list[dict[str, str]]:
    if not TRUTH_HISTORY.exists():
        raise FileNotFoundError(f"Missing price truth history: {TRUTH_HISTORY}")
    rows = read_csv(TRUTH_HISTORY)
    if not rows:
        return []
    missing = sorted(TRUTH_REQUIRED_COLUMNS.difference(rows[0].keys()))
    if missing:
        raise ValueError(f"Price truth history missing required columns: {missing}")

    normalised: list[dict[str, str]] = []
    for row in rows:
        out = dict(row)
        out["race_date"] = parse_date(row.get("race_date", ""))
        out["race_no"] = clean_race_no(row.get("race_no", ""))
        out["horse_key"] = key_text(row.get("horse_key", "")) or key_text(row.get("horse", ""))
        out["truth_match_key"] = truth_key(out)
        normalised.append(out)
    return normalised


def source_info_template(path: Path) -> dict[str, object]:
    return {
        "source_id": source_id(path),
        "source_file": path.name,
        "source_path": str(path),
        "status": "FOUND",
        "rows_loaded": 0,
        "usable_rows_for_truth_dates": 0,
        "date_column": "",
        "track_column": "",
        "race_no_column": "",
        "horse_column": "",
        "horse_key_column": "",
        "finish_column": "",
        "winner_column": "",
        "sp_column": "",
        "status_column": "",
        "rows_with_finish_positions": 0,
        "rows_with_winner_flags": 0,
        "rows_with_sp": 0,
        "exact_matches": 0,
        "notes": "",
    }


def prepare_source(
    path: Path,
    truth_dates: set[str],
) -> tuple[list[dict[str, str]], dict[str, object]]:
    info = source_info_template(path)
    try:
        raw_rows = read_csv(path)
    except Exception as exc:  # noqa: BLE001 - diagnostic should capture the source failure.
        info["status"] = "LOAD_ERROR"
        info["notes"] = str(exc)
        return [], info

    info["rows_loaded"] = len(raw_rows)
    if not raw_rows:
        info["status"] = "EMPTY"
        return [], info

    columns = list(raw_rows[0].keys())
    date_col = first_existing(columns, DATE_COLUMNS)
    track_col = first_existing(columns, TRACK_COLUMNS)
    race_no_col = first_existing(columns, RACE_NO_COLUMNS)
    horse_key_col = first_existing(columns, HORSE_KEY_COLUMNS)
    horse_col = first_existing(columns, HORSE_COLUMNS)
    finish_col = first_existing(columns, FINISH_COLUMNS)
    winner_col = first_existing(columns, WIN_COLUMNS)
    sp_col = first_existing(columns, SP_COLUMNS)
    status_col = first_existing(columns, STATUS_COLUMNS)

    info.update(
        {
            "date_column": date_col,
            "track_column": track_col,
            "race_no_column": race_no_col,
            "horse_column": horse_col,
            "horse_key_column": horse_key_col,
            "finish_column": finish_col,
            "winner_column": winner_col,
            "sp_column": sp_col,
            "status_column": status_col,
        }
    )

    if not date_col or not track_col or not race_no_col or not (horse_key_col or horse_col):
        info["status"] = "NO_KEY_SCHEMA"
        info["notes"] = "Missing date/track/race/horse fields needed for safe result matching."
        return [], info

    prepared: list[dict[str, str]] = []
    rows_with_finish = 0
    rows_with_winner = 0
    rows_with_sp = 0

    for raw in raw_rows:
        race_date = parse_date(raw.get(date_col, ""))
        if race_date not in truth_dates:
            continue

        horse = raw.get(horse_col, "") if horse_col else raw.get(horse_key_col, "")
        horse_key = key_text(raw.get(horse_key_col, "")) if horse_key_col else ""
        if not horse_key:
            horse_key = key_text(horse)

        finish = parse_numeric(raw.get(finish_col, "")) if finish_col else ""
        winner_raw = raw.get(winner_col, "") if winner_col else ""
        won = infer_won(finish, winner_raw, horse)
        sp = parse_numeric(raw.get(sp_col, "")) if sp_col else ""

        prepared_row = {
            "race_date": race_date,
            "track": raw.get(track_col, ""),
            "race_no": clean_race_no(raw.get(race_no_col, "")),
            "horse": horse,
            "horse_key": horse_key,
            "finish_position": finish,
            "won": won,
            "starting_price": sp,
            "result_status": raw.get(status_col, "") if status_col else "",
            "settlement_source": source_id(path),
            "source_file": path.name,
        }
        prepared_row["match_key"] = source_key(prepared_row)

        if (
            has_text(prepared_row["race_date"])
            and has_text(prepared_row["track"])
            and has_text(prepared_row["race_no"])
            and has_text(prepared_row["horse_key"])
        ):
            prepared.append(prepared_row)
            rows_with_finish += 1 if has_text(finish) else 0
            rows_with_winner += 1 if has_text(won) else 0
            rows_with_sp += 1 if has_text(sp) else 0

    info["usable_rows_for_truth_dates"] = len(prepared)
    info["rows_with_finish_positions"] = rows_with_finish
    info["rows_with_winner_flags"] = rows_with_winner
    info["rows_with_sp"] = rows_with_sp
    if not prepared:
        info["status"] = "NO_USABLE_ROWS_FOR_TRUTH_DATES"
        info["notes"] = "No rows with clear date/track/race/horse fields for truth history dates."
    else:
        info["status"] = "USABLE"
    return prepared, info


def index_sources(
    sources: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    indexed: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in sources:
        indexed[row["match_key"]].append(row)
    return indexed


def best_match(matches: list[dict[str, str]]) -> dict[str, str] | None:
    if not matches:
        return None
    final_matches = [
        match
        for match in matches
        if has_text(match.get("finish_position", "")) or has_text(match.get("won", ""))
    ]
    candidates = final_matches if final_matches else matches
    return sorted(candidates, key=lambda row: source_priority(row.get("settlement_source", "")))[0]


def build_readiness(
    truth_rows: list[dict[str, str]],
    source_indexes: dict[str, dict[str, list[dict[str, str]]]],
    source_infos: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    output_rows: list[dict[str, object]] = []

    for truth in truth_rows:
        key = truth["truth_match_key"]
        matches: list[dict[str, str]] = []
        source_match_counts: dict[str, int] = {}

        for sid, indexed in source_indexes.items():
            source_matches = indexed.get(key, [])
            if source_matches:
                source_match_counts[sid] = len(source_matches)
                matches.extend(source_matches)

        for sid, count in source_match_counts.items():
            source_infos[sid]["exact_matches"] = int(source_infos[sid].get("exact_matches", 0)) + count

        duplicate_count = sum(max(count - 1, 0) for count in source_match_counts.values())
        final_signatures = sorted(
            {
                source_signature(match)
                for match in matches
                if has_text(match.get("finish_position", ""))
                or has_text(match.get("won", ""))
                or has_text(match.get("starting_price", ""))
            }
        )
        ambiguous = len(final_signatures) > 1
        match = best_match(matches)

        finish = match.get("finish_position", "") if match else ""
        won = match.get("won", "") if match else ""
        sp = match.get("starting_price", "") if match else ""
        source = match.get("settlement_source", "") if match else ""
        result_status = match.get("result_status", "") if match else ""

        finish_ok = has_text(finish)
        won_ok = has_text(won)
        sp_ok = has_text(sp)

        if not matches:
            status = "WAIT_FOR_RESULTS"
            reason = "No result source matched race_date + track + race_no + horse_key."
        elif ambiguous:
            status = "PARTIAL_RESULTS_AVAILABLE"
            reason = "Multiple matched result signatures disagree; settlement must not proceed."
        elif finish_ok and won_ok:
            status = "SETTLEMENT_READY"
            reason = "Finish position and winner flag are available from matched result data."
        elif finish_ok or won_ok or sp_ok:
            status = "PARTIAL_RESULTS_AVAILABLE"
            reason = "Matched result data has only partial final fields."
        else:
            status = "WAIT_FOR_RESULTS"
            reason = "Matched by key, but final result fields are still blank."

        output_rows.append(
            {
                "snapshot_timestamp": truth.get("snapshot_timestamp", ""),
                "race_date": truth.get("race_date", ""),
                "track": truth.get("track", ""),
                "race_no": truth.get("race_no", ""),
                "horse": truth.get("horse", ""),
                "horse_key": truth.get("horse_key", ""),
                "truth_match_key": key,
                "truth_result_status": truth.get("result_status", ""),
                "truth_finish_position": truth.get("finish_position", ""),
                "truth_won": truth.get("won", ""),
                "truth_starting_price": truth.get("starting_price", ""),
                "result_readiness_status": status,
                "match_method": "DATE_TRACK_RACE_HORSE_KEY" if matches else "",
                "matched_source_count": len(source_match_counts),
                "matched_row_count": len(matches),
                "matched_sources": "|".join(sorted(source_match_counts.keys())),
                "duplicate_result_matches": duplicate_count,
                "duplicate_sources": "|".join(
                    f"{sid}:{count}"
                    for sid, count in sorted(source_match_counts.items())
                    if count > 1
                ),
                "ambiguous_result_match_flag": bool_text(ambiguous),
                "best_result_source": source,
                "best_result_status": result_status,
                "best_finish_position": finish,
                "best_won": won,
                "best_starting_price": sp,
                "finish_position_populated_flag": bool_text(finish_ok),
                "winner_flag_populated_flag": bool_text(won_ok),
                "sp_populated_flag": bool_text(sp_ok),
                "readiness_reason": reason,
                "built_at": now_utc(),
            }
        )

    return output_rows


def unique_truth_runners(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_key: dict[str, dict[str, object]] = {}
    for row in rows:
        key = str(row["truth_match_key"])
        if key not in by_key:
            by_key[key] = row
        elif (
            by_key[key]["result_readiness_status"] != "SETTLEMENT_READY"
            and row["result_readiness_status"] == "SETTLEMENT_READY"
        ):
            by_key[key] = row
    return list(by_key.values())


def race_key(row: dict[str, object]) -> str:
    return "|".join([str(row["race_date"]), key_text(row["track"]), clean_race_no(row["race_no"])])


def race_label(row: dict[str, object]) -> str:
    return f"{row['race_date']}|{row['track']}|R{row['race_no']}"


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


def count_flag(rows: list[dict[str, object]], column: str) -> int:
    return sum(1 for row in rows if row.get(column) == "TRUE")


def build_summary(
    truth_rows: list[dict[str, str]],
    readiness_rows: list[dict[str, object]],
    source_infos: dict[str, dict[str, object]],
    missing_sources: list[Path],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    unique_rows = unique_truth_runners(readiness_rows)
    race_groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in unique_rows:
        race_groups[race_key(row)].append(row)

    race_statuses: dict[str, str] = {}
    for key, group in race_groups.items():
        ready = sum(1 for row in group if row["result_readiness_status"] == "SETTLEMENT_READY")
        partial = sum(1 for row in group if row["result_readiness_status"] == "PARTIAL_RESULTS_AVAILABLE")
        ambiguous = sum(1 for row in group if row["ambiguous_result_match_flag"] == "TRUE")
        if ready == len(group) and ambiguous == 0:
            race_statuses[key] = "SETTLEMENT_READY"
        elif ready > 0 or partial > 0 or ambiguous > 0:
            race_statuses[key] = "PARTIAL_RESULTS_AVAILABLE"
        else:
            race_statuses[key] = "WAIT_FOR_RESULTS"

    races_ready = sum(1 for status in race_statuses.values() if status == "SETTLEMENT_READY")
    races_partial = sum(1 for status in race_statuses.values() if status == "PARTIAL_RESULTS_AVAILABLE")
    races_pending = sum(1 for status in race_statuses.values() if status == "WAIT_FOR_RESULTS")
    race_count = len(race_statuses)
    coverage_pct = (races_ready / race_count * 100.0) if race_count else 0.0

    pending_truth_rows = sum(
        1
        for row in truth_rows
        if not has_text(row.get("finish_position", "")) or not has_text(row.get("won", ""))
    )
    pending_loop_rows = 0
    if TRUTH_LOOP.exists():
        for row in read_csv(TRUTH_LOOP):
            status = norm(row.get("result_status", ""))
            finish = row.get("finish_position", "")
            won = row.get("won", "")
            if status == "PENDING" or not has_text(finish) or not has_text(won):
                pending_loop_rows += 1

    if race_count and races_ready == race_count:
        readiness_status = "SETTLEMENT_READY"
        recommendation = "SAFE_TO_BUILD_SETTLEMENT_ENGINE"
    elif races_ready > 0 or races_partial > 0:
        readiness_status = "PARTIAL_RESULTS_AVAILABLE"
        recommendation = "MONITOR_ONLY"
    else:
        readiness_status = "WAIT_FOR_RESULTS"
        recommendation = "NO_ACTION"

    source_values = list(source_infos.values())
    sources_with_finish = sum(1 for info in source_values if int(info["rows_with_finish_positions"]) > 0)
    sources_with_winner = sum(1 for info in source_values if int(info["rows_with_winner_flags"]) > 0)
    sources_with_sp = sum(1 for info in source_values if int(info["rows_with_sp"]) > 0)

    rows.extend(
        [
            summary_row("overall", "truth_history_rows", len(truth_rows), rel(TRUTH_HISTORY)),
            summary_row(
                "overall",
                "truth_history_snapshots",
                len({row.get("snapshot_timestamp", "") for row in truth_rows}),
                rel(TRUTH_HISTORY),
            ),
            summary_row("overall", "pending_result_rows", pending_truth_rows, rel(TRUTH_HISTORY)),
            summary_row("overall", "truth_loop_pending_rows", pending_loop_rows, rel(TRUTH_LOOP)),
            summary_row("overall", "races_awaiting_settlement", race_count, rel(TRUTH_HISTORY)),
            summary_row("overall", "result_sources_discovered", len(source_infos) + len(missing_sources)),
            summary_row("overall", "result_sources_found", len(source_infos)),
            summary_row("overall", "result_sources_missing", len(missing_sources)),
            summary_row("overall", "result_sources_containing_finish_positions", sources_with_finish),
            summary_row("overall", "result_sources_containing_winner_flags", sources_with_winner),
            summary_row("overall", "result_sources_containing_sp", sources_with_sp),
            summary_row("overall", "races_ready_for_settlement", races_ready),
            summary_row("overall", "races_partial_results_available", races_partial),
            summary_row("overall", "races_still_pending", races_pending),
            summary_row("overall", "settlement_coverage_pct", f"{coverage_pct:.2f}"),
            summary_row(
                "overall",
                "populated_finish_positions",
                count_flag(readiness_rows, "finish_position_populated_flag"),
            ),
            summary_row(
                "overall",
                "populated_winner_flags",
                count_flag(readiness_rows, "winner_flag_populated_flag"),
            ),
            summary_row(
                "overall",
                "populated_sp_values",
                count_flag(readiness_rows, "sp_populated_flag"),
            ),
            summary_row(
                "overall",
                "duplicate_result_matches",
                sum(int(row["duplicate_result_matches"]) for row in readiness_rows),
            ),
            summary_row(
                "overall",
                "ambiguous_result_matches",
                count_flag(readiness_rows, "ambiguous_result_match_flag"),
            ),
            summary_row("recommendation", "readiness_status", readiness_status),
            summary_row("recommendation", "recommendation", recommendation),
        ]
    )

    for path in missing_sources:
        rows.append(summary_row("source_files", path.name, "MISSING", str(path)))

    for sid, info in sorted(source_infos.items(), key=lambda item: item[0]):
        rows.append(
            summary_row(
                "source_files",
                sid,
                info["status"],
                str(info["source_path"]),
                str(info["notes"]),
            )
        )
        for metric in [
            "rows_loaded",
            "usable_rows_for_truth_dates",
            "rows_with_finish_positions",
            "rows_with_winner_flags",
            "rows_with_sp",
            "exact_matches",
        ]:
            rows.append(
                summary_row(
                    f"source_{metric}",
                    sid,
                    info[metric],
                    str(info["source_path"]),
                )
            )
        schema_notes = (
            f"date={info['date_column']}; track={info['track_column']}; "
            f"race_no={info['race_no_column']}; horse={info['horse_column']}; "
            f"horse_key={info['horse_key_column']}; finish={info['finish_column']}; "
            f"winner={info['winner_column']}; sp={info['sp_column']}; status={info['status_column']}"
        )
        rows.append(summary_row("source_schema", sid, "columns", str(info["source_path"]), schema_notes))

    for key, group in sorted(race_groups.items()):
        sample = group[0]
        ready = sum(1 for row in group if row["result_readiness_status"] == "SETTLEMENT_READY")
        partial = sum(1 for row in group if row["result_readiness_status"] == "PARTIAL_RESULTS_AVAILABLE")
        pending = sum(1 for row in group if row["result_readiness_status"] == "WAIT_FOR_RESULTS")
        rows.append(
            summary_row(
                "race_status",
                race_label(sample),
                race_statuses[key],
                notes=f"runners={len(group)}; ready={ready}; partial={partial}; pending={pending}",
            )
        )

    for status, count in sorted(
        defaultdict(
            int,
            {
                status: sum(1 for row in readiness_rows if row["result_readiness_status"] == status)
                for status in {row["result_readiness_status"] for row in readiness_rows}
            },
        ).items()
    ):
        rows.append(summary_row("row_readiness_status_counts", status, count))

    return rows


def main() -> None:
    truth_rows = load_truth_history()
    truth_dates = {row["race_date"] for row in truth_rows if has_text(row.get("race_date", ""))}

    source_paths, missing_sources = discover_sources()
    source_infos: dict[str, dict[str, object]] = {}
    source_indexes: dict[str, dict[str, list[dict[str, str]]]] = {}

    for path in source_paths:
        prepared, info = prepare_source(path, truth_dates)
        sid = str(info["source_id"])
        source_infos[sid] = info
        source_indexes[sid] = index_sources(prepared)

    readiness_rows = build_readiness(truth_rows, source_indexes, source_infos)
    summary_rows = build_summary(truth_rows, readiness_rows, source_infos, missing_sources)

    write_csv(OUTPUT, readiness_rows, READINESS_COLUMNS)
    write_csv(SUMMARY, summary_rows, SUMMARY_COLUMNS)

    key_sections = {"overall", "recommendation", "race_status", "row_readiness_status_counts"}
    printable = [row for row in summary_rows if row["section"] in key_sections]

    print("=" * 96)
    print("EDGEIQ PRICE TRUTH RESULT READINESS V1 - READ ONLY")
    print("=" * 96)
    print(f"input: {TRUTH_HISTORY}")
    print(f"input: {TRUTH_LOOP}")
    print(f"wrote: {OUTPUT}")
    print(f"wrote: {SUMMARY}")
    print("")
    for row in printable:
        print(
            f"{row['section']},{row['metric']},{row['value']},"
            f"{row['source_path']},{row['notes']}"
        )
    print("=" * 96)


if __name__ == "__main__":
    main()
