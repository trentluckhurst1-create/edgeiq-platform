from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
OUTPUT_DIR = DATA / "meetings"


def detail_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "meeting"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    if not CATALOG.exists():
        print("EDGEIQ_MEETING_DETAIL_FEEDS_V1 FAIL source_catalog_missing")
        return 1

    catalog = json.loads(CATALOG.read_text(encoding="utf-8-sig"))
    meetings = [item for item in catalog.get("meetings", []) if isinstance(item, dict)]
    generated_at = str(catalog.get("generatedAt") or "")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for existing in OUTPUT_DIR.glob("*.json"):
        existing.unlink()

    total_races = 0
    total_runners = 0
    total_history_rows = 0

    for meeting in meetings:
        date_value = str(meeting.get("date") or "")[:10]
        meeting_key = str(meeting.get("meetingKey") or "")
        races = [race for race in meeting.get("races", []) if isinstance(race, dict)]
        runners = [
            runner
            for race in races
            for runner in race.get("runners", [])
            if isinstance(runner, dict)
        ]
        total_races += len(races)
        total_runners += len(runners)
        total_history_rows += sum(
            len(runner.get("historicalRuns") or [])
            for runner in runners
        )

        path = OUTPUT_DIR / f"{date_value}_{detail_slug(meeting_key)}.json"
        write_json(
            path,
            {
                "schemaVersion": "edgeiq_meeting_detail_feed_v1",
                "generatedAt": generated_at,
                "date": date_value,
                "meetingKey": meeting_key,
                "meeting": meeting,
            },
        )

    print("EDGEIQ_MEETING_DETAIL_FEEDS_V1 PASS")
    print(f"MEETINGS={len(meetings)}")
    print(f"RACES={total_races}")
    print(f"RUNNERS={total_runners}")
    print(f"HISTORY_ROWS={total_history_rows}")
    print(f"OUTPUT_DIR={OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
