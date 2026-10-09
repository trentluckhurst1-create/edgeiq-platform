from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "public/data/edgeiq_three_day_product_catalog_v1.json"
RUN_KEYS = ("pastEvents", "past_events", "historicalRuns", "historical_runs", "formRuns", "form_runs", "previousRuns", "previous_runs")
POSITION_KEYS = ("finishPosition", "finish_position", "finishingPosition", "position", "placing", "place", "finish", "result")

def runs_from(value, depth=0):
    if depth > 8:
        return []
    if isinstance(value, dict):
        for key in RUN_KEYS:
            rows = value.get(key)
            if isinstance(rows, list) and rows:
                return rows
        for child in value.values():
            result = runs_from(child, depth + 1)
            if result:
                return result
    elif isinstance(value, list):
        for child in value:
            result = runs_from(child, depth + 1)
            if result:
                return result
    return []

def position(run):
    if not isinstance(run, dict):
        return ""
    for key in POSITION_KEYS:
        value = run.get(key)
        if value is None or str(value).strip() == "":
            continue
        text = str(value).strip().upper()
        if re.fullmatch(r"\\d{1,2}", text):
            return text
        if text in {"DNF", "F", "UR", "PU", "L", "BD"}:
            return text
    return ""

def enrich(catalog):
    added = 0
    existing = 0
    missing_source = 0
    invalid_positions = 0
    total = 0
    for meeting in catalog.get("meetings") or []:
        for race in meeting.get("races") or []:
            for runner in race.get("runners") or []:
                total += 1
                official = runner.get("official")
                if not isinstance(official, dict):
                    raise ValueError("Runner missing official record")
                if official.get("lastFive"):
                    existing += 1
                    continue
                # The catalogue stores display fields in official, not at runner root.
                # Its historicalRuns/evidenceRuns are separate; source retains the raw provider entry.
                rows = runner.get("historicalRuns") or runner.get("evidenceRuns") or runs_from(runner.get("source") or {})
                if not rows:
                    missing_source += 1
                    continue
                values = [position(row) for row in rows]
                values = [value for value in values if value][:5]
                if values:
                    official["lastFive"] = values
                    added += 1
                else:
                    invalid_positions += 1
    return dict(total=total, existing=existing, enriched=added, missing_source=missing_source, invalid_positions=invalid_positions)

def main():
    catalog = json.loads(P.read_text(encoding="utf-8-sig"))
    counts = enrich(catalog)
    P.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("LAST5_AUDIT " + " ".join(f"{key}={value}" for key, value in counts.items()))
    if counts["total"] and not (counts["existing"] or counts["enriched"]):
        print("LAST5_SOURCE_UNAVAILABLE: no certified historical form supplied; leaving values blank")
if __name__ == "__main__":
    main()
