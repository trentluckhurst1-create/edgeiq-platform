from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
OUTPUT_DIR = DATA / "meetings"
INDEX = OUTPUT_DIR / "index.json"


def text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def slug(value: Any) -> str:
    raw = text(value).lower()
    raw = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return raw or "meeting"


def runner_scratched(runner: dict[str, Any]) -> bool:
    official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
    source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
    values = [
        official.get("scratched"),
        source.get("scratched"),
        source.get("is_scratched"),
        official.get("status"),
        source.get("status"),
        source.get("runner_status"),
    ]
    return any(
        str(value).strip().lower() in {"true", "scr", "scratched", "lscr", "late scratching"}
        or "scratch" in str(value).strip().lower()
        for value in values
        if value is not None
    )


def lightweight_race(race: dict[str, Any]) -> dict[str, Any]:
    runners = race.get("runners", []) if isinstance(race.get("runners"), list) else []
    source = dict(race.get("source", {})) if isinstance(race.get("source"), dict) else {}
    source["_edgeiq_field_size"] = len(runners)
    source["_edgeiq_scratchings"] = sum(1 for runner in runners if isinstance(runner, dict) and runner_scratched(runner))
    source["_edgeiq_has_market"] = any(
        bool(
            text((runner.get("official") or {}).get("market"))
            or text((runner.get("source") or {}).get("market"))
        )
        for runner in runners
        if isinstance(runner, dict)
    )
    source["_edgeiq_race_detail_on_demand"] = True
    return {
        "raceKey": race.get("raceKey"),
        "raceNumber": race.get("raceNumber"),
        "raceName": race.get("raceName"),
        "distance": race.get("distance"),
        "raceClass": race.get("raceClass"),
        "raceTime": race.get("raceTime"),
        "trackCondition": race.get("trackCondition"),
        "rail": race.get("rail"),
        "runners": [],
        "source": source,
    }


def lightweight_meeting(meeting: dict[str, Any]) -> dict[str, Any]:
    races = meeting.get("races", []) if isinstance(meeting.get("races"), list) else []
    return {
        "meetingKey": meeting.get("meetingKey"),
        "meeting": meeting.get("meeting"),
        "providerMeetingKey": meeting.get("providerMeetingKey"),
        "date": meeting.get("date"),
        "trackCondition": meeting.get("trackCondition"),
        "rail": meeting.get("rail"),
        "raceCount": meeting.get("raceCount"),
        "races": [lightweight_race(race) for race in races if isinstance(race, dict)],
        "source": meeting.get("source", {}),
    }


def main() -> int:
    if not CATALOG.exists():
        print("EDGEIQ_MEETING_DETAIL_SHARDS_V1 FAIL catalog_missing")
        return 1

    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    meetings = [m for m in payload.get("meetings", []) if isinstance(m, dict)]

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    total_bytes = 0
    for meeting in meetings:
        date_value = text(meeting.get("date"))[:10]
        meeting_key = text(meeting.get("meetingKey"))
        filename = f"{date_value}_{slug(meeting_key)}.json"
        path = OUTPUT_DIR / filename
        meeting_payload = lightweight_meeting(meeting)
        detail = {
            "schemaVersion": "edgeiq_meeting_detail_v2_lightweight",
            "generatedAt": payload.get("generatedAt"),
            "date": date_value,
            "meetingKey": meeting_key,
            "meeting": meeting_payload,
        }
        path.write_text(json.dumps(detail, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
        size = path.stat().st_size
        total_bytes += size
        records.append(
            {
                "date": date_value,
                "meetingKey": meeting_key,
                "meeting": meeting.get("meeting"),
                "path": f"/data/meetings/{filename}",
                "bytes": size,
                "races": len(meeting_payload.get("races", [])),
                "raceDetailMode": "ON_DEMAND",
            }
        )

    index = {
        "schemaVersion": "edgeiq_meeting_detail_index_v2_lightweight",
        "generatedAt": payload.get("generatedAt"),
        "sourceCatalog": CATALOG.name,
        "meetings": records,
        "totalBytes": total_bytes,
        "raceDetailMode": "ON_DEMAND",
    }
    INDEX.write_text(json.dumps(index, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")

    print("EDGEIQ_MEETING_DETAIL_SHARDS_V1 PASS")
    print(f"MEETINGS={len(records)}")
    print(f"TOTAL_BYTES={total_bytes}")
    print(f"INDEX_BYTES={INDEX.stat().st_size}")
    print("RACE_DETAIL_MODE=ON_DEMAND")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
