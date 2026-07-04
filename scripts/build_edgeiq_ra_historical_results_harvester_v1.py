from __future__ import annotations

import csv
import html
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

from edgeiq_memory_safe_io import stream_csv_rows, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TARGETS = DATA / "edgeiq_temporal_direct_result_backfill_targets_v1.csv"
OUT = DATA / "edgeiq_ra_historical_results_harvest_v1.csv"
SUMMARY = DATA / "edgeiq_ra_historical_results_harvest_summary_v1.csv"
FAILURES = DATA / "edgeiq_ra_historical_results_harvest_failures_v1.csv"

BASE_URL = "https://www.racingaustralia.horse/FreeFields/Results.aspx"
CALENDAR_URL = "https://www.racingaustralia.horse/FreeFields/Calendar_Results.aspx?State=VIC"

REQUEST_TIMEOUT_SECONDS = int(os.getenv("EDGEIQ_RA_REQUEST_TIMEOUT_SECONDS", "30"))
REQUEST_SLEEP_SECONDS = float(os.getenv("EDGEIQ_RA_REQUEST_SLEEP_SECONDS", "2.0"))
MAX_RETRIES = int(os.getenv("EDGEIQ_RA_MAX_RETRIES", "2"))
USER_AGENT = os.getenv(
    "EDGEIQ_RA_USER_AGENT",
    "EDGEiQ-Racing-Research-Harvester/1.0 (+offline exact-race result backfill)",
)

OUT_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "finish_position",
    "official_margin",
    "official_time",
    "result_status",
    "source_url",
    "harvest_confidence",
    "canonical_runner_key",
    "safe_for_model_validation",
    "notes",
]

FAILURE_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "source_url",
    "failure_reason",
    "attempts",
    "http_status",
    "target_missing_horses",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

VICTORIAN_TRACKS = {
    "ARARAT",
    "AVOCA",
    "BAIRNSDALE",
    "BALLARAT",
    "BALNARRING",
    "BENDIGO",
    "BURRUMBEET",
    "CAULFIELD",
    "CAULFIELD HEATH",
    "CAMPERDOWN",
    "CASTERTON",
    "COLAC",
    "CRANBOURNE",
    "DONALD",
    "ECHUCA",
    "EDENHOPE",
    "FLEMINGTON",
    "GEELONG",
    "HAMILTON",
    "HORSHAM",
    "KILMORE",
    "KYNETON",
    "MILDURA",
    "MOE",
    "MOONEE VALLEY",
    "MORNINGTON",
    "MURTOA",
    "PAKENHAM",
    "SALE",
    "SANDOWN",
    "SEYMOUR",
    "ST ARNAUD",
    "STAWELL",
    "SWAN HILL",
    "TERANG",
    "TOWONG",
    "WANGARATTA",
    "WARRACKNABEAL",
    "WARRNAMBOOL",
    "WERRIBEE",
    "WODONGA",
    "YARRA VALLEY",
}

TRACK_ALIASES = {
    "BET365 PARK KILMORE": "KILMORE",
    "BET365 SEYMOUR": "SEYMOUR",
    "BET365 STAWELL": "STAWELL",
    "BET365 SWAN HILL": "SWAN HILL",
    "BET365 TERANG": "TERANG",
    "BET365 YARRA VALLEY": "YARRA VALLEY",
    "LADBROKES GEELONG": "GEELONG",
    "PICKLEBET PARK WERRIBEE": "WERRIBEE",
    "PICKLEBET PARK WODONGA": "WODONGA",
    "SOUTHSIDE CRANBOURNE": "CRANBOURNE",
    "SOUTHSIDE PAKENHAM": "PAKENHAM",
    "SOUTHSIDE PAKENHAM SYNTHETIC": "PAKENHAM",
    "SPORTSBET BALLARAT": "BALLARAT",
    "SPORTSBET BALLARAT SYNTHETIC": "BALLARAT",
    "SPORTSBET PAKENHAM": "PAKENHAM",
    "SPORTSBET WANGARATTA": "WANGARATTA",
    "THE VALLEY": "MOONEE VALLEY",
    "PAKENHAM SYNTHETIC": "PAKENHAM",
    "BALLARAT SYNTHETIC": "BALLARAT",
    "GEELONG SYNTHETIC": "GEELONG",
    "SANDOWN HILLSIDE": "SANDOWN",
    "SANDOWN LAKESIDE": "SANDOWN",
}


class TextTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tokens: list[str] = []

    def handle_data(self, data: str) -> None:
        text = clean(html.unescape(data))
        if text:
            self.tokens.append(text)


