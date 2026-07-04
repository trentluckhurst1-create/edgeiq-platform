from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_FEED = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
OUT = DATA / "edgeiq_race_status_safety_audit_v1.csv"
SUMMARY = DATA / "edgeiq_race_status_safety_audit_v1_summary.csv"

COUNTRY_SUFFIXES = ("IRE", "USA", "JPN", "GER", "SAF", "NZ", "GB", "FR")

EXPLICIT_ABANDONED_TERMS = (
    "ABANDONED",
    "ABANDON",
    "POSTPONED",
    "CANCELLED",
    "CANCELED",
    "VOID",
    "NO RACE",
    "NO_RACE",
)
EXPLICIT_NO_RESULT_TERMS = (
    "NO_RESULT",
    "NO RESULT",
    "NO OFFICIAL RESULT",
)

TERMINAL_RESULT_STATUSES = {
    "FINAL",
    "RESULTED",
    "FAILED_TO_FINISH",
    "CONFIRMED_SCRATCHED",
    "SCRATCHED",
    "CONFIRMED_NON_RUNNER",
    "NON_RUNNER",
    "NON_RUNNER_CONFIRMED",
}

PENDING_STATUSES = {
    "PENDING",
    "PENDING_OR_NO_POSITION",
    "PENDING_FINAL_RESULT_SOURCE",
    "WAIT_FOR_RESULTS",
    "NO_RESULT_ROW",
    "RESULT_PARSE_GAP",
    "UNKNOWN",
    "",
}

OUTPUT_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "race_time",
    "horse",
    "horse_key",
    "live_race_state",
    "live_runner_status",
    "live_is_scratched",
    "sportsbet_source_status",
    "sportsbet_runner_status",
    "sportsbet_selection_status",
    "sportsbet_status_code",
    "sportsbet_price",
    "sportsbet_event_id",
    "sportsbet_market_id",
    "selection_id",
    "ra_calendar_availability",
    "ra_calendar_status",
    "ra_result_status",
    "ra_finish_position",
    "settlement_result_status",
    "settlement_finish_position",
    "price_truth_result_status",
    "canonical_result_status",
    "source_signal_count",
    "abandoned_signal_sources",
    "no_result_signal_sources",
    "pending_signal_sources",
    "terminal_signal_sources",
    "race_status",
    "race_status_reason",
    "runner_settlement_guard",
    "safe_settlement_action",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value", "notes"]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    tmp.replace(path)


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.lower() in {"nan", "none", "null", "n/a", "-"} else text


def canonical_horse(value: Any) -> str:
    text = clean(value).upper()
    suffix_pattern = "|".join(COUNTRY_SUFFIXES)
    text = re.sub(rf"\s*\(({suffix_pattern})\)\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[^A-Z0-9]", "", text)
    for suffix in COUNTRY_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix) + 3:
            return text[: -len(suffix)]
    return text


def normalise_track(value: Any) -> str:
    text = clean(value).upper()
    if "SANDOWN" in text and "LAKESIDE" in text:
        return "SANDOWN LAKESIDE"
    if "KILMORE" in text:
        return "KILMORE"
    if "ECHUCA" in text:
        return "ECHUCA"
    text = re.sub(r"^(SPORTSBET|SPORTS BET|BET365|LADBROKES|TABTOUCH|TAB)\s+", "", text)
    text = re.sub(r"\b(VIC|PROFESSIONAL|PARK|RACECOURSE)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalise_race_no(value: Any) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def first(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = clean(row.get(name))
        if value:
            return value
    return ""


def runner_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        first(row, ["race_date", "date", "meeting_date"]),
        normalise_track(first(row, ["track", "track_normalised", "venue_label", "meeting"])),
        normalise_race_no(first(row, ["race_no", "race_number", "race"])),
        canonical_horse(first(row, ["horse_key", "horse", "runner", "horse_name", "runner_name"])),
    )


def race_key(row: dict[str, str]) -> tuple[str, str, str]:
    key = runner_key(row)
    return key[:3]


