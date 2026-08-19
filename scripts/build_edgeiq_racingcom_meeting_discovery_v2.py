
from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
OUTDIR = ROOT / "outputs" / "performance-intelligence" / "racingcom-v2" / "raw" / "meeting-discovery"
OUTDIR.mkdir(parents=True, exist_ok=True)

RACE_FIELDS = DATA / "race_fields.csv"
OUTPUT = DATA / "edgeiq_racingcom_meeting_discovery_v2.csv"
SUMMARY = DATA / "edgeiq_racingcom_meeting_discovery_v2_summary.json"
AUDIT = DATA / "edgeiq_racingcom_meeting_discovery_v2_audit.csv"
REPORT = DATA / "edgeiq_racingcom_meeting_discovery_v2_report.md"

CALENDAR_URL = "https://www.racing.com/calendar"
MEETS_BY_MONTH = "https://www.racing.com/services/appv2/GetMeetsByMonth/{year}/{month}"
BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")

OUTPUT_COLUMNS = [
    "meeting_id",
    "race_date",
    "track",
    "track_key",
    "state",
    "meeting_url",
    "source_url",
    "source_type",
    "discovery_timestamp",
    "http_status",
    "evidence_status",
    "provenance",
    "source_payload_path",
    "source_hash",
]

TRACK_SLUG_ALIASES = {
    "FLEMINGTON": "flemington",
    "CAULFIELD": "caulfield",
    "CAULFIELD HEATH": "caulfield-heath",
    "SANDOWN": "sandown",
    "SANDOWN HILLSIDE": "sandown-hillside",
    "SANDOWN LAKESIDE": "sandown-lakeside",
    "BENDIGO": "bendigo",
    "BALLARAT": "ballarat",
    "BALLARAT SYN": "sportsbet-ballarat-synthetic",
    "BALLARAT SYNTHETIC": "sportsbet-ballarat-synthetic",
    "GEELONG": "geelong",
    "PAKENHAM": "pakenham",
    "PAKENHAM SYNTHETIC": "southside-pakenham-synthetic",
    "CRANBOURNE": "cranbourne",
    "MOONEE VALLEY": "moonee-valley",
    "MORNINGTON": "mornington",
    "WARRNAMBOOL": "warrnambool",
    "SALE": "sale",
    "SEYMOUR": "seymour",
    "KILMORE": "kilmore",
    "KYNETON": "kyenton",
    "WANGARATTA": "wangaratta",
    "WERRIBEE": "werribee",
    "ECHUCA": "bet365-echuca",
    "SWAN HILL": "bet365-swan-hill",
}


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"", "NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def norm(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper())


def track_key(track: Any) -> str:
    value = norm(track)
    for prefix in ("SPORTSBET", "LADBROKES", "BET365", "PICKLEBETPARK"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    return value


def slugify_track(track: str) -> str:
    key = track_key(track)
    if key in TRACK_SLUG_ALIASES:
        return TRACK_SLUG_ALIASES[key]
    words = re.sub(r"[^a-z0-9]+", "-", clean(track).lower()).strip("-")
    for prefix in ("sportsbet-", "ladbrokes-", "bet365-", "picklebet-park-"):
        if words.startswith(prefix):
            words = words[len(prefix):]
    return words


def parse_date(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    m = re.search(r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", text)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](20\d{2})", text)
    if m:
        return f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    try:
        from datetime import datetime as dt
        parsed = dt.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.date().isoformat()
    except Exception:
        return ""


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: clean(row.get(col, "")) for col in columns})


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def cache_name(url: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9]+", "_", url).strip("_")[:160]
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return f"{safe}_{digest}.txt"


