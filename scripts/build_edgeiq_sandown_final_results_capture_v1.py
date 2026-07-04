from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PRICE_TRUTH = DATA / "edgeiq_price_truth_history_v1.csv"
TRUTH_LOOP = DATA / "edgeiq_results_truth_loop.csv"
SOURCE_DIAGNOSTIC = DATA / "edgeiq_final_results_source_diagnostic_v1.csv"

OUTPUT = DATA / "edgeiq_sandown_final_results_capture_v1.csv"
AUDIT = DATA / "edgeiq_sandown_final_results_capture_v1_audit.csv"

TARGET_DATE = "2026-05-31"
TARGET_TRACK = "SANDOWN LAKESIDE"
TARGET_RACES = {str(number) for number in range(1, 9)}

MANUAL_IMPORT_CANDIDATES = [
    DATA / "sandown_lakeside_2026_05_31_final_results_manual.csv",
    DATA / "edgeiq_sandown_lakeside_2026_05_31_final_results_manual.csv",
    DATA / "manual_sandown_final_results_2026_05_31.csv",
]

RESULT_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "finish_position",
    "won",
    "starting_price",
    "result_source",
    "result_status",
    "match_status",
    "notes",
]

AUDIT_COLUMNS = [
    "section",
    "metric",
    "value",
    "source_path",
    "notes",
    "built_at",
]

DATE_COLUMNS = ["race_date", "date", "run_date", "meeting_date", "event_date"]
TRACK_COLUMNS = ["track", "track_name", "meeting_name", "venue"]
RACE_NO_COLUMNS = ["race_no", "race_number", "race"]
HORSE_COLUMNS = ["horse", "horse_name", "runner", "runner_name", "selection_name"]
HORSE_KEY_COLUMNS = ["horse_key", "horse_clean", "canonical_runner_key"]
FINISH_COLUMNS = ["finish_position", "finish_pos", "finish_pos_num", "finish", "placing", "position"]
WIN_COLUMNS = ["won", "winner_flag", "winner", "is_winner", "result"]
SP_COLUMNS = ["starting_price", "sp", "sp_num", "price", "price_raw"]


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
    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%d%b%y", "%d%b%Y"]:
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


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


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


def result_key(row: dict[str, str]) -> str:
    return "|".join(
        [
            parse_date(row.get("race_date", "")),
            key_text(row.get("track", "")),
            clean_race_no(row.get("race_no", "")),
            horse_key(row.get("horse_key", "")) or horse_key(row.get("horse", "")),
        ]
    )


def infer_won(finish: str, winner_raw: str, horse: str) -> str:
    if finish == "1":
        return "TRUE"
    winner_text = norm(winner_raw)
    if winner_text in {"YES", "TRUE", "WON", "WIN", "WINNER", "1"}:
        return "TRUE"
    if winner_text in {"NO", "FALSE", "LOST", "LOSE", "0"}:
        return "FALSE"
    if winner_text and horse and horse_key(winner_text) == horse_key(horse):
        return "TRUE"
    if finish:
        return "FALSE"
    return ""


def load_target_rows() -> list[dict[str, str]]:
    columns, rows = read_csv(PRICE_TRUTH)
    required = {"race_date", "track", "race_no", "horse", "horse_key"}
    missing = sorted(required.difference(columns))
    if missing:
        raise ValueError(f"Price truth history missing required columns: {missing}")

    deduped: dict[str, dict[str, str]] = {}
    for row in rows:
        race_date = parse_date(row.get("race_date", ""))
        track = norm(row.get("track", ""))
        race_no = clean_race_no(row.get("race_no", ""))
        if race_date != TARGET_DATE or track != TARGET_TRACK or race_no not in TARGET_RACES:
            continue
        target = {
            "race_date": race_date,
            "track": TARGET_TRACK,
            "race_no": race_no,
            "horse": row.get("horse", "").strip(),
            "horse_key": horse_key(row.get("horse_key", "")) or horse_key(row.get("horse", "")),
        }
        deduped[result_key(target)] = target

    return sorted(
        deduped.values(),
        key=lambda row: (int(row["race_no"]), row["horse_key"]),
    )


