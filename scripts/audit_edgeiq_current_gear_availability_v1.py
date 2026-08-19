from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "engineering"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
OUT_JSON = DATA / "edgeiq_current_gear_availability_v1_audit.json"
OUT_TXT = DATA / "edgeiq_current_gear_availability_v1_audit.txt"
DOC = DOCS / "EDGEIQ_CURRENT_GEAR_AVAILABILITY_TRACE_20260715.md"

SOURCE_FILES = {
    "gear_terminal": DATA / "edgeiq_gear_terminal_feed_v1.csv",
    "current_gear_live_join": DATA / "edgeiq_current_gear_live_join_v1.csv",
    "gear_profile_feed": DATA / "edgeiq_gear_profile_feed_v1.csv",
    "gear_profile_engine": DATA / "edgeiq_gear_profile_engine_v1.csv",
    "gear_signal_engine": DATA / "edgeiq_gear_signal_engine_v1.csv",
    "meeting_gear_changes_audit": DATA / "edgeiq_meeting_gear_changes_tab_v1_audit.json",
}


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"none", "null", "nan", "n/a", "na", "-", "missing"}:
        return ""
    return text


def normalise(value: Any) -> str:
    return "".join(ch for ch in clean(value).upper() if ch.isalnum())


def number_text(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    try:
        n = float(text)
    except ValueError:
        return text
    return str(int(n)) if n.is_integer() else str(n)


def catalog_runner_keys() -> tuple[list[dict[str, str]], set[tuple[str, str, str, str]], set[str]]:
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    rows: list[dict[str, str]] = []
    keys: set[tuple[str, str, str, str]] = set()
    dates: set[str] = set()
    for meeting in payload.get("meetings", []) if isinstance(payload, dict) else []:
        if not isinstance(meeting, dict):
            continue
        date = clean(meeting.get("date"))
        track = clean(meeting.get("meeting"))
        dates.add(date)
        for race in meeting.get("races", []) or []:
            if not isinstance(race, dict):
                continue
            race_no = number_text(race.get("raceNumber"))
            for runner in race.get("runners", []) or []:
                if not isinstance(runner, dict):
                    continue
                official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
                source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
                horse = clean(official.get("runner")) or clean(source.get("horseName")) or clean(source.get("runnerName"))
                key = (date, normalise(track), race_no, normalise(horse))
                keys.add(key)
                gear_values = [
                    clean(official.get("gear")),
                    clean(official.get("currentGear")),
                    clean(source.get("gear")),
                    clean(source.get("currentGear")),
                    clean(source.get("currentGearText")),
                ]
                rows.append({"date": date, "track": track, "race_no": race_no, "horse": horse, "has_catalog_gear": "yes" if any(gear_values) else "no"})
    return rows, keys, dates


def profile_csv(path: Path, runner_keys: set[tuple[str, str, str, str]]) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "rows": 0, "runner_matches": 0}
    rows = 0
    dates: set[str] = set()
    tracks: set[str] = set()
    keys: set[tuple[str, str, str, str]] = set()
    gear_rows = 0
    fieldnames: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        for row in reader:
            rows += 1
            date = next((clean(row.get(f)) for f in ["race_date", "meeting_date", "date"] if clean(row.get(f))), "")
            track = next((clean(row.get(f)) for f in ["track", "meeting", "venue"] if clean(row.get(f))), "")
            race_no = next((number_text(row.get(f)) for f in ["race_no", "raceNumber", "race"] if number_text(row.get(f))), "")
            horse = next((clean(row.get(f)) for f in ["runner", "horse", "runner_name", "horse_name"] if clean(row.get(f))), "")
            if date:
                dates.add(date)
            if track:
                tracks.add(track)
            key = (date, normalise(track), race_no, normalise(horse))
            if all(key):
                keys.add(key)
            if any(clean(row.get(f)) for f in ["gear_current", "current_gear", "gear_changes", "gear_added", "gear_removed", "gear"]):
                gear_rows += 1
    return {
        "exists": True,
        "rows": rows,
        "date_count": len(dates),
        "dates": sorted(dates)[:20],
        "track_count": len(tracks),
        "tracks_sample": sorted(tracks)[:12],
        "fieldnames": fieldnames,
        "gear_rows": gear_rows,
        "runner_matches": len(keys & runner_keys),
    }


