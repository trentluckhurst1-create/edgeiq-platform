from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

csv.field_size_limit(1024 * 1024 * 128)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
HISTORICAL_RESULTS = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"

ENRICHED_JSON = DATA / "edgeiq_form_guide_enriched_v1.json"
ENRICHED_CSV = DATA / "edgeiq_form_guide_enriched_v1.csv"
SOURCE_INVENTORY = DATA / "edgeiq_form_guide_v2_1_source_inventory.csv"
SOURCE_INVENTORY_SUMMARY = DATA / "edgeiq_form_guide_v2_1_source_inventory_summary.txt"
COVERAGE_CSV = DATA / "edgeiq_form_guide_v2_1_coverage.csv"
COVERAGE_SUMMARY = DATA / "edgeiq_form_guide_v2_1_coverage_summary.txt"
JOIN_AUDIT = DATA / "edgeiq_form_guide_v2_1_join_audit.csv"

RELEVANT_TERMS = (
    "live_runner_board",
    "live_terminal",
    "fair_price",
    "display_fair_price",
    "ui_fair_price",
    "rated_price",
    "calibrated_price",
    "projected_rating",
    "performance_rating",
    "runner_profile",
    "runner_stats",
    "runner_dna",
    "distance_dna",
    "condition_dna",
    "class_dna",
    "historical_form",
    "results_warehouse",
    "last_run_date",
    "days_since",
    "market_price",
    "live_price",
    "sportsbet_price",
    "fixed_win",
    "odds",
    "track_record",
    "distance_record",
    "condition_record",
    "race_date",
    "race_number",
    "runner_name",
    "runner_id",
)

MARKET_PROVIDER_PRIORITY = (
    "SB2",
    "SB",
    "SPORTSBET",
    "BT",
    "BTOTE",
    "LB2",
    "LADBROKES",
    "N",
    "Q",
    "V",
)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    if text.lower() in {"", "-", "none", "null", "n/a", "na"}:
        return ""
    return text