def fetch_text(url: str) -> tuple[str, str, str, str, str]:
    request = Request(url, headers={"User-Agent": "EDGEiQ-RacingCom-MeetingDiscoveryV2/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read()
            http_status = str(getattr(response, "status", ""))
            final_url = clean(getattr(response, "url", url))
    except HTTPError as exc:
        body = exc.read() if hasattr(exc, "read") else b""
        http_status = str(exc.code)
        final_url = url
    except URLError as exc:
        return "", "FETCH_FAILED", "", "", clean(exc.reason)
    except Exception as exc:
        return "", "FETCH_FAILED", "", "", str(exc)
    digest = sha256_bytes(body)
    cache_path = OUTDIR / cache_name(url)
    cache_path.write_bytes(body)
    text = body.decode("utf-8", errors="replace")
    return text, http_status, final_url, str(cache_path.relative_to(ROOT)), digest


def first_value(mapping: dict[str, Any], names: list[str]) -> str:
    for name in names:
        if name in mapping and clean(mapping.get(name)):
            return clean(mapping.get(name))
        title_name = name[:1].upper() + name[1:]
        if title_name in mapping and clean(mapping.get(title_name)):
            return clean(mapping.get(title_name))
    return ""


def meeting_url_from_value(raw_url: str, date: str, track: str) -> str:
    raw_url = clean(raw_url)
    if raw_url:
        if re.match(r"^https?://", raw_url, re.I):
            return raw_url.split("?")[0]
        if re.match(r"^\d{4}-\d{2}-\d{2}/", raw_url):
            return f"https://www.racing.com/form/{raw_url.strip('/')}"
        return urljoin("https://www.racing.com", raw_url).split("?")[0]
    if date and track:
        return f"https://www.racing.com/form/{date}/{slugify_track(track)}"
    return ""


def make_meeting_id(date: str, track: str) -> str:
    return f"{date}_{track_key(track)}"


def row_from_evidence(date: str, track: str, state: str, meeting_url: str, source_url: str, source_type: str, evidence_status: str, provenance: str, http_status: str = "", source_payload_path: str = "", source_hash: str = "") -> dict[str, str]:
    date = parse_date(date)
    track = clean(track)
    state = clean(state) or "VIC"
    meeting_url = meeting_url_from_value(meeting_url, date, track)
    return {
        "meeting_id": make_meeting_id(date, track),
        "race_date": date,
        "track": track,
        "track_key": track_key(track),
        "state": state,
        "meeting_url": meeting_url,
        "source_url": clean(source_url),
        "source_type": source_type,
        "discovery_timestamp": BUILT_UTC,
        "http_status": clean(http_status),
        "evidence_status": evidence_status,
        "provenance": provenance,
        "source_payload_path": clean(source_payload_path),
        "source_hash": clean(source_hash),
    }


def meeting_rows_from_race_fields() -> list[dict[str, str]]:
    rows = []
    for row in read_csv_rows(RACE_FIELDS):
        date = parse_date(row.get("race_date"))
        track = clean(row.get("display_track") or row.get("track"))
        state = clean(row.get("state")) or "VIC"
        if not date or not track:
            continue
        rows.append(row_from_evidence(
            date=date,
            track=track,
            state=state,
            meeting_url=clean(row.get("meeting_url")),
            source_url=str(RACE_FIELDS.relative_to(ROOT)),
            source_type="LOCAL_RACE_FIELDS_MEETING_EVIDENCE",
            evidence_status="OBSERVED_IN_LOCAL_RACE_FIELDS",
            provenance="Meeting identity observed in race_fields.csv; no race-level expansion performed by V2 meeting discovery.",
            source_hash=sha256_bytes(RACE_FIELDS.read_bytes()),
        ))
    return rows


def month_targets(local_rows: list[dict[str, str]]) -> list[tuple[int, int]]:
    targets: list[tuple[int, int]] = []
    for row in local_rows:
        date = parse_date(row.get("race_date"))
        if date:
            y, m, _ = date.split("-")
            targets.append((int(y), int(m)))
    now = datetime.now()
    for offset in (-1, 0, 1):
        month = now.month + offset
        year = now.year
        while month < 1:
            month += 12
            year -= 1
        while month > 12:
            month -= 12
            year += 1
        targets.append((year, month))
    seen = []
    for item in targets:
        if item not in seen:
            seen.append(item)
    return seen[:6]


def meetings_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("meetings", "data", "items", "Meets", "RaceMeetings"):
        value = payload.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
    if isinstance(payload.get("Months"), list):
        out = []
        for month in payload["Months"]:
            if isinstance(month, dict):
                entries = month.get("CalendarEntries") or month.get("CalendarEntriesList") or []
                if isinstance(entries, list):
                    out.extend([x for x in entries if isinstance(x, dict)])
        return out
    return []


def meeting_rows_from_month_api(local_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    fetch_log: list[dict[str, str]] = []
    for year, month in month_targets(local_rows):
        url = MEETS_BY_MONTH.format(year=year, month=month)
        text, http_status, final_url, payload_path, digest = fetch_text(url)
        fetch_log.append({"source_url": url, "http_status": http_status, "payload_path": payload_path, "source_hash": digest, "bytes": str(len(text.encode('utf-8'))), "status": "FETCHED" if text else "EMPTY_OR_FAILED"})
        if not text or http_status not in {"200", ""}:
            continue
        try:
            payload = json.loads(text)
        except Exception:
            continue
        for meeting in meetings_from_payload(payload):
            state = first_value(meeting, ["state", "venueState"])
            blob = json.dumps(meeting, ensure_ascii=False).upper()
            if state and norm(state) != "VIC" and "VIC" not in blob:
                continue
            date = first_value(meeting, ["date", "meetingDate", "meetDate", "raceDate"])
            track = first_value(meeting, ["venueName", "venue", "trackName", "track", "name"])
            meeting_url = first_value(meeting, ["meetUrl", "url", "urlSegment"])
            if not parse_date(date) or not clean(track):
                continue
            rows.append(row_from_evidence(
                date=date,
                track=track,
                state=state or "VIC",
                meeting_url=meeting_url,
                source_url=url,
                source_type="RACINGCOM_GET_MEETS_BY_MONTH",
                evidence_status="OBSERVED_IN_RACINGCOM_MONTH_PAYLOAD",
                provenance="Meeting observed in Racing.com GetMeetsByMonth payload; V2 does not emit race-level rows from this meeting.",
                http_status=http_status,
                source_payload_path=payload_path,
                source_hash=digest,
            ))
    return rows, fetch_log


def meeting_rows_from_calendar_page() -> tuple[list[dict[str, str]], dict[str, str]]:
    text, http_status, final_url, payload_path, digest = fetch_text(CALENDAR_URL)
    rows: list[dict[str, str]] = []
    for match in re.finditer(r'href=["\']([^"\']*/form/\d{4}-\d{2}-\d{2}/[^"\']+)["\']', text):
        meeting_url = urljoin("https://www.racing.com", match.group(1).split("?")[0])
        parsed = re.search(r"/form/(\d{4}-\d{2}-\d{2})/([^/\"']+)", meeting_url)
        if not parsed:
            continue
        date = parsed.group(1)
        track = parsed.group(2).replace("-", " ").title()
        rows.append(row_from_evidence(
            date=date,
            track=track,
            state="VIC",
            meeting_url=meeting_url,
            source_url=CALENDAR_URL,
            source_type="RACINGCOM_CALENDAR_PAGE_LINK",
            evidence_status="OBSERVED_IN_RACINGCOM_CALENDAR_HTML",
            provenance="Meeting link observed in Racing.com calendar HTML; no race-level expansion performed.",
            http_status=http_status,
            source_payload_path=payload_path,
            source_hash=digest,
        ))
    return rows, {"source_url": CALENDAR_URL, "http_status": http_status, "payload_path": payload_path, "source_hash": digest, "bytes": str(len(text.encode('utf-8'))), "status": "FETCHED" if text else "EMPTY_OR_FAILED", "observed_links": str(len(rows))}


def merge_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if not row.get("meeting_id") or not row.get("race_date") or not row.get("track_key"):
            continue
        grouped.setdefault(row["meeting_id"], []).append(row)
    merged = []
    source_rank = {
        "RACINGCOM_GET_MEETS_BY_MONTH": 1,
        "RACINGCOM_CALENDAR_PAGE_LINK": 2,
        "LOCAL_RACE_FIELDS_MEETING_EVIDENCE": 3,
    }
    for meeting_id, members in grouped.items():
        members = sorted(members, key=lambda r: (source_rank.get(r["source_type"], 9), r["source_url"]))
        primary = dict(members[0])
        primary["source_url"] = " | ".join(sorted({m["source_url"] for m in members if m.get("source_url")}))
        primary["source_type"] = " | ".join(sorted({m["source_type"] for m in members if m.get("source_type")}))
        primary["http_status"] = " | ".join(sorted({m["http_status"] for m in members if m.get("http_status")}))
        primary["evidence_status"] = "MERGED_MEETING_EVIDENCE" if len(members) > 1 else primary["evidence_status"]
        primary["provenance"] = " || ".join(m["provenance"] for m in members if m.get("provenance"))
        primary["source_payload_path"] = " | ".join(sorted({m["source_payload_path"] for m in members if m.get("source_payload_path")}))
        primary["source_hash"] = " | ".join(sorted({m["source_hash"] for m in members if m.get("source_hash")}))
        merged.append(primary)
    return sorted(merged, key=lambda r: (r["race_date"], r["track_key"], r["meeting_id"]))


def build_audit(rows: list[dict[str, str]], fetch_log: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    columns = OUTPUT_COLUMNS
    race_level_cols = [c for c in ["race_no", "race_url", "speed_data_url", "csv_url"] if c in columns]
    duplicate_ids = len(rows) - len({r["meeting_id"] for r in rows})
    invalid_dates = sum(1 for r in rows if not re.match(r"^20\d{2}-\d{2}-\d{2}$", r.get("race_date", "")))
    invalid_urls = sum(1 for r in rows if r.get("meeting_url") and not re.match(r"^https://www\.racing\.com/form/", r["meeting_url"]))
    missing_provenance = sum(1 for r in rows if not r.get("provenance") or not r.get("source_url"))
    root_escape = sum(1 for r in rows for p in r.get("source_payload_path", "").split(" | ") if p and (".." in Path(p).parts or Path(p).is_absolute()))
    deterministic = rows == sorted(rows, key=lambda r: (r["race_date"], r["track_key"], r["meeting_id"]))
    checks = [
        ("output_rows_gt_zero", len(rows) > 0, len(rows), "Meeting rows emitted."),
        ("no_race_number_column", not race_level_cols, len(race_level_cols), ", ".join(race_level_cols)),
        ("no_race_url_generation_column", "race_url" not in columns, 0 if "race_url" not in columns else 1, "race_url absent from V2 meeting contract."),
        ("no_speed_data_url_generation_column", "speed_data_url" not in columns, 0 if "speed_data_url" not in columns else 1, "speed_data_url absent from V2 meeting contract."),
        ("no_csv_url_column", "csv_url" not in columns, 0 if "csv_url" not in columns else 1, "csv_url absent from V2 meeting contract."),
        ("no_duplicate_canonical_meetings", duplicate_ids == 0, duplicate_ids, "Duplicate meeting_id count."),
        ("valid_dates", invalid_dates == 0, invalid_dates, "Rows with invalid race_date."),
        ("valid_meeting_urls", invalid_urls == 0, invalid_urls, "Meeting URLs must be Racing.com form URLs when present."),
        ("provenance_retained", missing_provenance == 0, missing_provenance, "Rows missing source_url/provenance."),
        ("repository_local_payload_paths", root_escape == 0, root_escape, "Payload paths are relative to repository root."),
        ("deterministic_ordering", deterministic, int(not deterministic), "Rows sorted by date/track/meeting_id."),
    ]
    audit_rows = [{"check": name, "status": "PASS" if passed else "FAIL", "count": str(count), "detail": detail} for name, passed, count, detail in checks]
    status = "RACINGCOM_MEETING_DISCOVERY_V2_PASS" if all(passed for _, passed, _, _ in checks) else "RACINGCOM_MEETING_DISCOVERY_V2_REVIEW_REQUIRED"
    summary = {
        "status": status,
        "built_utc": BUILT_UTC,
        "meeting_rows": len(rows),
        "canonical_meetings": len({r["meeting_id"] for r in rows}),
        "source_types": dict(sorted({k: sum(1 for r in rows if k in r.get("source_type", "")) for k in {part for r in rows for part in r.get("source_type", "").split(" | ") if part}}.items())),
        "fetches": len(fetch_log),
        "fetch_log": fetch_log,
        "race_level_columns": race_level_cols,
        "duplicate_meeting_ids": duplicate_ids,
        "invalid_dates": invalid_dates,
        "invalid_meeting_urls": invalid_urls,
        "missing_provenance": missing_provenance,
        "repo_root_escape_count": root_escape,
        "production_changed": "NO",
        "race_level_rows_generated": 0,
        "fixed_race_expansion_used": "NO",
    }
    return audit_rows, summary


def main() -> int:
    local_rows = meeting_rows_from_race_fields()
    api_rows, fetch_log = meeting_rows_from_month_api(local_rows)
    html_rows, html_fetch = meeting_rows_from_calendar_page()
    fetch_log.append(html_fetch)
    merged = merge_rows(local_rows + api_rows + html_rows)
    audit_rows, summary = build_audit(merged, fetch_log)
    write_csv(OUTPUT, merged, OUTPUT_COLUMNS)
    write_csv(AUDIT, audit_rows, ["check", "status", "count", "detail"])
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    lines = [
        "# EDGEiQ Racing.com Meeting Discovery V2",
        "",
        f"Built UTC: `{BUILT_UTC}`",
        f"Status: `{summary['status']}`",
        "",
        "## Counts",
        f"- Meeting rows: `{summary['meeting_rows']}`",
        f"- Canonical meetings: `{summary['canonical_meetings']}`",
        f"- Race-level rows generated: `0`",
        f"- Fixed race expansion used: `NO`",
        "",
        "## Contract Guardrails",
        "- No `race_no` column.",
        "- No `race_url` column.",
        "- No `speed_data_url` column.",
        "- No CSV URL column.",
        "- No meeting-to-race expansion.",
        "- Payload caches are repository-local under `outputs/performance-intelligence/racingcom-v2/raw/meeting-discovery/`.",
        "",
        "## Source Types",
    ]
    for key, value in summary["source_types"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Audit"])
    for row in audit_rows:
        lines.append(f"- `{row['check']}`: `{row['status']}` ({row['count']}) - {row['detail']}")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "meeting_rows": summary["meeting_rows"], "canonical_meetings": summary["canonical_meetings"], "output": str(OUTPUT.relative_to(ROOT))}, indent=2))
    return 0 if summary["status"] == "RACINGCOM_MEETING_DISCOVERY_V2_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
