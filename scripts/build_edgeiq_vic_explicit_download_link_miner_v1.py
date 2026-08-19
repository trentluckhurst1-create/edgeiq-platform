from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA = APP_ROOT / "public" / "data"
RAW_VIC = PROJECT_ROOT / "outputs" / "sectionals" / "raw" / "VIC"

OUT = DATA / "edgeiq_vic_explicit_download_link_miner_v1.csv"
DIAG_OUT = DATA / "edgeiq_vic_explicit_download_link_miner_diagnostics_v1.csv"

INPUT_CSVS = [
    DATA / "edgeiq_racingcom_speed_network_probe_v1.csv",
    DATA / "edgeiq_racingcom_completed_payload_probe_v1.csv",
    DATA / "edgeiq_racingcom_graphql_parser_v1.csv",
    DATA / "edgeiq_racingcom_calendar_discovery_v1.csv",
]

MINE_COLUMNS = [
    "source_file",
    "source_type",
    "field_name",
    "match_text",
    "candidate_url",
    "confidence",
    "race_date",
    "track",
    "race_no",
    "meeting_id",
    "context_snippet",
]
DIAG_COLUMNS = ["metric", "value", "notes"]

URL_RE = re.compile(r"https?://[^\"'\s<>\\]+", re.IGNORECASE)
CSV_URL_RE = re.compile(r"https?://[^\"'\s<>\\]+?\.csv(?:\?[^\"'\s<>\\]*)?", re.IGNORECASE)
HREF_RE = re.compile(r"(?:href|src)\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
JSON_FIELD_RE = re.compile(
    r"['\"](?P<field>[A-Za-z0-9_]*(?:csv|download|export|file|asset|media|report|sectional|speed)[A-Za-z0-9_]*)['\"]\s*:\s*['\"](?P<value>[^'\"]+)['\"]",
    re.IGNORECASE,
)
KEYWORD_RE = re.compile(
    r"\.csv|download|export|speed\s*data|speedData|sectionals|sectionalsCsv|csvUrl|downloadUrl|fileUrl|href|asset|media|report",
    re.IGNORECASE,
)
MEETING_RACE_RE = re.compile(r"/(\d{6,})_(\d{2})\.csv", re.IGNORECASE)
RACE_PAGE_RE = re.compile(r"/form/(\d{4}-\d{2}-\d{2})/([^/]+)/race/(\d+)", re.IGNORECASE)
FILENAME_RACE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})_([^_]+)_R(\d+)", re.IGNORECASE)


def log(message: str) -> None:
    print(f"[vic_explicit_download_link_miner_v1] {message}")


def clean(value) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-", "UNKNOWN"} else text


def source_rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except Exception:
        return path.as_posix()


def classify_source(path: Path, csv_source_type: str = "") -> str:
    if csv_source_type:
        return csv_source_type
    lower = path.as_posix().lower()
    if lower.endswith(".html") or lower.endswith(".htm"):
        return "HTML"
    if lower.endswith(".json"):
        return "GRAPHQL_JSON"
    return "TEXT"


def normalise_url(value: str, base_url: str = "https://www.racing.com/") -> str:
    raw = unescape(unquote(clean(value))).replace("\\u0026", "&")
    raw = raw.rstrip(".,);]}>")
    if not raw:
        return ""
    if raw.startswith("//"):
        return "https:" + raw
    if raw.startswith("/"):
        return urljoin(base_url, raw)
    if raw.lower().startswith("cloudfront.net/"):
        return "https://d3qmfyv6ad9vwv." + raw
    return raw


def snippet(text: str, start: int, end: int, width: int = 180) -> str:
    left = max(0, start - width)
    right = min(len(text), end + width)
    return re.sub(r"\s+", " ", text[left:right]).strip()[:500]


def infer_from_text(value: str) -> tuple[str, str, str, str]:
    date = track = race_no = meeting_id = ""
    text = clean(value)
    page = RACE_PAGE_RE.search(text)
    if page:
        date = page.group(1)
        track = page.group(2).replace("-", " ").title()
        race_no = str(int(page.group(3)))
    csv_match = MEETING_RACE_RE.search(text)
    if csv_match:
        meeting_id = csv_match.group(1)
        race_no = race_no or str(int(csv_match.group(2)))
    file_match = FILENAME_RACE_RE.search(text)
    if file_match:
        date = date or file_match.group(1)
        track = track or file_match.group(2).replace("-", " ").title()
        race_no = race_no or str(int(file_match.group(3)))
    return date, track, race_no, meeting_id


def confidence_for(field: str, value: str, from_href: bool = False) -> str:
    field_l = clean(field).lower()
    value_l = clean(value).lower()
    if ".csv" in value_l and (value_l.startswith("http") or from_href or "cloudfront" in value_l):
        return "HIGH"
    if any(token in field_l for token in ["csvurl", "downloadurl", "fileurl", "sectionalscsv"]):
        return "MEDIUM" if ".csv" not in value_l else "HIGH"
    if "download" in value_l and (value_l.startswith("http") or from_href):
        return "HIGH"
    return "LOW"


