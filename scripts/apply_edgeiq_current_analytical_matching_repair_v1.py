from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
OUT_JSON = DATA / "edgeiq_current_analytical_matching_repair_v1_apply.json"
OUT_TXT = DATA / "edgeiq_current_analytical_matching_repair_v1_apply.txt"

FIELDS = {
    "EPI": ("edgeiq_epi_current_rating_v1.csv", "value"),
    "Suitability": ("edgeiq_current_suitability_v1.csv", "suitability"),
    "Form Momentum": ("edgeiq_current_form_momentum_v1.csv", "formMomentum"),
    "EDGEiQ Price": ("edgeiq_current_fair_prices_review_v5_2.csv", "rated_price_v5_2_review"),
    "Early Speed": ("edgeiq_current_early_speed_v1.csv", "earlySpeed"),
    "Late Speed": ("edgeiq_current_late_speed_v1.csv", "lateSpeed"),
}


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


def runner_name(runner: dict[str, Any]) -> str:
    official = runner.get("official") or {}
    source = runner.get("source") or {}
    return text(official.get("runner")) or text(source.get("horseName")) or text(source.get("runnerName")) or text(source.get("horse"))


def key(date: Any, track: Any, no: Any, runner: Any) -> tuple[str, str, str, str]:
    return (text(date), norm(track), race_no(no), norm(runner))


def catalog_keys() -> set[tuple[str, str, str, str]]:
    payload = json.loads(CATALOG.read_text(encoding="utf-8", errors="replace"))
    keys: set[tuple[str, str, str, str]] = set()
    for meeting in payload.get("meetings", []) or []:
        for race in meeting.get("races", []) or []:
            for runner in race.get("runners", []) or []:
                keys.add(key(meeting.get("date"), meeting.get("meeting"), race.get("raceNumber"), runner_name(runner)))
    return keys


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def row_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    date = row.get("raceDate") or row.get("race_date")
    track = row.get("meeting") or row.get("track")
    race = row.get("raceNumber") or row.get("race_no")
    runner = row.get("runnerName") or row.get("horse")
    return key(date, track, race, runner)


def main() -> None:
    catalog = catalog_keys()
    catalog_dates = sorted({item[0] for item in catalog if item[0]})
    summaries: dict[str, dict[str, Any]] = {}
    for field, (feed_name, value_field) in FIELDS.items():
        rows = read_rows(DATA / feed_name)
        feed_keys = {row_key(row) for row in rows}
        source_dates = sorted({item[0] for item in feed_keys if item[0]})
        matched_rows = [row for row in rows if row_key(row) in catalog]
        covered = sum(1 for row in matched_rows if text(row.get(value_field)))
        reason = "STALE_FEED_CURRENT_UNIVERSE_MISMATCH" if not matched_rows and source_dates != catalog_dates else "MISSING_UPSTREAM_EVIDENCE"
        summaries[field] = {
            "feed": feed_name,
            "value_field": value_field,
            "source_rows": len(rows),
            "source_dates": source_dates,
            "catalog_runners": len(catalog),
            "matched_rows_before": len(matched_rows),
            "covered_before": covered,
            "matched_rows_after": len(matched_rows),
            "covered_after": covered,
            "changed": False,
            "remaining_missing": max(0, len(catalog) - covered),
            "remaining_reason": reason,
        }
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "action": "NO_FEED_CHANGE",
        "catalog_runners": len(catalog),
        "catalog_dates": catalog_dates,
        "fields": summaries,
        "note": "No analytical feed was modified because available approved analytical feeds do not cover the active catalogue universe.",
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = ["EDGEIQ_CURRENT_ANALYTICAL_MATCHING_REPAIR_V1_APPLY", "action=NO_FEED_CHANGE", f"catalog_runners={len(catalog)}"]
    for field, summary in summaries.items():
        lines.append(
            f"{field}: before={summary['covered_before']}/{summary['catalog_runners']} after={summary['covered_after']}/{summary['catalog_runners']} reason={summary['remaining_reason']}"
        )
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT_TXT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
