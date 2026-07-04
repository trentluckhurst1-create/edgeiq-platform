from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORY_DOWNLOAD_DIR = DATA / "racingcom_sectional_history_downloads_v1"
EXISTING_DOWNLOAD_DIR = DATA / "racingcom_sectionals_downloads_v1"
HISTORY_MANIFEST = DATA / "racingcom_sectional_history_harvest_v1_manifest.csv"
EXISTING_MANIFEST = DATA / "racingcom_speed_data_csv_download_manifest_v1.csv"

MASTER_OUT = DATA / "racingcom_sectional_history_master_v1.csv"
HORSES_OUT = DATA / "racingcom_sectional_history_horses_v1.csv"
AUDIT_OUT = DATA / "racingcom_sectional_history_master_v1_audit.csv"

COUNTRY_SUFFIXES = ("NZ", "IRE", "GB", "FR", "USA", "JPN", "GER", "SAF")

MASTER_COLUMNS = [
    "meeting_date",
    "track",
    "race_no",
    "source_speed_data_url",
    "horse_name",
    "horse_key",
    "position",
    "early_speed",
    "mid_speed",
    "late_speed",
    "peak_speed",
    "avg_speed",
    "sectional_count",
    "source_file",
    "ingest_status",
]

HORSE_COLUMNS = [
    "horse_key",
    "horse_name",
    "runs_with_sectionals",
    "avg_early_speed",
    "avg_mid_speed",
    "avg_late_speed",
    "avg_peak_speed",
    "avg_speed",
    "best_peak_speed",
    "latest_meeting_date",
    "latest_track",
    "latest_race_no",
]