def add_record(records: list[dict[str, str]], source_path: Path, source_type: str, field_name: str, match_text: str, candidate_url: str, confidence: str, context: str, fallback: dict[str, str] | None = None) -> None:
    fallback = fallback or {}
    date, track, race_no, meeting_id = infer_from_text(" ".join([source_path.name, candidate_url, context, match_text]))
    records.append({
        "source_file": source_rel(source_path),
        "source_type": source_type,
        "field_name": clean(field_name),
        "match_text": clean(match_text)[:250],
        "candidate_url": normalise_url(candidate_url) if candidate_url else "",
        "confidence": confidence,
        "race_date": date or clean(fallback.get("race_date", "")),
        "track": track or clean(fallback.get("track", "")),
        "race_no": race_no or clean(fallback.get("race_no", "")),
        "meeting_id": meeting_id or clean(fallback.get("meeting_id", "")),
        "context_snippet": context[:500],
    })


def mine_text(path: Path, text: str, source_type: str, fallback: dict[str, str] | None = None) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    base_url = clean((fallback or {}).get("url", "")) or "https://www.racing.com/"
    for match in CSV_URL_RE.finditer(text):
        url = normalise_url(match.group(0), base_url)
        add_record(records, path, source_type, "explicit_csv_url", url, url, "HIGH", snippet(text, match.start(), match.end()), fallback)
    for match in HREF_RE.finditer(text):
        href = normalise_url(match.group(1), base_url)
        if KEYWORD_RE.search(href):
            conf = confidence_for("href", href, True)
            add_record(records, path, source_type, "href", match.group(1), href, conf, snippet(text, match.start(), match.end()), fallback)
    for match in JSON_FIELD_RE.finditer(text):
        field = match.group("field")
        value = normalise_url(match.group("value"), base_url)
        conf = confidence_for(field, value)
        add_record(records, path, source_type, field, match.group("value"), value if URL_RE.search(value) or value.startswith("/") else "", conf, snippet(text, match.start(), match.end()), fallback)
    for match in KEYWORD_RE.finditer(text):
        context = snippet(text, match.start(), match.end())
        if ".csv" in match.group(0).lower() or "download" in match.group(0).lower() or "export" in match.group(0).lower():
            # Keep weak text mentions visible, but never turn them into fetch targets.
            add_record(records, path, source_type, "keyword_mention", match.group(0), "", "LOW", context, fallback)
    return records


def csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def scan_file_inputs() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    file_paths: list[Path] = []
    for pattern in [RAW_VIC / "racingcom_speed_data" / "*.html", RAW_VIC / "*.html", RAW_VIC / "racingcom_graphql" / "*.json"]:
        file_paths.extend(sorted(pattern.parent.glob(pattern.name)) if pattern.parent.exists() else [])
    for path in sorted(set(file_paths)):
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except Exception:
            continue
        records.extend(mine_text(path, text, classify_source(path)))
    return records


def scan_csv_inputs() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    source_type_map = {
        "edgeiq_racingcom_speed_network_probe_v1.csv": "NETWORK_PROBE_CSV",
        "edgeiq_racingcom_completed_payload_probe_v1.csv": "COMPLETED_PAYLOAD_CSV",
        "edgeiq_racingcom_graphql_parser_v1.csv": "GRAPHQL_PARSER_CSV",
        "edgeiq_racingcom_calendar_discovery_v1.csv": "CALENDAR_DISCOVERY_CSV",
    }
    for path in INPUT_CSVS:
        rows = csv_rows(path)
        source_type = source_type_map.get(path.name, "CSV")
        pseudo_path = path
        for row in rows:
            fallback = {
                "race_date": clean(row.get("race_date", "")),
                "track": clean(row.get("track", "")),
                "race_no": clean(row.get("race_no", "")),
                "url": clean(row.get("url", "")) or clean(row.get("page_url", "")) or clean(row.get("speed_data_url", "")),
            }
            for field, value in row.items():
                text = clean(value)
                if not text:
                    continue
                if KEYWORD_RE.search(field) or KEYWORD_RE.search(text) or ".csv" in text.lower():
                    records.extend(mine_text(pseudo_path, f'"{field}": "{text}"', source_type, fallback))
            body_path = clean(row.get("body_saved_path", "")) or clean(row.get("raw_sample_file", ""))
            if body_path:
                raw_path = PROJECT_ROOT / body_path
                if raw_path.exists() and raw_path.is_file():
                    try:
                        body = raw_path.read_text(encoding="utf-8-sig", errors="ignore")
                    except Exception:
                        body = ""
                    if body:
                        records.extend(mine_text(raw_path, body, "GRAPHQL_JSON", fallback))
    return records


