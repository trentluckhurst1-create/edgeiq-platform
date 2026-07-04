from __future__ import annotations

import csv
import html
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PRICE_TRUTH = DATA / "edgeiq_price_truth_history_v1.csv"

CALENDAR_URL = "https://www.racingaustralia.horse/FreeFields/Calendar_Results.aspx?State=VIC"
BASE_URL = "https://www.racingaustralia.horse"
TARGET_DATE = "2026-05-31"
TARGET_TRACK = "SANDOWN LAKESIDE"
TARGET_RACES = {str(number) for number in range(1, 9)}

CALENDAR_OUT = DATA / "racing_australia_vic_results_calendar_v1.csv"
RAW_RESULTS_OUT = DATA / "racing_australia_sandown_2026_05_31_raw_results_v1.csv"
NORMALISED_OUT = DATA / "racing_australia_sandown_2026_05_31_normalised_results_v1.csv"
AUDIT_OUT = DATA / "racing_australia_vic_results_pipeline_v1_audit.csv"

REQUEST_TIMEOUT_SECONDS = 45
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 EDGEiQ-Research"
)

CALENDAR_COLUMNS = [
    "calendar_date_label",
    "meeting_date",
    "state",
    "venue_label",
    "availability_label",
    "meeting_url",
    "availability_url",
    "track_normalised",
    "meeting_type",
    "target_match",
    "calendar_status",
]

RAW_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "race_name",
    "distance",
    "row_index",
    "finish_raw",
    "saddlecloth",
    "horse_raw",
    "trainer_raw",
    "jockey_raw",
    "margin_raw",
    "barrier_raw",
    "weight_raw",
    "penalty_raw",
    "starting_price_raw",
    "result_source_url",
    "raw_cells",
    "parse_status",
]

NORMALISED_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "race_name",
    "distance",
    "horse",
    "horse_key",
    "finish_position",
    "won",
    "starting_price",
    "margin",
    "jockey",
    "trainer",
    "barrier",
    "weight",
    "result_source_url",
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


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def has_text(value: object) -> bool:
    text = str(value or "").strip()
    return bool(text) and text.lower() not in {"nan", "none", "null"}


def clean(value: object) -> str:
    text = html.unescape(str(value or "")).strip()
    text = re.sub(r"\s+", " ", text)
    if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"}:
        return ""
    return text


def strip_html(value: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", value, flags=re.DOTALL)
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return clean(text)


def normalise_text(value: object) -> str:
    text = clean(value).upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.replace("&", " AND ")
    text = re.sub(r"\([^)]*\)", " ", text)
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
        return "SANDOWN LAKESIDE"
    if track.startswith("SPORTSBET "):
        track = track.replace("SPORTSBET ", "", 1)
    return track


def clean_race_no(value: object) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def parse_price(value: object) -> str:
    text = clean(value)
    if not text:
        return ""
    if normalise_text(text) in {"SCR", "SCRATCHED", "SP", "TBA"}:
        return ""
    match = re.search(r"\d+(?:\.\d+)?", text.replace("$", ""))
    if not match:
        return ""
    return f"{float(match.group(0)):.2f}"


def parse_finish(value: object) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def parse_date_from_key(value: str) -> str:
    match = re.search(r"(20\d{2})([A-Za-z]{3})(\d{1,2})", value)
    if not match:
        return ""
    year, month_text, day = match.groups()
    try:
        parsed = datetime.strptime(f"{year}{month_text}{int(day):02d}", "%Y%b%d")
    except ValueError:
        return ""
    return parsed.strftime("%Y-%m-%d")


def absolute_url(href: str) -> str:
    raw_href = html.unescape(str(href or "")).strip()
    if not raw_href:
        return ""
    joined = urllib.parse.urljoin(BASE_URL, raw_href)
    parts = urllib.parse.urlsplit(joined)
    path = urllib.parse.quote(parts.path, safe="/")
    query = urllib.parse.quote(parts.query, safe="=&,")
    fragment = urllib.parse.quote(parts.fragment, safe="")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, fragment))


