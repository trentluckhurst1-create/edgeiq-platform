from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUTPUT = DATA / "edgeiq_racing_australia_track_conditions_v1.json"

STATE_URLS = {
    "VIC": "https://www.racingaustralia.horse/InteractiveForm/TrackCondition.aspx?State=VIC",
    "WA": "https://www.racingaustralia.horse/InteractiveForm/TrackCondition.aspx?State=WA",
}

MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

SPONSOR_PREFIXES = (
    "LADBROKES ",
    "SPORTSBET-",
    "SPORTSBET ",
    "BET365 ",
    "BETDELUXE ",
    "PICKLEBET PARK ",
)

ALIASES = {
    "CAULFIELD HEATH": "CAULFIELD",
    "SANDOWN HILLSIDE": "SANDOWN",
    "SANDOWN LAKESIDE": "SANDOWN",
    "LADBROKES PARK": "SANDOWN",
    "LADBROKES PARK HILLSIDE": "SANDOWN",
    "LADBROKES PARK LAKESIDE": "SANDOWN",
    "BALLARAT SYNTHETIC": "BALLARAT",
    "SPORTSBET-BALLARAT SYNTHETIC": "BALLARAT",
    "GEELONG SYNTHETIC": "GEELONG",
    "PAKENHAM SYNTHETIC": "PAKENHAM",
    "SOUTHSIDE PAKENHAM SYNTHETIC": "PAKENHAM",
    "BELMONT PARK": "BELMONT",
}

# Racing Australia can leave the main Track Condition table cell at the morning
# rating while publishing a later official change in the Comment cell, for example:
# "Track Upgraded to (Good 4) @ 1:53 PM after Race 3".  Only promote an explicit
# official-condition phrase; never infer a rating from unrelated prose.
TRACK_UPDATE_RE = re.compile(
    r"(?:\btrack\s+)?(?:upgraded|downgraded|rated|changed|amended)\s+"
    r"(?:to|as)?\s*\(?\s*((?:Firm|Good|Soft|Heavy|Synthetic)\s*\d+)\s*\)?",
    flags=re.IGNORECASE,
)


def clean(value: Any) -> str:
    if value is None:
        return ""
    value = re.sub(r"\s+", " ", str(value)).strip()
    if value.lower() in {"", "none", "null", "-"}:
        return ""
    return value


def usable(value: Any) -> str:
    value = clean(value)
    if value.lower() in {"n/a", "na", "not available", "tba"}:
        return ""
    return value


def canonical_track(value: Any) -> str:
    raw = clean(value).upper()
    for prefix in SPONSOR_PREFIXES:
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
            break
    raw = ALIASES.get(raw, raw)
    return raw.replace(" ", "_")


def canonical_condition(value: str) -> str:
    match = re.fullmatch(
        r"\s*(Firm|Good|Soft|Heavy|Synthetic)\s*(\d+)\s*",
        clean(value),
        flags=re.IGNORECASE,
    )
    if not match:
        return clean(value)
    return f"{match.group(1).title()} {match.group(2)}"


def latest_explicit_track_update(comment: str) -> tuple[str, str]:
    matches = list(TRACK_UPDATE_RE.finditer(clean(comment)))
    if not matches:
        return "", ""
    match = matches[-1]
    condition = canonical_condition(match.group(1))
    evidence = clean(match.group(0))
    return condition, evidence


class TrackConditionTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_tr = False
        self.in_td = False
        self.cells: list[dict[str, str]] = []
        self.rows: list[list[dict[str, str]]] = []
        self.parts: list[str] = []
        self.href = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "tr":
            self.in_tr = True
            self.cells = []
        elif tag == "td" and self.in_tr:
            self.in_td = True
            self.parts = []
            self.href = ""
        elif tag == "br" and self.in_td:
            self.parts.append(" | ")
        elif tag == "a" and self.in_td:
            for key, value in attrs:
                if key.lower() == "href" and value:
                    self.href = value
                    break

    def handle_data(self, data: str) -> None:
        if self.in_td:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "td" and self.in_td:
            self.cells.append({"text": clean("".join(self.parts)), "href": self.href})
            self.in_td = False
            self.parts = []
            self.href = ""
        elif tag == "tr" and self.in_tr:
            if self.cells:
                self.rows.append(self.cells)
            self.in_tr = False
            self.cells = []