def normalise_date(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return ""


def normalise_track(value: Any) -> str:
    text = clean_text(value).upper()
    text = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|TAB|THE)\b", " ", text)
    text = re.sub(r"\b(RACECOURSE|RACING|TRACK)\b", " ", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def normalise_runner_name(value: Any) -> str:
    text = clean_text(value).upper()
    text = re.sub(r"\s*\([A-Z]{2,3}\)\s*$", "", text)
    text = text.replace("'", "")
    text = text.replace("’", "")
    text = text.replace("&", "AND")
    return re.sub(r"[^A-Z0-9]+", "", text)


def normalise_runner_id(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "", clean_text(value))


def normalise_race_number(value: Any) -> str:
    text = clean_text(value).upper().replace("R", "")
    match = re.search(r"\d+", text)
    return match.group(0) if match else ""


def parse_number(value: Any) -> float | None:
    text = clean_text(value).replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    if not (parsed > 0 and parsed < 10000):
        return None
    return parsed


def parse_int(value: Any) -> int | None:
    text = clean_text(value)
    match = re.search(r"-?\d+", text)
    return int(match.group(0)) if match else None


def condition_family(value: Any) -> str:
    text = clean_text(value).upper()
    if "SYNTH" in text:
        return "SYNTHETIC"
    if "HEAVY" in text:
        return "HEAVY"
    if "SOFT" in text:
        return "SOFT"
    if "GOOD" in text:
        return "GOOD"
    if "FIRM" in text:
        return "FIRM"
    return ""


def distance_metres(value: Any) -> int | None:
    return parse_int(value)


def finish_num(value: Any) -> int | None:
    n = parse_int(value)
    if n is None or n <= 0 or n > 50:
        return None
    return n


def record_summary(runs: list[dict[str, Any]], predicate=lambda _run: True) -> dict[str, Any] | None:
    selected = [run for run in runs if predicate(run)]
    starts = len(selected)
    if starts <= 0:
        return None
    wins = sum(1 for run in selected if finish_num(run.get("finish")) == 1)
    seconds = sum(1 for run in selected if finish_num(run.get("finish")) == 2)
    thirds = sum(1 for run in selected if finish_num(run.get("finish")) == 3)
    return {
        "starts": starts,
        "wins": wins,
        "seconds": seconds,
        "thirds": thirds,
        "places": wins + seconds + thirds,
        "winPct": round((wins / starts) * 100, 1) if starts else 0,
        "placePct": round(((wins + seconds + thirds) / starts) * 100, 1) if starts else 0,
        "display": f"{starts}:{wins}-{seconds}-{thirds}",
    }


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def classify_file(path: Path, columns: list[str]) -> tuple[str, str]:
    name = path.name.lower()
    cols = " ".join(columns).lower()
    if any(token in name for token in ("audit", "summary", "checkpoint", "backup", "before")):
        return "audit", "NO"
    if "research" in name or "research" in cols:
        return "research", "NO"
    if any(token in name for token in ("deprecated", "legacy", "old")):
        return "deprecated", "NO"
    if "warehouse" in name or "historical" in name or "results_history" in name:
        return "historical", "YES for official historical form only"
    if "three_day_product_catalog" in name:
        return "production", "YES for current race identity and embedded current odds"
    if "live_runner_board" in name or "live_market" in name or "sportsbet" in name:
        return "production", "YES only when same race date/meeting/race/runner joins"
    if path.suffix.lower() in {".ts", ".tsx", ".py"}:
        return "source_code", "NO direct customer data"
    return "production", "REVIEW"


def source_inventory(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    current_dates = {clean_text(meeting.get("date")) for meeting in catalog.get("meetings", [])}
    current_tracks = {normalise_track(meeting.get("meeting")) for meeting in catalog.get("meetings", [])}
    rows: list[dict[str, Any]] = []
    data_candidates = [
        CATALOG,
        HISTORICAL_RESULTS,
        DATA / "edgeiq_live_runner_board_v1.csv",
        DATA / "edgeiq_live_runner_board_governed_v1.csv",
        DATA / "edgeiq_runner_profile_stats_v1.csv",
        DATA / "edgeiq_form_sectional_terminal_feed_v1.csv",
        DATA / "edgeiq_gear_terminal_feed_v1.csv",
        DATA / "sportsbet_live_market_v1.csv",
        DATA / "sportsbet_live_market_full_day_v5_2.csv",
        DATA / "rated_market_v5_2_market_coverage_safe.csv",
        DATA / "results_history.csv",
        DATA / "runner_form_history.csv",
        DATA / "results_tab_feed.csv",
    ]
    code_candidates: list[Path] = []
    for root in [ROOT / "scripts", ROOT / "src" / "edgeiq-os"]:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".py", ".ts", ".tsx"}:
                continue
            name_match = any(term.lower() in path.name.lower() for term in RELEVANT_TERMS)
            if name_match:
                code_candidates.append(path)
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if any(term.lower() in text.lower() for term in RELEVANT_TERMS):
                code_candidates.append(path)

    for path in [*data_candidates, *sorted(set(code_candidates))]:
        if not path.exists() or not path.is_file():
            continue

        rel = str(path.relative_to(ROOT))
        name_match = any(term.lower() in path.name.lower() for term in RELEVANT_TERMS)
        columns: list[str] = []
        row_count: str | int = ""
        date_min = ""
        date_max = ""
        meeting_count = ""
        race_count = ""
        runner_name_count = ""
        runner_id_count = ""
        contains_current = "UNKNOWN"

        try:
            if path.suffix.lower() == ".csv":
                with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
                    reader = csv.DictReader(handle)
                    columns = reader.fieldnames or []
                    header_match = any(term.lower() in " ".join(columns).lower() for term in RELEVANT_TERMS)
                    if not name_match and not header_match:
                        continue
                    date_values: list[str] = []
                    meetings: set[str] = set()
                    race_keys: set[str] = set()
                    runner_names: set[str] = set()
                    runner_ids: set[str] = set()
                    current_hit = False
                    count = 0
                    for row in reader:
                        count += 1
                        d = normalise_date(row.get("race_date") or row.get("date") or row.get("meeting_date"))
                        t = normalise_track(row.get("track") or row.get("meeting") or row.get("venue_name") or row.get("venue"))
                        rn = normalise_race_number(row.get("race_no") or row.get("race_number") or row.get("raceNumber"))
                        horse = normalise_runner_name(row.get("runner_name") or row.get("runner") or row.get("horse") or row.get("horseName"))
                        rid = normalise_runner_id(row.get("runner_id") or row.get("horse_code") or row.get("horseCode") or row.get("horse_key"))
                        if d:
                            date_values.append(d)
                        if t:
                            meetings.add(t)
                        if d and t and rn:
                            race_keys.add(f"{d}|{t}|{rn}")
                        if horse:
                            runner_names.add(horse)
                        if rid:
                            runner_ids.add(rid)
                        if d in current_dates and t in current_tracks:
                            current_hit = True
                    row_count = count
                    date_min = min(date_values) if date_values else ""
                    date_max = max(date_values) if date_values else ""
                    meeting_count = len(meetings)
                    race_count = len(race_keys)
                    runner_name_count = len(runner_names)
                    runner_id_count = len(runner_ids)
                    contains_current = "YES" if current_hit else "NO"
            elif path.suffix.lower() == ".json":
                text = path.read_text(encoding="utf-8", errors="replace")
                if not name_match and not any(term.lower() in text[:20000].lower() for term in RELEVANT_TERMS):
                    continue
                columns = ["json"]
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, list):
                        row_count = len(parsed)
                    elif isinstance(parsed, dict):
                        if isinstance(parsed.get("meetings"), list):
                            row_count = sum(
                                len(race.get("runners", []))
                                for meeting in parsed.get("meetings", [])
                                for race in meeting.get("races", [])
                            )
                            date_values = [clean_text(meeting.get("date")) for meeting in parsed.get("meetings", []) if clean_text(meeting.get("date"))]
                            date_min = min(date_values) if date_values else ""
                            date_max = max(date_values) if date_values else ""
                            meeting_count = len(parsed.get("meetings", []))
                            race_count = sum(len(meeting.get("races", [])) for meeting in parsed.get("meetings", []))
                            runner_name_count = row_count
                            runner_id_count = sum(
                                1
                                for meeting in parsed.get("meetings", [])
                                for race in meeting.get("races", [])
                                for runner in race.get("runners", [])
                                if normalise_runner_id((runner.get("source") or {}).get("horseCode") or (runner.get("source") or {}).get("id"))
                            )
                            contains_current = "YES"
                        else:
                            row_count = len(parsed)
                except json.JSONDecodeError:
                    row_count = ""
            else:
                text = path.read_text(encoding="utf-8", errors="replace")
                if not name_match and not any(term.lower() in text.lower() for term in RELEVANT_TERMS):
                    continue
                columns = sorted({term for term in RELEVANT_TERMS if term.lower() in text.lower()})
                row_count = ""
                contains_current = "N/A"
        except OSError as exc:
            columns = [f"READ_ERROR: {exc}"]

        feed_type, safe = classify_file(path, columns)
        rows.append(
            {
                "filename": rel,
                "row_count": row_count,
                "relevant_columns": "|".join(columns[:80]),
                "date_coverage": f"{date_min}..{date_max}" if date_min or date_max else "",
                "meeting_coverage": meeting_count,
                "race_coverage": race_count,
                "runner_name_coverage": runner_name_count,
                "runner_id_coverage": runner_id_count,
                "contains_current_selected_race_data": contains_current,
                "feed_type": feed_type,
                "safe_for_customer_facing_use": safe,
            }
        )

    rows.sort(key=lambda item: item["filename"])
    return rows