class RaceResultRowParser(HTMLParser):
    def __init__(self, target_race_no: str) -> None:
        super().__init__(convert_charrefs=True)
        self.target_race_no = target_race_no
        self.current_race_no = ""
        self.current_race_time = ""
        self.in_tr = False
        self.in_td = False
        self.current_cell: list[str] = []
        self.current_cells: list[str] = []
        self.rows: list[list[str]] = []
        self.race_times: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "tr":
            self.in_tr = True
            self.current_cells = []
        elif tag.lower() == "td" and self.in_tr:
            self.in_td = True
            self.current_cell = []

    def handle_data(self, data: str) -> None:
        text = clean(html.unescape(data))
        if not text:
            return
        race_header = token_is_race_header(text)
        if race_header:
            self.current_race_no = race_header
            self.current_race_time = ""
        if self.current_race_no and "Track Name:" in text and " Time:" in text:
            match = re.search(r"\bTime:\s*([0-9:.]+)", text)
            if match:
                self.current_race_time = match.group(1)
                self.race_times[self.current_race_no] = self.current_race_time
        if self.in_td:
            self.current_cell.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "td" and self.in_td:
            self.current_cells.append(clean(" ".join(self.current_cell)))
            self.current_cell = []
            self.in_td = False
        elif tag.lower() == "tr" and self.in_tr:
            if self.current_race_no == self.target_race_no and self.current_cells:
                self.rows.append(self.current_cells)
            self.current_cells = []
            self.in_tr = False


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
    text = text.replace("&", " AND ")
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"['`’‘]", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def horse_key(value: object) -> str:
    return normalise_text(value)


def normalise_track(value: object) -> str:
    track = normalise_text(value)
    track = re.sub(r"\bRACING\b", "", track)
    track = re.sub(r"\bCLUB\b", "", track)
    track = re.sub(r"\bPARK\b", "", track)
    track = re.sub(r"\bRACECOURSE\b", "", track)
    track = re.sub(r"\s+", " ", track).strip()
    return TRACK_ALIASES.get(track, track)


