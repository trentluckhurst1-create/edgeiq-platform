from pathlib import Path
from datetime import datetime, timezone
from html import unescape
from io import BytesIO
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import os
import re
import sys
import zipfile

import pandas as pd


APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG = APP_ROOT / "config" / "sectional_sources.csv"
DATA = APP_ROOT / "public" / "data"
RAW_ROOT = PROJECT_ROOT / "outputs" / "sectionals" / "raw"

INGESTION_OUT = DATA / "edgeiq_sectional_source_ingestion_v1.csv"
DIAG_OUT = DATA / "edgeiq_sectional_source_diagnostics_v1.csv"
DISCOVERED_OUT = DATA / "edgeiq_sectional_discovered_links_v1.csv"

CONFIG_COLUMNS = ["state", "source_name", "source_url", "source_type", "notes"]
DISCOVERED_COLUMNS = ["state", "source_name", "parent_url", "discovered_url", "link_text", "detected_type", "fetch_status"]

OUTPUT_COLUMNS = [
    "state",
    "source_name",
    "source_url",
    "source_type",
    "detected_file_type",
    "fetched_at",
    "raw_file",
    "parse_status",
    "parse_message",
    "horse_key",
    "horse",
    "race_date",
    "track",
    "race_no",
    "distance",
    "last_600",
    "last_400",
    "last_200",
    "early_speed",
    "mid_speed",
    "late_speed",
    "peak_speed",
    "top_speed",
    "distance_travelled",
    "sectional_rank",
    "last_600_rank",
    "last_400_rank",
    "last_200_rank",
    "tempo_grade",
    "pace_profile",
    "source_file",
]

DIAG_COLUMNS = [
    "source_count",
    "fetched_count",
    "parsed_count",
    "failed_count",
    "rows_parsed",
    "source_type_distribution",
    "latest_fetch_time",
]

LINK_KEYWORDS = ["sectional", "sectionals", "speed-data", "csv", "zip", "pdf"]
MAX_DISCOVERED_FETCHES = int(os.environ.get("EDGEIQ_SECTIONAL_MAX_DISCOVERED_FETCHES", "80"))


def log(message: str) -> None:
    print(f"[sectional_source_ingestion_v1] {message}")


def clean(value) -> str:
    return str(value or "").strip()


def upper(value) -> str:
    return clean(value).upper()


def norm(value) -> str:
    text = re.sub(r"\([^)]*\)", "", upper(value))
    return re.sub(r"[^A-Z0-9]+", "", text)


def has_value(value) -> bool:
    text = clean(value)
    if not text:
        return False
    return text.upper() not in {"NAN", "NONE", "NULL", "UNKNOWN", "N/A", "-", "NA"}


