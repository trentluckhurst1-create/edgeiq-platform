from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUTPUTS = ROOT / "outputs"

TRUTH_LOOP = DATA / "edgeiq_results_truth_loop.csv"
DIAGNOSTIC = DATA / "edgeiq_results_truth_loop_update_diagnostic_v1.csv"
SUMMARY = DATA / "edgeiq_results_truth_loop_update_diagnostic_v1_summary.csv"

EXPLICIT_SOURCE_PATHS = [
    DATA / "results_history.csv",
    DATA / "ra_horse_runs.csv",
    DATA / "horse_runs_ra.csv",
    DATA / "run_context.csv",
]

KNOWN_EXTRA_SOURCE_NAMES = [
    "edgeiq_canonical_results_truth_v1.csv",
    "results_history_clean.csv",
    "race_results.csv",
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
    "horse_runs_ra.csv": 20,
    "ra_horse_runs.csv": 21,
    "run_context.csv": 22,
    "run_context_FIXED.csv": 23,
}

DATE_COLUMNS = ["race_date", "date_k", "date", "run_date", "meeting_date", "event_date"]
TRACK_COLUMNS = ["track", "track_name", "meeting_name", "venue", "track_code"]
RACE_NO_COLUMNS = ["race_no", "race_k", "race_number", "race"]
HORSE_KEY_COLUMNS = ["horse_key", "horse_k", "horse_clean", "canonical_runner_key"]
HORSE_COLUMNS = ["horse", "horse_name", "runner", "runner_name", "selection_name"]
FINISH_COLUMNS = ["finish_position", "finish_pos_num", "finish_pos", "finish", "placing"]
WIN_COLUMNS = ["winner_flag", "won", "winner", "result"]
SP_COLUMNS = ["sp_num", "sp", "starting_price", "price", "price_raw"]
CLOSING_COLUMNS = ["closing_price", "close_price", "market_price"]
STATUS_COLUMNS = ["result_status", "result", "result_resolution_status", "safe_for_model_validation"]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def has_text(value: object) -> bool:
    if value is None or pd.isna(value):
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
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    if not match:
        return ""
    number = float(match.group(0))
    return str(int(number)) if number.is_integer() else f"{number:.2f}".rstrip("0").rstrip(".")


def parse_date(value: object) -> str:
    if not has_text(value):
        return ""
    text = str(value).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        parsed = pd.to_datetime(text, errors="coerce", format="%Y-%m-%d")
    elif re.match(r"^\d{1,2}[A-Za-z]{3}\d{2}$", text):
        parsed = pd.to_datetime(text, errors="coerce", format="%d%b%y")
    else:
        parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return ""
    return parsed.strftime("%Y-%m-%d")


def race_id_part(value: object, index: int) -> str:
    if not has_text(value):
        return ""
    parts = re.split(r"[|_]", str(value))
    return parts[index].strip() if len(parts) > index else ""


