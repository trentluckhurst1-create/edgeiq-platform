from __future__ import annotations

import csv
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

DOWNLOAD_DIR = DATA / "racingcom_sectionals_downloads_v1"
MANIFEST = DATA / "racingcom_speed_data_csv_download_manifest_v1.csv"

OUT = DATA / "racingcom_sectionals_normalised_v1.csv"
AUDIT = DATA / "racingcom_sectionals_normalised_v1_audit.csv"

COUNTRY_SUFFIXES = ("IRE", "USA", "JPN", "GER", "SAF", "NZ", "GB", "FR")

OUT_COLUMNS = [
    "meeting_date",
    "track",
    "race_no",
    "source_speed_data_url",
    "horse_name",
    "horse_key",
    "position",
    "barrier",
    "jockey",
    "trainer",
    "dist_run",
    "early_speed",
    "mid_speed",
    "late_speed",
    "peak_speed",
    "avg_speed",
    "source_file",
    "ingest_status",
]

AUDIT_COLUMNS = [
    "row_type",
    "source_file",
    "files_found",
    "files_read",
    "files_failed",
    "rows_output",
    "unique_horses",
    "unique_races",
    "missing_horse_name_rows",
    "missing_avg_speed_rows",
    "missing_columns",
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


def read_manifest() -> list[dict[str, str]]:
    if not MANIFEST.exists():
        return []
    try:
        with MANIFEST.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with MANIFEST.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def canonical_horse_key(value: Any) -> str:
    raw = clean(value).upper()
    pattern = "|".join(COUNTRY_SUFFIXES)
    bracket_suffix = bool(re.search(rf"\s*\(({pattern})\)\s*$", raw, flags=re.IGNORECASE))
    without_bracket_suffix = re.sub(rf"\s*\(({pattern})\)\s*$", "", raw, flags=re.IGNORECASE).strip()
    compact = re.sub(r"[^A-Z0-9]+", "", without_bracket_suffix)
    if bracket_suffix:
        return compact
    had_spaces_or_punctuation = bool(re.search(r"[^A-Z0-9]", without_bracket_suffix))
    if not had_spaces_or_punctuation:
        for suffix in COUNTRY_SUFFIXES:
            if compact.endswith(suffix) and len(compact) > len(suffix) + 3:
                return compact[: -len(suffix)]
    return compact


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


def detect_delimiter(text: str) -> str:
    first = text.splitlines()[0] if text.splitlines() else ""
    return ";" if first.count(";") >= first.count(",") else ","


def read_raw_rows(path: Path) -> tuple[list[list[str]], str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
    delimiter = detect_delimiter(text)
    rows = list(csv.reader(text.splitlines(), delimiter=delimiter))
    return rows, delimiter


def meeting_date_from_text(value: str) -> str:
    text = clean(value)
    for fmt in ("%d/%m/%Y %I:%M:%S %p", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[: len(datetime.strptime("31/05/2026 12:00:00 AM" if fmt == "%d/%m/%Y %I:%M:%S %p" else "31/05/2026" if fmt == "%d/%m/%Y" else "2026-05-31", fmt).strftime(fmt))], fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if match:
        return match.group(1)
    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return ""


def date_from_url(url: str) -> str:
    match = re.search(r"/form/(\d{4}-\d{2}-\d{2})/", clean(url))
    return match.group(1) if match else ""


def race_from_url(url: str) -> str:
    match = re.search(r"/race/(\d+)/", clean(url))
    return str(int(match.group(1))) if match else ""


def manifest_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in rows:
        filename = clean(row.get("downloaded_filename")) or Path(clean(row.get("local_path"))).name
        if filename and clean(row.get("csv_download_success")).upper() == "TRUE":
            lookup[filename] = row
    return lookup


def context_from_filename(path: Path) -> dict[str, str]:
    match = re.search(r"(?P<date>\d{4}-\d{2}-\d{2})_(?P<track>.+?)_R(?P<race>\d+)_", path.name)
    if not match:
        return {"meeting_date": "", "track": "", "race_no": "", "source_speed_data_url": ""}
    track = match.group("track").replace("-", " ").replace("_", " ").upper()
    return {
        "meeting_date": match.group("date"),
        "track": track,
        "race_no": str(int(match.group("race"))),
        "source_speed_data_url": "",
    }


def context_for_file(path: Path, manifest_by_file: dict[str, dict[str, str]]) -> dict[str, str]:
    manifest = manifest_by_file.get(path.name)
    if manifest:
        url = clean(manifest.get("source_speed_data_url"))
        return {
            "meeting_date": date_from_url(url),
            "track": clean(manifest.get("track")),
            "race_no": clean(manifest.get("race_no")) or race_from_url(url),
            "source_speed_data_url": url,
        }
    return context_from_filename(path)


def is_metadata_row(row: list[str]) -> bool:
    first = clean(row[0] if row else "")
    return bool(re.search(r"\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}", first))


def looks_like_header(row: list[str]) -> bool:
    lowered = {clean(cell).lower().replace(" ", "_") for cell in row}
    return bool(lowered & {"horse", "horse_name", "runner", "runner_name"}) and bool(
        lowered & {"avg_speed", "average_speed", "peak_speed", "dist_run", "distance"}
    )


def column_index(header: list[str], options: tuple[str, ...]) -> int | None:
    normalised = [clean(cell).lower().replace(" ", "_").replace("-", "_") for cell in header]
    for option in options:
        if option in normalised:
            return normalised.index(option)
    for option in options:
        for idx, value in enumerate(normalised):
            if option in value:
                return idx
    return None


def value_at(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return clean(row[index])


def average(values: list[float]) -> float | None:
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
    return average(early), average(middle), average(late)


def parse_triple_runner_row(row: list[str], context: dict[str, str], source_file: str) -> tuple[dict[str, Any] | None, str]:
    if len(row) < 5:
        return None, "ROW_TOO_SHORT"
    horse_name = clean(row[0])
    if not horse_name:
        return None, "MISSING_HORSE_NAME"

    position = clean(row[1])
    distances: list[float] = []
    speeds: list[float] = []
    index = 2
    while index + 1 < len(row):
        distance = parse_number(row[index])
        speed = parse_number(row[index + 1])
        if distance is not None:
            distances.append(distance)
        if speed is not None and speed > 0:
            speeds.append(speed)
        index += 3

    early, mid, late = phase_speeds(speeds)
    avg = average(speeds)
    peak = max(speeds) if speeds else None
    dist_run = max(distances) if distances else None

    ingest_status = "INGESTED" if horse_name and avg is not None else "INGESTED_WITH_MISSING_SPEED"
    return (
        {
            "meeting_date": context.get("meeting_date", ""),
            "track": context.get("track", ""),
            "race_no": context.get("race_no", ""),
            "source_speed_data_url": context.get("source_speed_data_url", ""),
            "horse_name": horse_name,
            "horse_key": canonical_horse_key(horse_name),
            "position": position,
            "barrier": "",
            "jockey": "",
            "trainer": "",
            "dist_run": format_number(dist_run),
            "early_speed": format_number(early),
            "mid_speed": format_number(mid),
            "late_speed": format_number(late),
            "peak_speed": format_number(peak),
            "avg_speed": format_number(avg),
            "source_file": source_file,
            "ingest_status": ingest_status,
        },
        ingest_status,
    )


def parse_header_rows(rows: list[list[str]], context: dict[str, str], source_file: str) -> tuple[list[dict[str, Any]], str]:
    header = rows[0]
    horse_idx = column_index(header, ("horse_name", "horse", "runner_name", "runner"))
    position_idx = column_index(header, ("position", "finish_position", "place", "placing"))
    barrier_idx = column_index(header, ("barrier", "bar"))
    jockey_idx = column_index(header, ("jockey",))
    trainer_idx = column_index(header, ("trainer",))
    dist_idx = column_index(header, ("dist_run", "distance_run", "distance"))
    early_idx = column_index(header, ("early_speed", "early_speed_kmh"))
    mid_idx = column_index(header, ("mid_speed", "midrace_speed", "mid_speed_kmh"))
    late_idx = column_index(header, ("late_speed", "late_speed_kmh"))
    peak_idx = column_index(header, ("peak_speed", "top_speed", "peak_speed_kmh"))
    avg_idx = column_index(header, ("avg_speed", "average_speed", "avg_speed_kmh"))

    output: list[dict[str, Any]] = []
    for row in rows[1:]:
        horse_name = value_at(row, horse_idx)
        output.append(
            {
                "meeting_date": context.get("meeting_date", ""),
                "track": context.get("track", ""),
                "race_no": context.get("race_no", ""),
                "source_speed_data_url": context.get("source_speed_data_url", ""),
                "horse_name": horse_name,
                "horse_key": canonical_horse_key(horse_name),
                "position": value_at(row, position_idx),
                "barrier": value_at(row, barrier_idx),
                "jockey": value_at(row, jockey_idx),
                "trainer": value_at(row, trainer_idx),
                "dist_run": value_at(row, dist_idx),
                "early_speed": value_at(row, early_idx),
                "mid_speed": value_at(row, mid_idx),
                "late_speed": value_at(row, late_idx),
                "peak_speed": value_at(row, peak_idx),
                "avg_speed": value_at(row, avg_idx),
                "source_file": source_file,
                "ingest_status": "INGESTED_HEADER_CSV" if horse_name and value_at(row, avg_idx) else "INGESTED_HEADER_CSV_WITH_MISSING_FIELDS",
            }
        )
    missing = []
    for name, idx in {
        "horse_name": horse_idx,
        "position": position_idx,
        "barrier": barrier_idx,
        "jockey": jockey_idx,
        "trainer": trainer_idx,
        "dist_run": dist_idx,
        "early_speed": early_idx,
        "mid_speed": mid_idx,
        "late_speed": late_idx,
        "peak_speed": peak_idx,
        "avg_speed": avg_idx,
    }.items():
        if idx is None:
            missing.append(name)
    return output, "|".join(missing)


def parse_download_file(path: Path, context: dict[str, str]) -> tuple[list[dict[str, Any]], str]:
    raw_rows, _delimiter = read_raw_rows(path)
    rows = [[clean(cell) for cell in row] for row in raw_rows if any(clean(cell) for cell in row)]
    if not rows:
        return [], "EMPTY_FILE"

    if is_metadata_row(rows[0]):
        if not context.get("meeting_date"):
            context["meeting_date"] = meeting_date_from_text(rows[0][0])
        data_rows = rows[1:]
        parsed: list[dict[str, Any]] = []
        statuses = Counter()
        for row in data_rows:
            parsed_row, status = parse_triple_runner_row(row, context, path.name)
            statuses[status] += 1
            if parsed_row:
                parsed.append(parsed_row)
        missing = ["barrier", "jockey", "trainer"]
        if any(not clean(row.get("avg_speed")) for row in parsed):
            missing.append("avg_speed")
        return parsed, "|".join(missing)

    if looks_like_header(rows[0]):
        return parse_header_rows(rows, context, path.name)

    parsed = []
    for row in rows:
        parsed_row, _status = parse_triple_runner_row(row, context, path.name)
        if parsed_row:
            parsed.append(parsed_row)
    return parsed, "barrier|jockey|trainer"


def final_status(files_found: int, files_read: int, rows_output: int) -> str:
    if files_found == 0:
        return "NO_DOWNLOADED_CSV_FILES_FOUND"
    if files_read == 0:
        return "SECTIONAL_CSV_INGEST_FAILED"
    if rows_output == 0:
        return "SECTIONAL_CSV_NO_ROWS_OUTPUT"
    return "SECTIONAL_CSV_INGESTED"


def main() -> None:
    manifest_rows = read_manifest()
    manifest_by_file = manifest_lookup(manifest_rows)
    files = sorted(DOWNLOAD_DIR.glob("*.csv"))
    output_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    files_read = 0
    files_failed = 0

    for path in files:
        context = context_for_file(path, manifest_by_file)
        try:
            parsed_rows, missing_columns = parse_download_file(path, context)
            if parsed_rows:
                files_read += 1
                output_rows.extend(parsed_rows)
            else:
                files_failed += 1
            audit_rows.append(
                {
                    "row_type": "FILE",
                    "source_file": path.name,
                    "files_found": "",
                    "files_read": 1 if parsed_rows else 0,
                    "files_failed": 0 if parsed_rows else 1,
                    "rows_output": len(parsed_rows),
                    "unique_horses": len({row["horse_key"] for row in parsed_rows if clean(row.get("horse_key"))}),
                    "unique_races": 1 if parsed_rows else 0,
                    "missing_horse_name_rows": sum(1 for row in parsed_rows if not clean(row.get("horse_name"))),
                    "missing_avg_speed_rows": sum(1 for row in parsed_rows if not clean(row.get("avg_speed"))),
                    "missing_columns": missing_columns,
                    "final_status": "FILE_INGESTED" if parsed_rows else "FILE_NO_ROWS_OUTPUT",
                }
            )
        except Exception as exc:  # noqa: BLE001 - one malformed file should not stop the batch.
            files_failed += 1
            audit_rows.append(
                {
                    "row_type": "FILE",
                    "source_file": path.name,
                    "files_found": "",
                    "files_read": 0,
                    "files_failed": 1,
                    "rows_output": 0,
                    "unique_horses": 0,
                    "unique_races": 0,
                    "missing_horse_name_rows": 0,
                    "missing_avg_speed_rows": 0,
                    "missing_columns": f"READ_FAILED:{exc.__class__.__name__}",
                    "final_status": "FILE_FAILED",
                }
            )

    unique_races = {
        "|".join([clean(row.get("meeting_date")), clean(row.get("track")), clean(row.get("race_no"))])
        for row in output_rows
        if clean(row.get("meeting_date")) and clean(row.get("track")) and clean(row.get("race_no"))
    }
    status = final_status(len(files), files_read, len(output_rows))
    summary_row = {
        "row_type": "SUMMARY",
        "source_file": "",
        "files_found": len(files),
        "files_read": files_read,
        "files_failed": files_failed,
        "rows_output": len(output_rows),
        "unique_horses": len({row["horse_key"] for row in output_rows if clean(row.get("horse_key"))}),
        "unique_races": len(unique_races),
        "missing_horse_name_rows": sum(1 for row in output_rows if not clean(row.get("horse_name"))),
        "missing_avg_speed_rows": sum(1 for row in output_rows if not clean(row.get("avg_speed"))),
        "missing_columns": "",
        "final_status": status,
    }

    write_csv(OUT, output_rows, OUT_COLUMNS)
    write_csv(AUDIT, [summary_row, *audit_rows], AUDIT_COLUMNS)

    print(f"[racingcom_sectionals_v1] files_found={len(files)} files_read={files_read} rows_output={len(output_rows)}")
    print(f"[racingcom_sectionals_v1] final_status={status}")
    print(f"[racingcom_sectionals_v1] wrote {OUT.relative_to(ROOT)}")
    print(f"[racingcom_sectionals_v1] wrote {AUDIT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
