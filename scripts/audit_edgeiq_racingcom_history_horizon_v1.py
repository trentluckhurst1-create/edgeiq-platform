from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TODAY = date.today()
CURRENT_YEAR = TODAY.year

RESULTS_CANDIDATES = [
    DATA / "edgeiq_racingcom_results_warehouse_full_v1.csv",
    DATA / "edgeiq_racingcom_results_warehouse_all_v1.csv",
    DATA / "edgeiq_racingcom_results_warehouse_v1.csv",
]
CALENDAR_CANDIDATES = [
    DATA / "edgeiq_racingcom_historical_calendar_backfill_v1.csv",
    DATA / "racingcom_historical_meeting_discovery_v1.csv",
]
SECTIONAL_CANDIDATES = [
    DATA / "racingcom_sectional_warehouse_v2.csv",
    DATA / "edgeiq_vic_sectional_warehouse_v1.csv",
    DATA / "edgeiq_vic_historical_sectional_warehouse_v1.csv",
    DATA / "racingcom_sectional_history_master_v1.csv",
]
REPLAY_CANDIDATES = [
    DATA / "replay_links.csv",
]

OUT_DETAIL = DATA / "edgeiq_racingcom_history_horizon_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_racingcom_history_horizon_v1_summary.csv"

REPRESENTATIVE_TRACKS = [
    "FLEMINGTON",
    "CAULFIELD",
    "MOONEE VALLEY",
    "SANDOWN",
    "CRANBOURNE",
    "BALLARAT",
    "BENDIGO",
    "GEELONG",
    "WARRNAMBOOL",
    "SALE",
]

DETAIL_COLUMNS = [
    "year",
    "representative_track",
    "meetings_found",
    "results_available",
    "sectionals_available",
    "replays_available",
    "first_meeting_found",
    "last_meeting_found",
    "results_coverage_pct",
    "sectionals_coverage_pct",
    "replays_coverage_pct",
    "calendar_source_used",
    "results_source_used",
    "sectional_sources_used",
    "replay_source_used",
    "notes",
    "built_at",
]

SUMMARY_COLUMNS = [
    "row_type",
    "year",
    "metric",
    "value",
    "meetings_found",
    "results_available",
    "sectionals_available",
    "replays_available",
    "tracks_with_meetings",
    "tracks_with_results",
    "tracks_with_sectionals",
    "tracks_with_replays",
    "first_meeting_found",
    "last_meeting_found",
    "notes",
    "built_at",
]


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    text = re.sub(r"\s+", " ", text)
    if text.upper() in {"", "NAN", "NONE", "NULL", "N/A", "NA", "-"}:
        return ""
    return text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    tmp.replace(path)


