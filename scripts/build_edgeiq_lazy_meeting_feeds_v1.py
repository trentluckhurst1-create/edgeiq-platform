from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
SUMMARY = DATA / "edgeiq_meetings_summary_feed_v1.json"
MEETINGS_DIR = DATA / "meetings"


def text(value, fallback="Not supplied"):
    if value is None:
        return fallback
    value = str(value).strip()
    return value if value else fallback


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value or "meeting"


def source_value(source, *keys):
    if not isinstance(source, dict):
        return None
    lowered = {str(key).lower(): key for key in source}
    for key in keys:
        actual = key if key in source else lowered.get(key.lower())
        if actual is not None and source.get(actual) not in (None, ""):
            return source.get(actual)
    return None


def main() -> None:
    if not CATALOG.exists():
        raise SystemExit(f"Missing catalogue: {CATALOG}")

    catalog = json.loads(CATALOG.read_text(encoding="utf-8-sig"))
    meetings = catalog.get("meetings") or []
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    day_labels = catalog.get("dayLabels") or {}
    dates = catalog.get("dates") or []

    MEETINGS_DIR.mkdir(parents=True, exist_ok=True)

    days = []
    for date_value in dates:
        day_meetings = []
        for meeting in meetings:
            if meeting.get("date") != date_value:
                continue

            meeting_key = text(meeting.get("meetingKey"), "")
            meeting_name = text(meeting.get("meeting"), "")
            meeting_source = meeting.get("source") or {}
            race_summaries = []

            for race in meeting.get("races") or []:
                race_source = race.get("source") or {}
                runners = race.get("runners") or []
                race_summaries.append({
                    "raceKey": text(race.get("raceKey"), ""),
                    "raceNumber": int(race.get("raceNumber") or 0),
                    "time": text(race.get("raceTime")),
                    "distance": text(race.get("distance")),
                    "name": text(race.get("raceName")),
                    "raceClass": text(race.get("raceClass")),
                    "fieldSize": len(runners),
                    "status": text(source_value(race_source, "raceStatus", "race_status", "status")),
                })

            state = text(source_value(meeting_source, "State", "state"), "VIC")
            day_meetings.append({
                "meetingKey": meeting_key,
                "meeting": meeting_name,
                "providerMeetingKey": text(meeting.get("providerMeetingKey"), ""),
                "date": date_value,
                "state": state,
                "track": text(meeting.get("trackCondition")),
                "rail": text(meeting.get("rail")),
                "races": len(meeting.get("races") or []),
                "raceSummaries": race_summaries,
            })

            detail = {
                "schemaVersion": "edgeiq_meeting_detail_feed_v1",
                "generatedAt": generated_at,
                "date": date_value,
                "meetingKey": meeting_key,
                "meeting": meeting,
            }
            detail_path = MEETINGS_DIR / f"{date_value}_{slug(meeting_key)}.json"
            detail_path.write_text(json.dumps(detail, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

        days.append({
            "key": day_labels.get(date_value, date_value),
            "date": date_value,
            "meetings": day_meetings,
        })

    summary = {
        "schemaVersion": "edgeiq_meetings_summary_feed_v1",
        "generatedAt": generated_at,
        "days": days,
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    total_races = sum(len(m.get("races") or []) for m in meetings)
    total_runners = sum(len(r.get("runners") or []) for m in meetings for r in (m.get("races") or []))
    print(f"[EDGEIQ] lazy feeds built meetings={len(meetings)} races={total_races} runners={total_runners}")
    print(f"[EDGEIQ] summary={SUMMARY}")


if __name__ == "__main__":
    main()
