from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timezone

import build_edgeiq_racingcom_three_day_race_list_v1 as source


def slug(value: str) -> str:
    text = value.lower().strip()
    text = re.sub(r"^(sportsbet|ladbrokes|bet365|picklebet)[- ]+", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    aliases = {
        "ballarat": "sportsbet-ballarat",
        "ballarat-synthetic": "sportsbet-ballarat-synthetic",
        "wodonga": "picklebet-park-wodonga",
    }
    return aliases.get(text, text)


def main() -> int:
    meetings = source.extract_calendar_meetings()
    for meeting in meetings:
        race_date = str(meeting.get("race_date") or "")[:10]
        track = str(meeting.get("normalised_track") or meeting.get("track") or "")
        meeting["form_url"] = f"https://www.racing.com/form/{race_date}/{slug(track)}"

    rows = source.fetch_races_browser(meetings)
    rows.sort(key=lambda row: (row.get("race_date", ""), row.get("normalised_track", ""), int(row.get("race_no") or 999)))
    source.write_csv(source.OUT, rows, source.FIELDS)
    source.write_csv(source.SUMMARY, [
        {"metric": "status", "value": "EDGEIQ_RACINGCOM_CURRENT_CATALOG_RECOVERY"},
        {"metric": "meetings", "value": len(meetings)},
        {"metric": "races", "value": len(rows)},
        {"metric": "today_races", "value": sum(1 for row in rows if row.get("day_bucket") == "TODAY")},
        {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat(timespec="seconds")},
    ], ["metric", "value"])

    today_rows = [row for row in rows if row.get("day_bucket") == "TODAY"]
    print(f"RACINGCOM_RECOVERY_MEETINGS={len(meetings)}")
    print(f"RACINGCOM_RECOVERY_RACES={len(rows)}")
    print(f"RACINGCOM_RECOVERY_TODAY_RACES={len(today_rows)}")
    if not today_rows:
        return 2

    for script in (
        "build_edgeiq_vic_three_day_meeting_calendar_v1.py",
        "build_edgeiq_three_day_product_catalog_v1.py",
    ):
        subprocess.run([sys.executable, f"scripts/{script}"], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
