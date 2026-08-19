from __future__ import annotations

import csv
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA = PROJECT_ROOT / "public" / "data"
OUTPUTS = PROJECT_ROOT / "outputs"

TERMINAL_FEED = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"

AUDIT_OUT = DATA / "edgeiq_live_market_price_ingestion_audit_v1.csv"
RUNNER_REVIEW_OUT = DATA / "edgeiq_live_market_price_ingestion_runner_review_v1.csv"
SOURCES_OUT = DATA / "edgeiq_live_market_price_ingestion_sources_v1.csv"

PRICE_FIELD_EXACT = {
    "sportsbet_price",
    "market_price",
    "current_price",
    "price",
    "odds",
    "fixed_win_price",
    "selection_price",
    "runner_price",
    "price_win",
    "live_price",
    "fixed_win",
    "win_price",
    "last_price",
    "latest_price",
    "decimal_odds",
    "current_odds",
}

PRICE_FIELD_CONTAINS = (
    "sportsbet_price",
    "market_price",
    "current_price",
    "selection_price",
    "runner_price",
    "fixed_win_price",
    "live_price",
)

EXCLUDED_PRICE_TOKENS = (
    "rated_price",
    "fair_price",
    "rated",
    "fair",
    "overlay",
    "edge",
    "prob",
    "probability",
    "sp_",
    "start_price",
    "starting_price",
    "open_price",
    "mid_price",
    "close_price",
    "low_price",
    "high_price",
    "prev_price",
    "previous_price",
    "entry_price",
    "closing_price",
)

RUNNER_FIELDS = (
    "horse",
    "horse_key",
    "runner",
    "runner_name",
    "selection",
    "selection_name",
    "entrant",
    "competitor",
)

TRACK_RACE_FIELDS = (
    "track",
    "meeting_name",
    "race_no",
    "race_number",
    "race_time",
    "race_date",
    "date",
    "event_name",
    "race_id",
    "race_key",
)

SOURCE_FIELDS = (
    "source",
    "bookmaker",
    "source_status",
    "market_source_status",
    "source_file",
    "market_source_file",
    "capture_timestamp_utc",
    "timestamp",
    "updated_at",
    "built_at",
)

SOURCE_FIELDS_OUT = [
    "file_path",
    "row_count",
    "relevant_price_columns_found",
    "horse_runner_columns_found",
    "track_race_columns_found",
    "source_columns_found",
    "latest_modified_time",
    "current_day_rows",
    "usable_runner_price_rows",
    "matched_current_terminal_runners",
    "notes",
]

RUNNER_REVIEW_FIELDS = [
    "horse",
    "track",
    "race_no",
    "race_time",
    "matched_market_source",
    "market_price_found",
    "market_price",
    "market_price_column",
    "source_race_date",
    "source_track",
    "source_race_no",
    "source_horse",
    "source_bookmaker",
    "source_timestamp",
    "match_method",
    "match_confidence",
    "fail_reason",
]

AUDIT_FIELDS = [
    "section",
    "metric",
    "value",
    "count",
    "notes",
]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null", "na", "n/a"} else text


def upper(value: object) -> str:
    return clean(value).upper()


def as_float(value: object) -> float | None:
    text = clean(value)
    if not text or text in {"-", "--"}:
        return None
    text = text.replace(",", "").replace("$", "").replace("%", "")
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def as_price(value: object) -> float | None:
    number = as_float(value)
    if number is None or number <= 1.0 or number > 1000.0:
        return None
    return number


def normalise_horse(value: object) -> str:
    text = clean(value)
    text = re.sub(r"\([^)]*\)", "", text)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def normalise_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", upper(value))


def track_keys(value: object) -> list[str]:
    exact = normalise_track(value)
    keys = [exact] if exact else []
    simplified = exact
    for suffix in ("LAKESIDE", "HILLSIDE", "RACECOURSE", "PARK", "SYNTHETIC"):
        if simplified.endswith(suffix):
            simplified = simplified[: -len(suffix)]
    simplified = simplified.strip()
    if simplified and simplified not in keys:
        keys.append(simplified)
    return keys


