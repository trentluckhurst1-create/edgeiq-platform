from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
RACE_DIR = DATA / "races"
RUNNER_DIR = DATA / "runners"
RACE_INDEX = RACE_DIR / "index.json"
RUNNER_INDEX = RUNNER_DIR / "index.json"


def text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def slug(value: Any) -> str:
    raw = text(value).lower()
    raw = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return raw or "item"


def lightweight_runner(runner: dict[str, Any], detail_path: str) -> dict[str, Any]:
    official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
    source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
    summary_source = {
        key: value
        for key, value in source.items()
        if key in {
            "scratched", "is_scratched", "runner_status", "status", "gear", "gear_changes",
            "market", "price", "barrier", "weight", "jockey", "trainer", "runner_number",
            "number", "silks", "form", "last_five"
        }
    }
    summary_source["runnerDetailPath"] = detail_path
    summary_source["lightweightRunner"] = True
    return {
        "official": official,
        "source": summary_source,
        "historicalRuns": [],
        "evidenceRuns": [],
    }


def main() -> int:
    if not CATALOG.exists():
        print("EDGEIQ_RACE_DETAIL_SHARDS_V2 FAIL catalog_missing")
        return 1

    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    meetings = [m for m in payload.get("meetings", []) if isinstance(m, dict)]

    for directory in (RACE_DIR, RUNNER_DIR):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)

    race_records: list[dict[str, Any]] = []
    runner_records: list[dict[str, Any]] = []
    race_total_bytes = 0
    runner_total_bytes = 0

    for meeting in meetings:
        date_value = text(meeting.get("date"))[:10]
        meeting_key = text(meeting.get("meetingKey"))
        races = meeting.get("races", []) if isinstance(meeting.get("races"), list) else []
        for race in races:
            if not isinstance(race, dict):
                continue
            race_key = text(race.get("raceKey"))
            race_copy = dict(race)
            full_runners = race.get("runners", []) if isinstance(race.get("runners"), list) else []
            summary_runners: list[dict[str, Any]] = []

            for runner_index, runner in enumerate(full_runners):
                if not isinstance(runner, dict):
                    continue
                official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
                runner_number = text(official.get("number") or official.get("no")) or str(runner_index + 1)
                runner_name = text(official.get("runner"))
                runner_filename = f"{date_value}_{slug(meeting_key)}_{slug(race_key)}_{runner_index + 1:02d}.json"
                runner_path = RUNNER_DIR / runner_filename
                public_runner_path = f"/data/runners/{runner_filename}"
                runner_detail = {
                    "schemaVersion": "edgeiq_runner_detail_v1",
                    "generatedAt": payload.get("generatedAt"),
                    "date": date_value,
                    "meetingKey": meeting_key,
                    "raceKey": race_key,
                    "runnerIndex": runner_index,
                    "runnerNumber": runner_number,
                    "runnerName": runner_name,
                    "runner": runner,
                }
                runner_path.write_text(json.dumps(runner_detail, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
                runner_size = runner_path.stat().st_size
                runner_total_bytes += runner_size
                runner_records.append({
                    "date": date_value,
                    "meetingKey": meeting_key,
                    "raceKey": race_key,
                    "runnerIndex": runner_index,
                    "runnerNumber": runner_number,
                    "runnerName": runner_name,
                    "path": public_runner_path,
                    "bytes": runner_size,
                })
                summary_runners.append(lightweight_runner(runner, public_runner_path))

            race_copy["runners"] = summary_runners
            race_filename = f"{date_value}_{slug(meeting_key)}_{slug(race_key)}.json"
            race_path = RACE_DIR / race_filename
            race_detail = {
                "schemaVersion": "edgeiq_race_detail_v2",
                "generatedAt": payload.get("generatedAt"),
                "date": date_value,
                "meetingKey": meeting_key,
                "raceKey": race_key,
                "race": race_copy,
            }
            race_path.write_text(json.dumps(race_detail, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
            race_size = race_path.stat().st_size
            race_total_bytes += race_size
            race_records.append({
                "date": date_value,
                "meetingKey": meeting_key,
                "raceKey": race_key,
                "raceNumber": race.get("raceNumber"),
                "path": f"/data/races/{race_filename}",
                "bytes": race_size,
                "runners": len(summary_runners),
            })

    RACE_INDEX.write_text(json.dumps({
        "schemaVersion": "edgeiq_race_detail_index_v2",
        "generatedAt": payload.get("generatedAt"),
        "sourceCatalog": CATALOG.name,
        "races": race_records,
        "totalBytes": race_total_bytes,
    }, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")

    RUNNER_INDEX.write_text(json.dumps({
        "schemaVersion": "edgeiq_runner_detail_index_v1",
        "generatedAt": payload.get("generatedAt"),
        "sourceCatalog": CATALOG.name,
        "runners": runner_records,
        "totalBytes": runner_total_bytes,
    }, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")

    print("EDGEIQ_RACE_DETAIL_SHARDS_V2 PASS")
    print(f"RACES={len(race_records)}")
    print(f"RUNNERS={len(runner_records)}")
    print(f"RACE_TOTAL_BYTES={race_total_bytes}")
    print(f"RUNNER_TOTAL_BYTES={runner_total_bytes}")
    print(f"RACE_INDEX_BYTES={RACE_INDEX.stat().st_size}")
    print(f"RUNNER_INDEX_BYTES={RUNNER_INDEX.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
