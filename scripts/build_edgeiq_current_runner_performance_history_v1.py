from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

csv.field_size_limit(1024 * 1024 * 128)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
OUTPUT = DATA / "edgeiq_current_runner_performance_history_v1.csv"
AUDIT = DATA / "edgeiq_current_runner_performance_history_v1_audit.json"

FIELDS = [
    "current_race_date",
    "current_track",
    "current_race_no",
    "current_horse",
    "current_runner_key",
    "historical_race_date",
    "historical_track",
    "historical_race_no",
    "historical_horse",
    "distance",
    "race_class",
    "going",
    "finish",
    "margin",
    "field_size",
    "jockey",
    "trainer",
    "sp",
    "performance_rating",
    "epi",
    "early_sectional",
    "late_sectional",
    "last_600",
    "last_400",
    "last_200",
    "history_source",
    "rating_source",
    "sectional_source",
    "identity_certification",
    "strict_prior_certified",
]


def text(value: Any) -> str:
    value = "" if value is None else str(value)
    value = re.sub(r"\s+", " ", value).strip()
    return "" if value.lower() in {"", "none", "null", "nan", "-", "n/a", "na"} else value


def canon(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", text(value).upper())


def track_canon(value: Any) -> str:
    raw = text(value).upper()
    raw = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|PICKLEBET|TAB|THE|PARK)\b", " ", raw)
    raw = raw.replace("CAULFIELD HEATH", "CAULFIELDHEATH")
    return canon(raw)


def race_no(value: Any) -> str:
    match = re.search(r"\d+", text(value))
    return str(int(match.group(0))) if match else ""