def operating_date() -> date:
    raw = clean(os.environ.get("EDGEIQ_PIPELINE_DATE"))
    if raw:
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            pass
    return datetime.now().date()


def infer_date(day: int, month: int, reference: date) -> str:
    candidates: list[date] = []
    for year in (reference.year - 1, reference.year, reference.year + 1):
        try:
            candidates.append(date(year, month, day))
        except ValueError:
            pass
    if not candidates:
        return ""
    return min(candidates, key=lambda candidate: abs((candidate - reference).days)).isoformat()


def parse_meeting_cell(value: str, reference: date) -> tuple[str, str]:
    value = clean(value)
    match = re.match(
        r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})-([A-Za-z]{3})\s+(.+)$",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return "", value
    day = int(match.group(1))
    month = MONTHS.get(match.group(2).upper())
    meeting = clean(match.group(3))
    return (infer_date(day, month, reference) if month else "", meeting)


def fetch_state(state: str, url: str, reference: date) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; EDGEiQ-Racing/1.0; +https://github.com/trentluckhurst1-create/edgeiq-platform)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")
        status = getattr(response, "status", 200)

    parser = TrackConditionTableParser()
    parser.feed(html)
    records: list[dict[str, Any]] = []
    condition_updates = 0

    for cells in parser.rows:
        if len(cells) < 10:
            continue
        meeting_cell = clean(cells[0].get("text"))
        race_date, meeting_name = parse_meeting_cell(meeting_cell, reference)
        if not race_date or not meeting_name:
            continue

        reported_condition = canonical_condition(usable(cells[2].get("text")))
        comment = usable(cells[8].get("text"))
        updated_condition, update_evidence = latest_explicit_track_update(comment)
        effective_condition = updated_condition or reported_condition
        if updated_condition and updated_condition != reported_condition:
            condition_updates += 1

        record = {
            "state": state,
            "race_date": race_date,
            "meeting_display": meeting_name,
            "canonical_track_identity": canonical_track(meeting_name),
            "track_type": usable(cells[1].get("text")),
            "track_condition": effective_condition,
            "track_condition_reported": reported_condition,
            "track_condition_update_source": "Racing Australia comment" if updated_condition else "",
            "track_condition_update_evidence": update_evidence,
            "penetrometer": usable(cells[3].get("text")),
            "weather_forecast": usable(cells[4].get("text")),
            "rail": usable(cells[5].get("text")),
            "irrigation": usable(cells[6].get("text")),
            "rainfall": usable(cells[7].get("text")),
            "comment": comment,
            "additional_information": usable(cells[9].get("text")),
            "meeting_details_href": clean(cells[0].get("href")),
            "source_url": url,
            "source_authority": "Racing Australia",
        }
        records.append(record)

    return records, {
        "state": state,
        "url": url,
        "http_status": status,
        "html_bytes": len(html.encode("utf-8")),
        "table_rows_parsed": len(records),
        "track_condition_comment_updates": condition_updates,
    }


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    reference = operating_date()
    records: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for state, url in STATE_URLS.items():
        try:
            state_records, source = fetch_state(state, url, reference)
            records.extend(state_records)
            sources.append(source)
        except Exception as exc:
            failures.append({"state": state, "url": url, "error": f"{type(exc).__name__}: {exc}"})

    payload = {
        "schema_version": "edgeiq_racing_australia_track_conditions_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "operating_date": reference.isoformat(),
        "authority": "Racing Australia",
        "records": records,
        "sources": sources,
        "failures": failures,
        "fabricated_values": 0,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("EDGEIQ_RACING_AUSTRALIA_TRACK_CONDITIONS_V1 " + ("PASS" if records else "FAIL"))
    print(f"RECORDS={len(records)}")
    print(f"VIC_RECORDS={sum(1 for row in records if row.get('state') == 'VIC')}")
    print(f"WA_RECORDS={sum(1 for row in records if row.get('state') == 'WA')}")
    print(f"TRACK_CONDITION_COMMENT_UPDATES={sum(int(row.get('track_condition') != row.get('track_condition_reported')) for row in records)}")
    print(f"FAILURES={len(failures)}")
    return 0 if records else 1


if __name__ == "__main__":
    raise SystemExit(main())