def load_historical_runs(current_runner_names: set[str]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    history: dict[str, list[dict[str, Any]]] = defaultdict(list)
    field_sizes: Counter[str] = Counter()
    if not HISTORICAL_RESULTS.exists():
        return history, {}

    with HISTORICAL_RESULTS.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            norm = normalise_runner_name(row.get("horse"))
            if clean_text(row.get("scratched")).upper() in {"TRUE", "YES", "Y", "1"}:
                continue
            if clean_text(row.get("has_results")).upper() in {"FALSE", "NO", "N", "0"}:
                continue
            race_key = historical_race_key(row)
            if race_key:
                field_sizes[race_key] += 1
            if norm not in current_runner_names:
                continue
            history[norm].append(row)

    for runs in history.values():
        runs.sort(key=lambda item: normalise_date(item.get("race_date")), reverse=True)

    return history, dict(field_sizes)


def historical_race_key(row: dict[str, Any]) -> str:
    race_id = clean_text(row.get("race_id"))
    if race_id:
        return f"race_id:{race_id}"
    return "|".join(
        [
            normalise_date(row.get("race_date")),
            normalise_track(row.get("track") or row.get("venue_name")),
            normalise_race_number(row.get("race_no")),
        ]
    )


def class_bucket(value: Any) -> str:
    text = clean_text(value).upper()
    if not text:
        return ""
    if "MAIDEN" in text or "MDN" in text:
        return "Maiden"
    match = re.search(r"BM\s*([0-9]+)", text)
    if match:
        rating = int(match.group(1))
        if rating <= 64:
            return "BM64 & Below"
        if rating <= 78:
            return "BM65-78"
        return "BM79+"
    if "GROUP" in text or re.search(r"\bG[123]\b", text):
        return "Group/Listed"
    if "LISTED" in text or text == "LR":
        return "Group/Listed"
    return clean_text(value)


def profile_rows_by_key(runs: list[dict[str, Any]], key_func, limit: int | None = None) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        key = key_func(run)
        if key:
            grouped[key].append(run)

    rows = [
        {"label": label, **summary}
        for label, items in grouped.items()
        if (summary := record_summary(items)) is not None
    ]
    rows.sort(key=lambda row: (-int(row.get("starts") or 0), str(row.get("label") or "")))
    return rows[:limit] if limit else rows


def market_from_runner(source: dict[str, Any]) -> tuple[float | None, str | None, str | None]:
    quotes = source.get("odds")
    if not isinstance(quotes, list):
        return None, None, None

    valid_quotes: list[tuple[int, float, str, str | None]] = []
    for quote in quotes:
        if not isinstance(quote, dict):
            continue
        price = parse_number(quote.get("oddsWin") or quote.get("winOdds"))
        if price is None:
            continue
        provider = clean_text(quote.get("providerCode")).upper()
        try:
            priority = MARKET_PROVIDER_PRIORITY.index(provider)
        except ValueError:
            priority = len(MARKET_PROVIDER_PRIORITY)
        as_at = None
        flucs = quote.get("flucsWin")
        if isinstance(flucs, list) and flucs:
            latest = flucs[-1]
            if isinstance(latest, dict):
                as_at = clean_text(latest.get("updateTime"))
        valid_quotes.append((priority, price, provider or "UNKNOWN", as_at))

    if not valid_quotes:
        return None, None, None

    priority, price, provider, as_at = sorted(valid_quotes, key=lambda item: item[0])[0]
    return price, f"edgeiq_three_day_product_catalog_v1.json:source.odds[{provider}].oddsWin", as_at


def form_run_from_history(row: dict[str, Any], field_sizes: dict[str, int]) -> dict[str, Any]:
    return {
        "date": normalise_date(row.get("race_date")) or None,
        "track": clean_text(row.get("track")) or clean_text(row.get("venue_name")) or None,
        "raceNumber": parse_int(row.get("race_no")),
        "distance": distance_metres(row.get("distance")),
        "condition": clean_text(row.get("track_condition")) or None,
        "conditionFamily": condition_family(row.get("track_condition")) or None,
        "class": clean_text(row.get("race_class")) or None,
        "position": finish_num(row.get("finish")) or clean_text(row.get("finish")) or None,
        "fieldSize": field_sizes.get(historical_race_key(row)) or None,
        "barrier": parse_int(row.get("barrier")),
        "weight": clean_text(row.get("weight")) or None,
        "jockey": clean_text(row.get("jockey")) or None,
        "margin": clean_text(row.get("margin")) or clean_text(row.get("margin_l")) or None,
        "startingPrice": clean_text(row.get("starting_price")) or None,
        "performanceRating": None,
        "note": clean_text(row.get("comment_short")) or None,
    }


def selected_race_key(date_value: str, meeting: str, race_number: Any) -> str:
    return f"{normalise_date(date_value)}|{normalise_track(meeting)}|{normalise_race_number(race_number)}"


def build_enriched() -> dict[str, Any]:
    if not CATALOG.exists():
        raise FileNotFoundError(f"Missing catalogue: {CATALOG}")

    catalog = read_json(CATALOG)
    current_names: set[str] = set()
    current_runner_keys: Counter[str] = Counter()

    for meeting in catalog.get("meetings", []):
        for race in meeting.get("races", []):
            for runner in race.get("runners", []):
                official = runner.get("official") or {}
                source = runner.get("source") or {}
                name = clean_text(official.get("runner")) or clean_text(source.get("horseName"))
                current_names.add(normalise_runner_name(name))
                current_runner_keys[
                    "|".join(
                        [
                            selected_race_key(meeting.get("date"), meeting.get("meeting"), race.get("raceNumber")),
                            normalise_runner_name(name),
                        ]
                    )
                ] += 1

    history_by_name, historical_field_sizes = load_historical_runs(current_names)

    race_payloads: list[dict[str, Any]] = []
    enriched_rows: list[dict[str, Any]] = []
    join_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    duplicate_keys: Counter[str] = Counter()

    for meeting in catalog.get("meetings", []):
        meeting_name = clean_text(meeting.get("meeting"))
        race_date = normalise_date(meeting.get("date"))
        for race in meeting.get("races", []):
            race_number = parse_int(race.get("raceNumber"))
            race_key = selected_race_key(race_date, meeting_name, race_number)
            selected_distance = distance_metres(race.get("distance"))
            selected_condition = condition_family(race.get("trackCondition"))
            runners_payload: list[dict[str, Any]] = []
            metrics = Counter()

            for index, runner in enumerate(race.get("runners", []), start=1):
                official = runner.get("official") or {}
                source = runner.get("source") or {}
                runner_name = clean_text(official.get("runner")) or clean_text(source.get("horseName")) or "Unnamed runner"
                norm_name = normalise_runner_name(runner_name)
                runner_id = normalise_runner_id(source.get("horseCode") or source.get("id")) or None
                runner_number = parse_int(official.get("no") or official.get("number") or source.get("raceEntryNumber")) or index
                row_key = f"{race_key}|{runner_number}|{norm_name}"
                duplicate_keys[row_key] += 1

                composite_key = f"{race_key}|{norm_name}"
                ambiguous_reason = "duplicate runner name in selected race" if current_runner_keys[composite_key] > 1 else ""
                join_method = "AMBIGUOUS" if ambiguous_reason else ("RUNNER_ID" if runner_id else "STRICT_COMPOSITE")

                all_history = history_by_name.get(norm_name, [])
                selected_history = [
                    run for run in all_history if normalise_date(run.get("race_date")) and normalise_date(run.get("race_date")) < race_date
                ]
                selected_history.sort(key=lambda item: normalise_date(item.get("race_date")), reverse=True)
                full_form = [form_run_from_history(run, historical_field_sizes) for run in selected_history[:20]]
                last_five = [
                    str(item.get("position"))
                    for item in full_form[:5]
                    if item.get("position") is not None and str(item.get("position")).strip()
                ]
                last_run_date = full_form[0].get("date") if full_form else None
                days = None
                if last_run_date and race_date:
                    days = (datetime.fromisoformat(race_date) - datetime.fromisoformat(str(last_run_date))).days
                    if days < 0:
                        days = None

                market_price, market_source, market_as_at = market_from_runner(source)
                track_record = record_summary(
                    selected_history,
                    lambda run: normalise_track(run.get("track") or run.get("venue_name")) == normalise_track(meeting_name),
                )
                distance_record = record_summary(
                    selected_history,
                    lambda run: selected_distance is not None and distance_metres(run.get("distance")) == selected_distance,
                )
                condition_record = record_summary(
                    selected_history,
                    lambda run: bool(selected_condition) and condition_family(run.get("track_condition")) == selected_condition,
                )
                career_record = record_summary(selected_history)
                track_distance_record = record_summary(
                    selected_history,
                    lambda run: normalise_track(run.get("track") or run.get("venue_name")) == normalise_track(meeting_name)
                    and selected_distance is not None
                    and distance_metres(run.get("distance")) == selected_distance,
                )
                condition_profile = profile_rows_by_key(
                    selected_history,
                    lambda run: condition_family(run.get("track_condition")).title() if condition_family(run.get("track_condition")) else "",
                )
                class_profile = profile_rows_by_key(
                    selected_history,
                    lambda run: class_bucket(run.get("race_class")),
                    limit=8,
                )
                selected_jockey = clean_text(official.get("jockey") or source.get("jockeyName") or source.get("jockey"))
                jockey_with_horse = record_summary(
                    selected_history,
                    lambda run: bool(selected_jockey)
                    and normalise_runner_name(run.get("jockey")) == normalise_runner_name(selected_jockey),
                )
                other_jockeys = record_summary(
                    selected_history,
                    lambda run: bool(selected_jockey)
                    and normalise_runner_name(run.get("jockey")) != normalise_runner_name(selected_jockey),
                )

                scratched = bool(official.get("scratched")) or clean_text(source.get("scratched")).upper() in {"TRUE", "YES", "Y", "1"}
                first_starter = len(selected_history) == 0
                payload = {
                    "raceDate": race_date,
                    "meeting": meeting_name,
                    "raceNumber": race_number,
                    "raceKey": race_key,
                    "runnerId": runner_id,
                    "runnerNumber": runner_number,
                    "runnerName": runner_name,
                    "normalisedRunnerName": norm_name,
                    "lastRunDate": last_run_date,
                    "daysSinceLastRun": days,
                    "epi": None,
                    "epiSource": None,
                    "marketPrice": None if scratched else market_price,
                    "marketSource": None if scratched or market_price is None else market_source,
                    "marketAsAt": None if scratched or market_price is None else market_as_at,
                    "edgeiqPrice": None,
                    "edgeiqPriceSource": None,
                    "trackRecord": track_record,
                    "distanceRecord": distance_record,
                    "conditionRecord": condition_record,
                    "careerRecord": career_record,
                    "trackDistanceRecord": track_distance_record,
                    "conditionProfile": condition_profile,
                    "classProfile": class_profile,
                    "jockeyProfile": {
                        "currentJockey": selected_jockey or None,
                        "jockeyWithHorse": jockey_with_horse,
                        "otherJockeys": other_jockeys,
                    },
                    "raceDayPattern": [],
                    "lastStart": full_form[0] if full_form else None,
                    "fullForm": full_form,
                    "lastFive": last_five,
                    "joinMethod": join_method,
                    "historySource": "edgeiq_historical_results_warehouse_v2_graphql.csv:horse exact normalised name" if selected_history else None,
                    "recordSource": "edgeiq_historical_results_warehouse_v2_graphql.csv official results aggregation" if selected_history else None,
                    "firstStarter": first_starter,
                    "scratched": scratched,
                }
                runners_payload.append(payload)
                enriched_rows.append(
                    {
                        "raceDate": race_date,
                        "meeting": meeting_name,
                        "raceNumber": race_number,
                        "runnerId": runner_id or "",
                        "runnerNumber": runner_number,
                        "runnerName": runner_name,
                        "lastRunDate": last_run_date or "",
                        "daysSinceLastRun": "" if days is None else days,
                        "epi": "",
                        "epiSource": "",
                        "marketPrice": "" if payload["marketPrice"] is None else payload["marketPrice"],
                        "marketSource": payload["marketSource"] or "",
                        "marketAsAt": payload["marketAsAt"] or "",
                        "edgeiqPrice": "",
                        "edgeiqPriceSource": "",
                        "trackRecord": track_record["display"] if track_record else "",
                        "distanceRecord": distance_record["display"] if distance_record else "",
                        "conditionRecord": condition_record["display"] if condition_record else "",
                        "fullFormCount": len(full_form),
                        "joinMethod": join_method,
                        "historySource": payload["historySource"] or "",
                    }
                )
                join_rows.append(
                    {
                        "race_date": race_date,
                        "meeting": meeting_name,
                        "race_number": race_number,
                        "runner_number": runner_number,
                        "runner_name": runner_name,
                        "runner_id": runner_id or "",
                        "join_method": join_method,
                        "matched_source_file": payload["historySource"] or "",
                        "matched_source_runner": full_form[0]["track"] if full_form else "",
                        "epi_match": "NO",
                        "market_match": "YES" if payload["marketPrice"] is not None else "NO",
                        "edgeiq_price_match": "NO",
                        "history_match": "YES" if full_form else "NO",
                        "ambiguity_reason": ambiguous_reason,
                    }
                )
                metrics["runners"] += 1
                metrics["runner_id_joins"] += 1 if join_method == "RUNNER_ID" else 0
                metrics["strict_composite_joins"] += 1 if join_method == "STRICT_COMPOSITE" else 0
                metrics["ambiguous_joins"] += 1 if join_method == "AMBIGUOUS" else 0
                metrics["unmatched_runners"] += 1 if join_method == "UNMATCHED" else 0
                metrics["last_run_date"] += 1 if last_run_date else 0
                metrics["days"] += 1 if days is not None else 0
                metrics["epi"] += 0
                metrics["market"] += 1 if payload["marketPrice"] is not None else 0
                metrics["edgeiq_price"] += 0
                metrics["track"] += 1 if track_record else 0
                metrics["dist"] += 1 if distance_record else 0
                metrics["cond"] += 1 if condition_record else 0
                metrics["full_form_history"] += 1 if full_form else 0
                metrics["first_starters"] += 1 if first_starter else 0
                metrics["scratchings"] += 1 if scratched else 0

            race_payloads.append(
                {
                    "raceDate": race_date,
                    "meeting": meeting_name,
                    "raceNumber": race_number,
                    "raceKey": race_key,
                    "runners": runners_payload,
                }
            )
            coverage_rows.append(
                {
                    "race_date": race_date,
                    "meeting": meeting_name,
                    "race_number": race_number,
                    "runners": metrics["runners"],
                    "runner_id_joins": metrics["runner_id_joins"],
                    "strict_composite_joins": metrics["strict_composite_joins"],
                    "ambiguous_joins": metrics["ambiguous_joins"],
                    "unmatched_runners": metrics["unmatched_runners"],
                    "last_run_date": metrics["last_run_date"],
                    "DAYS": metrics["days"],
                    "EPI": metrics["epi"],
                    "MARKET": metrics["market"],
                    "EDGEiQ_PRICE": metrics["edgeiq_price"],
                    "TRACK": metrics["track"],
                    "DIST": metrics["dist"],
                    "COND": metrics["cond"],
                    "full_form_history": metrics["full_form_history"],
                    "first_starters": metrics["first_starters"],
                    "scratchings": metrics["scratchings"],
                }
            )

    duplicates = [key for key, count in duplicate_keys.items() if count > 1]
    if duplicates:
        raise RuntimeError(f"Duplicate enriched runner keys detected: {duplicates[:10]}")

    inventory_rows = source_inventory(catalog)
    write_csv(
        SOURCE_INVENTORY,
        inventory_rows,
        [
            "filename",
            "row_count",
            "relevant_columns",
            "date_coverage",
            "meeting_coverage",
            "race_coverage",
            "runner_name_coverage",
            "runner_id_coverage",
            "contains_current_selected_race_data",
            "feed_type",
            "safe_for_customer_facing_use",
        ],
    )

    write_csv(
        ENRICHED_CSV,
        enriched_rows,
        [
            "raceDate",
            "meeting",
            "raceNumber",
            "runnerId",
            "runnerNumber",
            "runnerName",
            "lastRunDate",
            "daysSinceLastRun",
            "epi",
            "epiSource",
            "marketPrice",
            "marketSource",
            "marketAsAt",
            "edgeiqPrice",
            "edgeiqPriceSource",
            "trackRecord",
            "distanceRecord",
            "conditionRecord",
            "fullFormCount",
            "joinMethod",
            "historySource",
        ],
    )
    write_csv(
        JOIN_AUDIT,
        join_rows,
        [
            "race_date",
            "meeting",
            "race_number",
            "runner_number",
            "runner_name",
            "runner_id",
            "join_method",
            "matched_source_file",
            "matched_source_runner",
            "epi_match",
            "market_match",
            "edgeiq_price_match",
            "history_match",
            "ambiguity_reason",
        ],
    )
    write_csv(
        COVERAGE_CSV,
        coverage_rows,
        [
            "race_date",
            "meeting",
            "race_number",
            "runners",
            "runner_id_joins",
            "strict_composite_joins",
            "ambiguous_joins",
            "unmatched_runners",
            "last_run_date",
            "DAYS",
            "EPI",
            "MARKET",
            "EDGEiQ_PRICE",
            "TRACK",
            "DIST",
            "COND",
            "full_form_history",
            "first_starters",
            "scratchings",
        ],
    )

    payload = {
        "schemaVersion": "edgeiq_form_guide_enriched_v1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceContract": {
            "joinMethods": ["RUNNER_ID", "STRICT_COMPOSITE", "UNMATCHED", "AMBIGUOUS"],
            "market": "Current embedded bookmaker odds only: edgeiq_three_day_product_catalog_v1.json source.odds[].oddsWin. Historical startingPrice/SP is not used as current market.",
            "epi": "No approved same-race production EPI feed selected for this three-day catalogue; left null.",
            "edgeiqPrice": "No approved same-race production assessed-price feed selected for this three-day catalogue; left null.",
            "daysAndFullForm": "edgeiq_historical_results_warehouse_v2_graphql.csv official starts before selected race date.",
            "records": "Official historical results aggregated as starts:wins-seconds-thirds; track rule is selected track exact normalisation; distance rule is exact metres; condition rule is selected condition family GOOD/SOFT/HEAVY/SYNTHETIC/FIRM.",
        },
        "races": race_payloads,
    }
    ENRICHED_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    totals = Counter()
    for row in coverage_rows:
        for key, value in row.items():
            if key in {"race_date", "meeting", "race_number"}:
                continue
            totals[key] += int(value or 0)

    SOURCE_INVENTORY_SUMMARY.write_text(
        "\n".join(
            [
                "EDGEiQ Form Guide V2.1 source inventory",
                f"Generated: {payload['generatedAt']}",
                f"Candidate files inventoried: {len(inventory_rows)}",
                "",
                "Canonical selections:",
                "DAYS: edgeiq_historical_results_warehouse_v2_graphql.csv race_date, selected race date minus most recent prior official start",
                "FULL FORM: edgeiq_historical_results_warehouse_v2_graphql.csv official historical rows",
                "TRACK: edgeiq_historical_results_warehouse_v2_graphql.csv aggregate by selected track exact normalisation",
                "DIST: edgeiq_historical_results_warehouse_v2_graphql.csv aggregate by exact distance metres",
                "COND: edgeiq_historical_results_warehouse_v2_graphql.csv aggregate by selected condition family",
                "MARKET: edgeiq_three_day_product_catalog_v1.json source.odds[].oddsWin current embedded bookmaker quotes only",
                "EPI: not selected; no approved same-race production EPI feed matched this catalogue",
                "EDGEiQ PRICE: not selected; no approved same-race production assessed-price feed matched this catalogue",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    COVERAGE_SUMMARY.write_text(
        "\n".join(
            [
                "EDGEiQ Form Guide V2.1 coverage summary",
                f"Generated: {payload['generatedAt']}",
                f"Runners: {totals['runners']}",
                f"Runner-ID joins: {totals['runner_id_joins']}",
                f"Strict-composite joins: {totals['strict_composite_joins']}",
                f"Ambiguous joins: {totals['ambiguous_joins']}",
                f"Unmatched runners: {totals['unmatched_runners']}",
                f"DAYS: {totals['DAYS']}/{totals['runners']}",
                f"MARKET: {totals['MARKET']}/{totals['runners']}",
                f"EDGEiQ PRICE: {totals['EDGEiQ_PRICE']}/{totals['runners']}",
                f"EPI: {totals['EPI']}/{totals['runners']}",
                f"FULL FORM: {totals['full_form_history']}/{totals['runners']}",
                f"TRACK: {totals['TRACK']}/{totals['runners']}",
                f"DIST: {totals['DIST']}/{totals['runners']}",
                f"COND: {totals['COND']}/{totals['runners']}",
                f"First starters: {totals['first_starters']}",
                f"Scratchings: {totals['scratchings']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {ENRICHED_JSON}")
    print(f"Wrote {ENRICHED_CSV}")
    print(f"Wrote {COVERAGE_CSV}")
    print(f"Wrote {JOIN_AUDIT}")
    print(COVERAGE_SUMMARY.read_text(encoding="utf-8"))
    return payload


if __name__ == "__main__":
    build_enriched()