def result_key(row: dict[str, str]) -> str:
    return "|".join(
        [
            clean(row.get("race_date", "")),
            normalise_track(row.get("track", "")),
            clean_race_no(row.get("race_no", "")),
            horse_key(row.get("horse_key", "")) or horse_key(row.get("horse", "")),
        ]
    )


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


def fetch_url(url: str) -> tuple[str, str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-AU,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            content = response.read().decode(charset, errors="replace")
            return content, str(getattr(response, "status", "")), ""
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return body, str(exc.code), str(exc)
    except Exception as exc:  # noqa: BLE001 - audit output must preserve fetch failures.
        return "", "", repr(exc)


def parse_calendar(calendar_html: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    row_pattern = re.compile(
        r"<tr\b[^>]*class=['\"](?:EvenRow|OddRow)['\"][^>]*>(.*?)</tr>",
        flags=re.DOTALL | re.IGNORECASE,
    )
    for row_html in row_pattern.findall(calendar_html):
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row_html, flags=re.DOTALL | re.IGNORECASE)
        if len(cells) < 3:
            continue
        date_label = strip_html(cells[0])
        venue_link = re.search(r"<a\b[^>]*href=['\"]([^'\"]+)['\"][^>]*>(.*?)</a>", cells[1], flags=re.DOTALL | re.IGNORECASE)
        availability_link = re.search(r"<a\b[^>]*href=['\"]([^'\"]+)['\"][^>]*>(.*?)</a>", cells[2], flags=re.DOTALL | re.IGNORECASE)
        venue_label = strip_html(venue_link.group(2)) if venue_link else strip_html(cells[1])
        availability = strip_html(availability_link.group(2)) if availability_link else strip_html(cells[2])
        meeting_href = venue_link.group(1) if venue_link else ""
        availability_href = availability_link.group(1) if availability_link else ""
        meeting_date = parse_date_from_key(meeting_href)
        track = normalise_track(venue_label)
        meeting_type = "JUMPOUT" if "JUMPOUT" in normalise_text(venue_label) else "PROFESSIONAL"
        target_match = (
            meeting_date == TARGET_DATE
            and track == TARGET_TRACK
            and "AVAILABLE NOW" in normalise_text(availability)
            and meeting_type == "PROFESSIONAL"
        )
        rows.append(
            {
                "calendar_date_label": date_label,
                "meeting_date": meeting_date,
                "state": "VIC",
                "venue_label": venue_label,
                "availability_label": availability,
                "meeting_url": absolute_url(meeting_href),
                "availability_url": absolute_url(availability_href),
                "track_normalised": track,
                "meeting_type": meeting_type,
                "target_match": "TRUE" if target_match else "FALSE",
                "calendar_status": "PARSED",
            }
        )
    return rows


def extract_race_metadata(block: str, race_no: str) -> tuple[str, str]:
    race_title_match = re.search(
        r"<table\b[^>]*class=['\"]race-title['\"][^>]*>(.*?)</table>",
        block,
        flags=re.DOTALL | re.IGNORECASE,
    )
    race_title_text = strip_html(race_title_match.group(1)) if race_title_match else ""
    match = re.search(
        rf"Race\s+{re.escape(race_no)}\s*-\s*[0-9:]+\s*(?:AM|PM)\s+(.*?)\s*\((\d+)\s*METRES\)",
        race_title_text,
        flags=re.IGNORECASE,
    )
    if match:
        return clean(match.group(1)), match.group(2)
    match = re.search(rf"Race\s+{re.escape(race_no)}\s*-\s*(.*?)\s*\((\d+)\s*METRES\)", race_title_text, flags=re.IGNORECASE)
    if match:
        return clean(match.group(1)), match.group(2)
    return "", ""


def extract_cells(row_html: str) -> list[str]:
    cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row_html, flags=re.DOTALL | re.IGNORECASE)
    return [strip_html(cell) for cell in cells]