def normalise_result_source(path: Path) -> dict[str, dict[str, str]]:
    columns, rows = read_csv(path)
    if not rows:
        return {}

    date_col = first_existing(columns, DATE_COLUMNS)
    track_col = first_existing(columns, TRACK_COLUMNS)
    race_no_col = first_existing(columns, RACE_NO_COLUMNS)
    horse_col = first_existing(columns, HORSE_COLUMNS)
    horse_key_col = first_existing(columns, HORSE_KEY_COLUMNS)
    finish_col = first_existing(columns, FINISH_COLUMNS)
    win_col = first_existing(columns, WIN_COLUMNS)
    sp_col = first_existing(columns, SP_COLUMNS)

    if not date_col or not track_col or not race_no_col or not (horse_col or horse_key_col):
        return {}

    normalised: dict[str, dict[str, str]] = {}
    for row in rows:
        race_date = parse_date(row.get(date_col, ""))
        track = norm(row.get(track_col, ""))
        race_no = clean_race_no(row.get(race_no_col, ""))
        if race_date != TARGET_DATE or track != TARGET_TRACK or race_no not in TARGET_RACES:
            continue

        raw_horse = row.get(horse_col, "") if horse_col else row.get(horse_key_col, "")
        key = horse_key(row.get(horse_key_col, "")) if horse_key_col else ""
        if not key:
            key = horse_key(raw_horse)

        finish = parse_number(row.get(finish_col, "")) if finish_col else ""
        won = infer_won(finish, row.get(win_col, "") if win_col else "", raw_horse)
        sp = parse_number(row.get(sp_col, "")) if sp_col else ""

        result = {
            "race_date": race_date,
            "track": TARGET_TRACK,
            "race_no": race_no,
            "horse": raw_horse,
            "horse_key": key,
            "finish_position": finish,
            "won": won,
            "starting_price": sp,
            "result_source": rel(path),
        }
        if key:
            normalised[result_key(result)] = result
    return normalised


def final_source_paths_from_diagnostic() -> list[Path]:
    _, rows = read_csv(SOURCE_DIAGNOSTIC)
    paths: list[Path] = []
    for row in rows:
        status = row.get("source_status", "")
        if status not in {"FINAL_RESULTS_SOURCE_FOUND", "RESULTS_SOURCE_NEEDS_NORMALISATION"}:
            continue
        raw_path = row.get("file_path", "")
        if raw_path:
            path = ROOT / raw_path
            if path.exists() and path not in paths:
                paths.append(path)
    return paths


def candidate_import_paths() -> list[Path]:
    paths: list[Path] = []
    for path in MANUAL_IMPORT_CANDIDATES:
        if path.exists():
            paths.append(path)
    for path in final_source_paths_from_diagnostic():
        if path not in paths:
            paths.append(path)
    return paths


def build_capture_rows(target_rows: list[dict[str, str]]) -> tuple[list[dict[str, object]], str, str]:
    source_paths = candidate_import_paths()
    result_index: dict[str, dict[str, str]] = {}
    local_source_found = "NO"
    source_note = "No local final source or manual import file was available."

    for path in source_paths:
        candidate = normalise_result_source(path)
        ready_rows = sum(
            1
            for result in candidate.values()
            if has_text(result.get("finish_position", "")) and has_text(result.get("won", ""))
        )
        if ready_rows:
            result_index.update(candidate)
            local_source_found = "YES"
            source_note = f"Using local final source: {rel(path)}"
            break

    output_rows: list[dict[str, object]] = []
    for target in target_rows:
        match = result_index.get(result_key(target))
        if match and has_text(match.get("finish_position", "")) and has_text(match.get("won", "")):
            output_rows.append(
                {
                    "race_date": target["race_date"],
                    "track": target["track"],
                    "race_no": target["race_no"],
                    "horse": target["horse"],
                    "horse_key": target["horse_key"],
                    "finish_position": match.get("finish_position", ""),
                    "won": match.get("won", ""),
                    "starting_price": match.get("starting_price", ""),
                    "result_source": match.get("result_source", ""),
                    "result_status": "FINAL",
                    "match_status": "MATCHED_FINAL_RESULT",
                    "notes": "Final result matched from local source.",
                }
            )
        else:
            output_rows.append(
                {
                    "race_date": target["race_date"],
                    "track": target["track"],
                    "race_no": target["race_no"],
                    "horse": target["horse"],
                    "horse_key": target["horse_key"],
                    "finish_position": "",
                    "won": "",
                    "starting_price": "",
                    "result_source": "",
                    "result_status": "PENDING_FINAL_RESULT_SOURCE",
                    "match_status": "NO_FINAL_RESULT_SOURCE",
                    "notes": "Manual final results import required; do not infer from market/SP.",
                }
            )
    return output_rows, local_source_found, source_note


