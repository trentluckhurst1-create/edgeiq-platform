
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

csv.field_size_limit(min(sys.maxsize, 2147483647))

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "victoria-performance-intelligence-race-context-authority-v1"
RAW_DIR = DOCS / "raw-official-race-context-v1"

RACE_ENTRY_PATH = DATA / "edgeiq_race_entry_fact_v1.csv"
PERFORMANCE_CONTEXT_PATH = DATA / "edgeiq_race_entry_performance_context_fact_v1.csv"
SNAPSHOT_PATH = DATA / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv"
OUTPUT_PATH = DATA / "edgeiq_official_race_context_source_v1.csv"
SUMMARY_PATH = DATA / "edgeiq_official_race_context_source_v1_summary.csv"
AUDIT_PATH = DATA / "edgeiq_official_race_context_source_v1_audit.json"
REPORT_PATH = DOCS / "EDGEIQ_OFFICIAL_RACE_CONTEXT_SOURCE_V1.md"

MEETING_DISCOVERY_FILES = [
    ROOT / "outputs" / "performance-intelligence" / "racingcom-v2" / "raw" / "meeting-discovery" / "https_www_racing_com_services_appv2_GetMeetsByMonth_2026_7_f8c4ab40318d.txt",
    ROOT / "data" / "raw" / "racing-com-public-v1" / "meeting" / "appv2_get_meets_2026_7_200.json",
    DATA / "edgeiq_racingcom_three_day_raw_meetings_v1.json",
    DATA / "racingcom_getmeets_2026_07_debug.json",
]

OUTPUT_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "race_name",
    "race_distance_m",
    "race_class_code",
    "race_class_source_value",
    "rail_position",
    "track_condition",
    "track_rating",
    "meet_code",
    "race_id",
    "source_url",
    "meeting_evidence_file",
    "race_list_evidence_file",
    "meeting_evidence_sha256",
    "race_list_evidence_sha256",
    "governance_status",
    "builder_version",
    "built_at_utc",
]

BUILDER_VERSION = "edgeiq_official_race_context_source_v1.0.0"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def clean_track(value: str) -> str:
    value = text(value).upper()
    for token in ["SPORTSBET", "LADBROKES", "BET365", "PICKLEBET PARK", "SOUTHSIDE"]:
        value = value.replace(token, "")
    value = re.sub(r"[^A-Z0-9]", "", value)
    if "ECHUCA" in value:
        return "ECHUCA"
    if "CAULFIELD" in value:
        return "CAULFIELD"
    return value


def race_no_from_id(race_id: str) -> str:
    match = re.search(r"\|R(\d+)\|", text(race_id).upper())
    return match.group(1) if match else ""


def canonical_track_from_id(race_id: str) -> str:
    parts = text(race_id).split("|")
    return parts[2] if len(parts) > 2 else ""


def race_date_from_id(race_id: str) -> str:
    parts = text(race_id).split("|")
    return parts[1] if len(parts) > 1 else ""