def cell_is_probable_horse(value: object) -> bool:
    text = normalise_text(value)
    return bool(re.search(r"[A-Z]", text)) and text not in {"SCR", "SCRATCHED"} and not re.fullmatch(r"\d+", text)


def map_result_cells(cells: list[str]) -> dict[str, str]:
    layouts = []
    if len(cells) >= 12:
        layouts.append(
            {
                "finish_raw": cells[1],
                "saddlecloth": cells[3],
                "horse": cells[4],
                "trainer": cells[5],
                "jockey": cells[6],
                "margin": cells[7],
                "barrier": cells[8],
                "weight": cells[9],
                "penalty": cells[10],
                "starting_price_raw": cells[11],
                "layout": "RA_12_CELL_COLOUR_BLANK",
            }
        )
    if len(cells) >= 11:
        layouts.append(
            {
                "finish_raw": cells[1],
                "saddlecloth": cells[2],
                "horse": cells[3],
                "trainer": cells[4],
                "jockey": cells[5],
                "margin": cells[6],
                "barrier": cells[7],
                "weight": cells[8],
                "penalty": cells[9],
                "starting_price_raw": cells[10],
                "layout": "RA_11_CELL_STANDARD",
            }
        )
    for layout in layouts:
        if cell_is_probable_horse(layout["horse"]):
            return layout
    return {}