def calendar_race_key(row: dict[str, str], current_race_nos_by_date_track: dict[tuple[str, str], set[str]]) -> list[tuple[str, str, str]]:
    date = first(row, ["meeting_date", "race_date", "date"])
    track = normalise_track(first(row, ["track_normalised", "venue_label", "track"]))
    race_nos = current_race_nos_by_date_track.get((date, track), set())
    return [(date, track, race_no) for race_no in race_nos]


def compact_status(value: Any) -> str:
    return re.sub(r"\s+", "_", clean(value).upper())


def all_text(row: dict[str, str]) -> str:
    return " | ".join(clean(value).upper() for value in row.values() if clean(value))


def has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def classify_source_signal(source_name: str, row: dict[str, str]) -> tuple[str, str]:
    text = all_text(row)
    status = compact_status(
        first(
            row,
            [
                "race_status",
                "result_status",
                "result_resolution_status",
                "source_status",
                "calendar_status",
                "availability_label",
                "runner_status",
                "selection_status",
                "status_code",
                "match_status",
                "notes",
            ],
        )
    )

    if has_any(text, EXPLICIT_ABANDONED_TERMS):
        return "ABANDONED_SIGNAL", source_name
    if has_any(text, EXPLICIT_NO_RESULT_TERMS):
        return "NO_RESULT_SIGNAL", source_name
    if status in TERMINAL_RESULT_STATUSES:
        return "TERMINAL_RESULT_SIGNAL", source_name
    if status in PENDING_STATUSES or "INTERIM" in text or "PENDING" in text:
        return "PENDING_SIGNAL", source_name
    return "OBSERVED_SIGNAL", source_name


def discover_sources() -> list[tuple[str, Path, str]]:
    fixed = [
        ("SPORTSBET_LIVE", DATA / "sportsbet_live_market_v1.csv", "sportsbet"),
        ("SPORTSBET_FULL_DAY", DATA / "sportsbet_live_market_full_day_v5_2.csv", "sportsbet"),
        ("SPORTSBET_STATUS", DATA / "sportsbet_live_market_status_v1.csv", "sportsbet_status"),
        ("RA_CALENDAR", DATA / "racing_australia_vic_results_calendar_v1.csv", "calendar"),
        ("RA_SANDOWN_RESULTS", DATA / "racing_australia_sandown_2026_05_31_normalised_results_v1.csv", "result"),
        ("RA_SETTLEMENT_PREVIEW", DATA / "racing_australia_settlement_preview_v1.csv", "settlement"),
        ("RA_SETTLEMENT_CANDIDATE", DATA / "racing_australia_settlement_candidate_v1.csv", "settlement"),
        ("SANDOWN_FINAL_CAPTURE", DATA / "edgeiq_sandown_final_results_capture_v1.csv", "settlement"),
        ("PRICE_TRUTH_HISTORY", DATA / "edgeiq_price_truth_history_v1.csv", "settlement"),
        ("RESULTS_TRUTH_LOOP", DATA / "edgeiq_results_truth_loop.csv", "settlement"),
        ("CANONICAL_RESULTS_TRUTH", DATA / "edgeiq_canonical_results_truth_v1.csv", "result"),
        ("RACE_RESULTS", DATA / "race_results.csv", "result"),
    ]
    dynamic: list[tuple[str, Path, str]] = []
    for path in DATA.glob("racing_australia_*normalised_results*.csv"):
        if not any(path == item[1] for item in fixed):
            dynamic.append((f"RA_NORMALISED_{path.stem.upper()}", path, "result"))
    return [(name, path, kind) for name, path, kind in fixed + dynamic if path.exists()]


def source_value(rows: list[dict[str, str]], column_names: list[str]) -> str:
    values = [first(row, column_names) for row in rows]
    return next((value for value in values if value), "")


