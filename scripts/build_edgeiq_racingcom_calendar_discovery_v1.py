from pathlib import Path
from datetime import datetime, timezone
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import pandas as pd


APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA = APP_ROOT / "public" / "data"

RACE_FIELDS = DATA / "race_fields.csv"
OUT = DATA / "edgeiq_racingcom_calendar_discovery_v1.csv"
DIAG_OUT = DATA / "edgeiq_racingcom_calendar_diagnostics_v1.csv"

CALENDAR_URL = "https://www.racing.com/calendar"
MEETS_BY_MONTH = "https://www.racing.com/services/appv2/GetMeetsByMonth/{year}/{month}"

OUT_COLUMNS = [
    "race_date",
    "track",
    "state",
    "meeting_url",
    "race_no",
    "race_url",
    "speed_data_url",
    "source_url",
    "discovery_status",
]

DIAG_COLUMNS = ["metric", "value", "notes"]

TRACK_SLUG_ALIASES = {
    "FLEMINGTON": "flemington",
    "CAULFIELD": "caulfield",
    "CAULFIELD HEATH": "caulfield-heath",
    "SANDOWN": "sandown",
    "SANDOWN HILLSIDE": "sandown-hillside",
    "SANDOWN LAKESIDE": "sandown-lakeside",
    "BENDIGO": "bendigo",
    "BALLARAT": "ballarat",
    "GEELONG": "geelong",
    "PAKENHAM": "pakenham",
    "CRANBOURNE": "cranbourne",
    "MOONEE VALLEY": "moonee-valley",
    "MORNINGTON": "mornington",
    "WARRNAMBOOL": "warrnambool",
    "SALE": "sale",
    "SEYMOUR": "seymour",
    "KILMORE": "kilmore",
    "KYNETON": "kyneton",
    "WANGARATTA": "wangaratta",
    "WERRIBEE": "werribee",
}


def log(message: str) -> None:
    print(f"[racingcom_calendar_v1] {message}")


def clean(value) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def norm(value) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper())


def has_value(value) -> bool:
    return bool(clean(value))


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        log(f"missing {path.relative_to(PROJECT_ROOT)}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", on_bad_lines="skip").fillna("")
        log(f"read {path.relative_to(PROJECT_ROOT)}: {len(df)} rows")
        return df
    except Exception as exc:
        log(f"warning: failed to read {path}: {exc}")
        return pd.DataFrame()


