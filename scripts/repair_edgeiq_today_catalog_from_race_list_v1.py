from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from edgeiq_three_day_window_v1_common import build_three_day_window

csv.field_size_limit(1024 * 1024 * 128)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
RACE_LIST = DATA / "edgeiq_vic_three_day_race_list_v1.csv"
AUDIT = DATA / "edgeiq_today_catalog_repair_v1_audit.json"


def text(value: Any) -> str:
    if value is None:
        return ""
    value = re.sub(r"\s+", " ", str(value)).strip()
    return "" if value.lower() in {"", "none", "null", "nan", "-", "n/a", "na"} else value


def first(mapping: dict[str, Any], *keys: str) -> Any:
    lowered = {str(key).lower(): key for key in mapping}
    for key in keys:
        actual = key if key in mapping else lowered.get(key.lower())
        if actual is not None and mapping.get(actual) not in (None, ""):
            return mapping.get(actual)
    return None


def integer(value: Any) -> int | None:
    match = re.search(r"\d+", text(value))
    return int(match.group(0)) if match else None


def canonical_track(value: Any) -> str:
    raw = text(value).upper()
    raw = re.sub(r"^(?:PICKLEBET\s+PARK|PICKLEBET|SPORTSBET|LADBROKES|BET365|SOUTHSIDE)[\s-]+", "", raw)
    raw = re.sub(r"\bRACECOURSE\b", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    aliases = {
        "PICKLEBET PARK WODONGA": "WODONGA",
        "WODONGA": "WODONGA",
        "CAULFIELD HEATH": "CAULFIELD",
        "SANDOWN HILLSIDE": "SANDOWN HILLSIDE",
        "SANDOWN LAKESIDE": "SANDOWN LAKESIDE",
        "PAKENHAM SYNTHETIC": "PAKENHAM SYNTHETIC",
        "BALLARAT SYNTHETIC": "BALLARAT SYNTHETIC",
    }
    return aliases.get(raw, raw)


def parse_entries(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    value = text(raw)
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return [item for item in parsed if isinstance(item, dict)] if isinstance(parsed, list) else []


def runner_name(row: dict[str, Any]) -> str:
    horse = first(row, "horseName", "runnerName", "runner_name", "runner")
    if text(horse):
        return text(horse)
    nested = row.get("horse") if isinstance(row.get("horse"), dict) else {}
    return text(first(nested, "horseName", "name", "runnerName"))


def nested_text(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if isinstance(value, dict):
        return text(first(value, "fullName", "name", "displayName"))
    return text(value)


def last_five(row: dict[str, Any]) -> list[str]:
    nested = row.get("horse") if isinstance(row.get("horse"), dict) else {}
    value = first(row, "lastFive", "last5", "last_five", "form") or first(nested, "lastFive", "last5", "form")
    if isinstance(value, list):
        tokens = value
    else:
        tokens = re.findall(r"DNF|UR|PU|BD|F|\d{1,2}", text(value).upper())
    out: list[str] = []
    for token in tokens:
        token_text = text(token).upper()
        if token_text:
            out.append(token_text)
        if len(out) == 5:
            break
    return out


def normalize_runner(row: dict[str, Any], fallback_number: int) -> dict[str, Any]:
    horse = row.get("horse") if isinstance(row.get("horse"), dict) else {}
    number = first(row, "raceEntryNumber", "runnerNumber", "runner_number", "saddleclothNumber", "tabNumber", "number")
    if number in (None, ""):
        number = first(horse, "raceEntryNumber", "runnerNumber", "number")
    name = runner_name(row)
    official_number = number if number not in (None, "") else fallback_number
    jockey = nested_text(row, "jockey") or text(first(row, "jockeyName", "jockey_name"))
    trainer = nested_text(row, "trainer") or text(first(row, "trainerName", "trainer_name"))
    weight = text(first(row, "weight", "allocatedWeight", "allocated_weight", "weightKg"))
    barrier = first(row, "barrier", "barrierNumber", "barrier_number", "draw")
    scratched = str(first(row, "scratched", "isScratched", "scratchedFlag") or "").strip().lower() in {"true", "1", "yes", "scr", "scratched"}
    return {
        "official": {
            "no": official_number,
            "number": official_number,
            "runner": name,
            "barrier": barrier,
            "jockey": jockey or None,
            "trainer": trainer or None,
            "weight": weight or None,
            "market": first(row, "market", "price", "odds", "fixedWin"),
            "silkUrl": text(first(row, "silkUrl", "silk_url", "silk")) or text(first(horse, "silkUrl", "silk_url", "silk")) or None,
            "lastFive": last_five(row),
            "scratched": scratched,
            "horseCountry": text(first(row, "horseCountry", "horse_country", "country")) or None,
            "apprenticeClaim": text(first(row, "apprenticeAllowedClaim", "claim", "claimKg")) or None,
            "currentGear": text(first(row, "currentGear", "gear", "gearChanges")) or None,
        },
        "historicalRuns": [],
        "evidenceRuns": [],
        "source": row,
    }


def dedupe_runners(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        normalized = normalize_runner(entry, index)
        official = normalized["official"]
        name = re.sub(r"[^A-Z0-9]+", "", text(official.get("runner")).upper())
        if not name:
            continue
        identity = name
        if identity in seen:
            continue
        seen.add(identity)
        out.append(normalized)
    return out


def main() -> int:
    window = build_three_day_window()
    today = window.today
    if not CATALOG.exists() or not RACE_LIST.exists():
        raise SystemExit("TODAY_CATALOG_REPAIR FAIL missing catalog or race list")

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    with RACE_LIST.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    today_rows = [row for row in rows if text(row.get("race_date"))[:10] == today]
    grouped: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for row in today_rows:
        track = canonical_track(row.get("normalised_track") or row.get("track"))
        race_no = integer(row.get("race_no"))
        if track and race_no is not None:
            grouped[(track, race_no)].append(row)

    source_tracks = sorted({track for track, _ in grouped})
    existing_today = [m for m in catalog.get("meetings", []) if isinstance(m, dict) and text(m.get("date"))[:10] == today]
    existing_by_track = {canonical_track(m.get("meeting")): m for m in existing_today}
    repaired_tracks: list[str] = []

    for track in source_tracks:
        race_numbers = sorted(race_no for candidate_track, race_no in grouped if candidate_track == track)
        races: list[dict[str, Any]] = []
        for race_no in race_numbers:
            race_rows = grouped[(track, race_no)]
            row = max(race_rows, key=lambda item: len(parse_entries(item.get("form_entries_json"))))
            entries = parse_entries(row.get("form_entries_json"))
            runners = dedupe_runners(entries)
            races.append({
                "raceKey": f"{today}|{track}|R{race_no}",
                "raceNumber": race_no,
                "raceName": text(row.get("race_name")) or f"Race {race_no}",
                "distance": text(row.get("distance")) or None,
                "raceClass": text(row.get("race_class")) or None,
                "raceTime": text(row.get("race_time_utc")) or None,
                "trackCondition": text(row.get("track_condition")) or None,
                "rail": text(row.get("rail_position")) or None,
                "runners": runners,
                "source": row,
            })

        existing = existing_by_track.get(track)
        fresh_runner_count = sum(len(race["runners"]) for race in races)
        existing_runner_count = sum(len(race.get("runners", [])) for race in (existing or {}).get("races", []) if isinstance(race, dict))
        if existing is None or fresh_runner_count > existing_runner_count:
            meeting = {
                "meetingKey": f"{today}|{track}",
                "meeting": track.title() if track != "WODONGA" else "Wodonga",
                "providerMeetingKey": track,
                "date": today,
                "trackCondition": text(first(race_rows[0], "track_condition")) or None if race_numbers else None,
                "rail": text(first(race_rows[0], "rail_position")) or None if race_numbers else None,
                "raceCount": len(races),
                "races": races,
                "source": {"repairSource": "edgeiq_vic_three_day_race_list_v1.csv", "track": track},
            }
            catalog["meetings"] = [
                m for m in catalog.get("meetings", [])
                if not (isinstance(m, dict) and text(m.get("date"))[:10] == today and canonical_track(m.get("meeting")) == track)
            ]
            catalog["meetings"].append(meeting)
            repaired_tracks.append(track)

    catalog["meetings"].sort(key=lambda m: (text(m.get("date")), text(m.get("meeting"))))
    CATALOG.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    final_today = [m for m in catalog.get("meetings", []) if isinstance(m, dict) and text(m.get("date"))[:10] == today]
    audit = {
        "schemaVersion": "edgeiq_today_catalog_repair_v1",
        "generatedAt": datetime.now().isoformat(),
        "today": today,
        "raceListTodayRows": len(today_rows),
        "raceListTodayTracks": source_tracks,
        "repairedTracks": repaired_tracks,
        "finalTodayMeetings": [
            {
                "meeting": m.get("meeting"),
                "races": len(m.get("races", [])),
                "runners": sum(len(r.get("runners", [])) for r in m.get("races", []) if isinstance(r, dict)),
            }
            for m in final_today
        ],
    }
    AUDIT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print("TODAY_CATALOG_REPAIR PASS")
    print("TODAY=" + today)
    print("RACE_LIST_TODAY_ROWS=" + str(len(today_rows)))
    print("RACE_LIST_TODAY_TRACKS=" + ",".join(source_tracks))
    print("REPAIRED_TRACKS=" + (",".join(repaired_tracks) if repaired_tracks else "NONE"))
    for item in audit["finalTodayMeetings"]:
        print(f"TODAY_MEETING={item['meeting']} RACES={item['races']} RUNNERS={item['runners']}")
    return 0 if final_today else 2


if __name__ == "__main__":
    raise SystemExit(main())