def safe_name(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", clean(value))
    return text.strip("._") or "sectional_source"


def read_config() -> pd.DataFrame:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if not CONFIG.exists():
        pd.DataFrame(columns=CONFIG_COLUMNS).to_csv(CONFIG, index=False)
        log(f"created config template: {CONFIG.relative_to(APP_ROOT)}")
        return pd.DataFrame(columns=CONFIG_COLUMNS)
    try:
        df = pd.read_csv(CONFIG, dtype=str, encoding="utf-8-sig", on_bad_lines="skip").fillna("")
        for column in CONFIG_COLUMNS:
            if column not in df.columns:
                df[column] = ""
        return df[CONFIG_COLUMNS]
    except Exception as exc:
        log(f"warning: failed to read config: {exc}")
        return pd.DataFrame(columns=CONFIG_COLUMNS)


def detect_file_type_from_url(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    lowered = unescape(str(url or "")).lower()
    if suffix == ".csv" or ".csv" in lowered:
        return "CSV"
    if suffix in {".html", ".htm"}:
        return "HTML"
    if suffix == ".pdf" or ".pdf" in lowered:
        return "PDF"
    if suffix in {".xlsx", ".xls"} or ".xlsx" in lowered or ".xls" in lowered:
        return "XLSX"
    if suffix == ".zip" or ".zip" in lowered:
        return "ZIP"
    return "UNKNOWN"


def detect_file_type(path: Path, content: bytes = b"") -> str:
    url_type = detect_file_type_from_url(path.name)
    if url_type != "UNKNOWN":
        return url_type
    sample = content[:512].lstrip().lower()
    if sample.startswith(b"%pdf"):
        return "PDF"
    if content.startswith(b"PK"):
        return "ZIP"
    if sample.startswith(b"<") or b"<html" in sample or b"<table" in sample:
        return "HTML"
    if b"," in sample and b"\n" in sample:
        return "CSV"
    return "UNKNOWN"


def extension_for(file_type: str) -> str:
    return {
        "CSV": ".csv",
        "HTML": ".html",
        "PDF": ".pdf",
        "XLSX": ".xlsx",
        "ZIP": ".zip",
    }.get(file_type, ".bin")


def raw_dir_for(state: str) -> Path:
    raw_dir = RAW_ROOT / safe_name(state or "UNKNOWN").upper()
    raw_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir


def fetch_bytes(source_url: str) -> tuple[bytes | None, str]:
    parsed = urlparse(source_url)
    try:
        if parsed.scheme in {"http", "https"}:
            request = Request(source_url, headers={"User-Agent": "EDGEiQ-Racing-Sectional-Ingestion/1.0"})
            with urlopen(request, timeout=30) as response:
                return response.read(), "fetched"
        local_path = Path(source_url)
        if not local_path.is_absolute():
            local_path = (PROJECT_ROOT / local_path).resolve()
        if not local_path.exists():
            return None, f"local file missing: {local_path}"
        return local_path.read_bytes(), "copied local file"
    except Exception as exc:
        return None, str(exc)


def save_raw(content: bytes, state: str, source_name: str, source_url: str, fetched_at: str) -> tuple[Path, str]:
    raw_dir = raw_dir_for(state)
    stamp = fetched_at.replace(":", "").replace("-", "").replace("T", "_").replace("Z", "")
    guessed = Path(urlparse(source_url).path)
    temporary = raw_dir / f"{stamp}_{safe_name(source_name)}{guessed.suffix or '.bin'}"
    file_type = detect_file_type(temporary, content)
    raw_path = raw_dir / f"{stamp}_{safe_name(source_name)}{extension_for(file_type)}"
    raw_path.write_bytes(content)
    return raw_path, file_type


def read_raw_table(path: Path, file_type: str) -> tuple[pd.DataFrame, str]:
    try:
        if file_type == "CSV":
            return pd.read_csv(path, dtype=str, encoding="utf-8-sig", on_bad_lines="skip").fillna(""), "parsed CSV"
        if file_type == "HTML":
            tables = pd.read_html(path)
            if not tables:
                return pd.DataFrame(), "no HTML tables found"
            return tables[0].astype(str).fillna(""), f"parsed HTML table 1 of {len(tables)}"
        if file_type == "XLSX":
            return pd.read_excel(path, dtype=str).fillna(""), "parsed XLSX sheet 1"
        return pd.DataFrame(), f"{file_type} parsing not supported"
    except Exception as exc:
        return pd.DataFrame(), f"parse failed: {exc}"


def parse_time_to_seconds(value: str):
    text = clean(value)
    if not text:
        return None
    parts = text.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(text)
    except Exception:
        return None


def seconds_text(value) -> str:
    if value is None:
        return ""
    return f"{float(value):.2f}"


def expand_racing_queensland_sectional_csv(table: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    if table.empty or len(table.columns) < 3:
        return table, ""
    value_col = table.columns[-1]
    header_text = str(value_col)
    if "QLD" not in header_text and "TRACK" not in header_text:
        return table, ""
    if not table[value_col].astype(str).str.contains(";", regex=False).any():
        return table, ""

    track = ""
    distance = ""
    header_match = re.search(r"\d{4}-\d{2}-\d{2}\s+(.+?)\s+QLD", header_text)
    if header_match:
        track = header_match.group(1).strip()
    distance_match = re.search(r"_(\d+)m_", header_text, re.IGNORECASE)
    if distance_match:
        distance = distance_match.group(1)

    rows = []
    for _, row in table.iterrows():
        race_date = first_existing(row, ["Date", "race_date", "date"])
        race_no = first_existing(row, ["RaceNumber", "race_no", "race_number"])
        packed = clean(row.get(value_col, ""))
        parts = [part.strip() for part in packed.split(";")]
        if len(parts) < 5:
            continue
        horse = parts[0]
        barrier = parts[1] if len(parts) > 1 else ""
        section_times = []
        section_speeds = []
        section_markers = []
        for idx in range(2, len(parts) - 2, 3):
            marker = clean(parts[idx])
            speed = clean(parts[idx + 1])
            split_time = clean(parts[idx + 2])
            seconds = parse_time_to_seconds(split_time)
            if seconds is None:
                continue
            section_markers.append(marker)
            section_speeds.append(speed)
            section_times.append(seconds)
        if not section_times:
            continue
        inferred_distance = distance or (section_markers[-1] if section_markers else "")
        last_200 = section_times[-1] if len(section_times) >= 1 else None
        last_400 = sum(section_times[-2:]) if len(section_times) >= 2 else None
        last_600 = sum(section_times[-3:]) if len(section_times) >= 3 else None
        rows.append({
            "horse": horse,
            "horse_key": norm(horse),
            "race_date": race_date,
            "track": track,
            "state": "QLD",
            "race_no": race_no,
            "distance": inferred_distance,
            "barrier": barrier,
            "last_600": seconds_text(last_600),
            "last_400": seconds_text(last_400),
            "last_200": seconds_text(last_200),
            "early_speed": section_speeds[0] if section_speeds else "",
            "mid_speed": section_speeds[len(section_speeds) // 2] if section_speeds else "",
            "late_speed": section_speeds[-1] if section_speeds else "",
            "peak_speed": max([float(s) for s in section_speeds if re.fullmatch(r"\d+(\.\d+)?", s)], default=""),
            "top_speed": max([float(s) for s in section_speeds if re.fullmatch(r"\d+(\.\d+)?", s)], default=""),
        })
    if not rows:
        return table, ""
    return pd.DataFrame(rows).fillna("").astype(str), "parsed Racing Queensland semicolon sectional CSV"


def read_zip_tables(path: Path, state: str, source_name: str) -> tuple[list[tuple[pd.DataFrame, Path, str, str]], str]:
    tables: list[tuple[pd.DataFrame, Path, str, str]] = []
    try:
        with zipfile.ZipFile(path) as archive:
            for member in archive.namelist():
                member_type = detect_file_type_from_url(member)
                if member_type not in {"CSV", "XLSX"}:
                    continue
                content = archive.read(member)
                extracted_dir = raw_dir_for(state) / f"{path.stem}_contents"
                extracted_dir.mkdir(parents=True, exist_ok=True)
                extracted_path = extracted_dir / safe_name(Path(member).name)
                extracted_path.write_bytes(content)
                if member_type == "CSV":
                    table = pd.read_csv(BytesIO(content), dtype=str, encoding="utf-8-sig", on_bad_lines="skip").fillna("")
                else:
                    table = pd.read_excel(BytesIO(content), dtype=str).fillna("")
                tables.append((table, extracted_path, member_type, f"parsed ZIP member {member}"))
        if not tables:
            return tables, "ZIP contained no CSV/XLSX files"
        return tables, f"parsed {len(tables)} CSV/XLSX files from ZIP"
    except Exception as exc:
        return tables, f"ZIP parse failed: {exc}"


def extract_discovered_links(html_path: Path, source: pd.Series) -> list[dict[str, str]]:
    try:
        html = html_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        html = html_path.read_text(errors="ignore")
    parent_url = clean(source.get("source_url", ""))
    discovered = []
    seen = set()
    pattern = re.compile(r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL)
    for href, text_html in pattern.findall(html):
        link_text = re.sub(r"<[^>]+>", " ", text_html)
        link_text = re.sub(r"\s+", " ", unescape(link_text)).strip()
        absolute = urljoin(parent_url, unescape(href).strip())
        haystack = f"{absolute} {link_text}".lower()
        if not any(keyword in haystack for keyword in LINK_KEYWORDS):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        discovered.append({
            "state": clean(source.get("state", "")),
            "source_name": clean(source.get("source_name", "")),
            "parent_url": parent_url,
            "discovered_url": absolute,
            "link_text": link_text,
            "detected_type": detect_file_type_from_url(absolute),
            "fetch_status": "DISCOVERED",
        })
    return discovered


def first_existing(row: pd.Series, names: list[str]) -> str:
    lower_map = {str(col).lower().strip(): col for col in row.index}
    for name in names:
        key = name.lower().strip()
        if key in lower_map and has_value(row.get(lower_map[key], "")):
            return clean(row.get(lower_map[key], ""))
    return ""


def standardise_rows(raw: pd.DataFrame, source: pd.Series, raw_path: Path, file_type: str, fetched_at: str, status: str, message: str, source_url: str = "") -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if raw.empty:
        return rows
    for _, row in raw.iterrows():
        horse = first_existing(row, ["horse", "runner", "runner_name", "selection", "horse_name"])
        horse_key = first_existing(row, ["horse_key", "_horse_key"]) or norm(horse)
        if not has_value(horse_key) and not has_value(horse):
            continue
        rows.append({
            "state": clean(source.get("state", "")),
            "source_name": clean(source.get("source_name", "")),
            "source_url": source_url or clean(source.get("source_url", "")),
            "source_type": clean(source.get("source_type", "")),
            "detected_file_type": file_type,
            "fetched_at": fetched_at,
            "raw_file": raw_path.relative_to(PROJECT_ROOT).as_posix(),
            "parse_status": status,
            "parse_message": message,
            "horse_key": norm(horse_key or horse),
            "horse": horse,
            "race_date": first_existing(row, ["race_date", "date", "run_date", "meeting_date"]),
            "track": first_existing(row, ["track", "meeting", "venue"]),
            "race_no": first_existing(row, ["race_no", "race_number", "race"]),
            "distance": first_existing(row, ["distance", "race_distance", "distance_m"]),
            "last_600": first_existing(row, ["last_600", "last600", "sectional_600", "final_600"]),
            "last_400": first_existing(row, ["last_400", "last400", "sectional_400", "final_400"]),
            "last_200": first_existing(row, ["last_200", "last200", "sectional_200", "final_200"]),
            "early_speed": first_existing(row, ["early_speed", "early_speed_pct", "early_sectional", "first_600"]),
            "mid_speed": first_existing(row, ["mid_speed", "midrace_speed_pct", "mid_speed_pct", "mid_sectional"]),
            "late_speed": first_existing(row, ["late_speed", "closing_speed_pct", "late_speed_pct"]),
            "peak_speed": first_existing(row, ["peak_speed", "speed_figure", "sectional_score"]),
            "top_speed": first_existing(row, ["top_speed", "max_speed"]),
            "distance_travelled": first_existing(row, ["distance_travelled", "distance_covered"]),
            "sectional_rank": first_existing(row, ["sectional_rank", "sectional_score_rank"]),
            "last_600_rank": first_existing(row, ["last_600_rank", "last600_rank"]),
            "last_400_rank": first_existing(row, ["last_400_rank", "last400_rank"]),
            "last_200_rank": first_existing(row, ["last_200_rank", "last200_rank"]),
            "tempo_grade": first_existing(row, ["tempo_grade"]),
            "pace_profile": first_existing(row, ["pace_profile"]),
            "source_file": raw_path.relative_to(PROJECT_ROOT).as_posix(),
        })
    return rows


def build_diagnostics(config: pd.DataFrame, fetch_results: list[dict[str, str]], parsed_rows: int, latest_fetch_time: str) -> pd.DataFrame:
    fetched_count = sum(1 for result in fetch_results if result["fetched"] == "TRUE")
    parsed_count = sum(1 for result in fetch_results if result["parsed"] == "TRUE")
    failed_count = sum(1 for result in fetch_results if result["fetched"] != "TRUE")
    distribution = config["source_type"].replace("", "UNKNOWN").value_counts().to_dict() if not config.empty else {}
    row = {
        "source_count": str(len(config)),
        "fetched_count": str(fetched_count),
        "parsed_count": str(parsed_count),
        "failed_count": str(failed_count),
        "rows_parsed": str(parsed_rows),
        "source_type_distribution": "; ".join(f"{key}:{value}" for key, value in distribution.items()),
        "latest_fetch_time": latest_fetch_time,
    }
    return pd.DataFrame([row], columns=DIAG_COLUMNS)


def process_table_source(source: pd.Series, source_url: str, raw_path: Path, file_type: str, fetched_at: str) -> tuple[list[dict[str, str]], str, bool]:
    if file_type == "ZIP":
        zip_tables, zip_message = read_zip_tables(raw_path, clean(source.get("state", "")), clean(source.get("source_name", "")))
        records: list[dict[str, str]] = []
        for table, extracted_path, member_type, message in zip_tables:
            records.extend(standardise_rows(table, source, extracted_path, member_type, fetched_at, "PARSED", message, source_url))
        return records, zip_message, bool(records)
    table, message = read_raw_table(raw_path, file_type)
    if file_type == "CSV":
        expanded, expanded_message = expand_racing_queensland_sectional_csv(table)
        if expanded_message:
            table = expanded
            message = expanded_message
    records = standardise_rows(table, source, raw_path, file_type, fetched_at, "PARSED" if not table.empty else "NO_ROWS", message, source_url)
    return records, message, bool(records)


def discovered_sort_key(item: dict[str, str]) -> tuple[int, int, str]:
    priority = {"CSV": 0, "XLSX": 1, "ZIP": 2, "PDF": 3, "UNKNOWN": 4}
    text = item.get("discovered_url", "")
    dates = re.findall(r"(20\d{6})", text)
    newest = max([int(value) for value in dates], default=0)
    return (priority.get(item.get("detected_type", "UNKNOWN"), 5), -newest, text)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    config = read_config()
    fetched_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z"

    parsed_records: list[dict[str, str]] = []
    discovered_records: list[dict[str, str]] = []
    fetch_results: list[dict[str, str]] = []
    discovered_fetches = 0

    for _, source in config.iterrows():
        source_url = clean(source.get("source_url", ""))
        if not source_url:
            fetch_results.append({"fetched": "FALSE", "parsed": "FALSE", "message": "missing source_url"})
            continue

        content, fetch_message = fetch_bytes(source_url)
        if content is None:
            fetch_results.append({"fetched": "FALSE", "parsed": "FALSE", "message": fetch_message})
            log(f"{source.get('source_name', '')}: failed - {fetch_message}")
            continue

        raw_path, file_type = save_raw(content, clean(source.get("state", "")), clean(source.get("source_name", "")), source_url, fetched_at)
        records, parse_message, parsed = process_table_source(source, source_url, raw_path, file_type, fetched_at)
        parsed_records.extend(records)
        fetch_results.append({"fetched": "TRUE", "parsed": "TRUE" if parsed else "FALSE", "message": parse_message})
        log(f"{source.get('source_name', '')}: {fetch_message}; {file_type}; {parse_message}; rows={len(records)}")

        if file_type == "HTML":
            links = extract_discovered_links(raw_path, source)
            links = sorted(links, key=discovered_sort_key)
            log(f"{source.get('source_name', '')}: discovered links={len(links)}")
            for link in links:
                link_type = link["detected_type"]
                if link_type not in {"CSV", "XLSX", "ZIP", "PDF"}:
                    link["fetch_status"] = "DISCOVERED_ONLY"
                    discovered_records.append(link)
                    continue
                if discovered_fetches >= MAX_DISCOVERED_FETCHES:
                    link["fetch_status"] = "DISCOVERED_NOT_FETCHED_LIMIT"
                    discovered_records.append(link)
                    continue
                discovered_fetches += 1
                child_content, child_message = fetch_bytes(link["discovered_url"])
                if child_content is None:
                    link["fetch_status"] = f"FETCH_FAILED: {child_message}"
                    discovered_records.append(link)
                    continue
                child_path, child_type = save_raw(
                    child_content,
                    clean(source.get("state", "")),
                    f"{clean(source.get('source_name', ''))}_{link_type}",
                    link["discovered_url"],
                    fetched_at,
                )
                if child_type == "PDF":
                    link["fetch_status"] = "SAVED_PDF_RAW_ONLY"
                    discovered_records.append(link)
                    continue
                child_records, child_parse_message, child_parsed = process_table_source(source, link["discovered_url"], child_path, child_type, fetched_at)
                parsed_records.extend(child_records)
                if child_parsed:
                    fetch_results[-1]["parsed"] = "TRUE"
                link["detected_type"] = child_type
                link["fetch_status"] = "PARSED" if child_parsed else f"NO_ROWS: {child_parse_message}"
                discovered_records.append(link)

    parsed_df = pd.DataFrame(parsed_records, columns=OUTPUT_COLUMNS) if parsed_records else pd.DataFrame(columns=OUTPUT_COLUMNS)
    discovered_df = pd.DataFrame(discovered_records, columns=DISCOVERED_COLUMNS) if discovered_records else pd.DataFrame(columns=DISCOVERED_COLUMNS)
    diagnostics = build_diagnostics(config, fetch_results, len(parsed_df), fetched_at if len(config) else "")

    parsed_df.to_csv(INGESTION_OUT, index=False)
    discovered_df.to_csv(DISCOVERED_OUT, index=False)
    diagnostics.to_csv(DIAG_OUT, index=False)

    diag = diagnostics.iloc[0].to_dict()
    type_counts = discovered_df["detected_type"].value_counts().to_dict() if not discovered_df.empty else {}
    log(f"source_count: {diag['source_count']}")
    log(f"fetched_count: {diag['fetched_count']}")
    log(f"parsed_count: {diag['parsed_count']}")
    log(f"discovered_links: {len(discovered_df)}")
    log(f"discovered_type_distribution: {type_counts}")
    log(f"rows_parsed: {diag['rows_parsed']}")
    log(f"wrote {INGESTION_OUT.relative_to(APP_ROOT)}")
    log(f"wrote {DISCOVERED_OUT.relative_to(APP_ROOT)}")
    log(f"wrote {DIAG_OUT.relative_to(APP_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
