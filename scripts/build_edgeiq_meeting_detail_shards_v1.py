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
    values = [official.get("scratched"), source.get("scratched"), source.get("is_scratched"), official.get("status"), source.get("status")]
    return any(str(value).strip().lower() in {"true", "scr", "scratched", "lscr", "late scratching"} for value in values)


def slim_race(race: dict[str, Any]) -> dict[str, Any]:
    runners = race.get("runners", []) if isinstance(race.get("runners"), list) else []
    source = dict(race.get("source") or {}) if isinstance(race.get("source"), dict) else {}
    source["summary_field_size"] = len(runners)
    source["summary_scratchings"] = sum(1 for runner in runners if isinstance(runner, dict) and runner_scratched(runner))
    source["summary_market_loaded"] = any(
        bool((runner.get("official") or {}).get("market") or (runner.get("source") or {}).get("market"))
        for runner in runners if isinstance(runner, dict)
    )
    source["race_detail_shard"] = True
    return {**race, "runners": [], "source": source}


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
        slim_meeting = dict(meeting)
        slim_meeting["races"] = [slim_race(race) for race in meeting.get("races", []) if isinstance(race, dict)]
        filename = f"{date_value}_{slug(meeting_key)}.json"
        path = OUTPUT_DIR / filename
        detail = {
            "schemaVersion": "edgeiq_meeting_detail_v2",
            "generatedAt": payload.get("generatedAt"),
            "date": date_value,
            "meetingKey": meeting_key,
            "meeting": slim_meeting,
        }
        path.write_text(json.dumps(detail, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
        size = path.stat().st_size
        total_bytes += size
        records.append({
            "date": date_value,
            "meetingKey": meeting_key,
            "meeting": meeting.get("meeting"),
            "path": f"/data/meetings/{filename}",
            "bytes": size,
            "races": len(slim_meeting["races"]),
        })

    index = {
        "schemaVersion": "edgeiq_meeting_detail_index_v2",
        "generatedAt": payload.get("generatedAt"),
        "sourceCatalog": CATALOG.name,
        "meetings": records,
        "totalBytes": total_bytes,
    }
    INDEX.write_text(json.dumps(index, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")

    print("EDGEIQ_MEETING_DETAIL_SHARDS_V1 PASS")
    print(f"MEETINGS={len(records)}")
    print(f"TOTAL_BYTES={total_bytes}")
    print(f"INDEX_BYTES={INDEX.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