def row_value(row: dict[str, str], fields: tuple[str, ...] | list[str]) -> str:
    lower_map = {str(key).lower(): key for key in row.keys()}
    for field in fields:
        key = lower_map.get(field.lower())
        if key is not None:
            value = clean(row.get(key))
            if value:
                return value
    return ""


def csv_files() -> list[Path]:
    files: list[Path] = []
    if DATA.exists():
        files.extend(DATA.glob("*.csv"))
    if OUTPUTS.exists():
        files.extend(OUTPUTS.rglob("*.csv"))
    excluded_prefixes = (
        "edgeiq_live_market_price_ingestion_",
        "edgeiq_rated_price_rating_stack_",
    )
    return sorted(
        {
            path.resolve()
            for path in files
            if not any(path.name.startswith(prefix) for prefix in excluded_prefixes)
        }
    )


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def price_columns(headers: list[str]) -> list[str]:
    found: list[str] = []
    for header in headers:
        low = header.lower()
        if any(token in low for token in EXCLUDED_PRICE_TOKENS):
            continue
        if low in PRICE_FIELD_EXACT or any(token in low for token in PRICE_FIELD_CONTAINS):
            found.append(header)
    return found


def matching_columns(headers: list[str], candidates: tuple[str, ...]) -> list[str]:
    lowered = [(header, header.lower()) for header in headers]
    found: list[str] = []
    for header, low in lowered:
        if low in candidates or any(candidate in low for candidate in candidates):
            found.append(header)
    return found


def date_value(row: dict[str, str]) -> str:
    return clean(row.get("race_date") or row.get("date"))


def race_no_value(row: dict[str, str]) -> str:
    return clean(row.get("race_no") or row.get("race_number"))


def runner_keys(row: dict[str, str]) -> list[str]:
    keys: list[str] = []
    for field in RUNNER_FIELDS:
        value = row.get(field)
        key = normalise_horse(value)
        if key and key not in keys:
            keys.append(key)
    return keys


def best_price(row: dict[str, str], columns: list[str]) -> tuple[float | None, str]:
    for column in columns:
        value = as_price(row.get(column))
        if value is not None:
            return value, column
    return None, ""


def source_timestamp(row: dict[str, str]) -> str:
    for field in ("capture_timestamp_utc", "timestamp", "updated_at", "built_at", "sportsbet_timestamp", "market_capture_timestamp"):
        value = clean(row.get(field))
        if value:
            return value
    return ""


def source_bookmaker(row: dict[str, str]) -> str:
    return clean(row.get("bookmaker") or row.get("source"))


