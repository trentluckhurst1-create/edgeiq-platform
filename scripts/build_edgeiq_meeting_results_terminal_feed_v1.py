from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
OUT = DATA / "edgeiq_meeting_results_terminal_feed_v1.csv"
SUMMARY = DATA / "edgeiq_meeting_results_terminal_feed_summary_v1.csv"

FIELDS = [
    "meeting_key",
    "race_key",
    "race_date",
    "track",
    "race_no",
    "time",
    "winner",
    "jockey",
    "trainer",
    "sp_tab",
    "margin",
    "official_time",
    "track_condition",
    "status",
    "open",
    "source",
    "source_timestamp",
    "source_confidence",
]


def usable(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text in {"-", "—"}:
        return ""
    if text.lower() in {"null", "undefined", "none", "n/a", "na"}:
        return ""
    return text


def first(*values: object) -> str:
    for value in values:
        text = usable(value)
        if text:
            return text
    return ""


def result_status(race: dict) -> str:
    source = race.get("source") or {}
    raw = first(
        source.get("result_status"),
        source.get("race_status"),
        source.get("full_status"),
        source.get("meet_status"),
        source.get("status"),
    ).upper()
    if "OFFICIAL" in raw:
        return "OFFICIAL"
    if "UNOFFICIAL" in raw:
        return "UNOFFICIAL"
    if "ABANDON" in raw:
        return "ABANDONED"
    if "RESULT" in raw or "FINAL" in raw and any_winner(race):
        return "OFFICIAL" if any_winner(race) else "PENDING"
    return "UPCOMING"


def any_winner(race: dict) -> dict | None:
    runners = race.get("runners") or []
    for runner in runners:
        source = runner.get("source") or {}
        position = first(source.get("position"), source.get("finish"), source.get("finishing_position"))
        if position in {"1", "1.0"} or position.lower() in {"1st", "first"}:
            return runner
    return None


def runner_source(runner: dict | None) -> dict:
    if not runner:
        return {}
    return runner.get("source") or {}


def runner_official(runner: dict | None) -> dict:
    if not runner:
        return {}
    return runner.get("official") or {}


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    rows: list[dict[str, str]] = []

    for meeting in payload.get("meetings", []):
        meeting_key = first(meeting.get("meetingKey"), meeting.get("meeting_key"))
        for race in meeting.get("races", []):
            source = race.get("source") or {}
            winner = any_winner(race)
            winner_source = runner_source(winner)
            winner_official = runner_official(winner)
            status = result_status(race)
            rows.append(
                {
                    "meeting_key": meeting_key,
                    "race_key": first(race.get("raceKey"), source.get("race_key")),
                    "race_date": first(meeting.get("date"), source.get("race_date")),
                    "track": first(meeting.get("meeting"), source.get("track")),
                    "race_no": first(race.get("raceNumber"), source.get("race_no")),
                    "time": first(race.get("raceTime"), source.get("race_time"), source.get("race_time_utc")),
                    "winner": first(
                        source.get("winner"),
                        source.get("winner_name"),
                        winner_official.get("runner"),
                        winner_source.get("horseName"),
                    ),
                    "jockey": first(winner_official.get("jockey"), winner_source.get("jockeyName"), source.get("winner_jockey")),
                    "trainer": first(winner_official.get("trainer"), winner_source.get("trainerName"), source.get("winner_trainer")),
                    "sp_tab": first(winner_source.get("startingPrice"), winner_source.get("sp"), source.get("winner_sp")),
                    "margin": first(winner_source.get("margin"), source.get("winning_margin"), source.get("margin")),
                    "official_time": first(winner_source.get("winningTime"), source.get("official_time"), source.get("winning_time")),
                    "track_condition": first(race.get("trackCondition"), source.get("track_condition"), meeting.get("trackCondition")),
                    "status": status,
                    "open": "OPEN" if status in {"OFFICIAL", "UNOFFICIAL"} else "PENDING",
                    "source": first(source.get("source"), "edgeiq_three_day_product_catalog_v1"),
                    "source_timestamp": first(source.get("built_at"), payload.get("generatedAt")),
                    "source_confidence": "official" if status in {"OFFICIAL", "UNOFFICIAL"} else "pending",
                }
            )

    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    completed = sum(1 for row in rows if row["status"] in {"OFFICIAL", "UNOFFICIAL"})
    with SUMMARY.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["rows", "completed_rows", "pending_rows", "source"])
        writer.writeheader()
        writer.writerow(
            {
                "rows": len(rows),
                "completed_rows": completed,
                "pending_rows": len(rows) - completed,
                "source": CATALOG.name,
            }
        )

    print(f"Wrote {OUT} ({len(rows)} rows)")
    print(f"Wrote {SUMMARY}")
    if len(rows) > 10000:
        raise SystemExit("edgeiq_meeting_results_terminal_feed_v1 exceeds 10,000 row frontend budget")


if __name__ == "__main__":
    main()