def fetch_text(url: str) -> tuple[str, str, int]:
    request = Request(
        url,
        headers={
            "User-Agent": "EDGEiQ-Racing/1.0 calendar-discovery",
            "Accept": "application/json,text/html,*/*",
            "Referer": "https://www.racing.com/",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
            return body, "FETCHED", int(response.status)
    except HTTPError as exc:
        return exc.read().decode("utf-8", errors="replace") if exc.fp else "", f"HTTP_{exc.code}", int(exc.code)
    except URLError as exc:
        return "", f"URL_ERROR_{clean(exc.reason)}", 0
    except Exception as exc:
        return "", f"ERROR_{exc.__class__.__name__}", 0


def track_slug(track: str) -> str:
    key = clean(track).upper().replace("&", " AND ")
    if key in TRACK_SLUG_ALIASES:
        return TRACK_SLUG_ALIASES[key]
    slug = clean(track).lower()
    slug = re.sub(r"['’]", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug


def race_no(value) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def date_key(value) -> str:
    if not has_value(value):
        return ""
    parsed = pd.to_datetime(pd.Series([value]), errors="coerce", dayfirst=False).iloc[0]
    if pd.isna(parsed):
        return ""
    return parsed.strftime("%Y-%m-%d")


def live_vic_candidates(race_fields: pd.DataFrame) -> list[dict]:
    if race_fields.empty:
        return []
    df = race_fields.copy()
    if "state" in df.columns:
        df = df[df["state"].astype(str).str.upper().str.contains("VIC", na=False)]
    if df.empty:
        return []
    rows = []
    for _, row in df.iterrows():
        race_date = date_key(row.get("race_date", ""))
        track = clean(row.get("track", ""))
        rno = race_no(row.get("race_no", ""))
        if not race_date or not track or not rno:
            continue
        slug = track_slug(track)
        meeting_url = f"https://www.racing.com/form/{race_date}/{slug}"
        race_url = f"{meeting_url}/race/{rno}"
        rows.append({
            "race_date": race_date,
            "track": track,
            "state": "VIC",
            "meeting_url": meeting_url,
            "race_no": rno,
            "race_url": race_url,
            "speed_data_url": f"{race_url}/speed-data",
            "source_url": str(RACE_FIELDS.relative_to(PROJECT_ROOT)),
            "discovery_status": "LIVE_RACE_FIELDS_CANDIDATE",
        })
    return rows


def month_targets(race_fields: pd.DataFrame) -> list[tuple[int, int]]:
    dates = []
    if not race_fields.empty and "race_date" in race_fields.columns:
        parsed = pd.to_datetime(race_fields["race_date"], errors="coerce")
        dates.extend([d for d in parsed.dropna().tolist()])
    now = pd.Timestamp(datetime.now())
    dates.extend([now, now - pd.DateOffset(months=1), now + pd.DateOffset(months=1)])
    seen = []
    for value in dates:
        key = (int(value.year), int(value.month))
        if key not in seen:
            seen.append(key)
    return seen[:4]


def extract_meeting_value(meeting: dict, names: list[str]) -> str:
    for name in names:
        value = meeting.get(name)
        if has_value(value):
            return clean(value)
        title_name = name[:1].upper() + name[1:]
        value = meeting.get(title_name)
        if has_value(value):
            return clean(value)
    return ""


def rows_from_meeting(meeting: dict, source_url: str) -> list[dict]:
    date = date_key(extract_meeting_value(meeting, ["date", "meetingDate", "meetDate", "raceDate"]))
    track = extract_meeting_value(meeting, ["venueName", "venue", "trackName", "track", "name"])
    state = extract_meeting_value(meeting, ["state", "venueState"]) or "VIC"
    meeting_url = extract_meeting_value(meeting, ["meetUrl", "url", "urlSegment"])
    if meeting_url:
        if re.match(r"^\d{4}-\d{2}-\d{2}/", meeting_url):
            meeting_url = f"https://www.racing.com/form/{meeting_url}"
        else:
            meeting_url = urljoin("https://www.racing.com", meeting_url)
    elif date and track:
        meeting_url = f"https://www.racing.com/form/{date}/{track_slug(track)}"
    races = meeting.get("races") or meeting.get("raceList") or meeting.get("raceNumbers") or []
    rows = []
    if isinstance(races, list) and races:
        for race in races:
            rno = race_no(race.get("raceNumber") if isinstance(race, dict) else race)
            if not rno:
                continue
            race_url = f"{meeting_url}/race/{rno}" if meeting_url else ""
            rows.append({
                "race_date": date,
                "track": track,
                "state": state,
                "meeting_url": meeting_url,
                "race_no": rno,
                "race_url": race_url,
                "speed_data_url": f"{race_url}/speed-data" if race_url else "",
                "source_url": source_url,
                "discovery_status": "MEETS_BY_MONTH_RACE",
            })
    elif date and track:
        rows.append({
            "race_date": date,
            "track": track,
            "state": state,
            "meeting_url": meeting_url,
            "race_no": "",
            "race_url": "",
            "speed_data_url": "",
            "source_url": source_url,
            "discovery_status": "MEETS_BY_MONTH_MEETING",
        })
    return rows


def discover_months(race_fields: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    rows = []
    diagnostics = []
    for year, month in month_targets(race_fields):
        url = MEETS_BY_MONTH.format(year=year, month=month)
        body, status, http_status = fetch_text(url)
        diagnostics.append({"metric": "FETCH", "value": url, "notes": f"status={status}; http_status={http_status}; bytes={len(body)}"})
        if status != "FETCHED":
            continue
        try:
            payload = json.loads(body)
        except Exception as exc:
            diagnostics.append({"metric": "PARSE_FAILED", "value": url, "notes": str(exc)})
            continue
    meetings = payload if isinstance(payload, list) else payload.get("meetings") or payload.get("data") or payload.get("items") or []
    if not meetings and isinstance(payload, dict) and isinstance(payload.get("Months"), list):
        meetings = []
        for month in payload["Months"]:
            if isinstance(month, dict):
                meetings.extend(month.get("CalendarEntries") or month.get("CalendarEntriesList") or [])
    if isinstance(meetings, dict):
        meetings = meetings.get("meetings") or meetings.get("items") or []
    for meeting in meetings if isinstance(meetings, list) else []:
        if not isinstance(meeting, dict):
            continue
        state = extract_meeting_value(meeting, ["state", "venueState"])
        text = json.dumps(meeting, ensure_ascii=False)
        if state and norm(state) != "VIC" and "VIC" not in text.upper():
            continue
        rows.extend(rows_from_meeting(meeting, url))
    return rows, diagnostics


def discover_calendar_page() -> tuple[list[dict], dict]:
    body, status, http_status = fetch_text(CALENDAR_URL)
    rows = []
    for match in re.finditer(r'href=["\']([^"\']*/form/\d{4}-\d{2}-\d{2}/[^"\']+)["\']', body):
        meeting_url = urljoin("https://www.racing.com", match.group(1).split("?")[0])
        parsed = re.search(r"/form/(\d{4}-\d{2}-\d{2})/([^/\"']+)", meeting_url)
        if not parsed:
            continue
        date = parsed.group(1)
        track = parsed.group(2).replace("-", " ").title()
        rows.append({
            "race_date": date,
            "track": track,
            "state": "VIC",
            "meeting_url": meeting_url,
            "race_no": "",
            "race_url": "",
            "speed_data_url": "",
            "source_url": CALENDAR_URL,
            "discovery_status": "CALENDAR_PAGE_LINK",
        })
    return rows, {"metric": "FETCH", "value": CALENDAR_URL, "notes": f"status={status}; http_status={http_status}; bytes={len(body)}; links={len(rows)}"}


def expand_meeting_rows(rows: list[dict], default_races: int = 12) -> list[dict]:
    expanded = []
    for row in rows:
        if has_value(row.get("race_no", "")):
            expanded.append(row)
            continue
        meeting_url = clean(row.get("meeting_url", ""))
        if not meeting_url:
            expanded.append(row)
            continue
        for rno in range(1, default_races + 1):
            race_url = f"{meeting_url}/race/{rno}"
            next_row = dict(row)
            next_row["race_no"] = str(rno)
            next_row["race_url"] = race_url
            next_row["speed_data_url"] = f"{race_url}/speed-data"
            next_row["discovery_status"] = f"{row.get('discovery_status', 'MEETING')}_EXPANDED"
            expanded.append(next_row)
    return expanded


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    race_fields = read_csv(RACE_FIELDS)
    rows = live_vic_candidates(race_fields)
    diagnostics = [{"metric": "live_vic_candidates", "value": str(len(rows)), "notes": "Generated from race_fields.csv"}]

    month_rows, month_diag = discover_months(race_fields)
    rows.extend(month_rows)
    diagnostics.extend(month_diag)

    calendar_rows, calendar_diag = discover_calendar_page()
    rows.extend(calendar_rows)
    diagnostics.append(calendar_diag)

    rows = expand_meeting_rows(rows)
    if rows:
        output = pd.DataFrame(rows, columns=OUT_COLUMNS).fillna("")
        output = output.drop_duplicates(subset=["race_date", "track", "race_no", "speed_data_url"], keep="first")
        output = output.sort_values(["race_date", "track", "race_no", "discovery_status"])
    else:
        output = pd.DataFrame(columns=OUT_COLUMNS)

    diagnostics.extend([
        {"metric": "meetings_discovered", "value": str(len(output[["race_date", "track"]].drop_duplicates()) if not output.empty else 0), "notes": "Unique date/track pairs"},
        {"metric": "speed_data_urls", "value": str(int(output["speed_data_url"].astype(str).map(has_value).sum()) if not output.empty else 0), "notes": "Candidate speed-data URLs"},
        {"metric": "latest_discovery_time", "value": datetime.now(timezone.utc).isoformat(timespec="seconds"), "notes": "UTC"},
    ])

    diag = pd.DataFrame(diagnostics, columns=DIAG_COLUMNS)
    output.to_csv(OUT, index=False, encoding="utf-8")
    diag.to_csv(DIAG_OUT, index=False, encoding="utf-8")

    log(f"meetings discovered: {diag.loc[diag['metric'] == 'meetings_discovered', 'value'].iloc[0]}")
    log(f"speed-data URLs generated: {diag.loc[diag['metric'] == 'speed_data_urls', 'value'].iloc[0]}")
    log(f"wrote {OUT.relative_to(APP_ROOT)}")
    log(f"wrote {DIAG_OUT.relative_to(APP_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