def date_text(value: Any) -> str:
    raw = text(value)
    if not raw:
        return ""
    match = re.search(r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", raw)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw[:10], fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def parse_date(value: Any) -> date | None:
    raw = date_text(value)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def current_runners() -> list[dict[str, str]]:
    payload = json.loads(CATALOG.read_text(encoding="utf-8-sig"))
    rows: list[dict[str, str]] = []
    for meeting in payload.get("meetings", []):
        if not isinstance(meeting, dict):
            continue
        for race in meeting.get("races", []):
            if not isinstance(race, dict):
                continue
            for runner in race.get("runners", []):
                if not isinstance(runner, dict):
                    continue
                official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
                source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
                horse = text(official.get("runner")) or text(source.get("horse")) or text(source.get("runner"))
                rows.append(
                    {
                        "current_race_date": text(meeting.get("date"))[:10],
                        "current_track": text(meeting.get("meeting")),
                        "current_race_no": race_no(race.get("raceNumber")),
                        "current_horse": horse,
                        "current_runner_key": text(source.get("runner_key")) or f"{text(meeting.get('date'))}|{text(meeting.get('meeting'))}|R{race_no(race.get('raceNumber'))}|{canon(horse)}",
                        "current_horse_key": canon(horse),
                        "current_track_key": track_canon(meeting.get("meeting")),
                    }
                )
    return rows


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as handle:
        return list(csv.DictReader(handle))


def source_rows() -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []

    def add(path_name: str, source_name: str, mapping: dict[str, str], rating_col: str = "") -> None:
        for row in read_csv(DATA / path_name):
            horse = text(row.get(mapping.get("horse", "")))
            hist_date = date_text(row.get(mapping.get("date", "")))
            if not horse or not hist_date:
                continue
            candidates.append(
                {
                    "historical_race_date": hist_date,
                    "historical_track": text(row.get(mapping.get("track", ""))),
                    "historical_race_no": race_no(row.get(mapping.get("race_no", ""))),
                    "historical_horse": horse,
                    "distance": text(row.get(mapping.get("distance", ""))),
                    "race_class": text(row.get(mapping.get("race_class", ""))),
                    "going": text(row.get(mapping.get("going", ""))),
                    "finish": text(row.get(mapping.get("finish", ""))),
                    "margin": text(row.get(mapping.get("margin", ""))),
                    "field_size": text(row.get(mapping.get("field_size", ""))),
                    "jockey": text(row.get(mapping.get("jockey", ""))),
                    "trainer": text(row.get(mapping.get("trainer", ""))),
                    "sp": text(row.get(mapping.get("sp", ""))),
                    "performance_rating": text(row.get(rating_col)) if rating_col else "",
                    "epi": "",
                    "early_sectional": "",
                    "late_sectional": "",
                    "last_600": text(row.get(mapping.get("last_600", ""))),
                    "last_400": text(row.get(mapping.get("last_400", ""))),
                    "last_200": text(row.get(mapping.get("last_200", ""))),
                    "history_source": source_name,
                    "rating_source": source_name if rating_col and text(row.get(rating_col)) else "",
                    "sectional_source": "",
                    "_horse_key": canon(horse),
                    "_track_key": track_canon(row.get(mapping.get("track", ""))),
                    "_priority": str(mapping.get("_priority", "50")),
                }
            )

    add(
        "results_report.csv",
        "RESULTS_REPORT_GOVERNED",
        {
            "date": "race_date",
            "track": "track",
            "race_no": "race_no",
            "horse": "horse",
            "distance": "distance",
            "race_class": "race_name",
            "going": "track_condition",
            "finish": "finish_pos",
            "margin": "margin",
            "jockey": "jockey",
            "sp": "sp",
            "_priority": "10",
        },
        "run_rating",
    )
    add(
        "results_history_clean.csv",
        "RESULTS_HISTORY_CLEAN",
        {
            "date": "race_date",
            "track": "track",
            "race_no": "race_no",
            "horse": "horse",
            "distance": "distance",
            "race_class": "race_class",
            "going": "track_condition",
            "finish": "finish_pos",
            "margin": "margin",
            "field_size": "field_size",
            "jockey": "jockey",
            "trainer": "trainer",
            "sp": "sp",
            "_priority": "20",
        },
    )
    add(
        "historical_form_table.csv",
        "HISTORICAL_FORM_TABLE",
        {
            "date": "race_date",
            "track": "track",
            "race_no": "race_no",
            "horse": "horse",
            "distance": "distance",
            "going": "track_condition",
            "finish": "finish_pos",
            "margin": "margin",
            "jockey": "jockey",
            "trainer": "trainer",
            "sp": "sp",
            "_priority": "30",
        },
        "run_rating",
    )
    add(
        "form_card_runs_with_stewards.csv",
        "FORM_CARD_RUNS_WITH_STEWARDS",
        {
            "date": "run_date",
            "track": "track",
            "horse": "horse",
            "distance": "distance",
            "race_class": "race_class",
            "going": "track_condition",
            "finish": "finish_pos",
            "margin": "margin",
            "field_size": "field_size",
            "jockey": "jockey",
            "trainer": "trainer",
            "sp": "sp_text",
            "_priority": "40",
        },
        "run_rating",
    )
    add(
        "full_career_form.csv",
        "FULL_CAREER_FORM",
        {
            "date": "run_date",
            "track": "track",
            "horse": "horse",
            "distance": "distance",
            "race_class": "race_class",
            "going": "track_condition",
            "finish": "finish_pos",
            "margin": "margin",
            "field_size": "field_size",
            "jockey": "jockey",
            "trainer": "trainer",
            "sp": "sp_text",
            "_priority": "50",
        },
        "run_rating",
    )

    return candidates


def racingcom_last_start_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for race_row in read_csv(DATA / "edgeiq_vic_three_day_race_list_v1.csv"):
        try:
            entries = json.loads(race_row.get("form_entries_json") or "[]")
        except json.JSONDecodeError:
            entries = []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            horse = text(entry.get("horseName"))
            horse_obj = entry.get("horse") if isinstance(entry.get("horse"), dict) else {}
            last = horse_obj.get("lastProfessionalRaceEntryItem") if isinstance(horse_obj.get("lastProfessionalRaceEntryItem"), dict) else {}
            last_race = last.get("race") if isinstance(last.get("race"), dict) else {}
            hist_date = date_text(last_race.get("date") or entry.get("lastRaceDate") or horse_obj.get("lastRaceDate"))
            if not horse or not hist_date:
                continue
            rows.append(
                {
                    "historical_race_date": hist_date,
                    "historical_track": text(last_race.get("venueAbbr")),
                    "historical_race_no": "",
                    "historical_horse": horse,
                    "distance": text(last_race.get("distance")),
                    "race_class": "",
                    "going": "",
                    "finish": text(last.get("position") or last.get("positionAbbreviation")),
                    "margin": "",
                    "field_size": text(last_race.get("runnersCount")),
                    "jockey": "",
                    "trainer": text(entry.get("trainerName")),
                    "sp": text(entry.get("startingPrice")),
                    "performance_rating": "",
                    "epi": "",
                    "early_sectional": "",
                    "late_sectional": "",
                    "last_600": "",
                    "last_400": "",
                    "last_200": "",
                    "history_source": "RACING_COM_LAST_PROFESSIONAL_RACE",
                    "rating_source": "",
                    "sectional_source": "",
                    "_horse_key": canon(horse),
                    "_track_key": track_canon(last_race.get("venueAbbr")),
                    "_priority": "70",
                }
            )
    return rows


def last_five_rows(current: dict[str, str], runner_source: dict[str, Any]) -> list[dict[str, str]]:
    value = runner_source.get("last_five") or runner_source.get("lastFive")
    tokens: list[str] = []
    if isinstance(value, list):
        tokens = [text(item) for item in value]
    elif text(value):
        tokens = re.findall(r"\d+|DNF|F|UR|PU|BD", text(value).upper())
    rows = []
    for index, token in enumerate([item for item in tokens if item], start=1):
        rows.append(
            {
                **{field: "" for field in FIELDS},
                "current_race_date": current["current_race_date"],
                "current_track": current["current_track"],
                "current_race_no": current["current_race_no"],
                "current_horse": current["current_horse"],
                "current_runner_key": current["current_runner_key"],
                "historical_horse": current["current_horse"],
                "finish": token,
                "history_source": "RACING_COM_LAST_FIVE_FALLBACK",
                "identity_certification": f"LAST_FIVE_POSITION_ONLY_{index}",
                "strict_prior_certified": "UNKNOWN_SOURCE_DATE",
            }
        )
    return rows


def sectional_index() -> dict[tuple[str, str, str, str], dict[str, str]]:
    out: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in read_csv(DATA / "edgeiq_sectional_governed_v29.csv"):
        key = (
            date_text(row.get("race_date")),
            track_canon(row.get("canonical_track")),
            race_no(row.get("race_no")),
            canon(row.get("canonical_horse") or row.get("horse")),
        )
        if not all(key):
            continue
        candidate = {
            "early_sectional": text(row.get("original_col_early_velocity") or row.get("original_col_raw_early_speed")),
            "late_sectional": text(row.get("original_col_late_velocity") or row.get("original_col_raw_late_speed")),
            "last_600": text(row.get("original_col_last_600") or row.get("original_col_raw_last_600") or row.get("original_col_sectional_600")),
            "last_400": text(row.get("original_col_last_400") or row.get("original_col_raw_last_400") or row.get("original_col_sectional_400")),
            "last_200": text(row.get("original_col_last_200") or row.get("original_col_raw_last_200") or row.get("original_col_sectional_200")),
            "sectional_source": "edgeiq_sectional_governed_v29",
        }
        if key not in out or any(candidate.get(k) for k in ("early_sectional", "late_sectional", "last_600", "last_400", "last_200")):
            out[key] = candidate
    return out


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    current = current_runners()
    source = source_rows() + racingcom_last_start_rows()
    by_horse: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in source:
        by_horse[row["_horse_key"]].append(row)
    sections = sectional_index()

    output_rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str, str, str]] = set()

    catalog = json.loads(CATALOG.read_text(encoding="utf-8-sig"))
    source_by_runner_key: dict[str, dict[str, Any]] = {}
    for meeting in catalog.get("meetings", []):
        for race in meeting.get("races", []):
            for runner in race.get("runners", []):
                src = runner.get("source") if isinstance(runner.get("source"), dict) else {}
                off = runner.get("official") if isinstance(runner.get("official"), dict) else {}
                key = text(src.get("runner_key")) or f"{text(meeting.get('date'))}|{text(meeting.get('meeting'))}|R{race_no(race.get('raceNumber'))}|{canon(off.get('runner'))}"
                source_by_runner_key[key] = src

    for runner in current:
        current_date = parse_date(runner["current_race_date"])
        matched: list[dict[str, str]] = []
        for candidate in by_horse.get(runner["current_horse_key"], []):
            hist_date = parse_date(candidate["historical_race_date"])
            if current_date is None or hist_date is None or not hist_date < current_date:
                continue
            matched.append(candidate)
        matched.sort(key=lambda row: (row["historical_race_date"], -int(row.get("_priority") or "99")), reverse=True)
        for candidate in matched:
            dedupe_key = (
                runner["current_runner_key"],
                candidate["historical_race_date"],
                candidate["_track_key"],
                race_no(candidate["historical_race_no"]),
                candidate["_horse_key"],
                candidate["finish"],
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            row = {field: "" for field in FIELDS}
            row.update({field: runner.get(field, "") for field in ("current_race_date", "current_track", "current_race_no", "current_horse", "current_runner_key")})
            for field in FIELDS:
                if field.startswith("historical_") or field in {
                    "distance", "race_class", "going", "finish", "margin", "field_size",
                    "jockey", "trainer", "sp", "performance_rating", "epi", "history_source",
                    "rating_source", "sectional_source",
                }:
                    row[field] = candidate.get(field, "")
            sec_key = (
                row["historical_race_date"],
                track_canon(row["historical_track"]),
                race_no(row["historical_race_no"]),
                canon(row["historical_horse"]),
            )
            if sec_key in sections:
                for field, value in sections[sec_key].items():
                    if value:
                        row[field] = value
            row["identity_certification"] = "HORSE_NAME_CANONICAL_EXACT_STRICT_PRIOR"
            row["strict_prior_certified"] = "TRUE"
            output_rows.append(row)
        if not matched:
            output_rows.extend(last_five_rows(runner, source_by_runner_key.get(runner["current_runner_key"], {})))

    output_rows.sort(key=lambda row: (row["current_race_date"], row["current_track"], int(row["current_race_no"] or 0), canon(row["current_horse"]), row["historical_race_date"]), reverse=False)
    write_csv(OUTPUT, output_rows)

    def count(field: str) -> int:
        return sum(1 for row in output_rows if text(row.get(field)))

    grouped: dict[str, int] = defaultdict(int)
    for row in output_rows:
        grouped[row["current_runner_key"]] += 1

    audit = {
        "schemaVersion": "edgeiq_current_runner_performance_history_v1_audit",
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "currentRunners": len(current),
        "historyRows": len(output_rows),
        "runnersWith1PlusHistory": sum(1 for value in grouped.values() if value >= 1),
        "runnersWith3PlusHistory": sum(1 for value in grouped.values() if value >= 3),
        "runnersWith5PlusHistory": sum(1 for value in grouped.values() if value >= 5),
        "rowsWithDate": count("historical_race_date"),
        "rowsWithTrack": count("historical_track"),
        "rowsWithDistance": count("distance"),
        "rowsWithClass": count("race_class"),
        "rowsWithGoing": count("going"),
        "rowsWithFinish": count("finish"),
        "rowsWithMargin": count("margin"),
        "rowsWithRating": count("performance_rating"),
        "rowsWithEarly": count("early_sectional"),
        "rowsWithLate": count("late_sectional"),
        "rowsWithAnySectional": sum(1 for row in output_rows if any(text(row.get(field)) for field in ("early_sectional", "late_sectional", "last_600", "last_400", "last_200"))),
        "historySourceCounts": dict(sorted({source: sum(1 for row in output_rows if row.get("history_source") == source) for source in {row.get("history_source") for row in output_rows}}.items())),
        "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/"),
    }
    AUDIT.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("EDGEIQ_CURRENT_RUNNER_PERFORMANCE_HISTORY_V1 PASS")
    print(f"CURRENT_RUNNERS={audit['currentRunners']}")
    print(f"HISTORY_ROWS={audit['historyRows']}")
    print(f"RUNNERS_WITH_1_PLUS_HISTORY={audit['runnersWith1PlusHistory']}")
    print(f"RUNNERS_WITH_3_PLUS_HISTORY={audit['runnersWith3PlusHistory']}")
    print(f"RUNNERS_WITH_5_PLUS_HISTORY={audit['runnersWith5PlusHistory']}")
    print(f"ROWS_WITH_RATING={audit['rowsWithRating']}")
    print(f"ROWS_WITH_ANY_SECTIONAL={audit['rowsWithAnySectional']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