def fmt(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"


def audit_row(section: str, metric: str, value: object = "", count: object = "", notes: object = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "count": count,
        "notes": notes,
    }


def market_row_key(race_date: str, track_key: str, race_no: str, runner_key: str) -> str:
    return "|".join([race_date, track_key, race_no, runner_key])


def race_key_only(race_date: str, track_key: str, race_no: str) -> str:
    return "|".join([race_date, track_key, race_no])


def main() -> None:
    terminal_headers, terminal_rows_all = read_rows(TERMINAL_FEED)
    current_rows = [row for row in terminal_rows_all if upper(row.get("day_bucket")) == "TODAY"] or terminal_rows_all
    current_dates = {date_value(row) for row in current_rows if date_value(row)}
    current_runner_keys = set()
    current_runner_base_keys = set()
    current_race_keys = set()

    for row in current_rows:
        race_date = date_value(row)
        race_no = race_no_value(row)
        for tkey in track_keys(row.get("track")):
            current_race_keys.add(race_key_only(race_date, tkey, race_no))
        for hkey in runner_keys(row):
            current_runner_base_keys.add("|".join([race_date, race_no, hkey]))
            for tkey in track_keys(row.get("track")):
                current_runner_keys.add(market_row_key(race_date, tkey, race_no, hkey))

    exact_index: dict[str, list[dict[str, object]]] = defaultdict(list)
    alias_index: dict[str, list[dict[str, object]]] = defaultdict(list)
    no_date_index: dict[str, list[dict[str, object]]] = defaultdict(list)
    candidate_sources: list[dict[str, object]] = []

    files_scanned = 0
    candidates_with_price_columns = 0

    for path in csv_files():
        try:
            headers, rows = read_rows(path)
        except Exception as exc:  # keep audit alive on malformed side files
            candidate_sources.append(
                {
                    "file_path": str(path),
                    "row_count": "",
                    "relevant_price_columns_found": "",
                    "horse_runner_columns_found": "",
                    "track_race_columns_found": "",
                    "source_columns_found": "",
                    "latest_modified_time": "",
                    "current_day_rows": "",
                    "usable_runner_price_rows": "",
                    "matched_current_terminal_runners": "",
                    "notes": f"READ_ERROR={exc}",
                }
            )
            continue

        files_scanned += 1
        pcols = price_columns(headers)
        runner_cols = matching_columns(headers, RUNNER_FIELDS)
        track_race_cols = matching_columns(headers, TRACK_RACE_FIELDS)
        source_cols = matching_columns(headers, SOURCE_FIELDS)

        if not pcols and not runner_cols and not track_race_cols:
            continue

        current_day_rows = 0
        usable_runner_price_rows = 0
        matched_current_terminal_runners = set()

        if pcols:
            candidates_with_price_columns += 1

        for row in rows:
            row_date = date_value(row)
            row_race_no = race_no_value(row)
            row_track_keys = track_keys(row.get("track") or row.get("meeting_name"))
            row_runner_keys = runner_keys(row)
            price, price_column = best_price(row, pcols)

            if row_date and row_date in current_dates:
                current_day_rows += 1

            if price is None or not row_runner_keys or not row_track_keys or not row_race_no:
                continue

            usable_runner_price_rows += 1
            payload = {
                "file_path": str(path),
                "source_name": path.name,
                "price": price,
                "price_column": price_column,
                "race_date": row_date,
                "track": clean(row.get("track") or row.get("meeting_name")),
                "race_no": row_race_no,
                "horse": clean(row.get("horse") or row.get("runner") or row.get("runner_name") or row.get("selection_name") or row.get("selection")),
                "bookmaker": source_bookmaker(row),
                "timestamp": source_timestamp(row),
                "modified_time": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
            }

            for tkey in row_track_keys:
                for hkey in row_runner_keys:
                    if row_date:
                        key = market_row_key(row_date, tkey, row_race_no, hkey)
                        exact_index[key].append(payload)
                        if key in current_runner_keys:
                            matched_current_terminal_runners.add("|".join([row_date, row_race_no, hkey]))
                    no_date_key = market_row_key("", tkey, row_race_no, hkey)
                    no_date_index[no_date_key].append(payload)

            if row_date in current_dates:
                for tkey in row_track_keys:
                    for hkey in row_runner_keys:
                        alias_key = market_row_key(row_date, tkey, row_race_no, hkey)
                        alias_index[alias_key].append(payload)

        if pcols or runner_cols or track_race_cols:
            candidate_sources.append(
                {
                    "file_path": str(path),
                    "row_count": len(rows),
                    "relevant_price_columns_found": " | ".join(pcols),
                    "horse_runner_columns_found": " | ".join(runner_cols),
                    "track_race_columns_found": " | ".join(track_race_cols),
                    "source_columns_found": " | ".join(source_cols),
                    "latest_modified_time": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                    "current_day_rows": current_day_rows,
                    "usable_runner_price_rows": usable_runner_price_rows,
                    "matched_current_terminal_runners": len(matched_current_terminal_runners),
                    "notes": "CANDIDATE_PRICE_SOURCE" if pcols else "NO_RELEVANT_PRICE_COLUMNS",
                }
            )

    def choose_match(matches: list[dict[str, object]]) -> dict[str, object] | None:
        if not matches:
            return None
        return sorted(
            matches,
            key=lambda item: (
                str(item.get("timestamp") or ""),
                str(item.get("modified_time") or ""),
                str(item.get("source_name") or ""),
            ),
            reverse=True,
        )[0]

    runner_reviews: list[dict[str, object]] = []

    for row in current_rows:
        race_date = date_value(row)
        race_no = race_no_value(row)
        runner_name = clean(row.get("horse"))
        tkeys = track_keys(row.get("track"))
        hkeys = runner_keys(row)

        exact_matches: list[dict[str, object]] = []
        for tkey in tkeys:
            for hkey in hkeys:
                exact_matches.extend(exact_index.get(market_row_key(race_date, tkey, race_no, hkey), []))

        match = choose_match(exact_matches)
        match_method = "EXACT_DATE_TRACK_RACE_RUNNER" if match else ""
        match_confidence = "HIGH" if match else ""

        candidate_not_current = False
        if match is None:
            no_date_matches: list[dict[str, object]] = []
            for tkey in tkeys:
                for hkey in hkeys:
                    no_date_matches.extend(no_date_index.get(market_row_key("", tkey, race_no, hkey), []))
            match = choose_match(no_date_matches)
            if match is not None:
                match_method = "TRACK_RACE_RUNNER_NO_DATE"
                match_confidence = "LOW"
                candidate_not_current = True

        race_has_current_rows = any(race_key_only(race_date, tkey, race_no) in current_race_keys for tkey in tkeys)
        fail_reason = ""
        if candidate_not_current:
            fail_reason = "UNDATED_PRICE_CANDIDATE_NOT_CURRENT"
        elif match is None:
            same_race_source_rows = 0
            for source in candidate_sources:
                if int(source.get("current_day_rows") or 0) <= 0:
                    continue
                same_race_source_rows += int(source.get("matched_current_terminal_runners") or 0)
            terminal_status = clean(row.get("market_source_status") or row.get("ui_status"))
            terminal_file = clean(row.get("market_source_file"))
            terminal_rows = clean(row.get("market_source_rows"))
            if terminal_status:
                fail_reason = f"NO_RUNNER_MARKET_MATCH | terminal_status={terminal_status}"
            else:
                fail_reason = "NO_RUNNER_MARKET_MATCH"
            if terminal_file:
                fail_reason += f" | terminal_source_file={terminal_file}"
            if terminal_rows:
                fail_reason += f" | terminal_source_rows={terminal_rows}"
            if not race_has_current_rows:
                fail_reason += " | NO_CURRENT_TERMINAL_RACE_CONTEXT"
            if same_race_source_rows == 0:
                fail_reason += " | NO_CURRENT_DAY_SOURCE_MATCHES_TO_TERMINAL_RUNNERS"

        runner_reviews.append(
            {
                "horse": runner_name,
                "track": clean(row.get("track")),
                "race_no": race_no,
                "race_time": clean(row.get("race_time")),
                "matched_market_source": clean(match.get("source_name")) if match else "",
                "market_price_found": "NO_CURRENT_PRICE" if candidate_not_current else ("YES" if match else "NO"),
                "market_price": fmt(float(match["price"])) if match else "",
                "market_price_column": clean(match.get("price_column")) if match else "",
                "source_race_date": clean(match.get("race_date")) if match else "",
                "source_track": clean(match.get("track")) if match else "",
                "source_race_no": clean(match.get("race_no")) if match else "",
                "source_horse": clean(match.get("horse")) if match else "",
                "source_bookmaker": clean(match.get("bookmaker")) if match else "",
                "source_timestamp": clean(match.get("timestamp")) if match else "",
                "match_method": match_method if match else "NO_MATCH",
                "match_confidence": match_confidence if match else "NONE",
                "fail_reason": fail_reason,
            }
        )

    matched_count = sum(1 for row in runner_reviews if row["market_price_found"] == "YES")
    candidate_only_count = sum(1 for row in runner_reviews if row["market_price_found"] == "NO_CURRENT_PRICE")
    failed_count = len(runner_reviews) - matched_count
    source_match_counts = Counter(row["matched_market_source"] or "NO_MATCH" for row in runner_reviews)
    match_method_counts = Counter(row["match_method"] for row in runner_reviews)
    fail_reason_counts = Counter(row["fail_reason"].split(" | ")[0] if row["fail_reason"] else "MATCHED" for row in runner_reviews)

    audit_rows: list[dict[str, object]] = [
        audit_row("summary", "terminal_feed_rows", len(terminal_rows_all), len(terminal_rows_all), str(TERMINAL_FEED)),
        audit_row("summary", "current_terminal_runner_rows", len(current_rows), len(current_rows), "Filtered to day_bucket=TODAY when available."),
        audit_row("summary", "files_scanned", files_scanned, files_scanned),
        audit_row("summary", "candidate_sources_written", len(candidate_sources), len(candidate_sources)),
        audit_row("summary", "candidates_with_price_columns", candidates_with_price_columns, candidates_with_price_columns),
        audit_row("summary", "terminal_runners_with_market_match", matched_count, matched_count),
        audit_row("summary", "terminal_runners_without_market_match", failed_count, failed_count),
        audit_row("summary", "terminal_runners_with_undated_candidate_only", candidate_only_count, candidate_only_count),
    ]

    for source, count in sorted(source_match_counts.items()):
        audit_rows.append(audit_row("runner_match_source_counts", "matched_market_source", source, count))
    for method, count in sorted(match_method_counts.items()):
        audit_rows.append(audit_row("runner_match_method_counts", "match_method", method, count))
    for reason, count in sorted(fail_reason_counts.items()):
        audit_rows.append(audit_row("runner_fail_reason_counts", "fail_reason", reason, count))

    candidate_sources.sort(
        key=lambda row: (
            -(int(row.get("matched_current_terminal_runners") or 0) if str(row.get("matched_current_terminal_runners") or "").isdigit() else 0),
            -(int(row.get("current_day_rows") or 0) if str(row.get("current_day_rows") or "").isdigit() else 0),
            str(row.get("file_path") or ""),
        )
    )

    write_csv(SOURCES_OUT, candidate_sources, SOURCE_FIELDS_OUT)
    write_csv(RUNNER_REVIEW_OUT, runner_reviews, RUNNER_REVIEW_FIELDS)
    write_csv(AUDIT_OUT, audit_rows, AUDIT_FIELDS)

    print("=" * 100)
    print("EDGEIQ LIVE MARKET PRICE INGESTION AUDIT V1")
    print("=" * 100)
    print(f"terminal_feed_rows={len(terminal_rows_all)}")
    print(f"current_terminal_runner_rows={len(current_rows)}")
    print(f"files_scanned={files_scanned}")
    print(f"candidate_sources_written={len(candidate_sources)}")
    print(f"candidates_with_price_columns={candidates_with_price_columns}")
    print(f"terminal_runners_with_market_match={matched_count}")
    print(f"terminal_runners_without_market_match={failed_count}")
    print(f"terminal_runners_with_undated_candidate_only={candidate_only_count}")
    print()
    print("MATCH SOURCES")
    for source, count in sorted(source_match_counts.items()):
        print(f"{source}: {count}")
    print()
    print("SAVED:")
    print(AUDIT_OUT)
    print(RUNNER_REVIEW_OUT)
    print(SOURCES_OUT)


if __name__ == "__main__":
    main()