def source_id(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def first_existing(columns: list[str], candidates: list[str]) -> str:
    lower_to_real = {column.lower(): column for column in columns}
    for candidate in candidates:
        real = lower_to_real.get(candidate.lower())
        if real:
            return real
    return ""


def bool_mask(series: pd.Series) -> pd.Series:
    return series.apply(lambda value: bool(has_text(value))).astype(bool)


def count_has_text(series: pd.Series) -> int:
    return int(series.apply(lambda value: bool(has_text(value))).astype(bool).sum())


def source_priority(source: str) -> int:
    return SOURCE_PRIORITY.get(Path(source).name, 100)


def truth_key(row: pd.Series) -> str:
    return "|".join(
        [
            str(row["race_date"]),
            key_text(row["track"]),
            clean_race_no(row["race_no"]),
            key_text(row["horse_key"]),
        ]
    )


def source_signature(row: pd.Series) -> str:
    return "|".join(
        [
            str(row.get("finish_position", "")),
            str(row.get("won", "")),
            str(row.get("starting_price", "")),
        ]
    )


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
        if path.exists() and path not in found and path != TRUTH_LOOP:
            found.append(path)

    if OUTPUTS.exists():
        for name in OUTPUT_SOURCE_NAMES:
            for path in OUTPUTS.rglob(name):
                if path.exists() and path not in found:
                    found.append(path)

    return found, missing


def load_truth_loop() -> pd.DataFrame:
    if not TRUTH_LOOP.exists():
        raise FileNotFoundError(f"Missing results truth loop input: {TRUTH_LOOP}")
    truth = pd.read_csv(TRUTH_LOOP, dtype=str, keep_default_na=False, low_memory=False)
    required = {
        "race_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "finish_position",
        "result_status",
    }
    missing = sorted(required.difference(truth.columns))
    if missing:
        raise ValueError(f"Results truth loop missing required columns: {missing}")

    out = truth.copy()
    out["race_no"] = out["race_no"].map(clean_race_no)
    out["truth_loop_match_key"] = out.apply(truth_key, axis=1)
    out["pending_flag"] = out.apply(
        lambda row: norm(row.get("result_status", "")) == "PENDING"
        or not has_text(row.get("finish_position", "")),
        axis=1,
    )
    return out


def infer_won(row: pd.Series) -> str:
    finish = parse_numeric(row.get("finish_position", ""))
    if finish == "1":
        return "TRUE"

    winner_raw = norm(row.get("winner_raw", ""))
    horse = norm(row.get("horse", ""))
    if winner_raw in {"YES", "TRUE", "WON", "WIN"}:
        return "TRUE"
    if winner_raw in {"NO", "FALSE", "LOST", "LOSE"}:
        return "FALSE"
    if winner_raw and horse and key_text(winner_raw) == key_text(horse):
        return "TRUE"
    if finish:
        return "FALSE"
    return ""


def prepare_source(path: Path, truth_dates: set[str]) -> tuple[pd.DataFrame, dict[str, object]]:
    sid = source_id(path)
    info: dict[str, object] = {
        "source_id": sid,
        "source_file": path.name,
        "source_path": str(path),
        "status": "FOUND",
        "rows_loaded": 0,
        "usable_rows": 0,
        "date_column": "",
        "track_column": "",
        "race_no_column": "",
        "horse_column": "",
        "horse_key_column": "",
        "finish_column": "",
        "winner_column": "",
        "sp_column": "",
        "closing_column": "",
        "status_column": "",
        "notes": "",
    }

    try:
        raw = pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)
    except Exception as exc:
        info["status"] = "LOAD_ERROR"
        info["notes"] = str(exc)
        return pd.DataFrame(), info

    info["rows_loaded"] = len(raw)
    columns = list(raw.columns)
    date_col = first_existing(columns, DATE_COLUMNS)
    track_col = first_existing(columns, TRACK_COLUMNS)
    race_col = first_existing(columns, RACE_NO_COLUMNS)
    horse_key_col = first_existing(columns, HORSE_KEY_COLUMNS)
    horse_col = first_existing(columns, HORSE_COLUMNS)
    finish_col = first_existing(columns, FINISH_COLUMNS)
    win_col = first_existing(columns, WIN_COLUMNS)
    sp_col = first_existing(columns, SP_COLUMNS)
    closing_col = first_existing(columns, CLOSING_COLUMNS)
    status_col = first_existing(columns, STATUS_COLUMNS)

    info.update(
        {
            "date_column": date_col,
            "track_column": track_col,
            "race_no_column": race_col,
            "horse_column": horse_col,
            "horse_key_column": horse_key_col,
            "finish_column": finish_col,
            "winner_column": win_col,
            "sp_column": sp_col,
            "closing_column": closing_col,
            "status_column": status_col,
        }
    )

    if not horse_col and not horse_key_col:
        info["status"] = "NO_HORSE_FIELD"
        info["notes"] = "No horse/runner identity field found."
        return pd.DataFrame(), info

    prepared = pd.DataFrame(index=raw.index)
    if date_col:
        prepared["race_date"] = raw[date_col].map(parse_date)
    elif "race_id" in raw.columns:
        prepared["race_date"] = raw["race_id"].map(lambda value: parse_date(race_id_part(value, 0)))
    else:
        prepared["race_date"] = ""

    if track_col:
        prepared["track"] = raw[track_col]
    elif "race_id" in raw.columns:
        prepared["track"] = raw["race_id"].map(lambda value: race_id_part(value, 1))
    else:
        prepared["track"] = ""

    if race_col:
        prepared["race_no"] = raw[race_col].map(clean_race_no)
    elif "race_id" in raw.columns:
        prepared["race_no"] = raw["race_id"].map(lambda value: clean_race_no(race_id_part(value, 2)))
    else:
        prepared["race_no"] = ""

    if horse_key_col and horse_key_col.lower() == "canonical_runner_key":
        prepared["horse_key"] = raw[horse_key_col].map(lambda value: key_text(race_id_part(value, 3)))
    elif horse_key_col:
        prepared["horse_key"] = raw[horse_key_col].map(key_text)
    elif horse_col:
        prepared["horse_key"] = raw[horse_col].map(key_text)
    else:
        prepared["horse_key"] = ""

    prepared["horse"] = raw[horse_col] if horse_col else raw[horse_key_col]
    prepared["track_key"] = prepared["track"].map(key_text)
    prepared["finish_position"] = raw[finish_col].map(parse_numeric) if finish_col else ""
    prepared["winner_raw"] = raw[win_col] if win_col else ""
    prepared["won"] = prepared.apply(infer_won, axis=1)
    prepared["starting_price"] = raw[sp_col].map(parse_numeric) if sp_col else ""
    prepared["closing_price"] = raw[closing_col].map(parse_numeric) if closing_col else ""
    prepared["result_status"] = raw[status_col] if status_col else ""
    prepared["source_id"] = sid
    prepared["source_file"] = path.name
    prepared["source_path"] = str(path)
    prepared["match_key"] = (
        prepared["race_date"].astype(str)
        + "|"
        + prepared["track_key"].astype(str)
        + "|"
        + prepared["race_no"].astype(str)
        + "|"
        + prepared["horse_key"].astype(str)
    )

    date_filtered = prepared[prepared["race_date"].isin(truth_dates)].copy()
    usable_mask = (
        bool_mask(date_filtered["race_date"])
        & bool_mask(date_filtered["track_key"])
        & bool_mask(date_filtered["race_no"])
        & bool_mask(date_filtered["horse_key"])
    )
    usable = date_filtered[usable_mask].copy()

    info["usable_rows"] = len(usable)
    if len(usable) == 0:
        info["status"] = "NO_USABLE_ROWS_FOR_TRUTH_DATES"
        info["notes"] = "No rows with clear date/track/race/horse fields for truth-loop race dates."
    else:
        info["status"] = "USABLE"

    return usable, info


