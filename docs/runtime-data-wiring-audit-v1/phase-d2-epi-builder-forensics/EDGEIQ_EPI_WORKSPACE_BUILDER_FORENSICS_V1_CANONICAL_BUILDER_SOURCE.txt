from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
FORM_GUIDE = DATA / "edgeiq_form_guide_enriched_v2.json"
HISTORICAL_RATING = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
OUT = DATA / "edgeiq_epi_workspace_terminal_feed_v1.csv"
SUMMARY = DATA / "edgeiq_epi_workspace_terminal_feed_summary_v1.csv"
TRACE = DATA / "edgeiq_epi_workspace_engineering_build_v1_trace.txt"
HISTORICAL_EPI_CONFLICTS = DATA / "edgeiq_historical_epi_lookup_conflicts_v1.csv"

START_KEYS = [f"start_{index}" for index in range(10, 0, -1)]

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
    "current_epi",
    "rank",
    "field_avg",
    "diff",
    *START_KEYS,
    "peak_last_10",
    "average_last_10",
    "governed_trend",
    "source",
    "source_timestamp",
    "source_confidence",
    "row_status",
    *[f"{key}_class" for key in START_KEYS],
    *[f"{key}_context" for key in START_KEYS],
]

CONTEXT_FIELDS = [
    "DATE",
    "TRACK",
    "MEETING / RACE",
    "DISTANCE",
    "CLASS",
    "CONDITION",
    "BARRIER",
    "WEIGHT",
    "JOCKEY",
    "TRAINER",
    "FINISH",
    "MARGIN",
    "SP",
    "EPI",
    "ERI",
    "8-6",
    "6-4",
    "4-2",
    "2-F",
    "SOURCE",
    "VERSION / TIMESTAMP",
]


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"none", "null", "nan", "n/a", "na", "-", "missing"}:
        return ""
    return text


def normalise(value: Any) -> str:
    return "".join(ch for ch in clean(value).upper() if ch.isalnum())


TRACK_ALIASES = {
    # Flemington
    "FLEMINGTON": "FLEM",
    "FLEM": "FLEM",

    # Caulfield / Caulfield Heath
    "CAULFIELD": "CAUL",
    "CAUL": "CAUL",
    "CAULFIELDHEATH": "CAUH",
    "CAUH": "CAUH",

    # Sandown
    "SANDOWN": "SANL",
    "SPORTSBETSANDOWNLAKESIDE": "SANL",
    "SANDOWNLAKESIDE": "SANL",
    "SANL": "SANL",
    "SPORTSBETSANDOWNHILLSIDE": "SANH",
    "SANDOWNHILLSIDE": "SANH",
    "SANH": "SANH",

    # Pakenham
    "PAKENHAM": "PAKM",
    "SOUTHSIDEPAKENHAM": "PAKM",
    "PAKM": "PAKM",
    "PAKENHAMSYNTHETIC": "PAKS",
    "SPORTSBETPAKENHAMSYNTHETIC": "PAKS",
    "PAKS": "PAKS",

    # Cranbourne
    "CRANBOURNE": "CRAN",
    "SOUTHSIDECRANBOURNE": "CRAN",
    "CRAN": "CRAN",

    # Geelong
    "GEELONG": "GEEL",
    "LADBROKESGEELONG": "GEEL",
    "GEEL": "GEEL",

    # Ballarat
    "BALLARAT": "BRAT",
    "SPORTSBETBALLARAT": "BRAT",
    "BRAT": "BRAT",
    "BALLARATSYNTHETIC": "BALS",
    "SPORTSBETBALLARATSYNTHETIC": "BALS",
    "BALS": "BALS",

    # Other Victorian tracks
    "WARRNAMBOOL": "WNBL",
    "WNBL": "WNBL",
    "WERRIBEE": "WERR",
    "PICKLEBETPARKWERRIBEE": "WERR",
    "WERR": "WERR",
    "MORNINGTON": "MORN",
    "MORN": "MORN",
    "WANGARATTA": "WANG",
    "SPORTSBETWANGARATTA": "WANG",
    "WANG": "WANG",
    "KYNETON": "KYNE",
    "BET365PARKKYNETON": "KYNE",
    "KYNE": "KYNE",
    "ECHUCA": "ECHA",
    "BET365ECHUCA": "ECHA",
    "ECHA": "ECHA",
    "SEYMOUR": "SEYM",
    "BET365SEYMOUR": "SEYM",
    "SEYM": "SEYM",
    "HORSHAM": "HSHM",
    "HSHM": "HSHM",
    "TERANG": "TER",
    "BET365TERANG": "TER",
    "TER": "TER",
    "COLAC": "CLAC",
    "BET365COLAC": "CLAC",
    "CLAC": "CLAC",
    "DONALD": "DON",
    "DON": "DON",
    "TATURA": "TAT",
    "TAT": "TAT",
    "ARARAT": "ARAT",
    "ARAT": "ARAT",
    "BENDIGO": "BDGO",
    "BDGO": "BDGO",
    "SALE": "SALE",
    "MOE": "MOE",
    "BENALLA": "BEN",
    "BEN": "BEN",
    "HAMILTON": "HAM",
    "HAM": "HAM",
    "SWANHILL": "SWAN",
    "SWAN": "SWAN",
    "MILDURA": "MILD",
    "MILD": "MILD",
    "STAWELL": "STAW",
    "STAW": "STAW",
    "CASTERTON": "CAST",
    "CAST": "CAST",
}


