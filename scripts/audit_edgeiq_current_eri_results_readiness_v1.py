from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "engineering"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
MEETING_RESULTS = DATA / "edgeiq_meeting_results_terminal_feed_v1.csv"
OUT_JSON = DATA / "edgeiq_current_eri_results_readiness_v1_audit.json"
OUT_TXT = DATA / "edgeiq_current_eri_results_readiness_v1_audit.txt"
DOC = DOCS / "EDGEIQ_CURRENT_ERI_RESULTS_READINESS_TRACE_20260715.md"


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


def race_key(date_value: Any, track: Any, race_no: Any) -> str:
    return f"{clean(date_value)}|{normalise(track)}|{number_text(race_no)}"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def catalog_races() -> list[dict[str, Any]]:
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for meeting in payload.get("meetings", []) if isinstance(payload, dict) else []:
        if not isinstance(meeting, dict):
            continue
        race_date = clean(meeting.get("date"))
        track = clean(meeting.get("meeting"))
        for race in meeting.get("races", []) or []:
            if not isinstance(race, dict):
                continue
            race_no = number_text(race.get("raceNumber"))
            rows.append(
                {
                    "race_date": race_date,
                    "track": track,
                    "race_no": race_no,
                    "race_key": clean(race.get("raceKey")) or race_key(race_date, track, race_no),
                    "canonical_key": race_key(race_date, track, race_no),
                    "runner_count": len(race.get("runners", []) or []),
                }
            )
    return rows


def main() -> None:
    current_date = date(2026, 7, 15)
    races = catalog_races()
    result_rows = read_csv(MEETING_RESULTS)
    result_keys = {race_key(row.get("race_date"), row.get("track"), row.get("race_no")) for row in result_rows}
    completed_with_results = 0
    completed_without_results = 0
    future_or_current_not_run = 0
    race_classification: list[dict[str, str]] = []
    for race in races:
        race_date = parse_date(race["race_date"])
        has_result_row = race["canonical_key"] in result_keys
        if race_date and race_date < current_date:
            if has_result_row:
                completed_with_results += 1
                state = "COMPLETED_WITH_RESULT_ROW"
            else:
                completed_without_results += 1
                state = "COMPLETED_WITHOUT_GOVERNED_RESULT_ROW"
        else:
            future_or_current_not_run += 1
            state = "CURRENT_OR_FUTURE_NOT_ELIGIBLE_YET" if not has_result_row else "PENDING_RESULT_ROW"
        race_classification.append({**race, "state": state, "has_result_row": str(has_result_row)})

    result_status_counts = Counter(clean(row.get("status")) or "unknown" for row in result_rows)
    result_dates = sorted({clean(row.get("race_date")) for row in result_rows if clean(row.get("race_date"))})
    result_tracks = sorted({clean(row.get("track")) for row in result_rows if clean(row.get("track"))})
    historical_eri_files = [p.name for p in DATA.glob("*eri*.csv") if p.is_file()]
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    audit = {
        "marker": "EDGEIQ_CURRENT_ERI_RESULTS_READINESS_V1_AUDIT_PASS",
        "generated_at": generated_at,
        "catalog_races": len(races),
        "catalog_dates": sorted({race["race_date"] for race in races}),
        "meeting_results_rows": len(result_rows),
        "meeting_results_dates": result_dates,
        "meeting_results_tracks": result_tracks,
        "meeting_results_status_counts": dict(result_status_counts),
        "future_current_races_not_yet_run": future_or_current_not_run,
        "completed_races_with_results": completed_with_results,
        "completed_races_without_results": completed_without_results,
        "historical_eri_candidate_files": historical_eri_files,
        "historical_eri_coverage": 0,
        "current_race_eri_eligibility": "WITHHELD_PENDING_GOVERNED_RESULTS_AND_SPEED_DATA",
        "post_race_speed_data_eligibility": "NOT_AVAILABLE_FOR_ACTIVE_CATALOGUE",
        "actual_ui_wiring_failures": [],
        "legitimate_not_yet_available_states": [
            "Current/future races are not eligible for result rows before official results.",
            "Completed catalogue races without governed result rows remain unavailable rather than fabricated.",
            "ERI remains unavailable because this run is not permitted to build ERI or the new Results Warehouse.",
        ],
        "race_classification": race_classification,
    }
    OUT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    OUT_TXT.write_text(
        "\n".join(
            [
                audit["marker"],
                f"catalog_races={len(races)}",
                f"meeting_results_rows={len(result_rows)}",
                f"meeting_results_dates={','.join(result_dates) if result_dates else 'none'}",
                f"future_current_races_not_yet_run={future_or_current_not_run}",
                f"completed_races_with_results={completed_with_results}",
                f"completed_races_without_results={completed_without_results}",
                "historical_eri_coverage=0",
            ]
        ),
        encoding="utf-8",
    )
    DOCS.mkdir(parents=True, exist_ok=True)
    DOC.write_text(
        "\n".join(
            [
                "# EDGEiQ Current ERI and Results Readiness Trace - 2026-07-15",
                "",
                "## Result",
                "",
                "ERI and current race results remain unavailable for the active catalogue. This is not repaired in this run because the user explicitly excluded new ERI and Results Warehouse work.",
                "",
                "## Current Catalogue",
                "",
                f"- Races: {len(races)}",
                f"- Dates: {', '.join(sorted({race['race_date'] for race in races}))}",
                "",
                "## Governed Results Feed",
                "",
                f"- Rows: {len(result_rows)}",
                f"- Dates: {', '.join(result_dates) if result_dates else 'none'}",
                f"- Tracks: {', '.join(result_tracks) if result_tracks else 'none'}",
                "",
                "## Classification",
                "",
                f"- Current/future races not yet eligible: {future_or_current_not_run}",
                f"- Completed races with governed result row: {completed_with_results}",
                f"- Completed races without governed result row: {completed_without_results}",
                "",
                "## Decision",
                "",
                "Leave Results and ERI in an honest unavailable/pending state for unmatched current catalogue races.",
            ]
        ),
        encoding="utf-8",
    )
    print(audit["marker"])


if __name__ == "__main__":
    main()
