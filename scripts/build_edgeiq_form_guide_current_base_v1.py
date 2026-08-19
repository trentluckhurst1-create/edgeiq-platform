
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
RESULTS_MASTER = DATA / "edgeiq_results_master_v1.csv"
OUT_JSON = DATA / "edgeiq_form_guide_enriched_v1.json"
OUT_CSV = DATA / "edgeiq_form_guide_current_base_v1.csv"
SUMMARY = DATA / "edgeiq_form_guide_current_base_v1_summary.csv"
REPORT = DATA / "edgeiq_form_guide_current_base_v1_report.txt"


def clean(value: Any) -> str:
    if value is None or isinstance(value, (dict, list, tuple)):
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return "" if text.lower() in {"", "-", "none", "null", "n/a", "na", "unknown"} else text


def normalise_runner(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"\s*\([A-Z]{2,3}\)\s*$", "", text)
    text = text.replace("'", "").replace("?", "").replace("&", "AND")
    return re.sub(r"[^A-Z0-9]+", "", text)


def normalise_track(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|TAB|THE)\b", " ", text)
    text = re.sub(r"\b(RACECOURSE|RACING|TRACK)\b", " ", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def normalise_date(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    text = text.split("T", 1)[0].split(" ", 1)[0].replace("/", "-")
    parts = text.split("-")
    if len(parts) != 3:
        return ""
    if len(parts[0]) == 4:
        y, m, d = parts
    else:
        d, m, y = parts
    try:
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    except ValueError:
        return ""


def parse_dt(value: Any) -> datetime | None:
    text = normalise_date(value)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return None


def race_no(value: Any) -> str:
    match = re.search(r"\d+", clean(value).upper().replace("R", ""))
    return str(int(match.group(0))) if match else ""


def number(value: Any) -> float | None:
    text = clean(value).replace("$", "").replace(",", "").replace("kg", "").replace("L", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def distance_m(value: Any) -> str:
    match = re.search(r"\d+", clean(value))
    return match.group(0) if match else ""


def odds_value(value: Any) -> float | None:
    return number(value)


def first_price(source: dict[str, Any], official: dict[str, Any]) -> tuple[float | None, str]:
    value = odds_value(official.get("market"))
    if value:
        return value, "RACING_COM_MARKET"
    odds = source.get("odds") if isinstance(source.get("odds"), list) else []
    preferred = ["LB2", "SB2", "BT", "PB3", "BTOTE", "BTOTESP"]
    by_provider = {clean(o.get("providerCode")): o for o in odds if isinstance(o, dict)}
    for provider in preferred:
        row = by_provider.get(provider)
        if not row:
            continue
        value = odds_value(row.get("oddsWin"))
        if value:
            return value, provider
    for row in odds:
        if isinstance(row, dict):
            value = odds_value(row.get("oddsWin"))
            if value:
                return value, clean(row.get("providerCode")) or "RACING_COM_MARKET"
    return None, ""


def is_scratched(official: dict[str, Any], source: dict[str, Any]) -> bool:
    vals = [official.get("scratched"), source.get("scratched"), source.get("is_scratched"), official.get("status"), source.get("status")]
    return any(str(v).strip().lower() in {"true", "1", "yes", "scr", "scratched", "lscr", "late scratching"} for v in vals)


def stat_record(text: Any) -> dict[str, Any] | None:
    # Racing.com stats generally appear as starts:wins-seconds-thirds.
    value = clean(text)
    match = re.search(r"(\d+)\s*:\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)", value)
    if not match:
        return None
    starts, wins, seconds, thirds = [int(x) for x in match.groups()]
    places = wins + seconds + thirds
    return {
        "starts": starts,
        "wins": wins,
        "seconds": seconds,
        "thirds": thirds,
        "places": places,
        "winPct": round((wins / starts) * 100, 1) if starts else 0,
        "placePct": round((places / starts) * 100, 1) if starts else 0,
        "display": value,
    }


def load_history(current_names: set[str]) -> dict[str, list[dict[str, Any]]]:
    histories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not RESULTS_MASTER.exists():
        return histories
    with RESULTS_MASTER.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            runner_key = normalise_runner(row.get("normalized_runner") or row.get("runner"))
            if runner_key not in current_names:
                continue
            status = clean(row.get("result_status")).upper()
            if status == "SCRATCHED":
                continue
            row_date = normalise_date(row.get("race_date"))
            if not row_date:
                continue
            position = number(row.get("position"))
            field_size = None
            # Results master does not always carry field size; leave null rather than fabricate.
            margin = number(row.get("beaten_margin") or row.get("margin"))
            histories[runner_key].append({
                "date": row_date,
                "track": clean(row.get("track")),
                "raceNumber": race_no(row.get("race_no")),
                "distance": number(row.get("distance")),
                "condition": clean(row.get("condition")),
                "conditionFamily": clean(row.get("condition")),
                "class": clean(row.get("class")),
                "position": int(position) if position is not None else None,
                "fieldSize": field_size,
                "positionInRunning": None,
                "barrier": number(row.get("barrier")),
                "weight": clean(row.get("weight")),
                "jockey": clean(row.get("jockey")),
                "margin": margin,
                "startingPrice": number(row.get("starting_price") or row.get("sp")),
                "performanceRating": number(row.get("epi_post") or row.get("speed_rating_raw") or row.get("speed_rating")),
                "note": clean(row.get("race_name")),
                "source": "edgeiq_results_master_v1.csv",
                "status": clean(row.get("result_status")),
            })
    for rows in histories.values():
        rows.sort(key=lambda x: x.get("date") or "", reverse=True)
    return histories


def build() -> dict[str, Any]:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    current_names: set[str] = set()
    for meeting in catalog.get("meetings", []):
        for race in meeting.get("races", []):
            for runner in race.get("runners", []):
                official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
                source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
                horse = clean(official.get("runner") or source.get("horseName"))
                if horse:
                    current_names.add(normalise_runner(horse))
    histories = load_history(current_names)
    races: list[dict[str, Any]] = []
    csv_rows: list[dict[str, Any]] = []
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    total_runners = 0
    runners_with_history = 0
    total_runs = 0

    for meeting in catalog.get("meetings", []):
        meeting_date = normalise_date(meeting.get("date"))
        meeting_name = clean(meeting.get("meeting"))
        for race in meeting.get("races", []):
            rno = race_no(race.get("raceNumber"))
            race_key = clean(race.get("raceKey")) or f"{meeting_date}|{normalise_track(meeting_name)}|R{rno}"
            race_obj = {
                "raceDate": meeting_date,
                "meeting": meeting_name,
                "raceNumber": int(rno or 0) or rno,
                "raceKey": race_key,
                "trackCondition": clean(race.get("trackCondition") or meeting.get("trackCondition")),
                "rail": clean(race.get("rail") or meeting.get("rail")),
                "distance": distance_m(race.get("distance")),
                "raceClass": clean(race.get("raceClass") or race.get("class")),
                "runners": [],
            }
            for runner in race.get("runners", []):
                official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
                source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
                horse_obj = source.get("horse") if isinstance(source.get("horse"), dict) else {}
                horse = clean(official.get("runner") or source.get("horseName"))
                runner_norm = normalise_runner(horse)
                source_history = [run for run in histories.get(runner_norm, []) if (run.get("date") or "") < meeting_date]
                full_form = source_history[:8]
                last_run = full_form[0] if full_form else None
                last_run_date = last_run.get("date") if last_run else clean(source.get("lastRaceDate") or horse_obj.get("lastRaceDate"))
                days_since = None
                target_date = parse_dt(meeting_date)
                last_date = parse_dt(last_run_date)
                if target_date and last_date and last_date < target_date:
                    days_since = (target_date - last_date).days
                market_value, market_source = first_price(source, official)
                runner_number = race_no(official.get("no") or official.get("number") or source.get("raceEntryNumber"))
                profile_stats = horse_obj.get("stats") if isinstance(horse_obj.get("stats"), list) else []
                career_record = None
                if profile_stats and isinstance(profile_stats[0], dict):
                    starts = int(number(profile_stats[0].get("starts")) or 0)
                    wins = int(number(profile_stats[0].get("firsts")) or 0)
                    seconds = int(number(profile_stats[0].get("seconds")) or 0)
                    thirds = int(number(profile_stats[0].get("thirds")) or 0)
                    career_record = {
                        "starts": starts,
                        "wins": wins,
                        "seconds": seconds,
                        "thirds": thirds,
                        "places": wins + seconds + thirds,
                        "winPct": round((wins / starts) * 100, 1) if starts else 0,
                        "placePct": round(((wins + seconds + thirds) / starts) * 100, 1) if starts else 0,
                        "display": f"{starts}:{wins}-{seconds}-{thirds}",
                    }
                runner_obj = {
                    "raceDate": meeting_date,
                    "meeting": meeting_name,
                    "raceNumber": int(rno or 0) or rno,
                    "raceKey": race_key,
                    "runnerId": clean(source.get("id") or source.get("runnerId") or source.get("horseCode") or horse_obj.get("id")) or None,
                    "runnerNumber": int(runner_number or 0) or None,
                    "runnerName": horse,
                    "normalisedRunnerName": runner_norm,
                    "lastRunDate": last_run_date or None,
                    "daysSinceLastRun": days_since,
                    "epi": None,
                    "epiSource": None,
                    "marketPrice": market_value,
                    "marketSource": market_source or None,
                    "marketAsAt": built_at if market_value is not None else None,
                    "edgeiqPrice": None,
                    "edgeiqPriceSource": None,
                    "trackRecord": stat_record(source.get("trackStats")),
                    "distanceRecord": stat_record(source.get("distanceStats")),
                    "conditionRecord": None,
                    "careerRecord": career_record,
                    "trackDistanceRecord": stat_record(source.get("trackDistanceStats")),
                    "conditionProfile": [
                        {"label": "Firm", **record} for record in [stat_record(horse_obj.get("firmStats"))] if record
                    ] + [
                        {"label": "Good", **record} for record in [stat_record(horse_obj.get("goodStats"))] if record
                    ] + [
                        {"label": "Soft", **record} for record in [stat_record(horse_obj.get("softStats"))] if record
                    ] + [
                        {"label": "Heavy", **record} for record in [stat_record(horse_obj.get("heavyStats"))] if record
                    ] + [
                        {"label": "Synthetic", **record} for record in [stat_record(horse_obj.get("syntheticStats"))] if record
                    ],
                    "classProfile": [{"label": "Class", **record} for record in [stat_record(source.get("atThisClassStats"))] if record],
                    "jockeyProfile": {"currentJockey": stat_record(source.get("jockeyStats")), "jockeyWithHorse": None, "otherJockeys": None},
                    "raceDayPattern": [],
                    "lastStart": last_run,
                    "lastFive": [str(run.get("position")) for run in full_form[:5] if run.get("position") is not None] or (official.get("lastFive") or []),
                    "fullForm": full_form,
                    "joinMethod": "CURRENT_CATALOG_TO_RESULTS_MASTER_ASOF_RUNNER",
                    "historySource": "edgeiq_results_master_v1.csv" if full_form else None,
                    "recordSource": "edgeiq_three_day_product_catalog_v1",
                    "firstStarter": not bool(full_form),
                    "scratched": is_scratched(official, source),
                }
                race_obj["runners"].append(runner_obj)
                total_runners += 1
                total_runs += len(full_form)
                if full_form:
                    runners_with_history += 1
                csv_rows.append({
                    "race_date": meeting_date,
                    "meeting": meeting_name,
                    "race_number": rno,
                    "runner_number": runner_number,
                    "runner_name": horse,
                    "history_rows": len(full_form),
                    "last_run_date": last_run_date or "",
                    "days_since_last_run": days_since if days_since is not None else "",
                    "market_price": market_value if market_value is not None else "",
                    "market_source": market_source,
                    "history_status": "OK_HISTORY" if full_form else "NO_GOVERNED_HISTORY",
                })
            races.append(race_obj)
    payload = {
        "schemaVersion": "edgeiq_form_guide_enriched_v1_current_catalog_base",
        "generatedAt": built_at,
        "sourceContract": {
            "currentRunners": "edgeiq_three_day_product_catalog_v1.json",
            "recentForm": "edgeiq_results_master_v1.csv as-of race_date < current race date",
            "pricing": "market snapshots only; EDGEiQ fair price remains null until governed pricing feed has current rows",
            "noFabrication": True,
        },
        "races": races,
    }
    return payload, csv_rows, total_runners, runners_with_history, total_runs


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    if OUT_JSON.exists():
        checkpoint = OUT_JSON.with_name(OUT_JSON.stem + "_CHECKPOINT_PRE_FULL_PRODUCT_POPULATION_REPAIR_20260726" + OUT_JSON.suffix)
        if not checkpoint.exists():
            checkpoint.write_bytes(OUT_JSON.read_bytes())
    payload, rows, total_runners, runners_with_history, total_runs = build()
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(OUT_CSV, rows, ["race_date", "meeting", "race_number", "runner_number", "runner_name", "history_rows", "last_run_date", "days_since_last_run", "market_price", "market_source", "history_status"])
    write_csv(SUMMARY, [{
        "status": "CURRENT_FORM_GUIDE_BASE_BUILT",
        "races": len(payload.get("races", [])),
        "runners": total_runners,
        "runners_with_history": runners_with_history,
        "history_runs": total_runs,
        "source": "edgeiq_three_day_product_catalog_v1 + edgeiq_results_master_v1 as-of",
    }], ["status", "races", "runners", "runners_with_history", "history_runs", "source"])
    REPORT.write_text("\n".join([
        "EDGEIQ FORM GUIDE CURRENT BASE V1",
        "status=CURRENT_FORM_GUIDE_BASE_BUILT",
        f"races={len(payload.get('races', []))}",
        f"runners={total_runners}",
        f"runners_with_history={runners_with_history}",
        f"history_runs={total_runs}",
        "same_race_leakage=NO",
        "pricing_math_changed=NO",
        "epi_math_changed=NO",
    ]) + "\n", encoding="utf-8")
    print(REPORT.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