def canonical_track(value: Any) -> str:
    key = normalise(value)
    return TRACK_ALIASES.get(key, key)


def number_text(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    try:
        number = float(text.replace("$", "").replace(",", ""))
    except ValueError:
        digits = "".join(ch for ch in text if ch.isdigit())
        return digits or text
    if number.is_integer():
        return str(int(number))
    return str(number)


def metric(value: Any, places: int = 1) -> str:
    if isinstance(value, dict):
        value = value.get("value")
    text = clean(value)
    if not text:
        return ""
    try:
        return f"{float(text):.{places}f}"
    except ValueError:
        return text


def metric_float(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")
    text = clean(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def race_match_key(date: Any, track: Any, race_no: Any) -> tuple[str, str, str]:
    return (clean(date), normalise(track), number_text(race_no))


def runner_match_key(value: Any) -> str:
    return normalise(value)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        yield from csv.DictReader(handle)


def catalog_races(payload: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for meeting in payload.get("meetings", []) if isinstance(payload, dict) else []:
        if not isinstance(meeting, dict):
            continue
        for race in meeting.get("races", []) or []:
            if isinstance(race, dict):
                pairs.append((meeting, race))
    return pairs


def form_race_index(payload: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for race in payload.get("races", []) if isinstance(payload, dict) else []:
        if not isinstance(race, dict):
            continue
        key = race_match_key(race.get("raceDate"), race.get("meeting"), race.get("raceNumber"))
        if all(key):
            index[key] = race
    return index


def runner_no(runner: dict[str, Any], fallback: int) -> str:
    official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
    return number_text(official.get("no") or official.get("number") or runner.get("runnerNumber")) or str(fallback)


def runner_name(runner: dict[str, Any]) -> str:
    official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
    source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
    return clean(official.get("runner") or source.get("horseName") or source.get("runnerName") or runner.get("runnerName"))


def collect_historical_keys(form_races: dict[tuple[str, str, str], dict[str, Any]]) -> set[tuple[str, str, str, str]]:
    keys: set[tuple[str, str, str, str]] = set()
    for race in form_races.values():
        for runner in race.get("runners", []) or []:
            horse_key = runner_match_key(runner.get("runnerName"))
            for run in runner.get("fullForm", []) or []:
                distance = number_text(run.get("distance"))
                key = (
                    horse_key,
                    clean(run.get("date")),
                    canonical_track(run.get("track")),
                    distance,
                )
                if horse_key and key[1] and key[2]:
                    keys.add(key)
    return keys


def historical_rating_index(
    required_keys: set[tuple[str, str, str, str]]
) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    governed: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    if not required_keys:
        return governed

    for row in read_csv_rows(HISTORICAL_RATING) or []:
        horse = runner_match_key(row.get("horse"))
        date = clean(row.get("race_date"))
        track = canonical_track(row.get("track"))
        distance = number_text(row.get("distance"))
        key = (horse, date, track, distance)

        if key in required_keys:
            grouped.setdefault(key, []).append(row)

    conflicts: list[dict[str, str]] = []

    for key, rows in grouped.items():
        rated_rows: list[tuple[float, dict[str, str]]] = []

        for row in rows:
            rating = metric_float(row.get("performance_rating_v6_1_research"))
            if rating is not None:
                rated_rows.append((rating, row))

        unique_ratings = sorted({rating for rating, _ in rated_rows})

        if len(unique_ratings) == 1:
            rating = unique_ratings[0]

            source_files = sorted(
                {
                    clean(row.get("source_file")) or clean(row.get("_source_file"))
                    for _, row in rated_rows
                    if clean(row.get("source_file")) or clean(row.get("_source_file"))
                }
            )

            built_values = sorted(
                {
                    clean(row.get("built_at_v6_1_research"))
                    for _, row in rated_rows
                    if clean(row.get("built_at_v6_1_research"))
                }
            )

            governed[key] = {
                "status": "UNIQUE" if len(rows) == 1 else "SAME_RATING_MULTIPLE_ROWS",
                "rating": rating,
                "source_files": source_files,
                "built_at": built_values[-1] if built_values else "",
                "match_count": len(rows),
            }
            continue

        if len(unique_ratings) > 1:
            horse, date, track, distance = key
            source_files = sorted(
                {
                    clean(row.get("source_file")) or clean(row.get("_source_file"))
                    for row in rows
                    if clean(row.get("source_file")) or clean(row.get("_source_file"))
                }
            )

            governed[key] = {
                "status": "CONFLICTING_RATINGS",
                "rating": None,
                "ratings": unique_ratings,
                "source_files": source_files,
                "built_at": "",
                "match_count": len(rows),
            }

            conflicts.append(
                {
                    "horse_key": horse,
                    "race_date": date,
                    "canonical_track": track,
                    "distance": distance,
                    "match_count": str(len(rows)),
                    "candidate_ratings": " | ".join(
                        f"{rating:.10g}" for rating in unique_ratings
                    ),
                    "source_files": " | ".join(source_files),
                    "decision": "HISTORICAL_EPI_UNAVAILABLE_CONFLICT",
                }
            )
            continue

        governed[key] = {
            "status": "NO_RATED_ROWS",
            "rating": None,
            "source_files": [],
            "built_at": "",
            "match_count": len(rows),
        }

    conflict_fields = [
        "horse_key",
        "race_date",
        "canonical_track",
        "distance",
        "match_count",
        "candidate_ratings",
        "source_files",
        "decision",
    ]

    with HISTORICAL_EPI_CONFLICTS.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=conflict_fields)
        writer.writeheader()
        writer.writerows(
            sorted(
                conflicts,
                key=lambda row: (
                    row["horse_key"],
                    row["race_date"],
                    row["canonical_track"],
                    row["distance"],
                ),
            )
        )

    return governed


def current_epi_value(runner: dict[str, Any]) -> float | None:
    return metric_float(runner.get("epi") or runner.get("rating"))


def source_time(runner: dict[str, Any]) -> str:
    for key in ["epi", "rating", "earlySpeed", "lateSpeed", "suitability", "formMomentum"]:
        value = runner.get(key)
        if isinstance(value, dict) and clean(value.get("asAt")):
            return clean(value.get("asAt"))
    return ""


def source_text(runner: dict[str, Any]) -> str:
    values = []
    for key in ["epi", "rating"]:
        value = runner.get(key)
        if isinstance(value, dict) and clean(value.get("source")):
            values.append(clean(value.get("source")))
    return " | ".join(dict.fromkeys(values)) or "edgeiq_form_guide_enriched_v2.json"


def historical_epi_for_run(
    runner: dict[str, Any],
    run: dict[str, Any],
    historical: dict[tuple[str, str, str, str], dict[str, Any]],
) -> tuple[float | None, str, str]:
    direct = metric_float(run.get("historicalEpi"))

    if direct is not None:
        value = (
            run.get("historicalEpi")
            if isinstance(run.get("historicalEpi"), dict)
            else {}
        )
        return (
            direct,
            clean(value.get("source"))
            or "edgeiq_form_guide_enriched_v2.json:historicalEpi",
            clean(value.get("version") or value.get("asAt")),
        )

    key = (
        runner_match_key(runner.get("runnerName")),
        clean(run.get("date")),
        canonical_track(run.get("track")),
        number_text(run.get("distance")),
    )

    result = historical.get(key)

    if not result:
        return None, "", ""

    if result.get("status") not in {
        "UNIQUE",
        "SAME_RATING_MULTIPLE_ROWS",
    }:
        return None, "", ""

    rating = metric_float(result.get("rating"))

    if rating is None:
        return None, "", ""

    status = clean(result.get("status"))
    source_suffix = (
        ":same_rating_duplicates_collapsed"
        if status == "SAME_RATING_MULTIPLE_ROWS"
        else ""
    )

    return (
        rating,
        (
            "edgeiq_historical_performance_rating_v6_1_research.csv:"
            "performance_rating_v6_1_research"
            f"{source_suffix}"
        ),
        clean(result.get("built_at")),
    )


def margin_float(value: Any) -> float | None:
    text = clean(value).upper().replace("L", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def position_number(value: Any) -> int | None:
    text = clean(value)
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def tile_class(epi: float | None, eri: float | None, run: dict[str, Any]) -> str:
    if epi is None:
        return "missing"
    if eri is None:
        position = position_number(run.get("position"))
        margin = margin_float(run.get("margin"))
        if position == 1 or (margin is not None and margin <= 1):
            return "positive"
        if (position is not None and position >= 8) or (margin is not None and margin >= 6):
            return "negative"
        return "neutral"
    diff = epi - eri
    if diff >= 2:
        return "positive"
    if diff <= -2:
        return "negative"
    return "neutral"


def context_for_run(runner: dict[str, Any], run: dict[str, Any], epi: float | None, epi_source: str, epi_version: str) -> str:
    eri = metric(run.get("raceRating"))
    sectionals = run.get("sectionalIndices") if isinstance(run.get("sectionalIndices"), dict) else {}
    values = {
        "DATE": clean(run.get("date")),
        "TRACK": clean(run.get("track")),
        "MEETING / RACE": f"{clean(run.get('track'))} R{number_text(run.get('raceNumber'))}".strip(),
        "DISTANCE": f"{number_text(run.get('distance'))}m" if number_text(run.get("distance")) else "",
        "CLASS": clean(run.get("class")),
        "CONDITION": clean(run.get("condition")),
        "BARRIER": number_text(run.get("barrier")),
        "WEIGHT": clean(run.get("weight")),
        "JOCKEY": clean(run.get("jockey")),
        "TRAINER": clean(runner.get("latestTrainer") or runner.get("trainer")),
        "FINISH": clean(run.get("position")),
        "MARGIN": clean(run.get("margin")),
        "SP": clean(run.get("startingPrice")),
        "EPI": metric(epi),
        "ERI": eri,
        "8-6": metric(sectionals.get("index800To600") if isinstance(sectionals, dict) else None),
        "6-4": metric(sectionals.get("index600To400") if isinstance(sectionals, dict) else None),
        "4-2": metric(sectionals.get("index400To200") if isinstance(sectionals, dict) else None),
        "2-F": metric(sectionals.get("index200ToFinish") if isinstance(sectionals, dict) else None),
        "SOURCE": epi_source,
        "VERSION / TIMESTAMP": epi_version,
    }
    return json.dumps({field: values.get(field, "") for field in CONTEXT_FIELDS}, separators=(",", ":"))


def trend_from_values(values: list[float]) -> str:
    if len(values) < 3:
        return ""
    recent = sum(values[:3]) / 3
    older = sum(values[-3:]) / 3
    delta = recent - older
    if delta >= 2:
        return "Rising"
    if delta <= -2:
        return "Easing"
    return "Holding"


def build() -> tuple[int, int, int, int]:
    generated_at = datetime.now(timezone.utc).isoformat()
    catalog = read_json(CATALOG)
    form_payload = read_json(FORM_GUIDE)
    races = catalog_races(catalog)
    form_index = form_race_index(form_payload)
    historical = historical_rating_index(collect_historical_keys(form_index))
    rows: list[dict[str, str]] = []
    historical_tiles = 0
    populated_contexts = 0

    for meeting, race in races:
        date = clean(meeting.get("date"))
        track = clean(meeting.get("meeting"))
        race_no = number_text(race.get("raceNumber"))
        form_race = form_index.get(race_match_key(date, track, race_no), {})
        form_runners = {
            runner_match_key(runner.get("runnerName")): runner
            for runner in form_race.get("runners", []) or []
            if isinstance(runner, dict)
        }
        catalog_runners = race.get("runners", []) or []
        display_runners: list[tuple[str, str, dict[str, Any], dict[str, Any] | None]] = []
        for index, catalog_runner in enumerate(catalog_runners, start=1):
            name = runner_name(catalog_runner)
            form_runner = form_runners.get(runner_match_key(name))
            display_runners.append((runner_no(catalog_runner, index), name, catalog_runner, form_runner))

        current_values = [current_epi_value(form_runner) for _, _, _, form_runner in display_runners if form_runner]
        current_values = [value for value in current_values if value is not None]
        field_avg = sum(current_values) / len(current_values) if current_values else None
        sorted_values = sorted(current_values, reverse=True)

        for no, name, _catalog_runner, form_runner in display_runners:
            current_epi = current_epi_value(form_runner) if form_runner else None
            rank = str(sorted_values.index(current_epi) + 1) if current_epi is not None and current_epi in sorted_values else ""
            diff = current_epi - field_avg if current_epi is not None and field_avg is not None else None
            row = {
                "workspace_id": "BETA-013",
                "meeting_key": clean(meeting.get("meetingKey")),
                "race_key": clean(race.get("raceKey")),
                "generated_at": generated_at,
                "race_date": date,
                "track": track,
                "race_no": race_no,
                "no": no,
                "horse": name,
                "current_epi": metric(current_epi),
                "rank": rank,
                "field_avg": metric(field_avg),
                "diff": metric(diff),
                "peak_last_10": "",
                "average_last_10": "",
                "governed_trend": "",
                "source": source_text(form_runner or {}),
                "source_timestamp": source_time(form_runner or {}) or clean(form_payload.get("generatedAt")),
                "source_confidence": "governed" if form_runner else "unavailable",
                "row_status": "current" if form_runner else "unavailable",
            }
            for key in START_KEYS:
                row[key] = ""
                row[f"{key}_class"] = "missing"
                row[f"{key}_context"] = ""
            epi_values: list[float] = []
            runs = (form_runner or {}).get("fullForm", [])[:10] if form_runner else []
            for offset, run in enumerate(runs, start=1):
                if not isinstance(run, dict):
                    continue
                start_key = f"start_{offset}"
                epi, epi_source, epi_version = historical_epi_for_run(form_runner or {}, run, historical)
                eri = metric_float(run.get("raceRating"))
                if epi is not None:
                    row[start_key] = metric(epi)
                    row[f"{start_key}_class"] = tile_class(epi, eri, run)
                    epi_values.append(epi)
                    historical_tiles += 1
                context = context_for_run(form_runner or {}, run, epi, epi_source, epi_version)
                row[f"{start_key}_context"] = context if epi is not None else ""
                if epi is not None:
                    populated_contexts += 1
            if epi_values:
                row["peak_last_10"] = metric(max(epi_values))
                row["average_last_10"] = metric(sum(epi_values) / len(epi_values))
                row["governed_trend"] = trend_from_values(epi_values)
            rows.append(row)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    with SUMMARY.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(
            [
                {"metric": "rows", "value": len(rows)},
                {"metric": "races", "value": len(races)},
                {"metric": "historical_tiles", "value": historical_tiles},
                {"metric": "contexts", "value": populated_contexts},
                {"metric": "source", "value": HISTORICAL_RATING.name},
            ]
        )
    TRACE.write_text(
        "\n".join(
            [
                "EDGEIQ_EPI_WORKSPACE_TERMINAL_FEED_V1",
                f"generated_at={generated_at}",
                f"rows={len(rows)}",
                f"races={len(races)}",
                f"historical_tiles={historical_tiles}",
                f"contexts={populated_contexts}",
                f"catalog={CATALOG.name}",
                f"form_guide={FORM_GUIDE.name}",
                f"historical_rating={HISTORICAL_RATING.name}",
            ]
        ),
        encoding="utf-8",
    )
    return len(rows), len(races), historical_tiles, populated_contexts


if __name__ == "__main__":
    row_count, race_count, tile_count, context_count = build()
    print(
        f"EDGEIQ_EPI_WORKSPACE_TERMINAL_FEED_V1 rows={row_count} races={race_count} "
        f"historical_tiles={tile_count} contexts={context_count}"
    )
