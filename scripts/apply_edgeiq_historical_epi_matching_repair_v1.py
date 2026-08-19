from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
FORM = DATA / "edgeiq_form_guide_enriched_v2.json"
EPI_FEED = DATA / "edgeiq_epi_workspace_terminal_feed_v1.csv"
HIST = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
OUT_JSON = DATA / "edgeiq_historical_epi_matching_repair_v1_apply.json"
OUT_TXT = DATA / "edgeiq_historical_epi_matching_repair_v1_apply.txt"


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


def key(date: Any, track: Any, no: Any) -> tuple[str, str, str]:
    return (text(date), norm(track), race_no(no))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def catalog() -> tuple[set[tuple[str, str, str]], int]:
    payload = load_json(CATALOG)
    races: set[tuple[str, str, str]] = set()
    runners = 0
    for meeting in payload.get("meetings", []) or []:
        for race in meeting.get("races", []) or []:
            races.add(key(meeting.get("date"), meeting.get("meeting"), race.get("raceNumber")))
            runners += len(race.get("runners", []) or [])
    return races, runners


def form() -> tuple[set[tuple[str, str, str]], int, int, int]:
    payload = load_json(FORM)
    races: set[tuple[str, str, str]] = set()
    runner_count = 0
    historical_runs = 0
    governed_hist_epi_runs = 0
    for race in payload.get("races", []) or []:
        races.add(key(race.get("raceDate"), race.get("meeting"), race.get("raceNumber")))
        for runner in race.get("runners", []) or []:
            runner_count += 1
            for run in runner.get("fullForm", []) or []:
                historical_runs += 1
                epi = run.get("historicalEpi")
                if isinstance(epi, dict):
                    if text(epi.get("value")):
                        governed_hist_epi_runs += 1
                elif text(epi):
                    governed_hist_epi_runs += 1
    return races, runner_count, historical_runs, governed_hist_epi_runs


def main() -> None:
    catalog_races, catalog_runners = catalog()
    form_races, form_runners, historical_runs, governed_hist_epi_runs = form()
    race_matches = len(catalog_races & form_races)
    reason = "NO_CURRENT_DATE_FORM_ENRICHMENT_ROWS" if race_matches == 0 else "NO_SAFE_REPAIR_APPLIED"
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "action": "NO_FEED_CHANGE",
        "reason": reason,
        "catalog_races": len(catalog_races),
        "catalog_runners": catalog_runners,
        "form_races": len(form_races),
        "form_runners": form_runners,
        "race_matches": race_matches,
        "runners_with_historical_form": 0 if race_matches == 0 else None,
        "governed_historical_epi_runs_in_form_source": governed_hist_epi_runs,
        "historical_runs_in_form_source": historical_runs,
        "historical_rating_source_exists": HIST.exists(),
        "catalog_dates": sorted({item[0] for item in catalog_races if item[0]}),
        "form_dates": sorted({item[0] for item in form_races if item[0]}),
        "note": "No historical EPI tiles were written because current catalogue races do not match the form enrichment races. Historical EPI was not derived from non-EPI fields.",
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_TXT.write_text(
        "\n".join(
            [
                "EDGEIQ_HISTORICAL_EPI_MATCHING_REPAIR_V1_APPLY",
                f"action={payload['action']}",
                f"reason={reason}",
                f"catalog_races={len(catalog_races)}",
                f"catalog_runners={catalog_runners}",
                f"form_races={len(form_races)}",
                f"form_runners={form_runners}",
                f"race_matches={race_matches}",
                f"historical_runs_in_form_source={historical_runs}",
                f"governed_historical_epi_runs_in_form_source={governed_hist_epi_runs}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(OUT_TXT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
