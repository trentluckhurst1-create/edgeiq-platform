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
INTELLIGENCE = DATA / "edgeiq_current_race_intelligence_v1.json"
OUT_JSON = DATA / "edgeiq_current_insights_matching_repair_v1_apply.json"
OUT_TXT = DATA / "edgeiq_current_insights_matching_repair_v1_apply.txt"


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


def race_key(date: Any, track: Any, no: Any) -> tuple[str, str, str]:
    return (text(date), norm(track), race_no(no))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def catalog_races() -> set[tuple[str, str, str]]:
    payload = load_json(CATALOG)
    output: set[tuple[str, str, str]] = set()
    for meeting in payload.get("meetings", []) or []:
        for race in meeting.get("races", []) or []:
            output.add(race_key(meeting.get("date"), meeting.get("meeting"), race.get("raceNumber")))
    return output


def intelligence_races() -> tuple[set[tuple[str, str, str]], Counter]:
    payload = load_json(INTELLIGENCE)
    keys: set[tuple[str, str, str]] = set()
    evidence = Counter()
    for race in payload.get("races", []) or []:
        key = race_key(race.get("raceDate"), race.get("meeting"), race.get("raceNumber"))
        keys.add(key)
        overview = race.get("overview") if isinstance(race.get("overview"), dict) else {}
        statements = overview.get("statements") if isinstance(overview, dict) else []
        if isinstance(statements, list):
            evidence["overview_statements"] += sum(1 for item in statements if text(item.get("statement") if isinstance(item, dict) else item))
        runners = race.get("runners") if isinstance(race.get("runners"), list) else []
        for runner in runners:
            if not isinstance(runner, dict):
                continue
            for category, field in [
                ("stable_intent", "stableIntent"),
                ("prep_stage", "prepStage"),
                ("heavy_skill", "heavySkill"),
                ("campaign_profile", "campaignProfile"),
                ("distance_profile", "distanceProfile"),
                ("track_profile", "trackProfile"),
                ("late_strength", "lateSpeed"),
                ("suitability", "suitability"),
                ("form_momentum", "formMomentum"),
                ("race_shape_relevance", "raceShape"),
                ("map_pressure", "mapPressure"),
                ("market_behaviour", "marketBehaviour"),
            ]:
                value = runner.get(field)
                if isinstance(value, dict):
                    if text(value.get("value")) or text(value.get("band")) or text(value.get("summary")):
                        evidence[category] += 1
                elif text(value):
                    evidence[category] += 1
    return keys, evidence


def main() -> None:
    catalog = catalog_races()
    source, evidence = intelligence_races()
    matches = catalog & source
    reason = "NO_CURRENT_DATE_INTELLIGENCE_SOURCE_ROWS" if not matches else "NO_SAFE_REPAIR_APPLIED"
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "action": "NO_FEED_CHANGE",
        "reason": reason,
        "catalog_races": len(catalog),
        "source_races": len(source),
        "race_matches": len(matches),
        "catalog_dates": sorted({item[0] for item in catalog if item[0]}),
        "source_dates": sorted({item[0] for item in source if item[0]}),
        "source_evidence_by_category": dict(evidence),
        "note": "No insights were copied because the approved race-intelligence source does not cover the active catalogue window.",
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_TXT.write_text(
        "\n".join(
            [
                "EDGEIQ_CURRENT_INSIGHTS_MATCHING_REPAIR_V1_APPLY",
                f"action={payload['action']}",
                f"reason={reason}",
                f"catalog_races={len(catalog)}",
                f"source_races={len(source)}",
                f"race_matches={len(matches)}",
                f"source_dates={','.join(payload['source_dates'])}",
                f"catalog_dates={','.join(payload['catalog_dates'])}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(OUT_TXT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