def dedupe(records: list[dict[str, str]]) -> list[dict[str, str]]:
    rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    best: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for record in records:
        key = (
            record.get("source_file", ""),
            record.get("field_name", ""),
            record.get("candidate_url", "") or record.get("match_text", ""),
            record.get("context_snippet", "")[:120],
        )
        current = best.get(key)
        if current is None or rank.get(record.get("confidence", "LOW"), 9) < rank.get(current.get("confidence", "LOW"), 9):
            best[key] = record
    return sorted(best.values(), key=lambda row: (rank.get(row.get("confidence", "LOW"), 9), row.get("source_type", ""), row.get("source_file", ""), row.get("candidate_url", "")))


def diagnostics(records: list[dict[str, str]], files_scanned: int) -> list[dict[str, str]]:
    high = [r for r in records if r["confidence"] == "HIGH"]
    med = [r for r in records if r["confidence"] == "MEDIUM"]
    low = [r for r in records if r["confidence"] == "LOW"]
    candidate_csv = [r for r in records if ".csv" in r.get("candidate_url", "").lower()]
    candidate_download = [r for r in records if r.get("candidate_url") and ("download" in r.get("candidate_url", "").lower() or ".csv" in r.get("candidate_url", "").lower())]
    source_counts = Counter(r["source_type"] for r in records)
    field_counts = Counter(r["field_name"] for r in records if r.get("field_name"))
    if candidate_csv:
        action = "RUN_EXPLICIT_DOWNLOAD_FETCHER_FOR_HIGH_CONFIDENCE_CSV_URLS"
    elif high:
        action = "INSPECT_HIGH_CONFIDENCE_DOWNLOAD_LINKS_BEFORE_FETCHING"
    else:
        action = "NO_EXPLICIT_CSV_LINKS_FOUND; CONTINUE MINING COMPLETED SPEED-DATA PAGE PAYLOADS"
    return [
        {"metric": "run_timestamp_utc", "value": datetime.now(timezone.utc).isoformat(timespec="seconds"), "notes": "UTC run timestamp"},
        {"metric": "files_scanned", "value": str(files_scanned), "notes": "Raw files and public data CSVs scanned"},
        {"metric": "matches_found", "value": str(len(records)), "notes": "Explicit URL/field/keyword evidence rows"},
        {"metric": "high_confidence_links", "value": str(len(high)), "notes": "Explicit .csv/download URL in payload or href"},
        {"metric": "medium_confidence_links", "value": str(len(med)), "notes": "Explicit CSV/download-style field but incomplete URL"},
        {"metric": "low_confidence_mentions", "value": str(len(low)), "notes": "Generic keyword mention only"},
        {"metric": "candidate_csv_urls", "value": str(len(candidate_csv)), "notes": "Rows with candidate URL containing .csv"},
        {"metric": "candidate_download_urls", "value": str(len(candidate_download)), "notes": "Rows with candidate URL containing download or .csv"},
        {"metric": "source_type_counts", "value": json.dumps(dict(source_counts), sort_keys=True), "notes": "Evidence by source type"},
        {"metric": "top_field_names", "value": json.dumps(dict(field_counts.most_common(15)), sort_keys=True), "notes": "Most common field/link types"},
        {"metric": "recommended_next_action", "value": action, "notes": "Conservative next action"},
    ]


def count_inputs() -> int:
    count = 0
    for pattern in [RAW_VIC / "racingcom_speed_data" / "*.html", RAW_VIC / "*.html", RAW_VIC / "racingcom_graphql" / "*.json"]:
        count += len(list(pattern.parent.glob(pattern.name))) if pattern.parent.exists() else 0
    count += sum(1 for p in INPUT_CSVS if p.exists())
    # Count referenced body files separately for diagnostics.
    for path in INPUT_CSVS:
        for row in csv_rows(path):
            body_path = clean(row.get("body_saved_path", "")) or clean(row.get("raw_sample_file", ""))
            if body_path and (PROJECT_ROOT / body_path).exists():
                count += 1
    return count


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    records = dedupe(scan_file_inputs() + scan_csv_inputs())
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MINE_COLUMNS)
        writer.writeheader()
        writer.writerows(records)
    diag = diagnostics(records, count_inputs())
    with DIAG_OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=DIAG_COLUMNS)
        writer.writeheader()
        writer.writerows(diag)
    values = {row["metric"]: row["value"] for row in diag}
    log(f"files_scanned: {values.get('files_scanned', '0')}")
    log(f"matches_found: {values.get('matches_found', '0')}")
    log(f"high_confidence_links: {values.get('high_confidence_links', '0')}")
    log(f"candidate_csv_urls: {values.get('candidate_csv_urls', '0')}")
    log(f"recommended_next_action: {values.get('recommended_next_action', '')}")
    log(f"wrote {OUT.relative_to(APP_ROOT)}")
    log(f"wrote {DIAG_OUT.relative_to(APP_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
