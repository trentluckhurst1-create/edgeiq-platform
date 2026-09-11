from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
OUTPUT_DIR = DATA / "races"
INDEX = OUTPUT_DIR / "index.json"


def text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def slug(value: Any) -> str:
    raw = text(value).lower()
    raw = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return raw or "item"


def main() -> int:
    if not CATALOG.exists():
        print("EDGEIQ_RACE_DETAIL_SHARDS_V1 FAIL catalog_missing")
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
        for race in meeting.get("races", []) if isinstance(meeting.get("races"), list) else []:
            if not isinstance(race, dict):
                continue
            race_key = text(race.get("raceKey"))
            filename = f"{date_value}_{slug(meeting_key)}_{slug(race_key)}.json"
            path = OUTPUT_DIR / filename
            detail = {
                "schemaVersion": "edgeiq_race_detail_v1",
                "generatedAt": payload.get("generatedAt"),
                "date": date_value,
                "meetingKey": meeting_key,
                "raceKey": race_key,
                "race": race,
            }
            path.write_text(json.dumps(detail, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
            size = path.stat().st_size
            total_bytes += size
            records.append({
                "date": date_value,
                "meetingKey": meeting_key,
                "raceKey": race_key,
                "raceNumber": race.get("raceNumber"),
                "path": f"/data/races/{filename}",
                "bytes": size,
                "runners": len(race.get("runners", [])) if isinstance(race.get("runners"), list) else 0,
            })

    index = {
        "schemaVersion": "edgeiq_race_detail_index_v1",
        "generatedAt": payload.get("generatedAt"),
        "sourceCatalog": CATALOG.name,
        "races": records,
        "totalBytes": total_bytes,
    }
    INDEX.write_text(json.dumps(index, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")

    print("EDGEIQ_RACE_DETAIL_SHARDS_V1 PASS")
    print(f"RACES={len(records)}")
    print(f"TOTAL_BYTES={total_bytes}")
    print(f"INDEX_BYTES={INDEX.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
