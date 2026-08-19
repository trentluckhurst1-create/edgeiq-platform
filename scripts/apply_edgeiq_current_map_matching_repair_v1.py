from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
CURRENT_MAP = DATA / "edgeiq_current_map_v1.json"
APPLY_OUT = DATA / "edgeiq_current_map_matching_repair_v1_apply.json"
APPLY_TXT = DATA / "edgeiq_current_map_matching_repair_v1_apply.txt"


def text(value: Any) -> str:
    if value is None:
        return ""
    output = str(value).strip()
    if output.lower() in {"", "-", "none", "null", "undefined", "n/a", "na"}:
        return ""
    return output


def norm(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", text(value).upper().replace("SPORTSBET", " ").replace("LADBROKES", " ").replace("BET365", " "))


def race_no(value: Any) -> str:
    found = re.search(r"\d+", text(value))
    return found.group(0) if found else ""


def key(date: Any, track: Any, race_number: Any, runner: Any = "") -> tuple[str, str, str, str]:
    return (text(date), norm(track), race_no(race_number), norm(runner))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def catalog_keys() -> tuple[set[tuple[str, str, str, str]], set[tuple[str, str, str]]]:
    payload = load_json(CATALOG)
    runner_keys: set[tuple[str, str, str, str]] = set()
    race_keys: set[tuple[str, str, str]] = set()
    for meeting in payload.get("meetings", []) or []:
        for race in meeting.get("races", []) or []:
            race_key = key(meeting.get("date"), meeting.get("meeting"), race.get("raceNumber"))[:3]
            race_keys.add(race_key)
            for runner in race.get("runners", []) or []:
                official = runner.get("official") or {}
                source = runner.get("source") or {}
                name = text(official.get("runner")) or text(source.get("horseName")) or text(source.get("runnerName")) or text(source.get("horse"))
                runner_keys.add((*race_key, norm(name)))
    return runner_keys, race_keys


def current_map_keys() -> tuple[set[tuple[str, str, str, str]], set[tuple[str, str, str]], Counter]:
    payload = load_json(CURRENT_MAP)
    rows = payload.get("runners", []) if isinstance(payload, dict) else []
    runner_keys: set[tuple[str, str, str, str]] = set()
    race_keys: set[tuple[str, str, str]] = set()
    evidence = Counter()
    for row in rows:
        row_key = key(row.get("raceDate"), row.get("meeting"), row.get("raceNumber"), row.get("runnerName"))
        runner_keys.add(row_key)
        race_keys.add(row_key[:3])
        if text(row.get("runStyle")) or text(row.get("projectedZone")) not in {"", "UNRESOLVED"} or text(row.get("earlySpeed")):
            evidence["rows_with_any_map_evidence"] += 1
        if text(row.get("runStyle")):
            evidence["run_style_rows"] += 1
        if text(row.get("earlySpeed")):
            evidence["early_speed_rows"] += 1
        if text(row.get("projectedZone")) and text(row.get("projectedZone")).upper() != "UNRESOLVED":
            evidence["projected_position_rows"] += 1
    evidence["source_rows"] = len(rows)
    return runner_keys, race_keys, evidence


def main() -> None:
    catalog_runner_keys, catalog_race_keys = catalog_keys()
    map_runner_keys, map_race_keys, evidence = current_map_keys()
    race_matches = len(catalog_race_keys & map_race_keys)
    runner_matches = len(catalog_runner_keys & map_runner_keys)
    source_dates = sorted({item[0] for item in map_race_keys if item[0]})
    catalog_dates = sorted({item[0] for item in catalog_race_keys if item[0]})
    source_tracks = sorted({item[1] for item in map_race_keys if item[1]})
    catalog_tracks = sorted({item[1] for item in catalog_race_keys if item[1]})

    reason = "NO_CURRENT_DATE_MAP_SOURCE_ROWS" if race_matches == 0 and source_dates != catalog_dates else "NO_SAFE_REPAIR_APPLIED"
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "action": "NO_FEED_CHANGE",
        "reason": reason,
        "catalog_races": len(catalog_race_keys),
        "catalog_runners": len(catalog_runner_keys),
        "map_source_rows": evidence["source_rows"],
        "source_races": len(map_race_keys),
        "race_matches": race_matches,
        "runner_matches": runner_matches,
        "source_dates": source_dates,
        "catalog_dates": catalog_dates,
        "source_tracks": source_tracks,
        "catalog_tracks": catalog_tracks,
        "evidence": dict(evidence),
        "note": "No governed map rows were copied into the current terminal feed because the available current-map source does not cover the active catalogue window.",
    }
    APPLY_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    APPLY_TXT.write_text(
        "\n".join(
            [
                "EDGEIQ_CURRENT_MAP_MATCHING_REPAIR_V1_APPLY",
                f"action={payload['action']}",
                f"reason={reason}",
                f"catalog_races={len(catalog_race_keys)}",
                f"catalog_runners={len(catalog_runner_keys)}",
                f"map_source_rows={evidence['source_rows']}",
                f"race_matches={race_matches}",
                f"runner_matches={runner_matches}",
                f"source_dates={','.join(source_dates)}",
                f"catalog_dates={','.join(catalog_dates)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(APPLY_TXT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
