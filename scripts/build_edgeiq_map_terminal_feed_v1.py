from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
CURRENT_MAP = DATA / "edgeiq_current_map_v1.json"
OUT = DATA / "edgeiq_map_terminal_feed_v1.csv"
SUMMARY = DATA / "edgeiq_map_terminal_feed_summary_v1.csv"
TRACE = DATA / "edgeiq_map_engineering_build_v1_trace.txt"

FIELDNAMES = [
    "workspace_id",
    "meeting_key",
    "race_key",
    "generated_at",
    "race_date",
    "track",
    "race_no",
    "no",
    "horse",
    "barrier",
    "effective_barrier",
    "run_style",
    "early_speed",
    "projected_position",
    "source",
    "source_timestamp",
    "source_confidence",
    "row_status",
]


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"none", "null", "nan", "n/a", "na", "-"}:
        return ""
    return text


def normalise(value: Any) -> str:
    return "".join(ch for ch in clean(value).upper() if ch.isalnum())


def number_text(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    if number.is_integer():
        return str(int(number))
    return text


def runner_name(runner: dict[str, Any]) -> str:
    official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
    source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
    return (
        clean(official.get("runner"))
        or clean(source.get("horseName"))
        or clean(source.get("runnerName"))
        or clean(source.get("horse"))
    )


def runner_no(runner: dict[str, Any], index: int) -> str:
    official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
    source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
    return (
        number_text(official.get("no"))
        or number_text(official.get("number"))
        or number_text(source.get("runnerNumber"))
        or number_text(source.get("runner_no"))
        or number_text(source.get("saddlecloth"))
        or str(index + 1)
    )


def runner_barrier(runner: dict[str, Any]) -> str:
    official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
    source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
    return (
        number_text(official.get("barrier"))
        or number_text(source.get("barrierNumber"))
        or number_text(source.get("liveBarrierNumber"))
        or number_text(source.get("barrier"))
    )


def build_current_map_index() -> dict[tuple[str, str, str, str], dict[str, Any]]:
    if not CURRENT_MAP.exists():
        return {}
    payload = json.loads(CURRENT_MAP.read_text(encoding="utf-8"))
    rows = payload.get("runners", []) if isinstance(payload, dict) else []
    index: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = (
            clean(row.get("raceDate")),
            normalise(row.get("meeting")),
            number_text(row.get("raceNumber")),
            normalise(row.get("runnerName")),
        )
        if all(key):
            index[key] = row
    return index


def current_value(row: dict[str, Any] | None, key: str) -> str:
    if not row:
        return ""
    value = clean(row.get(key))
    if value.upper() == "UNRESOLVED":
        return ""
    return value


def main() -> None:
    if not CATALOG.exists():
        raise FileNotFoundError(CATALOG)

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    meetings = catalog.get("meetings", []) if isinstance(catalog, dict) else []
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    current_index = build_current_map_index()
    output_rows: list[dict[str, str]] = []
    matched_current = 0

    for meeting in meetings:
        if not isinstance(meeting, dict):
            continue
        meeting_key = clean(meeting.get("meetingKey"))
        race_date = clean(meeting.get("date"))
        track = clean(meeting.get("meeting"))
        for race in meeting.get("races", []) or []:
            if not isinstance(race, dict):
                continue
            race_key = clean(race.get("raceKey"))
            race_no = number_text(race.get("raceNumber"))
            for index, runner in enumerate(race.get("runners", []) or []):
                if not isinstance(runner, dict):
                    continue
                horse = runner_name(runner)
                barrier = runner_barrier(runner)
                current = current_index.get((race_date, normalise(track), race_no, normalise(horse)))
                if current:
                    matched_current += 1
                effective_barrier = number_text(current.get("barrier")) if current else barrier
                projected_position = current_value(current, "projectedZone")
                run_style = current_value(current, "runStyle")
                early_speed = current_value(current, "earlySpeed")
                confidence = "governed" if current and (projected_position or run_style or early_speed) else "official" if barrier else "unavailable"
                output_rows.append(
                    {
                        "workspace_id": "BETA-009",
                        "meeting_key": meeting_key,
                        "race_key": race_key,
                        "generated_at": generated_at,
                        "race_date": race_date,
                        "track": track,
                        "race_no": race_no,
                        "no": runner_no(runner, index),
                        "horse": horse,
                        "barrier": barrier,
                        "effective_barrier": effective_barrier,
                        "run_style": run_style,
                        "early_speed": early_speed,
                        "projected_position": projected_position,
                        "source": clean(current.get("sourceVersion")) if current else "THREE_DAY_PRODUCT_CATALOG_V1",
                        "source_timestamp": generated_at,
                        "source_confidence": confidence,
                        "row_status": "current" if current else "pending_map_evidence",
                    }
                )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(output_rows)

    unique_races = len({row["race_key"] for row in output_rows if row["race_key"]})
    with SUMMARY.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(
            [
                {"metric": "rows", "value": len(output_rows)},
                {"metric": "races", "value": unique_races},
                {"metric": "matched_current_map_rows", "value": matched_current},
                {"metric": "frontend_limit", "value": 10000},
                {"metric": "status", "value": "PASS" if len(output_rows) <= 10000 else "WARN_OVER_LIMIT"},
            ]
        )

    TRACE.write_text(
        "\n".join(
            [
                "EDGEIQ_MAP_TERMINAL_FEED_V1",
                f"generated_at={generated_at}",
                f"rows={len(output_rows)}",
                f"races={unique_races}",
                f"matched_current_map_rows={matched_current}",
                f"source_catalog={CATALOG.name}",
                f"source_current_map={CURRENT_MAP.name if CURRENT_MAP.exists() else 'missing'}",
            ]
        ),
        encoding="utf-8",
    )

    if len(output_rows) > 10000:
        raise RuntimeError(f"edgeiq_map_terminal_feed_v1 exceeds frontend limit: {len(output_rows)}")
    print(f"EDGEIQ_MAP_TERMINAL_FEED_V1 rows={len(output_rows)} races={unique_races} matched_current_map_rows={matched_current}")


if __name__ == "__main__":
    main()
