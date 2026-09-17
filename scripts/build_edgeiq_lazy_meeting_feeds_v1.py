from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"
CATALOG = PUBLIC / "edgeiq_three_day_product_catalog_v1.json"
SUMMARY = PUBLIC / "edgeiq_meetings_summary_v1.json"
DETAIL = PUBLIC / "edgeiq_meeting_detail_v1.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def as_list(value):
    return value if isinstance(value, list) else []


def pick(obj, *keys, default=None):
    if not isinstance(obj, dict):
        return default
    for key in keys:
        value = obj.get(key)
        if value is not None and value != "":
            return value
    return default


def main() -> None:
    catalog = load_json(CATALOG)
    source_days = as_list(catalog.get("days"))
    if not source_days:
        source_days = as_list(catalog.get("meetingDays"))

    days = []
    details = {}
    for index, day in enumerate(source_days[:3]):
        meetings_in = as_list(day.get("meetings"))
        meetings = []
        for meeting in meetings_in:
            race_summaries = as_list(meeting.get("raceSummaries"))
            if not race_summaries:
                race_summaries = as_list(meeting.get("races"))
            race_count = int(pick(meeting, "raceCount", "races", default=len(race_summaries)) or len(race_summaries)) if not isinstance(meeting.get("races"), list) else len(race_summaries)
            declared = 0
            for race in race_summaries:
                declared += int(pick(race, "fieldSize", "runnerCount", "declared", default=0) or 0)
            meeting_id = str(pick(meeting, "meetingId", "id", "slug", default=f"meeting-{index}-{len(meetings)}"))
            summary = {
                "meetingId": meeting_id,
                "meeting": pick(meeting, "meeting", "name", "track", "venue", default="—"),
                "state": pick(meeting, "state", "region", default="—"),
                "races": race_count,
                "declared": declared,
                "firstRace": pick(meeting, "firstRace", "firstRaceTime", default="—"),
                "rail": pick(meeting, "rail", "railPosition", default="—"),
                "track": pick(meeting, "track", "trackCondition", "going", default="—"),
                "weather": pick(meeting, "weather", default="—"),
                "scratchings": int(pick(meeting, "scratchings", "scratchingCount", default=0) or 0),
                "raceSummaries": race_summaries,
            }
            meetings.append(summary)
            details[meeting_id] = meeting

        totals = {
            "meetings": len(meetings),
            "races": sum(int(m["races"]) for m in meetings),
            "declared": sum(int(m["declared"]) for m in meetings),
            "scratchings": sum(int(m["scratchings"]) for m in meetings),
        }
        days.append({
            "key": pick(day, "key", default=["today", "tomorrow", "day2"][index]),
            "date": pick(day, "date", "displayDate", default=""),
            "displayDate": pick(day, "displayDate", "date", default=""),
            "totals": totals,
            "meetings": meetings,
        })

    generated = datetime.now(timezone.utc).isoformat()
    summary_payload = {"generatedAt": generated, "days": days}
    detail_payload = {"generatedAt": generated, "meetings": details}
    SUMMARY.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    DETAIL.write_text(json.dumps(detail_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    all_totals = {
        "meetings": sum(d["totals"]["meetings"] for d in days),
        "races": sum(d["totals"]["races"] for d in days),
        "declared": sum(d["totals"]["declared"] for d in days),
    }
    print("EDGEIQ_DASHBOARD_FEEDS=PASS")
    print(json.dumps(all_totals, sort_keys=True))


if __name__ == "__main__":
    main()