def build_diagnostic(truth: pd.DataFrame, source_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for _, truth_row in truth.iterrows():
        key = truth_row["truth_loop_match_key"]
        matches: list[pd.Series] = []
        source_counts: dict[str, int] = {}

        for sid, frame in source_frames.items():
            if len(frame) == 0:
                continue
            exact = frame[frame["match_key"].eq(key)]
            if len(exact):
                source_counts[sid] = len(exact)
                for _, match in exact.iterrows():
                    matches.append(match)

        signatures = sorted({source_signature(match) for match in matches})
        ambiguous = len(signatures) > 1
        duplicate_matches = sum(max(count - 1, 0) for count in source_counts.values())
        best_match = None
        if matches:
            best_match = sorted(matches, key=lambda row: source_priority(str(row.get("source_id", ""))))[0]

        finish_position = str(best_match.get("finish_position", "")) if best_match is not None else ""
        won = str(best_match.get("won", "")) if best_match is not None else ""
        starting_price = str(best_match.get("starting_price", "")) if best_match is not None else ""
        closing_price = str(best_match.get("closing_price", "")) if best_match is not None else ""
        best_source = str(best_match.get("source_id", "")) if best_match is not None else ""
        source_status = str(best_match.get("result_status", "")) if best_match is not None else ""

        if not matches:
            update_status = "NO_RESULT_MATCH"
            reason = "No external result source matched race_date + track + race_no + horse_key."
        elif ambiguous:
            update_status = "AMBIGUOUS_RESULT_MATCH"
            reason = "Multiple external result signatures disagree."
        elif not has_text(finish_position) and not has_text(won):
            update_status = "MATCHED_PENDING_RESULT_FIELDS"
            reason = "External source matched by key but has no finish_position or winner flag."
        elif not has_text(finish_position) or not has_text(won):
            update_status = "MATCHED_PARTIAL_RESULT_FIELDS"
            reason = "External source matched by key but final settlement fields are incomplete."
        else:
            update_status = "FINAL_RESULT_AVAILABLE"
            reason = "External source has finish_position and winner flag."

        rows.append(
            {
                "built_at": now_utc(),
                "race_date": truth_row["race_date"],
                "track": truth_row["track"],
                "race_no": truth_row["race_no"],
                "horse": truth_row["horse"],
                "horse_key": truth_row["horse_key"],
                "current_result_status": truth_row.get("result_status", ""),
                "current_finish_position": truth_row.get("finish_position", ""),
                "truth_loop_match_key": key,
                "pending_flag": "TRUE" if bool(truth_row.get("pending_flag")) else "FALSE",
                "update_status": update_status,
                "match_method": "RACE_DATE_TRACK_RACE_NO_HORSE_KEY" if matches else "",
                "matched_source_count": len(source_counts),
                "matched_row_count": len(matches),
                "matched_sources": "|".join(sorted(source_counts.keys())),
                "duplicate_result_matches": duplicate_matches,
                "duplicate_sources": "|".join(
                    f"{source}:{count}" for source, count in sorted(source_counts.items()) if count > 1
                ),
                "ambiguous_match_flag": "TRUE" if ambiguous else "FALSE",
                "best_update_source": best_source,
                "source_result_status": source_status,
                "available_finish_position": finish_position,
                "available_winner_flag": won,
                "available_starting_price": starting_price,
                "available_closing_price": closing_price,
                "pending_reason": reason,
                "write_status": "READ_ONLY_DIAGNOSTIC",
            }
        )

    return pd.DataFrame(rows)


def summary_row(section: str, metric: str, value: object, source_path: str = "", notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "source_path": source_path,
        "notes": notes,
        "built_at": now_utc(),
    }


def recommend_source(diagnostic: pd.DataFrame, source_infos: list[dict[str, object]]) -> tuple[str, str]:
    final_rows = diagnostic[diagnostic["update_status"].eq("FINAL_RESULT_AVAILABLE")]
    if len(final_rows) == 0:
        structurally_matched = diagnostic[pd.to_numeric(diagnostic["matched_row_count"], errors="coerce").fillna(0) > 0]
        if len(structurally_matched):
            top_source = structurally_matched["best_update_source"].value_counts().index[0]
            top_count = int(structurally_matched["best_update_source"].value_counts().iloc[0])
            return (
                "NO_SAFE_UPDATE_SOURCE",
                f"{top_source} structurally matched {top_count} rows but did not provide final finish/winner fields.",
            )
        return "NO_SAFE_UPDATE_SOURCE", "No external result source matched truth-loop rows."

    best_source = final_rows["best_update_source"].value_counts().index[0]
    best_count = int(final_rows["best_update_source"].value_counts().iloc[0])
    return best_source, f"Most final result rows available from this source: {best_count}."


def race_status(frame: pd.DataFrame) -> tuple[str, str]:
    total = len(frame)
    final = int(frame["update_status"].eq("FINAL_RESULT_AVAILABLE").sum())
    ambiguous = int(frame["update_status"].eq("AMBIGUOUS_RESULT_MATCH").sum())
    partial = int(frame["update_status"].eq("MATCHED_PARTIAL_RESULT_FIELDS").sum())
    pending_fields = int(frame["update_status"].eq("MATCHED_PENDING_RESULT_FIELDS").sum())
    no_match = int(frame["update_status"].eq("NO_RESULT_MATCH").sum())

    if final == total and ambiguous == 0:
        return "FINAL_RESULTS_AVAILABLE", "All runners have finish_position and winner flag."
    if ambiguous:
        return "PENDING_AMBIGUOUS_MATCHES", f"{ambiguous} ambiguous runner matches block updates."
    if final:
        return "PARTIAL_RESULTS_AVAILABLE", f"{final}/{total} runners have final fields."
    if pending_fields or partial:
        return "PENDING_RESULT_FIELDS", f"{pending_fields + partial}/{total} runners match structurally but final fields are blank/incomplete."
    return "PENDING_NO_RESULT_MATCH", f"{no_match}/{total} runners have no external result match."


def build_summary(
    truth: pd.DataFrame,
    diagnostic: pd.DataFrame,
    found_paths: list[Path],
    missing_paths: list[Path],
    source_infos: list[dict[str, object]],
    source_frames: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    pending_rows = int(truth["pending_flag"].sum())
    race_contexts = truth[["race_date", "track", "race_no"]].drop_duplicates().shape[0]
    finish_count = count_has_text(diagnostic["available_finish_position"])
    winner_count = count_has_text(diagnostic["available_winner_flag"])
    sp_count = count_has_text(diagnostic["available_starting_price"])
    final_rows = int(diagnostic["update_status"].eq("FINAL_RESULT_AVAILABLE").sum())
    ambiguous_rows = int(diagnostic["ambiguous_match_flag"].eq("TRUE").sum())
    duplicate_rows = int(pd.to_numeric(diagnostic["duplicate_result_matches"], errors="coerce").fillna(0).sum())

    races_with_final = 0
    races_pending = 0
    race_rows: list[dict[str, object]] = []
    for (race_date, track, race_no), frame in diagnostic.groupby(["race_date", "track", "race_no"], dropna=False):
        status, reason = race_status(frame)
        if status == "FINAL_RESULTS_AVAILABLE":
            races_with_final += 1
        else:
            races_pending += 1
        race_rows.append(
            summary_row(
                "race_status",
                f"{race_date}|{track}|R{race_no}",
                status,
                notes=reason,
            )
        )

    recommendation, recommendation_reason = recommend_source(diagnostic, source_infos)
    safe_to_update = (
        final_rows == len(truth)
        and ambiguous_rows == 0
        and duplicate_rows == 0
        and finish_count == len(truth)
        and winner_count == len(truth)
    )
    overall_status = "SAFE_TO_UPDATE_RESULTS_LOOP" if safe_to_update else "WAIT_FOR_RESULTS"

    rows.extend(
        [
            summary_row("overall", "truth_loop_rows_loaded", len(truth)),
            summary_row("overall", "pending_rows", pending_rows),
            summary_row("overall", "race_dates", ",".join(sorted(truth["race_date"].drop_duplicates().astype(str)))),
            summary_row("overall", "track_race_contexts", race_contexts),
            summary_row("overall", "result_source_files_found", len(found_paths)),
            summary_row("overall", "result_source_files_missing", len(missing_paths)),
            summary_row("overall", "exact_matched_rows", int((pd.to_numeric(diagnostic["matched_row_count"], errors="coerce").fillna(0) > 0).sum())),
            summary_row("overall", "final_result_rows_available", final_rows),
            summary_row("overall", "finish_position_available_rows", finish_count),
            summary_row("overall", "winner_flag_available_rows", winner_count),
            summary_row("overall", "sp_available_rows", sp_count),
            summary_row("overall", "duplicate_result_matches", duplicate_rows),
            summary_row("overall", "ambiguous_matches", ambiguous_rows),
            summary_row("overall", "races_with_available_final_results", races_with_final),
            summary_row("overall", "races_still_pending", races_pending),
            summary_row("recommendation", "safest_update_source_recommendation", recommendation, notes=recommendation_reason),
            summary_row("recommendation", "status", overall_status, notes="No results were written by this diagnostic."),
        ]
    )

    for path in missing_paths:
        rows.append(summary_row("source_files", path.name, "MISSING", str(path)))

    for info in source_infos:
        sid = str(info["source_id"])
        rows.append(summary_row("source_files", sid, info["status"], info["source_path"], info.get("notes", "")))
        rows.append(summary_row("result_rows_loaded_by_source", sid, info["rows_loaded"], info["source_path"]))
        rows.append(summary_row("usable_rows_for_truth_dates", sid, info["usable_rows"], info["source_path"]))
        rows.append(
            summary_row(
                "source_schema",
                sid,
                "columns",
                notes=(
                    f"date={info.get('date_column','')}; track={info.get('track_column','')}; "
                    f"race_no={info.get('race_no_column','')}; horse={info.get('horse_column','')}; "
                    f"horse_key={info.get('horse_key_column','')}; finish={info.get('finish_column','')}; "
                    f"winner={info.get('winner_column','')}; sp={info.get('sp_column','')}; "
                    f"closing={info.get('closing_column','')}; status={info.get('status_column','')}"
                ),
            )
        )

    for sid, frame in source_frames.items():
        source_matches = diagnostic["matched_sources"].str.contains(re.escape(sid), regex=True, na=False)
        exact_count = int(source_matches.sum())
        source_diag = diagnostic[source_matches]
        rows.append(summary_row("exact_matches_by_source", sid, exact_count))
        rows.append(summary_row("finish_position_availability_by_source", sid, count_has_text(source_diag["available_finish_position"])))
        rows.append(summary_row("winner_availability_by_source", sid, count_has_text(source_diag["available_winner_flag"])))
        rows.append(summary_row("sp_availability_by_source", sid, count_has_text(source_diag["available_starting_price"])))

    for status, count in diagnostic["update_status"].value_counts(dropna=False).sort_index().items():
        rows.append(summary_row("update_status_counts", str(status), int(count)))

    rows.extend(race_rows)
    return pd.DataFrame(rows)


def main() -> None:
    print("=" * 90)
    print("EDGEIQ RESULTS TRUTH LOOP UPDATE DIAGNOSTIC V1 - READ/REVIEW ONLY")
    print("=" * 90)

    truth = load_truth_loop()
    truth_dates = set(truth["race_date"].dropna().astype(str))
    found_paths, missing_paths = discover_sources()

    source_infos: list[dict[str, object]] = []
    source_frames: dict[str, pd.DataFrame] = {}
    for path in found_paths:
        frame, info = prepare_source(path, truth_dates)
        source_infos.append(info)
        source_frames[str(info["source_id"])] = frame

    diagnostic = build_diagnostic(truth, source_frames)
    summary = build_summary(truth, diagnostic, found_paths, missing_paths, source_infos, source_frames)

    diagnostic.to_csv(DIAGNOSTIC, index=False)
    summary.to_csv(SUMMARY, index=False)

    print(f"input: {TRUTH_LOOP}")
    print(f"wrote: {DIAGNOSTIC}")
    print(f"wrote: {SUMMARY}")
    print()
    print(summary[summary["section"].isin(["overall", "recommendation", "update_status_counts"])].to_string(index=False))
    print()
    print(summary[summary["section"].eq("race_status")].to_string(index=False))
    print()
    print(summary[summary["section"].isin(["source_files", "result_rows_loaded_by_source", "usable_rows_for_truth_dates", "exact_matches_by_source", "finish_position_availability_by_source", "winner_availability_by_source", "sp_availability_by_source"])].to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