def build_source_indexes(
    live_rows: list[dict[str, str]],
) -> tuple[
    dict[tuple[str, str, str, str], dict[str, list[dict[str, str]]]],
    dict[tuple[str, str, str], dict[str, list[dict[str, str]]]],
    list[dict[str, str]],
]:
    live_race_keys = {race_key(row) for row in live_rows}
    live_runner_keys = {runner_key(row) for row in live_rows}
    current_race_nos_by_date_track: dict[tuple[str, str], set[str]] = defaultdict(set)
    for date, track, race_no in live_race_keys:
        current_race_nos_by_date_track[(date, track)].add(race_no)

    runner_sources: dict[tuple[str, str, str, str], dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    race_sources: dict[tuple[str, str, str], dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    source_audit: list[dict[str, str]] = []

    for source_name, path, kind in discover_sources():
        rows = read_csv(path)
        matched_runner_rows = 0
        matched_race_rows = 0
        explicit_abandoned = 0
        explicit_no_result = 0
        terminal_rows = 0
        pending_rows = 0

        for row in rows:
            signal, _ = classify_source_signal(source_name, row)
            if signal == "ABANDONED_SIGNAL":
                explicit_abandoned += 1
            elif signal == "NO_RESULT_SIGNAL":
                explicit_no_result += 1
            elif signal == "TERMINAL_RESULT_SIGNAL":
                terminal_rows += 1
            elif signal == "PENDING_SIGNAL":
                pending_rows += 1

            if kind == "calendar":
                for key in calendar_race_key(row, current_race_nos_by_date_track):
                    if key in live_race_keys:
                        race_sources[key][source_name].append(row)
                        matched_race_rows += 1
                continue

            rkey = runner_key(row)
            if all(rkey) and rkey in live_runner_keys:
                runner_sources[rkey][source_name].append(row)
                race_sources[rkey[:3]][source_name].append(row)
                matched_runner_rows += 1
                matched_race_rows += 1
                continue

            rk = race_key(row)
            if all(rk) and rk in live_race_keys:
                race_sources[rk][source_name].append(row)
                matched_race_rows += 1

        source_audit.append(
            {
                "source": source_name,
                "path": str(path),
                "rows_loaded": str(len(rows)),
                "matched_runner_rows": str(matched_runner_rows),
                "matched_race_rows": str(matched_race_rows),
                "explicit_abandoned_or_postponed_rows": str(explicit_abandoned),
                "explicit_no_result_rows": str(explicit_no_result),
                "terminal_result_rows": str(terminal_rows),
                "pending_rows": str(pending_rows),
            }
        )

    return runner_sources, race_sources, source_audit


def race_status_from_sources(
    race_rows: dict[str, list[dict[str, str]]],
    live_runner_count: int,
) -> tuple[str, str, list[str], list[str], list[str], list[str]]:
    abandoned_sources: list[str] = []
    no_result_sources: list[str] = []
    pending_sources: list[str] = []
    terminal_sources: list[str] = []
    terminal_runner_keys: set[str] = set()

    for source_name, rows in race_rows.items():
        for row in rows:
            signal, source = classify_source_signal(source_name, row)
            key = runner_key(row)
            if signal == "ABANDONED_SIGNAL":
                abandoned_sources.append(source)
            elif signal == "NO_RESULT_SIGNAL":
                no_result_sources.append(source)
            elif signal == "PENDING_SIGNAL":
                pending_sources.append(source)
            elif signal == "TERMINAL_RESULT_SIGNAL":
                terminal_sources.append(source)
                if all(key):
                    terminal_runner_keys.add("|".join(key))

    if abandoned_sources:
        return "ABANDONED", "Explicit abandoned/postponed/void/no-race signal found.", abandoned_sources, no_result_sources, pending_sources, terminal_sources
    if no_result_sources:
        return "NO_RESULT", "Explicit no-result signal found; block loss settlement.", abandoned_sources, no_result_sources, pending_sources, terminal_sources
    if terminal_runner_keys and len(terminal_runner_keys) >= live_runner_count:
        return "RESULTED", "Terminal result status found for all live runners in the race.", abandoned_sources, no_result_sources, pending_sources, terminal_sources
    if terminal_runner_keys:
        return "PENDING", "Partial terminal results only; do not settle missing runners as losses.", abandoned_sources, no_result_sources, pending_sources, terminal_sources
    return "PENDING", "No complete final result source; preserve as pending.", abandoned_sources, no_result_sources, pending_sources, terminal_sources


def runner_guard(
    race_status: str,
    source_rows: dict[str, list[dict[str, str]]],
) -> tuple[str, str, str]:
    statuses: list[str] = []
    for rows in source_rows.values():
        for row in rows:
            statuses.append(compact_status(first(row, ["result_status", "result_resolution_status", "race_status"])))

    if race_status in {"ABANDONED", "NO_RESULT", "PENDING"}:
        return "BLOCK_SETTLEMENT_NO_LOSS", "DO_NOT_SETTLE_AS_LOSS", "Race is not safely resulted."
    if any(status in {"FINAL", "RESULTED"} for status in statuses):
        return "TERMINAL_RESULT", "SAFE_TO_SETTLE_FROM_RESULT_SOURCE", "Runner has terminal final/resulted status."
    if any(status in {"FAILED_TO_FINISH"} for status in statuses):
        return "FAILED_TO_FINISH_TERMINAL", "SAFE_TO_SETTLE_AS_NON_WINNER", "Runner failed to finish; terminal non-winner."
    if any(status in {"CONFIRMED_SCRATCHED", "SCRATCHED", "CONFIRMED_NON_RUNNER", "NON_RUNNER"} for status in statuses):
        return "NON_RUNNER_TERMINAL", "SAFE_TO_EXCLUDE_FROM_LOSS_CALC", "Runner is confirmed scratched/non-runner."
    return "REVIEW_MISSING_RUNNER_STATUS", "DO_NOT_SETTLE_AS_LOSS", "Race resulted but runner terminal status is missing."


def build_audit() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    live_rows = read_csv(LIVE_FEED)
    runner_sources, race_sources, source_audit = build_source_indexes(live_rows)

    race_live_counts = Counter(race_key(row) for row in live_rows)
    race_status_cache: dict[tuple[str, str, str], tuple[str, str, list[str], list[str], list[str], list[str]]] = {}
    for key, count in race_live_counts.items():
        race_status_cache[key] = race_status_from_sources(race_sources.get(key, {}), count)

    output_rows: list[dict[str, Any]] = []
    for live in live_rows:
        rkey = runner_key(live)
        rk = rkey[:3]
        source_rows = runner_sources.get(rkey, {})
        race_status, reason, abandoned_sources, no_result_sources, pending_sources, terminal_sources = race_status_cache[rk]
        guard, action, guard_note = runner_guard(race_status, source_rows)

        sportsbet_rows = source_rows.get("SPORTSBET_LIVE", []) or source_rows.get("SPORTSBET_FULL_DAY", [])
        ra_rows = source_rows.get("RA_SANDOWN_RESULTS", [])
        settlement_rows = (
            source_rows.get("RA_SETTLEMENT_PREVIEW", [])
            or source_rows.get("RA_SETTLEMENT_CANDIDATE", [])
            or source_rows.get("SANDOWN_FINAL_CAPTURE", [])
        )
        price_truth_rows = source_rows.get("PRICE_TRUTH_HISTORY", [])
        canonical_rows = source_rows.get("CANONICAL_RESULTS_TRUTH", [])

        output_rows.append(
            {
                "race_date": rkey[0],
                "track": first(live, ["track"]),
                "race_no": rkey[2],
                "race_time": first(live, ["race_time"]),
                "horse": first(live, ["horse"]),
                "horse_key": rkey[3],
                "live_race_state": first(live, ["race_state"]),
                "live_runner_status": first(live, ["runner_status", "ui_status"]),
                "live_is_scratched": first(live, ["is_scratched", "scratch_status"]),
                "sportsbet_source_status": source_value(sportsbet_rows, ["source_status"]),
                "sportsbet_runner_status": source_value(sportsbet_rows, ["runner_status"]),
                "sportsbet_selection_status": source_value(sportsbet_rows, ["selection_status"]),
                "sportsbet_status_code": source_value(sportsbet_rows, ["status_code"]),
                "sportsbet_price": source_value(sportsbet_rows, ["sportsbet_price", "price_win"]),
                "sportsbet_event_id": source_value(sportsbet_rows, ["event_id", "sportsbet_event_id"]),
                "sportsbet_market_id": source_value(sportsbet_rows, ["market_id", "sportsbet_market_id"]),
                "selection_id": source_value(sportsbet_rows, ["selection_id"]),
                "ra_calendar_availability": source_value(race_sources.get(rk, {}).get("RA_CALENDAR", []), ["availability_label"]),
                "ra_calendar_status": source_value(race_sources.get(rk, {}).get("RA_CALENDAR", []), ["calendar_status"]),
                "ra_result_status": source_value(ra_rows, ["result_status"]),
                "ra_finish_position": source_value(ra_rows, ["finish_position", "finish_pos"]),
                "settlement_result_status": source_value(settlement_rows, ["result_status"]),
                "settlement_finish_position": source_value(settlement_rows, ["finish_position", "finish_pos"]),
                "price_truth_result_status": source_value(price_truth_rows, ["result_status"]),
                "canonical_result_status": source_value(canonical_rows, ["result_status", "result_resolution_status"]),
                "source_signal_count": sum(len(rows) for rows in source_rows.values()),
                "abandoned_signal_sources": ";".join(sorted(set(abandoned_sources))),
                "no_result_signal_sources": ";".join(sorted(set(no_result_sources))),
                "pending_signal_sources": ";".join(sorted(set(pending_sources))),
                "terminal_signal_sources": ";".join(sorted(set(terminal_sources))),
                "race_status": race_status,
                "race_status_reason": reason,
                "runner_settlement_guard": guard,
                "safe_settlement_action": action,
                "notes": guard_note,
            }
        )

    race_status_counts = Counter(row["race_status"] for row in output_rows)
    guard_counts = Counter(row["runner_settlement_guard"] for row in output_rows)
    action_counts = Counter(row["safe_settlement_action"] for row in output_rows)
    unique_races = {race_key(row) for row in live_rows}

    summary_rows: list[dict[str, Any]] = [
        {"metric": "live_rows_loaded", "value": str(len(live_rows)), "notes": str(LIVE_FEED)},
        {"metric": "live_races", "value": str(len(unique_races)), "notes": ""},
        {"metric": "output_rows", "value": str(len(output_rows)), "notes": ""},
        {"metric": "race_status_counts", "value": "; ".join(f"{key}:{value}" for key, value in sorted(race_status_counts.items())), "notes": ""},
        {"metric": "runner_settlement_guard_counts", "value": "; ".join(f"{key}:{value}" for key, value in sorted(guard_counts.items())), "notes": ""},
        {"metric": "safe_settlement_action_counts", "value": "; ".join(f"{key}:{value}" for key, value in sorted(action_counts.items())), "notes": ""},
        {"metric": "abandoned_runner_rows", "value": str(race_status_counts.get("ABANDONED", 0)), "notes": ""},
        {"metric": "no_result_runner_rows", "value": str(race_status_counts.get("NO_RESULT", 0)), "notes": ""},
        {"metric": "pending_runner_rows", "value": str(race_status_counts.get("PENDING", 0)), "notes": ""},
        {"metric": "status", "value": "RACE_STATUS_SAFETY_AUDITED", "notes": "Read-only audit; no settlement files modified."},
        {"metric": "settlement_safety_rule", "value": "BLOCK_ABANDONED_NO_RESULT_PENDING", "notes": "Do not settle abandoned, no-result, or pending races as losses."},
    ]

    for source in source_audit:
        summary_rows.append(
            {
                "metric": f"source::{source['source']}",
                "value": f"rows={source['rows_loaded']}; matched_runner_rows={source['matched_runner_rows']}; matched_race_rows={source['matched_race_rows']}",
                "notes": f"abandoned={source['explicit_abandoned_or_postponed_rows']}; no_result={source['explicit_no_result_rows']}; terminal={source['terminal_result_rows']}; pending={source['pending_rows']}; path={source['path']}",
            }
        )

    return output_rows, summary_rows


def main() -> None:
    rows, summary = build_audit()
    write_csv(OUT, rows, OUTPUT_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("EDGEiQ Race Status Safety Audit V1")
    print(f"rows written: {len(rows)}")
    print(f"output: {OUT}")
    print(f"summary: {SUMMARY}")


if __name__ == "__main__":
    main()