def atomic_write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp_path = Path(tmp)
    try:
        with tmp_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        tmp_path.replace(path)
    finally:
        tmp_path.unlink(missing_ok=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp_path = Path(tmp)
    try:
        tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(path)
    finally:
        tmp_path.unlink(missing_ok=True)


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def load_snapshot_target_keys() -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    for row in read_csv(PERFORMANCE_CONTEXT_PATH):
        race_id = text(row.get("race_id") or row.get("canonical_race_id"))
        date = text(row.get("race_date")) or race_date_from_id(race_id)
        track = clean_track(text(row.get("track") or row.get("track_id") or row.get("canonical_track") or canonical_track_from_id(race_id)))
        race_no = text(row.get("race_no") or row.get("race_number")) or race_no_from_id(race_id)
        if date and track and race_no:
            keys.add((date, track, str(int(race_no))))
    if keys:
        return keys
    for row in read_csv(SNAPSHOT_PATH):
        race_id = text(row.get("race_id") or row.get("canonical_race_id"))
        date = text(row.get("race_date")) or race_date_from_id(race_id)
        track = clean_track(canonical_track_from_id(race_id))
        race_no = race_no_from_id(race_id)
        if date and track and race_no:
            keys.add((date, track, str(int(race_no))))
    return keys


def meeting_entries_from_payload(payload: Any) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if isinstance(payload, list):
        for item in payload:
            entries.extend(meeting_entries_from_payload(item.get("payload") if isinstance(item, dict) and "payload" in item else item))
        return entries
    if not isinstance(payload, dict):
        return entries
    for month in payload.get("Months") or []:
        for entry in month.get("CalendarEntries") or []:
            if isinstance(entry, dict):
                entries.append(entry)
    return entries


def load_meeting_lookup(target_keys: set[tuple[str, str, str]]) -> dict[tuple[str, str], dict[str, Any]]:
    wanted = {(date, track) for date, track, _ in target_keys}
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for path in MEETING_DISCOVERY_FILES:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        for entry in meeting_entries_from_payload(payload):
            date = text(entry.get("Date"))[:10]
            track = clean_track(text(entry.get("Track") or entry.get("Venue")))
            if (date, track) not in wanted:
                continue
            lookup[(date, track)] = {
                "meet_code": text(entry.get("MeetCode")),
                "track_code": text(entry.get("TrackCode")),
                "url_segment": text(entry.get("UrlSegment")),
                "source_file": str(path.relative_to(ROOT)),
                "source_sha256": sha_text(path.read_text(encoding="utf-8", errors="ignore")),
                "track": track,
                "date": date,
            }
    return lookup


def capture_public_racingcom_context(meetings: dict[tuple[str, str], dict[str, Any]], target_keys: set[tuple[str, str, str]]) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[tuple[str, str], list[dict[str, Any]]], list[dict[str, Any]]]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError(f"PLAYWRIGHT_NOT_AVAILABLE: {exc}") from exc

    meeting_payloads: dict[tuple[str, str], dict[str, Any]] = {}
    race_list_payloads: dict[tuple[str, str], list[dict[str, Any]]] = {}
    capture_audit: list[dict[str, Any]] = []
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0", viewport={"width": 1400, "height": 1000})
        for key, meeting in sorted(meetings.items()):
            date, track = key
            race_numbers = sorted(int(race_no) for d, t, race_no in target_keys if d == date and t == track)
            first_race = race_numbers[0] if race_numbers else 1
            url_segment = text(meeting.get("url_segment"))
            source_url = f"https://www.racing.com/form/{url_segment}/race/{first_race}" if url_segment else ""
            page = context.new_page()
            errors: list[str] = []

            def save_response(prefix: str, payload: dict[str, Any]) -> Path:
                compact = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                digest = sha_text(compact)[:16]
                file_path = RAW_DIR / f"{date}_{track}_{prefix}_{digest}.json"
                write_json(file_path, payload)
                return file_path

            def handle_response(resp: Any) -> None:
                if "graphql.rmdprod.racing.com" not in resp.url:
                    return
                try:
                    payload = json.loads(resp.text())
                except Exception:
                    return
                data = payload.get("data") or {}
                meeting_payload = data.get("getMeeting")
                if isinstance(meeting_payload, dict) and text(meeting_payload.get("id")) == text(meeting.get("meet_code")):
                    evidence_file = save_response("getMeeting", payload)
                    meeting_payload["__evidence_file"] = str(evidence_file.relative_to(ROOT))
                    meeting_payload["__evidence_sha256"] = sha_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))
                    meeting_payloads[key] = meeting_payload
                race_list = data.get("getNoCacheRacesForMeet")
                if isinstance(race_list, list):
                    races_for_meet = []
                    for race in race_list:
                        if not isinstance(race, dict):
                            continue
                        meet_obj = race.get("meet") or {}
                        meet_url = text(meet_obj.get("meetUrlSegment") or meet_obj.get("meetUrl"))
                        if url_segment and url_segment not in meet_url:
                            continue
                        races_for_meet.append(race)
                    if races_for_meet:
                        evidence_file = save_response("getNoCacheRacesForMeet", payload)
                        for race in races_for_meet:
                            race["__evidence_file"] = str(evidence_file.relative_to(ROOT))
                            race["__evidence_sha256"] = sha_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))
                        race_list_payloads[key] = races_for_meet

            page.on("response", handle_response)
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            try:
                page.goto(source_url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(12000)
            except Exception as exc:
                errors.append(repr(exc))
            visible = ""
            try:
                visible = page.locator("body").inner_text(timeout=5000)
            except Exception as exc:
                errors.append(f"body:{exc!r}")
            visible_path = RAW_DIR / f"{date}_{track}_visible_text_{sha_text(visible)[:16]}.txt"
            visible_path.write_text(visible, encoding="utf-8")
            page.close()
            capture_audit.append({
                "race_date": date,
                "track": track,
                "meet_code": meeting.get("meet_code", ""),
                "source_url": source_url,
                "meeting_payload_captured": bool(meeting_payloads.get(key)),
                "race_list_payload_captured": bool(race_list_payloads.get(key)),
                "visible_text_file": str(visible_path.relative_to(ROOT)),
                "visible_text_length": len(visible),
                "errors": " | ".join(errors),
            })
        context.close()
        browser.close()
    return meeting_payloads, race_list_payloads, capture_audit


def build_rows(target_keys: set[tuple[str, str, str]], meetings: dict[tuple[str, str], dict[str, Any]], meeting_payloads: dict[tuple[str, str], dict[str, Any]], race_list_payloads: dict[tuple[str, str], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    built_at = now_utc()
    output: list[dict[str, Any]] = []
    race_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for meeting_key, races in race_list_payloads.items():
        date, track = meeting_key
        for race in races:
            race_no = text(race.get("raceNumber"))
            if race_no:
                race_by_key[(date, track, str(int(race_no)))] = race
    for target in sorted(target_keys):
        date, track, race_no = target
        meeting = meetings.get((date, track), {})
        meeting_payload = meeting_payloads.get((date, track), {})
        race = race_by_key.get(target, {})
        race_class = text(race.get("rdcClass") or race.get("nameForm"))
        rail = text(meeting_payload.get("railPosition"))
        status = "COMPLETE_OFFICIAL_RACE_CONTEXT" if race_class and rail else "BLOCKED_MISSING_OFFICIAL_RACE_CONTEXT"
        output.append({
            "race_date": date,
            "track": track,
            "race_no": race_no,
            "race_name": text(race.get("name")),
            "race_distance_m": re.sub(r"[^0-9]", "", text(race.get("distance"))),
            "race_class_code": race_class,
            "race_class_source_value": text(race.get("rdcClass") or race.get("nameForm")),
            "rail_position": rail,
            "track_condition": text(race.get("trackCondition") or meeting_payload.get("trackCondition")),
            "track_rating": text(race.get("trackRating") or meeting_payload.get("trackRating")),
            "meet_code": text(meeting.get("meet_code") or meeting_payload.get("id")),
            "race_id": text(race.get("id")),
            "source_url": f"https://www.racing.com/form/{text(meeting.get('url_segment'))}/race/{race_no}" if text(meeting.get("url_segment")) else "",
            "meeting_evidence_file": text(meeting_payload.get("__evidence_file")),
            "race_list_evidence_file": text(race.get("__evidence_file")),
            "meeting_evidence_sha256": text(meeting_payload.get("__evidence_sha256")),
            "race_list_evidence_sha256": text(race.get("__evidence_sha256")),
            "governance_status": status,
            "builder_version": BUILDER_VERSION,
            "built_at_utc": built_at,
        })
    return output


def write_report(rows: list[dict[str, Any]], capture_audit: list[dict[str, Any]], meetings: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(row["governance_status"] for row in rows)
    payload = {
        "status": "OFFICIAL_RACE_CONTEXT_SOURCE_BUILT" if status_counts.get("COMPLETE_OFFICIAL_RACE_CONTEXT", 0) == len(rows) and rows else "OFFICIAL_RACE_CONTEXT_SOURCE_PARTIAL",
        "target_races": len(rows),
        "complete_races": status_counts.get("COMPLETE_OFFICIAL_RACE_CONTEXT", 0),
        "blocked_races": len(rows) - status_counts.get("COMPLETE_OFFICIAL_RACE_CONTEXT", 0),
        "meetings_discovered": len(meetings),
        "meeting_payloads_captured": sum(1 for row in capture_audit if row.get("meeting_payload_captured")),
        "race_list_payloads_captured": sum(1 for row in capture_audit if row.get("race_list_payload_captured")),
        "protected_systems": {
            "pricing_changed": "NO",
            "probability_changed": "NO",
            "v6_1_changed": "NO",
            "v7_2g2_changed": "NO",
            "ui_changed": "NO",
        },
    }
    write_json(AUDIT_PATH, {**payload, "capture_audit": capture_audit})
    atomic_write_csv(SUMMARY_PATH, [{"metric": k, "value": v} for k, v in payload.items() if not isinstance(v, dict)], ["metric", "value"])
    REPORT_PATH.write_text("\n".join([
        "# EDGEiQ Official Race Context Source V1",
        "",
        f"Status: {payload['status']}",
        f"Target races: {payload['target_races']}",
        f"Complete races: {payload['complete_races']}",
        f"Blocked races: {payload['blocked_races']}",
        "",
        "## Method",
        "Public Racing.com form pages were opened in a normal browser session. The builder captured visible-page GraphQL responses for getMeeting and getNoCacheRacesForMeet. No credentials, hidden tokens or access-control bypasses are used.",
        "",
        "## Governed fields",
        "- rail_position comes from getMeeting.railPosition.",
        "- race_class_code comes from getNoCacheRacesForMeet.rdcClass, with nameForm only as a direct official source fallback if rdcClass is blank.",
        "- No race-name, prize-money or rail inference is used.",
        "",
    ]) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    target_keys = load_snapshot_target_keys()
    meetings = load_meeting_lookup(target_keys)
    meeting_payloads, race_list_payloads, capture_audit = capture_public_racingcom_context(meetings, target_keys)
    rows = build_rows(target_keys, meetings, meeting_payloads, race_list_payloads)
    atomic_write_csv(OUTPUT_PATH, rows, OUTPUT_FIELDS)
    payload = write_report(rows, capture_audit, meetings)
    print("EDGEIQ_OFFICIAL_RACE_CONTEXT_SOURCE_V1_BUILD_PASS")
    for key in ["status", "target_races", "complete_races", "blocked_races", "meetings_discovered", "meeting_payloads_captured", "race_list_payloads_captured"]:
        print(f"{key}={payload.get(key)}")


if __name__ == "__main__":
    main()