def main() -> None:
    catalog_rows, runner_keys, catalog_dates = catalog_runner_keys()
    source_profiles = {name: profile_csv(path, runner_keys) if path.suffix.lower() == ".csv" else {"exists": path.exists(), "rows": None} for name, path in SOURCE_FILES.items()}
    catalog_gear_rows = sum(1 for row in catalog_rows if row["has_catalog_gear"] == "yes")
    current_terminal = source_profiles.get("gear_terminal", {})
    matched_current_gear_rows = int(current_terminal.get("runner_matches") or 0)
    terminal_gear_rows = int(current_terminal.get("gear_rows") or 0)

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    reasons = Counter()
    if catalog_gear_rows == 0:
        reasons["THREE_DAY_CATALOG_OMITS_GEAR"] = len(catalog_rows)
    if matched_current_gear_rows == 0:
        reasons["NO_CURRENT_RUNNER_KEY_MATCH_IN_GEAR_TERMINAL"] = len(catalog_rows)
    if terminal_gear_rows == 0:
        reasons["GEAR_TERMINAL_HAS_NO_USER_FACING_GEAR_VALUES"] += len(catalog_rows)

    audit = {
        "marker": "EDGEIQ_CURRENT_GEAR_AVAILABILITY_V1_AUDIT_PASS",
        "generated_at": generated_at,
        "catalog_dates": sorted(catalog_dates),
        "catalog_runners": len(catalog_rows),
        "catalog_gear_rows": catalog_gear_rows,
        "gear_terminal_runner_matches": matched_current_gear_rows,
        "gear_terminal_gear_rows": terminal_gear_rows,
        "gear_terminal_no_change_or_blank_rows": max(0, len(catalog_rows) - terminal_gear_rows),
        "coverage": {
            "race_form_terminal_gear": terminal_gear_rows,
            "meeting_gear_workspace_available": bool(source_profiles.get("meeting_gear_changes_audit", {}).get("exists")),
        },
        "source_profiles": source_profiles,
        "unavailable_reasons": dict(reasons),
        "decision": "Current gear terminal has partial governed gear detail. This run audits availability only and does not add UI columns automatically.",
    }
    OUT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    OUT_TXT.write_text(
        "\n".join(
            [
                audit["marker"],
                f"catalog_runners={len(catalog_rows)}",
                f"catalog_gear_rows={catalog_gear_rows}",
                f"gear_terminal_runner_matches={matched_current_gear_rows}",
                f"gear_terminal_gear_rows={terminal_gear_rows}",
                f"gear_terminal_no_change_or_blank_rows={max(0, len(catalog_rows) - terminal_gear_rows)}",
                f"unavailable_reasons={dict(reasons)}",
            ]
        ),
        encoding="utf-8",
    )
    DOCS.mkdir(parents=True, exist_ok=True)
    DOC.write_text(
        "\n".join(
            [
                "# EDGEiQ Current Gear Availability Trace - 2026-07-15",
                "",
                "## Result",
                "",
                "Gear is partially available in the current terminal feed. The current run only audits availability and does not add Gear columns automatically.",
                "",
                "## Current Universe",
                "",
                f"- Dates: {', '.join(sorted(catalog_dates))}",
                f"- Runners: {len(catalog_rows)}",
                f"- Catalog rows with gear fields populated: {catalog_gear_rows}",
                "",
                "## Source Findings",
                "",
                f"- Gear terminal runner matches: {matched_current_gear_rows}",
                f"- Gear terminal rows with user-facing gear values: {terminal_gear_rows}",
                f"- Gear terminal blank/no-change rows: {max(0, len(catalog_rows) - terminal_gear_rows)}",
                f"- Meeting Gear Changes workspace audit present: {bool(source_profiles.get('meeting_gear_changes_audit', {}).get('exists'))}",
                "",
                "## Decision",
                "",
                "Do not add Gear to Race/Form automatically in this data recovery run. A current governed feed exists and can be wired in a separate UI/data-consumption task if the locked column specifications allow it.",
            ]
        ),
        encoding="utf-8",
    )
    print(audit["marker"])


if __name__ == "__main__":
    main()