def audit_row(
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


def build_audit(
    target_rows: list[dict[str, str]],
    capture_rows: list[dict[str, object]],
    local_source_found: str,
    source_note: str,
) -> list[dict[str, object]]:
    finish_count = sum(1 for row in capture_rows if has_text(row.get("finish_position", "")))
    won_count = sum(1 for row in capture_rows if has_text(row.get("won", "")))
    sp_count = sum(1 for row in capture_rows if has_text(row.get("starting_price", "")))
    pending_count = sum(1 for row in capture_rows if row.get("result_status") == "PENDING_FINAL_RESULT_SOURCE")
    ready_count = sum(1 for row in capture_rows if row.get("match_status") == "MATCHED_FINAL_RESULT")
    race_count = len({row["race_no"] for row in target_rows})
    runner_count = len({result_key(row) for row in target_rows})
    settlement_ready = ready_count == len(target_rows) and finish_count == len(target_rows) and won_count == len(target_rows)
    status = "FINAL_RESULTS_CAPTURE_READY" if settlement_ready else "NO_FINAL_RESULTS_SOURCE"
    recommendation = "FINAL_RESULTS_CAPTURE_READY" if settlement_ready else "MANUAL_RESULTS_IMPORT_REQUIRED"

    rows = [
        audit_row("target", "target_date", TARGET_DATE),
        audit_row("target", "target_track", TARGET_TRACK),
        audit_row("target", "target_races", "R1-R8"),
        audit_row("audit", "target_rows", len(target_rows), rel(PRICE_TRUTH)),
        audit_row("audit", "races", race_count, rel(PRICE_TRUTH)),
        audit_row("audit", "runners", runner_count, rel(PRICE_TRUTH)),
        audit_row("audit", "local_final_source_found", local_source_found, notes=source_note),
        audit_row("audit", "finish_positions_populated", finish_count),
        audit_row("audit", "winner_flags_populated", won_count),
        audit_row("audit", "sp_populated", sp_count),
        audit_row("audit", "pending_rows", pending_count),
        audit_row("audit", "ready_rows", ready_count),
        audit_row("audit", "settlement_ready", "TRUE" if settlement_ready else "FALSE"),
        audit_row("status", "status", status),
        audit_row("recommendation", "recommendation", recommendation),
    ]

    for path in MANUAL_IMPORT_CANDIDATES:
        rows.append(
            audit_row(
                "manual_import_candidate",
                path.name,
                "FOUND" if path.exists() else "MISSING",
                rel(path),
                "Optional manual import path checked.",
            )
        )
    return rows


def main() -> None:
    target_rows = load_target_rows()
    capture_rows, local_source_found, source_note = build_capture_rows(target_rows)
    audit_rows = build_audit(target_rows, capture_rows, local_source_found, source_note)

    write_csv(OUTPUT, capture_rows, RESULT_COLUMNS)
    write_csv(AUDIT, audit_rows, AUDIT_COLUMNS)

    print("=" * 96)
    print("EDGEIQ SANDOWN FINAL RESULTS CAPTURE V1 - NO SETTLEMENT")
    print("=" * 96)
    print(f"wrote: {OUTPUT}")
    print(f"wrote: {AUDIT}")
    print("")
    for row in audit_rows:
        if row["section"] in {"audit", "status", "recommendation"}:
            print(f"{row['section']},{row['metric']},{row['value']},{row['notes']}")
    print("=" * 96)


if __name__ == "__main__":
    main()