def normalise_race_no(value: object) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def normalise_date(value: object) -> str:
    text = clean(value).replace("/", "-")
    if not text:
        return ""
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%m-%y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    match = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    match = re.search(r"(\d{1,2})-(\d{1,2})-(20\d{2})", text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return text[:10]


def ra_date_key(value: str) -> str:
    date = normalise_date(value)
    if not date:
        return ""
    parsed = datetime.strptime(date, "%Y-%m-%d")
    return parsed.strftime("%Y%b%d")


def canonical_runner_key(race_date: str, track: str, race_no: str, horse: str) -> str:
    if not race_date or not track or not race_no or not horse:
        return ""
    return f"{race_date}|{track}|{race_no}|{horse_key(horse)}"


def race_url(race_date: str, track: str) -> str:
    key = f"{ra_date_key(race_date)},VIC,{track.title()}"
    return f"{BASE_URL}?{urllib.parse.urlencode({'Key': key})}"


def target_race_key(row: dict[str, str]) -> str:
    race_date = normalise_date(row.get("race_date"))
    track = normalise_track(row.get("track"))
    race_no = normalise_race_no(row.get("race_no"))
    return f"{race_date}|{track}|{race_no}" if race_date and track and race_no else ""


def read_targets() -> dict[str, dict[str, object]]:
    targets: dict[str, dict[str, object]] = {}
    for row in stream_csv_rows(TARGETS):
        race_date = normalise_date(row.get("race_date"))
        track = normalise_track(row.get("track"))
        race_no = normalise_race_no(row.get("race_no"))
        if not race_date or not track or not race_no:
            continue
        key = f"{race_date}|{track}|{race_no}"
        missing_horses = [horse_key(item) for item in clean(row.get("missing_horse_list")).split(";") if horse_key(item)]
        targets[key] = {
            "race_date": race_date,
            "track": track,
            "race_no": race_no,
            "missing_horses": missing_horses,
            "raw_track": clean(row.get("track")),
            "temporal_rows": clean(row.get("temporal_rows")),
        }
    return targets


def read_existing_harvest() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not OUT.exists():
        return rows
    try:
        for row in stream_csv_rows(OUT):
            if clean(row.get("canonical_runner_key")):
                rows.append(row)
    except Exception:
        return []
    return rows


def read_existing_failures() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not FAILURES.exists():
        return rows
    try:
        rows.extend(stream_csv_rows(FAILURES))
    except Exception:
        return []
    return rows


def persist(harvest: list[dict[str, object]], failures: list[dict[str, object]], summary: list[dict[str, object]] | None = None) -> None:
    deduped: dict[str, dict[str, object]] = {}
    for row in harvest:
        key = clean(row.get("canonical_runner_key"))
        if key:
            deduped[key] = row
    write_csv_atomic(OUT, list(deduped.values()), OUT_FIELDS)
    write_csv_atomic(FAILURES, failures, FAILURE_FIELDS)
    if summary is not None:
        write_csv_atomic(SUMMARY, summary, SUMMARY_FIELDS)


def fetch_url(url: str) -> tuple[str, int, str]:
    last_error = ""
    status = 0
    for attempt in range(1, MAX_RETRIES + 2):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                status = int(getattr(response, "status", 200))
                body = response.read().decode("utf-8", errors="replace")
                return body, status, ""
        except urllib.error.HTTPError as exc:
            status = exc.code
            last_error = f"HTTP_{exc.code}"
        except Exception as exc:
            last_error = type(exc).__name__ + ":" + str(exc)[:180]
        if attempt <= MAX_RETRIES:
            time.sleep(REQUEST_SLEEP_SECONDS * attempt)
    return "", status, last_error


def page_tokens(markup: str) -> list[str]:
    parser = TextTableParser()
    parser.feed(markup)
    return parser.tokens


def token_is_race_header(token: str) -> str:
    match = re.match(r"Race\s+(\d+)\s+-", clean(token), re.IGNORECASE)
    return str(int(match.group(1))) if match else ""


def finish_value(token: str) -> str:
    text = clean(token).upper()
    if text in {"FF", "LR", "BD", "DNF", "F", "PU"}:
        return ""
    match = re.match(r"^(\d+)(?:ST|ND|RD|TH)?$", text)
    if match:
        pos = int(match.group(1))
        if 0 < pos < 40:
            return str(pos)
    return ""


def is_runner_no(token: str) -> bool:
    return bool(re.match(r"^\d+[A-Z]?$", clean(token), re.IGNORECASE))


def is_non_runner_finish_token(token: str) -> bool:
    return clean(token).upper() in {"SCR", "LSCR", "LR", "FF", "BD", "DNF", "F", "PU"}


def parse_row_cells(markup: str, target_race_no: str) -> tuple[list[list[str]], dict[str, str]]:
    parser = RaceResultRowParser(target_race_no)
    parser.feed(markup)
    return parser.rows, parser.race_times


def parse_result_rows_from_cells(cells_rows: list[list[str]], race_times: dict[str, str], source_url: str, target: dict[str, object]) -> list[dict[str, object]]:
    race_no_target = str(target["race_no"])
    race_date = str(target["race_date"])
    track = str(target["track"])
    rows: list[dict[str, object]] = []
    for cells in cells_rows:
        if len(cells) < 4:
            continue
        if len(cells) == 1 and "Track Name:" in cells[0]:
            continue
        finish = clean(cells[1]) if len(cells) > 1 else ""
        runner_no = clean(cells[2]) if len(cells) > 2 else ""
        horse = clean(cells[3]) if len(cells) > 3 else ""
        if not horse or not is_runner_no(runner_no):
            continue
        finish_position = finish_value(finish)
        result_status = "RESULTED" if finish_position else "SCRATCHED_OR_NO_FINISH"
        margin = clean(cells[6]) if len(cells) > 6 and re.match(r"^\d+(\.\d+)?L$", clean(cells[6]), re.IGNORECASE) else ""
        rows.append(
            {
                "race_date": race_date,
                "track": track,
                "race_no": race_no_target,
                "horse": horse,
                "finish_position": finish_position,
                "official_margin": margin,
                "official_time": race_times.get(race_no_target, ""),
                "result_status": result_status,
                "source_url": source_url,
                "harvest_confidence": "HIGH" if finish_position else "LOW",
                "canonical_runner_key": canonical_runner_key(race_date, track, race_no_target, horse),
                "safe_for_model_validation": "YES" if finish_position else "NO",
                "notes": "Official Racing Australia results harvest. No inferred placings.",
            }
        )
    return rows


def extract_race_time(tokens: list[str], race_no: str) -> str:
    current = ""
    for token in tokens:
        header = token_is_race_header(token)
        if header:
            current = header
            continue
        if current == race_no and "Track Name:" in token and " Time:" in token:
            match = re.search(r"\bTime:\s*([0-9:.]+)", token)
            if match:
                return match.group(1)
    return ""


def harvest_target(target: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    race_date = str(target["race_date"])
    track = str(target["track"])
    race_no = str(target["race_no"])
    url = race_url(race_date, track)
    if track not in VICTORIAN_TRACKS:
        return [], {
            "race_date": race_date,
            "track": track,
            "race_no": race_no,
            "source_url": url,
            "failure_reason": "NON_VIC_TARGET_NOT_HARVESTED_FROM_VIC_SOURCE",
            "attempts": 0,
            "http_status": "",
            "target_missing_horses": ";".join(target.get("missing_horses", [])),
            "notes": f"Primary source is VIC calendar: {CALENDAR_URL}",
        }
    markup, status, error = fetch_url(url)
    if not markup:
        return [], {
            "race_date": race_date,
            "track": track,
            "race_no": race_no,
            "source_url": url,
            "failure_reason": error or "FETCH_FAILED",
            "attempts": MAX_RETRIES + 1,
            "http_status": status,
            "target_missing_horses": ";".join(target.get("missing_horses", [])),
            "notes": "Request failed. No placements inferred.",
        }
    cells_rows, race_times = parse_row_cells(markup, race_no)
    rows = parse_result_rows_from_cells(cells_rows, race_times, url, target)
    if not rows:
        return [], {
            "race_date": race_date,
            "track": track,
            "race_no": race_no,
            "source_url": url,
            "failure_reason": "NO_RUNNER_PLACINGS_PARSED",
            "attempts": MAX_RETRIES + 1,
            "http_status": status,
            "target_missing_horses": ";".join(target.get("missing_horses", [])),
            "notes": "Fetched Racing Australia page but could not parse target race runner placings.",
        }
    return rows, None


def build_summary(targets: dict[str, dict[str, object]], harvest: list[dict[str, object]], failures: list[dict[str, object]]) -> list[dict[str, object]]:
    target_races = len(targets)
    harvested_races = {f"{row['race_date']}|{row['track']}|{row['race_no']}" for row in harvest if clean(row.get("finish_position"))}
    safe_rows = [row for row in harvest if row.get("safe_for_model_validation") == "YES"]
    status_counts = Counter(clean(row.get("result_status")) for row in harvest)
    failure_counts = Counter(clean(row.get("failure_reason")) for row in failures)
    summary: list[dict[str, object]] = [
        {"metric": "target_races", "value": target_races},
        {"metric": "harvested_races_with_finish_positions", "value": len(harvested_races)},
        {"metric": "runner_rows_harvested", "value": len(harvest)},
        {"metric": "safe_for_model_validation_yes", "value": len(safe_rows)},
        {"metric": "failed_races", "value": len(failures)},
        {"metric": "source", "value": CALENDAR_URL},
        {"metric": "research_pipeline_offline_only", "value": "YES"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]
    for key, value in sorted(status_counts.items()):
        summary.append({"metric": f"result_status::{key}", "value": value})
    for key, value in sorted(failure_counts.items()):
        summary.append({"metric": f"failure_reason::{key}", "value": value})
    return summary


def main() -> None:
    targets = read_targets()
    harvest = read_existing_harvest()
    failures = read_existing_failures()
    harvested_race_keys = {f"{row.get('race_date')}|{row.get('track')}|{row.get('race_no')}" for row in harvest}
    failures = [row for row in failures if f"{row.get('race_date')}|{row.get('track')}|{row.get('race_no')}" not in harvested_race_keys]
    failed_race_keys = {f"{row.get('race_date')}|{row.get('track')}|{row.get('race_no')}" for row in failures}

    print("=" * 88)
    print("EDGEIQ RACING AUSTRALIA HISTORICAL RESULTS HARVESTER V1")
    print("=" * 88)
    print(f"target races: {len(targets)}")
    print(f"existing harvested race keys: {len(harvested_race_keys)}")
    print(f"existing failed race keys: {len(failed_race_keys)}")

    for key, target in sorted(targets.items()):
        if key in harvested_race_keys:
            continue
        rows, failure = harvest_target(target)
        if rows:
            failures = [row for row in failures if f"{row.get('race_date')}|{row.get('track')}|{row.get('race_no')}" != key]
            harvest.extend(rows)
            print(f"HARVESTED {key}: {len(rows)} rows")
        if failure:
            failures = [row for row in failures if f"{row.get('race_date')}|{row.get('track')}|{row.get('race_no')}" != key]
            failures.append(failure)
            print(f"FAILED {key}: {failure['failure_reason']}")
        summary = build_summary(targets, harvest, failures)
        persist(harvest, failures, summary)
        time.sleep(REQUEST_SLEEP_SECONDS)

    summary = build_summary(targets, harvest, failures)
    persist(harvest, failures, summary)
    print(f"runner rows harvested: {len(harvest)}")
    print(f"failed races: {len(failures)}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {FAILURES}")


if __name__ == "__main__":
    main()