def parse_meeting_results(meeting_html: str, source_url: str) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    raw_rows: list[dict[str, object]] = []
    normalised_rows: list[dict[str, object]] = []
    parts = re.split(r"<a\s+name=['\"]Race(\d+)['\"]\s*></a>", meeting_html, flags=re.IGNORECASE)
    if len(parts) <= 1:
        return raw_rows, normalised_rows

    for index in range(1, len(parts), 2):
        race_no = clean_race_no(parts[index])
        block = parts[index + 1]
        if race_no not in TARGET_RACES:
            continue
        race_name, distance = extract_race_metadata(block, race_no)
        table_match = re.search(
            r"<table\b[^>]*class=['\"]race-strip-fields['\"][^>]*>(.*?)</table>",
            block,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if not table_match:
            continue
        result_rows = re.findall(
            r"<tr\b[^>]*class=['\"](?:EvenRow|OddRow)['\"][^>]*>(.*?)</tr>",
            table_match.group(1),
            flags=re.DOTALL | re.IGNORECASE,
        )
        for row_index, row_html in enumerate(result_rows, start=1):
            cells = extract_cells(row_html)
            mapped = map_result_cells(cells)
            if not mapped:
                continue
            finish_raw = clean(mapped["finish_raw"])
            saddlecloth = clean(mapped["saddlecloth"])
            horse = clean(mapped["horse"])
            trainer = clean(mapped["trainer"])
            jockey = clean(mapped["jockey"])
            margin = clean(mapped["margin"])
            barrier = clean(mapped["barrier"])
            weight = clean(mapped["weight"])
            penalty = clean(mapped["penalty"])
            starting_price_raw = clean(mapped["starting_price_raw"])
            finish_position = parse_finish(finish_raw)
            starting_price = parse_price(starting_price_raw)
            won = "TRUE" if finish_position == "1" else "FALSE" if finish_position else ""
            result_status = "FINAL" if finish_position else "NO_FINISH_POSITION_IN_RA_ROW"

            raw_rows.append(
                {
                    "race_date": TARGET_DATE,
                    "track": TARGET_TRACK,
                    "race_no": race_no,
                    "race_name": race_name,
                    "distance": distance,
                    "row_index": row_index,
                    "finish_raw": finish_raw,
                    "saddlecloth": saddlecloth,
                    "horse_raw": horse,
                    "trainer_raw": trainer,
                    "jockey_raw": jockey,
                    "margin_raw": margin,
                    "barrier_raw": barrier,
                    "weight_raw": weight,
                    "penalty_raw": penalty,
                    "starting_price_raw": starting_price_raw,
                    "result_source_url": source_url,
                    "raw_cells": "|".join(cells),
                    "parse_status": f"PARSED_{mapped['layout']}",
                }
            )
            normalised_rows.append(
                {
                    "race_date": TARGET_DATE,
                    "track": TARGET_TRACK,
                    "race_no": race_no,
                    "race_name": race_name,
                    "distance": distance,
                    "horse": horse,
                    "horse_key": horse_key(horse),
                    "finish_position": finish_position,
                    "won": won,
                    "starting_price": starting_price,
                    "margin": margin,
                    "jockey": jockey,
                    "trainer": trainer,
                    "barrier": barrier,
                    "weight": weight,
                    "result_source_url": source_url,
                    "result_status": result_status,
                    "match_status": "",
                    "notes": "",
                }
            )
    return raw_rows, normalised_rows


def load_target_runners() -> dict[str, dict[str, str]]:
    columns, rows = read_csv(PRICE_TRUTH)
    required = {"race_date", "track", "race_no", "horse", "horse_key"}
    missing = sorted(required.difference(columns))
    if missing:
        raise ValueError(f"Price truth history missing required columns: {missing}")

    targets: dict[str, dict[str, str]] = {}
    for row in rows:
        race_date = clean(row.get("race_date", ""))
        track = normalise_track(row.get("track", ""))
        race_no = clean_race_no(row.get("race_no", ""))
        if race_date != TARGET_DATE or track != TARGET_TRACK or race_no not in TARGET_RACES:
            continue
        target = {
            "race_date": race_date,
            "track": TARGET_TRACK,
            "race_no": race_no,
            "horse": clean(row.get("horse", "")),
            "horse_key": horse_key(row.get("horse_key", "")) or horse_key(row.get("horse", "")),
            "is_scratched": clean(row.get("is_scratched", "")),
        }
        targets[result_key(target)] = target
    return targets


def apply_target_matching(normalised_rows: list[dict[str, object]], targets: dict[str, dict[str, str]]) -> tuple[int, int, int, int]:
    key_to_rows: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in normalised_rows:
        key = result_key(
            {
                "race_date": str(row.get("race_date", "")),
                "track": str(row.get("track", "")),
                "race_no": str(row.get("race_no", "")),
                "horse": str(row.get("horse", "")),
                "horse_key": str(row.get("horse_key", "")),
            }
        )
        key_to_rows[key].append(row)

    duplicate_matches = 0
    ambiguous_matches = 0
    for key, rows in key_to_rows.items():
        target_match = key in targets
        duplicate = len(rows) > 1 and target_match
        local_ambiguous = False
        if duplicate:
            duplicate_matches += len(rows) - 1
            signatures = {
                "|".join(
                    [
                        str(row.get("finish_position", "")),
                        str(row.get("won", "")),
                        str(row.get("starting_price", "")),
                    ]
                )
                for row in rows
            }
            local_ambiguous = len(signatures) > 1
            if local_ambiguous:
                ambiguous_matches += len(rows)

        for row in rows:
            if not target_match:
                row["match_status"] = "RESULT_NOT_IN_TARGET_PRICE_TRUTH"
                row["notes"] = "Racing Australia result row did not match current price-truth target runner key."
            elif local_ambiguous:
                row["match_status"] = "AMBIGUOUS_RESULT_MATCH"
                row["notes"] = "Multiple Racing Australia rows matched the same target runner key with conflicting result values."
            elif duplicate:
                row["match_status"] = "DUPLICATE_RESULT_MATCH"
                row["notes"] = "Multiple Racing Australia rows matched the same target runner key."
            else:
                row["match_status"] = "MATCHED_TARGET_RUNNER"
                row["notes"] = "Matched by race_date + track + race_no + horse_key."

    result_keys = set(key_to_rows)
    matched_target_keys = len(result_keys.intersection(targets))
    unmatched_target_keys = len(set(targets).difference(result_keys))
    return matched_target_keys, unmatched_target_keys, duplicate_matches, ambiguous_matches


def audit_row(section: str, metric: str, value: object, source_path: str = "", notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "source_path": source_path,
        "notes": notes,
        "built_at": now_utc(),
    }


def build_audit(
    *,
    calendar_html: str,
    calendar_error: str,
    calendar_rows: list[dict[str, object]],
    target_url: str,
    meeting_html: str,
    meeting_error: str,
    raw_rows: list[dict[str, object]],
    normalised_rows: list[dict[str, object]],
    targets: dict[str, dict[str, str]],
    matched_target_runners: int,
    unmatched_target_runners: int,
    duplicate_matches: int,
    ambiguous_matches: int,
) -> list[dict[str, object]]:
    target_link_found = bool(target_url)
    calendar_fetched = bool(calendar_html) and not calendar_error
    meeting_fetched = bool(meeting_html) and not meeting_error
    races_parsed = len({str(row.get("race_no", "")) for row in normalised_rows if has_text(row.get("race_no", ""))})
    finish_count = sum(1 for row in normalised_rows if has_text(row.get("finish_position", "")))
    winner_count = sum(1 for row in normalised_rows if has_text(row.get("won", "")))
    sp_count = sum(1 for row in normalised_rows if has_text(row.get("starting_price", "")))
    target_scratched = sum(1 for row in targets.values() if normalise_text(row.get("is_scratched", "")) in {"TRUE", "YES", "1"})
    settlement_ready = (
        calendar_fetched
        and target_link_found
        and meeting_fetched
        and races_parsed == 8
        and matched_target_runners == len(targets)
        and unmatched_target_runners == 0
        and duplicate_matches == 0
        and ambiguous_matches == 0
        and finish_count >= len(targets)
        and winner_count >= len(targets)
    )

    if not calendar_fetched or not target_link_found or not meeting_fetched or not normalised_rows:
        recommendation = "RESULTS_CAPTURE_FAILED"
    elif settlement_ready:
        recommendation = "RESULTS_CAPTURE_READY_FOR_SETTLEMENT_DIAGNOSTIC"
    else:
        recommendation = "RESULTS_PARTIAL_ONLY"

    rows = [
        audit_row("target", "target_date", TARGET_DATE),
        audit_row("target", "target_track", TARGET_TRACK),
        audit_row("target", "target_races", "R1-R8"),
        audit_row("fetch", "calendar_fetched", "YES" if calendar_fetched else "NO", CALENDAR_URL, calendar_error),
        audit_row("fetch", "target_meeting_link_found", "YES" if target_link_found else "NO", target_url),
        audit_row("fetch", "meeting_page_fetched", "YES" if meeting_fetched else "NO", target_url, meeting_error),
        audit_row("parse", "calendar_rows", len(calendar_rows), str(CALENDAR_OUT)),
        audit_row("parse", "races_parsed", races_parsed, str(RAW_RESULTS_OUT)),
        audit_row("parse", "raw_result_rows", len(raw_rows), str(RAW_RESULTS_OUT)),
        audit_row("parse", "normalised_result_rows", len(normalised_rows), str(NORMALISED_OUT)),
        audit_row("match", "target_truth_runners", len(targets), str(PRICE_TRUTH)),
        audit_row("match", "target_truth_scratched_flags", target_scratched, str(PRICE_TRUTH)),
        audit_row("match", "matched_target_runners", matched_target_runners, str(NORMALISED_OUT)),
        audit_row("match", "unmatched_target_runners", unmatched_target_runners, str(PRICE_TRUTH)),
        audit_row("match", "duplicate_matches", duplicate_matches, str(NORMALISED_OUT)),
        audit_row("match", "ambiguous_matches", ambiguous_matches, str(NORMALISED_OUT)),
        audit_row("fields", "finish_positions_populated", finish_count, str(NORMALISED_OUT)),
        audit_row("fields", "winner_flags_populated", winner_count, str(NORMALISED_OUT)),
        audit_row("fields", "sp_populated", sp_count, str(NORMALISED_OUT)),
        audit_row("status", "settlement_ready", "TRUE" if settlement_ready else "FALSE"),
        audit_row("recommendation", "recommendation", recommendation),
    ]

    race_counts = Counter(str(row.get("race_no", "")) for row in normalised_rows)
    for race_no in sorted(TARGET_RACES, key=int):
        rows.append(audit_row("race_counts", f"R{race_no}", race_counts.get(race_no, 0)))

    result_keys = {
        result_key(
            {
                "race_date": str(row.get("race_date", "")),
                "track": str(row.get("track", "")),
                "race_no": str(row.get("race_no", "")),
                "horse": str(row.get("horse", "")),
                "horse_key": str(row.get("horse_key", "")),
            }
        )
        for row in normalised_rows
    }
    unmatched_keys = sorted(set(targets).difference(result_keys))
    for key in unmatched_keys[:50]:
        target = targets[key]
        rows.append(
            audit_row(
                "unmatched_target_runner",
                f"R{target['race_no']} {target['horse']}",
                target["horse_key"],
                str(PRICE_TRUTH),
                "No Racing Australia result row matched this price-truth target runner.",
            )
        )
    return rows


def main() -> None:
    targets = load_target_runners()

    calendar_html, calendar_status, calendar_error = fetch_url(CALENDAR_URL)
    calendar_rows = parse_calendar(calendar_html) if calendar_html else []
    target_rows = [row for row in calendar_rows if row.get("target_match") == "TRUE"]
    target_url = str(target_rows[0].get("meeting_url", "")) if target_rows else ""

    if target_url:
        time.sleep(0.5)
    meeting_html, meeting_status, meeting_error = fetch_url(target_url) if target_url else ("", "", "Target meeting URL not found.")
    raw_rows, normalised_rows = parse_meeting_results(meeting_html, target_url) if meeting_html else ([], [])
    matched, unmatched, duplicates, ambiguous = apply_target_matching(normalised_rows, targets)

    audit_rows = build_audit(
        calendar_html=calendar_html,
        calendar_error=calendar_error,
        calendar_rows=calendar_rows,
        target_url=target_url,
        meeting_html=meeting_html,
        meeting_error=meeting_error,
        raw_rows=raw_rows,
        normalised_rows=normalised_rows,
        targets=targets,
        matched_target_runners=matched,
        unmatched_target_runners=unmatched,
        duplicate_matches=duplicates,
        ambiguous_matches=ambiguous,
    )

    write_csv(CALENDAR_OUT, calendar_rows, CALENDAR_COLUMNS)
    write_csv(RAW_RESULTS_OUT, raw_rows, RAW_COLUMNS)
    write_csv(NORMALISED_OUT, normalised_rows, NORMALISED_COLUMNS)
    write_csv(AUDIT_OUT, audit_rows, AUDIT_COLUMNS)

    print("=" * 96)
    print("RACING AUSTRALIA VIC RESULTS PIPELINE V1 - CAPTURE ONLY")
    print("=" * 96)
    print(f"calendar_http_status: {calendar_status}")
    print(f"meeting_http_status: {meeting_status}")
    print(f"target_url: {target_url}")
    print(f"wrote: {CALENDAR_OUT}")
    print(f"wrote: {RAW_RESULTS_OUT}")
    print(f"wrote: {NORMALISED_OUT}")
    print(f"wrote: {AUDIT_OUT}")
    print("")
    for row in audit_rows:
        if row["section"] in {"fetch", "parse", "match", "fields", "status", "recommendation"}:
            print(f"{row['section']},{row['metric']},{row['value']},{row['notes']}")
    print("=" * 96)


if __name__ == "__main__":
    main()