def choose_existing_path(candidates: Iterable[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def parse_iso_date(value: Any) -> date | None:
    text = clean(value)
    if not text:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None
    return None


def date_from_row(row: dict[str, str], columns: tuple[str, ...]) -> date | None:
    for column in columns:
        parsed = parse_iso_date(row.get(column))
        if parsed is not None:
            return parsed
    return None


def normalise_track(value: Any) -> str:
    raw = clean(value).upper()
    raw = raw.replace("-", " ")
    raw = re.sub(r"[^A-Z0-9 ]+", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


def representative_track(raw_track: Any) -> str | None:
    track = normalise_track(raw_track)
    if not track:
        return None
    if "FLEMINGTON" in track:
        return "FLEMINGTON"
    if ("MOONEE VALLEY" in track) or track == "THE VALLEY":
        return "MOONEE VALLEY"
    if "CAULFIELD" in track and "HEATH" not in track:
        return "CAULFIELD"
    if "SANDOWN" in track:
        return "SANDOWN"
    if "CRANBOURNE" in track:
        return "CRANBOURNE"
    if "BALLARAT" in track:
        return "BALLARAT"
    if "BENDIGO" in track:
        return "BENDIGO"
    if "GEELONG" in track:
        return "GEELONG"
    if "WARRNAMBOOL" in track:
        return "WARRNAMBOOL"
    if re.search(r"(^| )SALE($| )", track):
        return "SALE"
    return None


def pct(part: int, whole: int) -> str:
    if whole <= 0:
        return "0.00"
    return f"{(part / whole) * 100.0:.2f}"


def add_meeting(
    container: dict[str, dict[int, set[str]]],
    rep_track: str,
    meeting_day: date,
) -> None:
    container.setdefault(rep_track, defaultdict(set))[meeting_day.year].add(meeting_day.isoformat())


def collect_calendar_meetings(path: Path) -> tuple[dict[str, dict[int, set[str]]], list[date]]:
    meetings: dict[str, dict[int, set[str]]] = {}
    seen_dates: list[date] = []
    for row in read_csv(path):
        meeting_day = date_from_row(row, ("meeting_date", "race_date", "date_k"))
        if meeting_day is None or meeting_day > TODAY:
            continue
        if clean(row.get("state")) and clean(row.get("state")).upper() != "VIC":
            continue
        if clean(row.get("is_trial")).upper() == "TRUE":
            continue
        if clean(row.get("is_jumpout")).upper() == "TRUE":
            continue
        if clean(row.get("is_abandoned")).upper() == "TRUE":
            continue
        rep_track = representative_track(row.get("track"))
        if rep_track is None:
            continue
        add_meeting(meetings, rep_track, meeting_day)
        seen_dates.append(meeting_day)
    return meetings, seen_dates


def collect_results_meetings(path: Path) -> tuple[dict[str, dict[int, set[str]]], list[date]]:
    meetings: dict[str, dict[int, set[str]]] = {}
    seen_dates: list[date] = []
    for row in read_csv(path):
        meeting_day = date_from_row(row, ("meeting_date", "race_date", "date_k"))
        if meeting_day is None or meeting_day > TODAY:
            continue
        rep_track = representative_track(row.get("track"))
        if rep_track is None:
            continue
        add_meeting(meetings, rep_track, meeting_day)
        seen_dates.append(meeting_day)
    return meetings, seen_dates


def collect_sectional_meetings(paths: list[Path]) -> tuple[dict[str, dict[int, set[str]]], list[date], list[str]]:
    meetings: dict[str, dict[int, set[str]]] = {}
    seen_dates: list[date] = []
    used_sources: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        used_sources.append(path.name)
        for row in read_csv(path):
            meeting_day = date_from_row(row, ("meeting_date", "race_date", "date_k"))
            if meeting_day is None or meeting_day > TODAY:
                continue
            rep_track = representative_track(row.get("track"))
            if rep_track is None:
                continue
            add_meeting(meetings, rep_track, meeting_day)
            seen_dates.append(meeting_day)
    return meetings, seen_dates, used_sources


def collect_replay_meetings(path: Path) -> tuple[dict[str, dict[int, set[str]]], list[date]]:
    meetings: dict[str, dict[int, set[str]]] = {}
    seen_dates: list[date] = []
    for row in read_csv(path):
        meeting_day = date_from_row(row, ("race_date", "meeting_date"))
        if meeting_day is None or meeting_day > TODAY:
            continue
        replay_url = clean(row.get("replay_url"))
        available_flag = clean(row.get("available_flag")).upper() in {"TRUE", "YES", "1"}
        if not replay_url and not available_flag:
            continue
        rep_track = representative_track(row.get("track"))
        if rep_track is None:
            continue
        add_meeting(meetings, rep_track, meeting_day)
        seen_dates.append(meeting_day)
    return meetings, seen_dates


def min_year_from_dates(*date_lists: list[date]) -> int:
    years = [day.year for date_list in date_lists for day in date_list]
    return min(years) if years else CURRENT_YEAR


def union_dates(*date_sets: set[str]) -> list[str]:
    merged: set[str] = set()
    for values in date_sets:
        merged.update(values)
    return sorted(merged)


def meaningful_coverage(row: dict[str, Any]) -> bool:
    return (
        int(row.get("tracks_with_meetings", 0) or 0) >= 7
        and int(row.get("tracks_with_results", 0) or 0) >= 7
        and int(row.get("tracks_with_sectionals", 0) or 0) >= 7
        and int(row.get("results_available", 0) or 0) >= 20
        and int(row.get("sectionals_available", 0) or 0) >= 20
    )


def build_detail_and_summary() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    built_at = datetime.now().isoformat()

    calendar_path = choose_existing_path(CALENDAR_CANDIDATES)
    results_path = choose_existing_path(RESULTS_CANDIDATES)
    replay_path = choose_existing_path(REPLAY_CANDIDATES)
    sectional_paths = [path for path in SECTIONAL_CANDIDATES if path.exists()]

    calendar_meetings, calendar_dates = collect_calendar_meetings(calendar_path) if calendar_path else ({}, [])
    results_meetings, results_dates = collect_results_meetings(results_path) if results_path else ({}, [])
    sectional_meetings, sectional_dates, sectional_sources = collect_sectional_meetings(sectional_paths)
    replay_meetings, replay_dates = collect_replay_meetings(replay_path) if replay_path else ({}, [])

    start_year = min_year_from_dates(calendar_dates, results_dates, sectional_dates)
    years = list(range(CURRENT_YEAR, start_year - 1, -1))

    detail_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for year in years:
        yearly_totals = {
            "meetings_found": 0,
            "results_available": 0,
            "sectionals_available": 0,
            "replays_available": 0,
            "tracks_with_meetings": 0,
            "tracks_with_results": 0,
            "tracks_with_sectionals": 0,
            "tracks_with_replays": 0,
        }
        overall_dates: set[str] = set()

        for rep_track in REPRESENTATIVE_TRACKS:
            calendar_dates_for_track = calendar_meetings.get(rep_track, {}).get(year, set())
            results_dates_for_track = results_meetings.get(rep_track, {}).get(year, set())
            sectional_dates_for_track = sectional_meetings.get(rep_track, {}).get(year, set())
            replay_dates_for_track = replay_meetings.get(rep_track, {}).get(year, set())

            union_for_track = union_dates(
                calendar_dates_for_track,
                results_dates_for_track,
                sectional_dates_for_track,
                replay_dates_for_track,
            )

            first_meeting = union_for_track[0] if union_for_track else ""
            last_meeting = union_for_track[-1] if union_for_track else ""

            meetings_found = len(calendar_dates_for_track)
            results_available = len(results_dates_for_track)
            sectionals_available = len(sectional_dates_for_track)
            replays_available = len(replay_dates_for_track)

            if meetings_found > 0:
                yearly_totals["tracks_with_meetings"] += 1
            if results_available > 0:
                yearly_totals["tracks_with_results"] += 1
            if sectionals_available > 0:
                yearly_totals["tracks_with_sectionals"] += 1
            if replays_available > 0:
                yearly_totals["tracks_with_replays"] += 1

            yearly_totals["meetings_found"] += meetings_found
            yearly_totals["results_available"] += results_available
            yearly_totals["sectionals_available"] += sectionals_available
            yearly_totals["replays_available"] += replays_available
            overall_dates.update(union_for_track)

            notes: list[str] = []
            if meetings_found == 0 and (results_available > 0 or sectionals_available > 0):
                notes.append("coverage exists outside calendar discovery file")
            if replays_available == 0:
                notes.append("no usable local replay-link evidence")

            detail_rows.append(
                {
                    "year": year,
                    "representative_track": rep_track,
                    "meetings_found": meetings_found,
                    "results_available": results_available,
                    "sectionals_available": sectionals_available,
                    "replays_available": replays_available,
                    "first_meeting_found": first_meeting,
                    "last_meeting_found": last_meeting,
                    "results_coverage_pct": pct(results_available, meetings_found),
                    "sectionals_coverage_pct": pct(sectionals_available, meetings_found),
                    "replays_coverage_pct": pct(replays_available, meetings_found),
                    "calendar_source_used": calendar_path.name if calendar_path else "",
                    "results_source_used": results_path.name if results_path else "",
                    "sectional_sources_used": ";".join(sectional_sources),
                    "replay_source_used": replay_path.name if replay_path else "",
                    "notes": " | ".join(notes),
                    "built_at": built_at,
                }
            )

        overall_dates_sorted = sorted(overall_dates)
        summary_rows.append(
            {
                "row_type": "YEAR_SUMMARY",
                "year": year,
                "metric": "",
                "value": "",
                "meetings_found": yearly_totals["meetings_found"],
                "results_available": yearly_totals["results_available"],
                "sectionals_available": yearly_totals["sectionals_available"],
                "replays_available": yearly_totals["replays_available"],
                "tracks_with_meetings": yearly_totals["tracks_with_meetings"],
                "tracks_with_results": yearly_totals["tracks_with_results"],
                "tracks_with_sectionals": yearly_totals["tracks_with_sectionals"],
                "tracks_with_replays": yearly_totals["tracks_with_replays"],
                "first_meeting_found": overall_dates_sorted[0] if overall_dates_sorted else "",
                "last_meeting_found": overall_dates_sorted[-1] if overall_dates_sorted else "",
                "notes": (
                    "partial year through audit date | meaningful coverage threshold met"
                    if year == CURRENT_YEAR and meaningful_coverage(yearly_totals)
                    else "partial year through audit date"
                    if year == CURRENT_YEAR
                    else "meaningful coverage threshold met"
                    if meaningful_coverage(yearly_totals)
                    else ""
                ),
                "built_at": built_at,
            }
        )

    yearly_summary_lookup = {
        int(row["year"]): row
        for row in summary_rows
        if row.get("row_type") == "YEAR_SUMMARY"
    }

    earliest_results_year = min((year for year, row in yearly_summary_lookup.items() if int(row["results_available"]) > 0), default=None)
    earliest_sectionals_year = min((year for year, row in yearly_summary_lookup.items() if int(row["sectionals_available"]) > 0), default=None)
    earliest_meaningful_year = min((year for year, row in yearly_summary_lookup.items() if meaningful_coverage(row)), default=None)

    earliest_results_date = min((day.isoformat() for day in results_dates), default="")
    earliest_sectionals_date = min((day.isoformat() for day in sectional_dates), default="")
    earliest_calendar_date = min((day.isoformat() for day in calendar_dates), default="")

    recommended_harvest_start_date = f"{earliest_meaningful_year}-01-01" if earliest_meaningful_year else (earliest_calendar_date or earliest_results_date or earliest_sectionals_date)

    summary_metric_rows = [
        {
            "row_type": "KEY_METRIC",
            "metric": "scope_note",
            "value": "LOCAL_FILE_EVIDENCE_ONLY_NO_LIVE_HARVEST",
            "notes": "audit uses existing Racing.com-derived local files only and does not probe the live site or perform any backfill",
        },
        {
            "row_type": "KEY_METRIC",
            "metric": "earliest_results_year",
            "value": earliest_results_year or "",
            "notes": f"earliest results date {earliest_results_date}" if earliest_results_date else "no local results evidence found",
        },
        {
            "row_type": "KEY_METRIC",
            "metric": "earliest_sectionals_year",
            "value": earliest_sectionals_year or "",
            "notes": f"earliest sectionals date {earliest_sectionals_date}" if earliest_sectionals_date else "no local sectional evidence found",
        },
        {
            "row_type": "KEY_METRIC",
            "metric": "earliest_year_with_meaningful_coverage",
            "value": earliest_meaningful_year or "",
            "notes": "meaningful = 7+ representative tracks with meetings/results/sectionals and 20+ meeting hits for results and sectionals",
        },
        {
            "row_type": "KEY_METRIC",
            "metric": "recommended_harvest_start_date",
            "value": recommended_harvest_start_date,
            "notes": "recommended start uses earliest meaningful local VIC coverage; calendar evidence extends to 2023-01-01",
        },
        {
            "row_type": "KEY_METRIC",
            "metric": "replay_coverage_note",
            "value": "NO_USABLE_LOCAL_REPLAY_URL_COVERAGE",
            "notes": "replay_links.csv exists, but no nonblank replay_url or available_flag=TRUE rows were found for representative Victorian meetings",
        },
        {
            "row_type": "SOURCE_USED",
            "metric": "calendar_source",
            "value": calendar_path.name if calendar_path else "",
            "notes": earliest_calendar_date or "missing",
        },
        {
            "row_type": "SOURCE_USED",
            "metric": "results_source",
            "value": results_path.name if results_path else "",
            "notes": earliest_results_date or "missing",
        },
        {
            "row_type": "SOURCE_USED",
            "metric": "sectional_sources",
            "value": ";".join(sectional_sources),
            "notes": earliest_sectionals_date or "missing",
        },
        {
            "row_type": "SOURCE_USED",
            "metric": "replay_source",
            "value": replay_path.name if replay_path else "",
            "notes": "no usable replay rows" if replay_path else "missing",
        },
    ]

    for row in summary_metric_rows:
        row["year"] = ""
        row["meetings_found"] = ""
        row["results_available"] = ""
        row["sectionals_available"] = ""
        row["replays_available"] = ""
        row["tracks_with_meetings"] = ""
        row["tracks_with_results"] = ""
        row["tracks_with_sectionals"] = ""
        row["tracks_with_replays"] = ""
        row["first_meeting_found"] = ""
        row["last_meeting_found"] = ""
        row["built_at"] = built_at
        summary_rows.append(row)

    return detail_rows, summary_rows


def main() -> None:
    detail_rows, summary_rows = build_detail_and_summary()
    write_csv(OUT_DETAIL, detail_rows, DETAIL_COLUMNS)
    write_csv(OUT_SUMMARY, summary_rows, SUMMARY_COLUMNS)

    print("EDGEiQ Racing.com history horizon audit complete")
    print(f"detail_out={OUT_DETAIL}")
    print(f"summary_out={OUT_SUMMARY}")

    year_rows = [row for row in summary_rows if row.get("row_type") == "YEAR_SUMMARY"]
    for row in sorted(year_rows, key=lambda item: int(item["year"]), reverse=True):
        print(
            f"year={row['year']} "
            f"meetings_found={row['meetings_found']} "
            f"results_available={row['results_available']} "
            f"sectionals_available={row['sectionals_available']} "
            f"replays_available={row['replays_available']}"
        )

    metric_rows = [row for row in summary_rows if row.get("row_type") == "KEY_METRIC"]
    for row in metric_rows:
        print(f"{row['metric']}={row['value']}")


if __name__ == "__main__":
    main()