AUDIT_COLUMNS = [
    "files_found",
    "files_read",
    "files_failed",
    "rows_output",
    "unique_horses",
    "unique_races",
    "final_status",
]


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    tmp.replace(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def canonical_horse_key(value: Any) -> str:
    raw = clean(value).upper()
    if not raw:
        return ""
    suffix_pattern = "|".join(COUNTRY_SUFFIXES)
    raw = re.sub(rf"\s*\(({suffix_pattern})\)\s*$", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(rf"\s+({suffix_pattern})\s*$", "", raw, flags=re.IGNORECASE).strip()
    return re.sub(r"[^A-Z0-9]+", "", raw)


def parse_number(value: Any) -> float | None:
    text = clean(value).replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def format_number(value: float | None) -> str:
    if value is None:
        return ""
    rounded = round(value, 2)
    if rounded.is_integer():
        return str(int(rounded))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def avg(values: list[float]) -> float | None:
    return mean(values) if values else None


def phase_speeds(speeds: list[float]) -> tuple[float | None, float | None, float | None]:
    if not speeds:
        return None, None, None
    if len(speeds) == 1:
        return speeds[0], speeds[0], speeds[0]
    chunk = max(1, len(speeds) // 3)
    early = speeds[:chunk]
    late = speeds[-chunk:]
    middle = speeds[chunk:-chunk] if len(speeds) > chunk * 2 else speeds[chunk:-chunk] or speeds
    return avg(early), avg(middle), avg(late)


def detect_delimiter(text: str) -> str:
    first_line = text.splitlines()[0] if text.splitlines() else ""
    return ";" if first_line.count(";") >= first_line.count(",") else ","


def read_raw_rows(path: Path) -> list[list[str]]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
    delimiter = detect_delimiter(text)
    return [[clean(cell) for cell in row] for row in csv.reader(text.splitlines(), delimiter=delimiter) if any(clean(cell) for cell in row)]


def date_from_any(value: Any) -> str:
    text = clean(value)
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    for fmt in ("%d/%m/%Y %I:%M:%S %p", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def url_date(url: str) -> str:
    match = re.search(r"/form/(\d{4}-\d{2}-\d{2})/", clean(url))
    return match.group(1) if match else ""


def url_race_no(url: str) -> str:
    match = re.search(r"/race/(\d+)/", clean(url))
    return str(int(match.group(1))) if match else ""


def url_track_slug(url: str) -> str:
    match = re.search(r"/form/\d{4}-\d{2}-\d{2}/([^/]+)/race/", clean(url))
    return match.group(1) if match else ""


def track_from_slug(slug: str) -> str:
    return clean(slug).replace("-", " ").replace("_", " ").upper()


def normalise_track_for_key(track: str) -> str:
    value = clean(track).upper()
    value = re.sub(r"^(SPORTSBET|LADBROKES|BET365|PICKLEBET PARK|SOUTHSIDE)\s+", "", value)
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def manifest_lookup() -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for manifest_path in (HISTORY_MANIFEST, EXISTING_MANIFEST):
        for row in read_csv(manifest_path):
            filename = clean(row.get("downloaded_filename")) or Path(clean(row.get("local_path"))).name
            if not filename:
                continue
            url = clean(row.get("speed_data_url")) or clean(row.get("source_speed_data_url"))
            lookup[filename] = {
                "meeting_date": clean(row.get("meeting_date")) or url_date(url),
                "track": clean(row.get("track")) or track_from_slug(clean(row.get("track_slug")) or url_track_slug(url)),
                "race_no": clean(row.get("race_no")) or url_race_no(url),
                "source_speed_data_url": url,
            }
    return lookup


def context_from_filename(path: Path) -> dict[str, str]:
    match = re.search(r"(?P<date>\d{4}-\d{2}-\d{2})_(?P<slug>.+?)_R(?P<race>\d+)_", path.name)
    if not match:
        return {"meeting_date": "", "track": "", "race_no": "", "source_speed_data_url": ""}
    slug = match.group("slug")
    return {
        "meeting_date": match.group("date"),
        "track": track_from_slug(slug),
        "race_no": str(int(match.group("race"))),
        "source_speed_data_url": f"https://www.racing.com/form/{match.group('date')}/{slug}/race/{int(match.group('race'))}/speed-data",
    }


def context_for_file(path: Path, lookup: dict[str, dict[str, str]]) -> dict[str, str]:
    context = lookup.get(path.name)
    if context:
        return context.copy()
    return context_from_filename(path)


def is_metadata_row(row: list[str]) -> bool:
    first = row[0] if row else ""
    return bool(date_from_any(first))


def looks_like_header(row: list[str]) -> bool:
    lowered = [clean(cell).lower().replace(" ", "_").replace("-", "_") for cell in row]
    return any(value in lowered for value in ("horse", "horse_name", "runner", "runner_name")) and any(
        value in lowered for value in ("avg_speed", "average_speed", "peak_speed", "early_speed")
    )


def header_index(header: list[str], options: tuple[str, ...]) -> int | None:
    lowered = [clean(cell).lower().replace(" ", "_").replace("-", "_") for cell in header]
    for option in options:
        if option in lowered:
            return lowered.index(option)
    for option in options:
        for idx, value in enumerate(lowered):
            if option in value:
                return idx
    return None


def row_value(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return clean(row[index])


def parse_racingcom_runner_row(row: list[str], context: dict[str, str], source_file: str) -> dict[str, Any] | None:
    if len(row) < 5:
        return None
    horse_name = clean(row[0])
    horse_key = canonical_horse_key(horse_name)
    if not horse_name or not horse_key:
        return None

    position = clean(row[1])
    speeds: list[float] = []
    index = 2
    while index + 1 < len(row):
        speed = parse_number(row[index + 1])
        if speed is not None and speed > 0:
            speeds.append(speed)
        index += 3

    early, mid, late = phase_speeds(speeds)
    peak = max(speeds) if speeds else None
    average = avg(speeds)
    return {
        "meeting_date": context.get("meeting_date") or "",
        "track": context.get("track") or "",
        "race_no": context.get("race_no") or "",
        "source_speed_data_url": context.get("source_speed_data_url") or "",
        "horse_name": horse_name,
        "horse_key": horse_key,
        "position": position,
        "early_speed": format_number(early),
        "mid_speed": format_number(mid),
        "late_speed": format_number(late),
        "peak_speed": format_number(peak),
        "avg_speed": format_number(average),
        "sectional_count": len(speeds),
        "source_file": source_file,
        "ingest_status": "INGESTED" if speeds else "INGESTED_WITH_MISSING_SPEED",
    }


def parse_header_csv(rows: list[list[str]], context: dict[str, str], source_file: str) -> list[dict[str, Any]]:
    header = rows[0]
    horse_idx = header_index(header, ("horse_key", "horse_name", "horse", "runner_name", "runner"))
    position_idx = header_index(header, ("position", "finish_position", "place", "placing"))
    early_idx = header_index(header, ("early_speed",))
    mid_idx = header_index(header, ("mid_speed", "midrace_speed"))
    late_idx = header_index(header, ("late_speed",))
    peak_idx = header_index(header, ("peak_speed", "top_speed"))
    avg_idx = header_index(header, ("avg_speed", "average_speed"))
    count_idx = header_index(header, ("sectional_count",))
    date_idx = header_index(header, ("meeting_date", "race_date", "date"))
    track_idx = header_index(header, ("track", "venue"))
    race_idx = header_index(header, ("race_no", "race_number"))
    url_idx = header_index(header, ("source_speed_data_url", "speed_data_url"))

    parsed: list[dict[str, Any]] = []
    for row in rows[1:]:
        horse_name = row_value(row, horse_idx)
        horse_key = canonical_horse_key(horse_name)
        if not horse_key:
            continue
        parsed.append(
            {
                "meeting_date": row_value(row, date_idx) or context.get("meeting_date", ""),
                "track": row_value(row, track_idx) or context.get("track", ""),
                "race_no": row_value(row, race_idx) or context.get("race_no", ""),
                "source_speed_data_url": row_value(row, url_idx) or context.get("source_speed_data_url", ""),
                "horse_name": horse_name,
                "horse_key": horse_key,
                "position": row_value(row, position_idx),
                "early_speed": row_value(row, early_idx),
                "mid_speed": row_value(row, mid_idx),
                "late_speed": row_value(row, late_idx),
                "peak_speed": row_value(row, peak_idx),
                "avg_speed": row_value(row, avg_idx),
                "sectional_count": row_value(row, count_idx),
                "source_file": source_file,
                "ingest_status": "INGESTED_HEADER_CSV" if row_value(row, avg_idx) else "INGESTED_HEADER_CSV_WITH_MISSING_SPEED",
            }
        )
    return parsed


def parse_download(path: Path, context: dict[str, str]) -> list[dict[str, Any]]:
    rows = read_raw_rows(path)
    if not rows:
        return []
    if is_metadata_row(rows[0]):
        if not context.get("meeting_date"):
            context["meeting_date"] = date_from_any(rows[0][0])
        return [row for row in (parse_racingcom_runner_row(raw, context, path.name) for raw in rows[1:]) if row]
    if looks_like_header(rows[0]):
        return parse_header_csv(rows, context, path.name)
    return [row for row in (parse_racingcom_runner_row(raw, context, path.name) for raw in rows) if row]


def source_files() -> list[Path]:
    files: list[Path] = []
    for folder in (HISTORY_DOWNLOAD_DIR, EXISTING_DOWNLOAD_DIR):
        if folder.exists():
            files.extend(sorted(folder.glob("*.csv")))
    return files


def speed_score(row: dict[str, Any]) -> int:
    score = 0
    for column in ("avg_speed", "peak_speed", "early_speed", "mid_speed", "late_speed"):
        if clean(row.get(column)):
            score += 1
    if int(parse_number(row.get("sectional_count")) or 0) > 0:
        score += 1
    return score


def dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (
            clean(row.get("meeting_date")),
            normalise_track_for_key(clean(row.get("track"))),
            clean(row.get("race_no")),
            clean(row.get("horse_key")),
        )
        if not all(key):
            continue
        previous = best.get(key)
        if previous is None or speed_score(row) > speed_score(previous):
            best[key] = row
    return sorted(best.values(), key=lambda item: (clean(item.get("meeting_date")), normalise_track_for_key(clean(item.get("track"))), int(clean(item.get("race_no")) or 0), clean(item.get("horse_name"))))


def numeric(value: Any) -> float | None:
    return parse_number(value)


def average_column(rows: list[dict[str, Any]], column: str) -> str:
    values = [value for value in (numeric(row.get(column)) for row in rows) if value is not None]
    return format_number(avg(values))


def build_horse_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if clean(row.get("horse_key")) and numeric(row.get("avg_speed")) is not None:
            groups[clean(row.get("horse_key"))].append(row)

    summary: list[dict[str, Any]] = []
    for horse_key, group in groups.items():
        group.sort(key=lambda row: (clean(row.get("meeting_date")), clean(row.get("track")), int(clean(row.get("race_no")) or 0)))
        latest = group[-1]
        peaks = [value for value in (numeric(row.get("peak_speed")) for row in group) if value is not None]
        summary.append(
            {
                "horse_key": horse_key,
                "horse_name": clean(latest.get("horse_name")),
                "runs_with_sectionals": len(group),
                "avg_early_speed": average_column(group, "early_speed"),
                "avg_mid_speed": average_column(group, "mid_speed"),
                "avg_late_speed": average_column(group, "late_speed"),
                "avg_peak_speed": average_column(group, "peak_speed"),
                "avg_speed": average_column(group, "avg_speed"),
                "best_peak_speed": format_number(max(peaks) if peaks else None),
                "latest_meeting_date": clean(latest.get("meeting_date")),
                "latest_track": clean(latest.get("track")),
                "latest_race_no": clean(latest.get("race_no")),
            }
        )
    return sorted(summary, key=lambda item: (-int(item["runs_with_sectionals"]), item["horse_name"]))


def final_status(files_found: int, files_read: int, rows_output: int) -> str:
    if files_found == 0:
        return "NO_SECTIONAL_HISTORY_FILES_FOUND"
    if files_read == 0:
        return "SECTIONAL_HISTORY_MASTER_READ_FAILED"
    if rows_output == 0:
        return "SECTIONAL_HISTORY_MASTER_EMPTY"
    return "SECTIONAL_HISTORY_MASTER_BUILT"


def main() -> None:
    lookup = manifest_lookup()
    files = source_files()
    parsed_rows: list[dict[str, Any]] = []
    files_read = 0
    files_failed = 0

    for path in files:
        context = context_for_file(path, lookup)
        try:
            rows = parse_download(path, context)
            if rows:
                files_read += 1
                parsed_rows.extend(rows)
            else:
                files_failed += 1
        except Exception as exc:  # noqa: BLE001 - one malformed source must not stop the master.
            files_failed += 1
            print(f"[racingcom_sectional_history_master_v1] failed {path.name}: {exc.__class__.__name__}: {exc}")

    master_rows = dedupe_rows(parsed_rows)
    horse_rows = build_horse_summary(master_rows)
    unique_races = {
        "|".join([clean(row.get("meeting_date")), normalise_track_for_key(clean(row.get("track"))), clean(row.get("race_no"))])
        for row in master_rows
        if clean(row.get("meeting_date")) and clean(row.get("track")) and clean(row.get("race_no"))
    }
    status = final_status(len(files), files_read, len(master_rows))
    audit_row = {
        "files_found": len(files),
        "files_read": files_read,
        "files_failed": files_failed,
        "rows_output": len(master_rows),
        "unique_horses": len({row["horse_key"] for row in master_rows if clean(row.get("horse_key"))}),
        "unique_races": len(unique_races),
        "final_status": status,
    }

    write_csv(MASTER_OUT, master_rows, MASTER_COLUMNS)
    write_csv(HORSES_OUT, horse_rows, HORSE_COLUMNS)
    write_csv(AUDIT_OUT, [audit_row], AUDIT_COLUMNS)

    print(f"[racingcom_sectional_history_master_v1] files_found={len(files)} files_read={files_read} rows_output={len(master_rows)}")
    print(f"[racingcom_sectional_history_master_v1] unique_horses={audit_row['unique_horses']} unique_races={audit_row['unique_races']}")
    print(f"[racingcom_sectional_history_master_v1] final_status={status}")
    print(f"[racingcom_sectional_history_master_v1] wrote {MASTER_OUT.relative_to(ROOT)}")
    print(f"[racingcom_sectional_history_master_v1] wrote {HORSES_OUT.relative_to(ROOT)}")
    print(f"[racingcom_sectional_history_master_v1] wrote {AUDIT_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
