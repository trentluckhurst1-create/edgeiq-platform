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
HISTORICAL_RUN_RATINGS_MASTER = DATA / "edgeiq_historical_run_ratings_master_v1.csv"
HISTORICAL_FINAL_ORCHESTRATOR_V34 = DATA / "edgeiq_historical_epi_final_orchestrator_v34.csv"
HISTORICAL_EXTERNAL_RESULTS_SUPPLEMENT_V37 = DATA / "edgeiq_historical_epi_external_results_supplement_v37.csv"
HISTORICAL_RATEABLE_SUPPLEMENT_V38 = DATA / "edgeiq_historical_epi_rateable_supplement_v38.csv"
HISTORICAL_FINAL_RAW_RECOVERY_V33 = DATA / "edgeiq_historical_epi_final_raw_recovery_v33.csv"
HISTORICAL_ITERATIVE_COMPONENT_V29 = DATA / "edgeiq_historical_epi_iterative_component_convergence_v29.csv"
HISTORICAL_INTEGRATED_CONVERGENCE_V27 = DATA / "edgeiq_historical_epi_integrated_convergence_v27.csv"
HISTORICAL_FINAL_CONVERGENCE_V25 = DATA / "edgeiq_historical_epi_final_convergence_v25.csv"
HISTORICAL_RACE_GRAPH_V24 = DATA / "edgeiq_historical_epi_race_graph_reconstruction_v24.csv"
HISTORICAL_REPOSITORY_SWEEP_V23 = DATA / "edgeiq_historical_epi_repository_sweep_v23.csv"
HISTORICAL_FULL_RACE_RECOVERY_V22 = DATA / "edgeiq_historical_epi_full_race_recovery_v22.csv"
HISTORICAL_LINEAGE_RECOVERY_V20 = DATA / "edgeiq_historical_epi_lineage_recovery_v20.csv"
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
    "SPORTSBETBALLARATSYN": "BALS",
    "BALS": "BALS",

    # Other Victorian tracks
    "WARRNAMBOOL": "WNBL",
    "WNBL": "WNBL",
    "WERRIBEE": "WERR",
    "PICKLEBETPARKWERRIBEE": "WERR",
    "WERR": "WERR",
    "BAIRNSDALE": "BAIR",
    "BET365BAIRNSDALE": "BAIR",
    "BAIR": "BAIR",
    "YARRAVALLEY": "YVLY",
    "BET365YARRAVALLEY": "YVLY",
    "YVLY": "YVLY",
    "TRARALGON": "TRAR",
    "BET365TRARALGON": "TRAR",
    "TRAR": "TRAR",
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
    "MOUNTGAMBIER": "MTG",
    "MTGAMBIER": "MTG",
    "MTG": "MTG",
    "HAWKESBURY": "HAWK",
    "HAWK": "HAWK",
    "WYONG": "WYNG",
    "WYNG": "WYNG",
    "KEMBLAGRANGE": "KGR",
    "KGR": "KGR",
    "WODONGA": "WOD",
    "WOD": "WOD",
    "MUSWELLBROOK": "MUSW",
    "MUSW": "MUSW",
    "CANBERRA": "CANB",
    "CANB": "CANB",
    "ORANGE": "ORAN",
    "ORAN": "ORAN",
    "GOSFORD": "GOSF",
    "GOSF": "GOSF",
    "HANGINGROCK": "HROK",
    "HROK": "HROK",
    "LEETON": "LEET",
    "LEET": "LEET",
    "COROWA": "CORO",
    "CORO": "CORO",
    "NARACOORTE": "NARA",
    "NARA": "NARA",
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

    # EDGEIQ_GOVERNED_HISTORICAL_EPI_MASTER_FALLBACK_V5
    # V6.1 remains first authority. Master fills only exact keys absent from V6.1.
    for row in read_csv_rows(HISTORICAL_RUN_RATINGS_MASTER) or []:
        horse = runner_match_key(row.get("horse"))
        date = clean(row.get("race_date"))
        track = canonical_track(row.get("track"))
        distance = number_text(row.get("distance"))
        key = (horse, date, track, distance)

        if key not in required_keys:
            continue

        existing_rows = grouped.get(key, [])
        existing_has_rating = any(
            metric_float(existing.get("performance_rating_v6_1_research")) is not None
            for existing in existing_rows
        )

        if existing_has_rating:
            continue

        if existing_rows:
            grouped.pop(key, None)

        rating = metric_float(row.get("performance_rating"))
        if rating is None:
            continue

        fallback_row = dict(row)
        fallback_row["performance_rating_v6_1_research"] = rating
        fallback_row["source_file"] = (
            "edgeiq_historical_run_ratings_master_v1.csv:performance_rating"
        )
        fallback_row["_edgeiq_epi_master_fallback"] = "1"
        fallback_row["built_at_v6_1_research"] = clean(
            row.get("built_at")
            or row.get("created_at")
            or row.get("as_of_date")
        )
        grouped.setdefault(key, []).append(fallback_row)

    # EDGEIQ_HISTORICAL_EPI_DETERMINISTIC_IDENTITY_RESCUE_V13
    # Governed rescue rules:
    # 1) exact master identity with one unique numeric rating;
    # 2) blank Form Guide distance where horse+date+track has one unique master rating;
    # 3) track mismatch where horse+date+distance has one unique master rating and one unique master track.
    #
    # Existing rated V6.1/grouped evidence always retains priority.
    master_exact: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    master_hdt: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    master_hdd: dict[tuple[str, str, str], list[dict[str, str]]] = {}

    for master_row in read_csv_rows(HISTORICAL_RUN_RATINGS_MASTER) or []:
        master_horse = runner_match_key(master_row.get("horse"))
        master_date = clean(master_row.get("race_date"))
        master_track = canonical_track(master_row.get("track"))
        master_distance = number_text(master_row.get("distance"))
        master_rating = metric_float(master_row.get("performance_rating"))

        if master_rating is None:
            continue

        master_key = (
            master_horse,
            master_date,
            master_track,
            master_distance,
        )

        master_exact.setdefault(master_key, []).append(master_row)
        master_hdt.setdefault(
            (master_horse, master_date, master_track),
            [],
        ).append(master_row)
        master_hdd.setdefault(
            (master_horse, master_date, master_distance),
            [],
        ).append(master_row)

    rescue_counts = {
        "EXACT_MASTER_UNIQUE": 0,
        "BLANK_DISTANCE_UNIQUE": 0,
        "TRACK_MISMATCH_UNIQUE": 0,
    }

    for required_key in sorted(required_keys):
        existing_rows = grouped.get(required_key, [])
        existing_ratings = sorted(
            {
                metric_float(existing.get("performance_rating_v6_1_research"))
                for existing in existing_rows
                if metric_float(
                    existing.get("performance_rating_v6_1_research")
                ) is not None
            }
        )

        # Never override existing numeric governed evidence, including conflicts.
        if existing_ratings:
            continue

        req_horse, req_date, req_track, req_distance = required_key
        candidates = master_exact.get(required_key, [])
        rescue_reason = "EXACT_MASTER_UNIQUE"

        if not candidates and not req_distance:
            candidates = master_hdt.get(
                (req_horse, req_date, req_track),
                [],
            )
            rescue_reason = "BLANK_DISTANCE_UNIQUE"

        if not candidates and req_distance:
            track_candidates = master_hdd.get(
                (req_horse, req_date, req_distance),
                [],
            )

            track_values = sorted(
                {
                    canonical_track(candidate.get("track"))
                    for candidate in track_candidates
                    if canonical_track(candidate.get("track"))
                }
            )

            if len(track_values) == 1:
                candidates = track_candidates
                rescue_reason = "TRACK_MISMATCH_UNIQUE"

        candidate_ratings = sorted(
            {
                metric_float(candidate.get("performance_rating"))
                for candidate in candidates
                if metric_float(candidate.get("performance_rating")) is not None
            }
        )

        if len(candidate_ratings) != 1:
            continue

        selected_rating = candidate_ratings[0]
        selected_rows = [
            candidate
            for candidate in candidates
            if metric_float(candidate.get("performance_rating"))
            == selected_rating
        ]

        if not selected_rows:
            continue

        rescue = dict(selected_rows[0])
        rescue["performance_rating_v6_1_research"] = selected_rating
        rescue["source_file"] = (
            "edgeiq_historical_run_ratings_master_v1.csv:"
            f"performance_rating:{rescue_reason}"
        )
        rescue["_edgeiq_epi_master_fallback"] = "1"
        rescue["built_at_v6_1_research"] = clean(
            rescue.get("built_at")
            or rescue.get("created_at")
            or rescue.get("as_of_date")
        )

        grouped[required_key] = [rescue]
        rescue_counts[rescue_reason] += 1

    print(
        "HISTORICAL_EPI_V13_RESCUE "
        + " ".join(
            f"{key}={value}"
            for key, value in rescue_counts.items()
        )
    )

    # EDGEIQ_HISTORICAL_EPI_LINEAGE_RECOVERY_FALLBACK_V20
    # Exact last-priority fallback for NO_GOVERNED_ROW keys only.
    # Never overrides existing numeric governed evidence or conflict rows.
    lineage_recovery_added = 0

    for lineage_row in read_csv_rows(HISTORICAL_LINEAGE_RECOVERY_V20) or []:
        lineage_key = (
            runner_match_key(lineage_row.get("horse")),
            clean(lineage_row.get("race_date")),
            canonical_track(
                lineage_row.get("canonical_track")
                or lineage_row.get("track")
            ),
            number_text(lineage_row.get("distance")),
        )

        if lineage_key not in required_keys:
            continue

        existing_rows = grouped.get(lineage_key, [])
        existing_ratings = {
            metric_float(existing.get("performance_rating_v6_1_research"))
            for existing in existing_rows
            if metric_float(
                existing.get("performance_rating_v6_1_research")
            ) is not None
        }

        if existing_ratings:
            continue

        lineage_rating = metric_float(lineage_row.get("performance_rating"))
        if lineage_rating is None:
            continue

        fallback = dict(lineage_row)
        fallback["performance_rating_v6_1_research"] = lineage_rating
        fallback["source_file"] = (
            "edgeiq_historical_epi_lineage_recovery_v20.csv:"
            "performance_rating"
        )
        fallback["_edgeiq_epi_master_fallback"] = "1"
        fallback["built_at_v6_1_research"] = clean(lineage_row.get("built_at"))

        grouped[lineage_key] = [fallback]
        lineage_recovery_added += 1

    print(
        f"HISTORICAL_EPI_V20_LINEAGE_RECOVERY_ADDED="
        f"{lineage_recovery_added}"
    )

    # EDGEIQ_HISTORICAL_EPI_FULL_RACE_RECOVERY_FALLBACK_V22
    # Exact last-priority fallback for NO_GOVERNED_ROW keys only.
    # Existing numeric governed evidence and conflicts always retain priority.
    full_race_recovery_added = 0

    for recovery_row in read_csv_rows(HISTORICAL_FULL_RACE_RECOVERY_V22) or []:
        recovery_key = (
            runner_match_key(recovery_row.get("horse")),
            clean(recovery_row.get("race_date")),
            canonical_track(
                recovery_row.get("canonical_track")
                or recovery_row.get("track")
            ),
            number_text(recovery_row.get("distance")),
        )

        if recovery_key not in required_keys:
            continue

        existing_rows = grouped.get(recovery_key, [])
        existing_ratings = {
            metric_float(existing.get("performance_rating_v6_1_research"))
            for existing in existing_rows
            if metric_float(
                existing.get("performance_rating_v6_1_research")
            ) is not None
        }

        if existing_ratings:
            continue

        recovery_rating = metric_float(
            recovery_row.get("performance_rating")
        )

        if recovery_rating is None:
            continue

        fallback = dict(recovery_row)
        fallback["performance_rating_v6_1_research"] = recovery_rating
        fallback["source_file"] = (
            "edgeiq_historical_epi_full_race_recovery_v22.csv:"
            "performance_rating"
        )
        fallback["_edgeiq_epi_master_fallback"] = "1"
        fallback["built_at_v6_1_research"] = clean(
            recovery_row.get("built_at")
        )

        grouped[recovery_key] = [fallback]
        full_race_recovery_added += 1

    print(
        f"HISTORICAL_EPI_V22_FULL_RACE_RECOVERY_ADDED="
        f"{full_race_recovery_added}"
    )

    # EDGEIQ_HISTORICAL_EPI_REPOSITORY_SWEEP_FALLBACK_V23
    repository_sweep_added = 0

    for sweep_row in read_csv_rows(HISTORICAL_REPOSITORY_SWEEP_V23) or []:
        sweep_key = (
            runner_match_key(sweep_row.get("horse")),
            clean(sweep_row.get("race_date")),
            canonical_track(sweep_row.get("canonical_track") or sweep_row.get("track")),
            number_text(sweep_row.get("distance")),
        )

        if sweep_key not in required_keys:
            continue

        sweep_rating = metric_float(sweep_row.get("performance_rating"))
        if sweep_rating is None:
            continue

        original_status = clean(sweep_row.get("original_status"))

        # Normal recovery rows never override numeric governed evidence.
        if original_status != "CONFLICTING_RATINGS":
            existing_rows = grouped.get(sweep_key, [])
            existing_ratings = {
                metric_float(existing.get("performance_rating_v6_1_research"))
                for existing in existing_rows
                if metric_float(existing.get("performance_rating_v6_1_research")) is not None
            }
            if existing_ratings:
                continue

        fallback = dict(sweep_row)
        fallback["performance_rating_v6_1_research"] = sweep_rating
        fallback["source_file"] = (
            "edgeiq_historical_epi_repository_sweep_v23.csv:"
            "performance_rating"
        )
        fallback["_edgeiq_epi_master_fallback"] = "1"
        fallback["built_at_v6_1_research"] = clean(sweep_row.get("built_at"))

        grouped[sweep_key] = [fallback]
        repository_sweep_added += 1

    print(
        f"HISTORICAL_EPI_V23_REPOSITORY_SWEEP_ADDED="
        f"{repository_sweep_added}"
    )

    # EDGEIQ_HISTORICAL_EPI_RACE_GRAPH_FALLBACK_V24
    race_graph_added = 0

    for graph_row in read_csv_rows(HISTORICAL_RACE_GRAPH_V24) or []:
        graph_key = (
            runner_match_key(graph_row.get("horse")),
            clean(graph_row.get("race_date")),
            canonical_track(graph_row.get("canonical_track") or graph_row.get("track")),
            number_text(graph_row.get("distance")),
        )

        if graph_key not in required_keys:
            continue

        graph_rating = metric_float(graph_row.get("performance_rating"))
        if graph_rating is None:
            continue

        original_status = clean(graph_row.get("original_status"))

        if original_status != "CONFLICTING_RATINGS":
            existing_rows = grouped.get(graph_key, [])
            existing_ratings = {
                metric_float(existing.get("performance_rating_v6_1_research"))
                for existing in existing_rows
                if metric_float(existing.get("performance_rating_v6_1_research")) is not None
            }
            if existing_ratings:
                continue

        fallback = dict(graph_row)
        fallback["performance_rating_v6_1_research"] = graph_rating
        fallback["source_file"] = (
            "edgeiq_historical_epi_race_graph_reconstruction_v24.csv:"
            "performance_rating"
        )
        fallback["_edgeiq_epi_master_fallback"] = "1"
        fallback["built_at_v6_1_research"] = clean(graph_row.get("built_at"))

        grouped[graph_key] = [fallback]
        race_graph_added += 1

    print(f"HISTORICAL_EPI_V24_RACE_GRAPH_ADDED={race_graph_added}")

    # EDGEIQ_HISTORICAL_EPI_FINAL_CONVERGENCE_FALLBACK_V25
    final_convergence_added = 0

    for convergence_row in read_csv_rows(HISTORICAL_FINAL_CONVERGENCE_V25) or []:
        convergence_key = (
            runner_match_key(convergence_row.get("horse")),
            clean(convergence_row.get("race_date")),
            canonical_track(
                convergence_row.get("canonical_track")
                or convergence_row.get("track")
            ),
            number_text(convergence_row.get("distance")),
        )

        if convergence_key not in required_keys:
            continue

        convergence_rating = metric_float(
            convergence_row.get("performance_rating")
        )
        if convergence_rating is None:
            continue

        original_status = clean(convergence_row.get("original_status"))

        if original_status != "CONFLICTING_RATINGS":
            existing_rows = grouped.get(convergence_key, [])
            existing_ratings = {
                metric_float(existing.get("performance_rating_v6_1_research"))
                for existing in existing_rows
                if metric_float(
                    existing.get("performance_rating_v6_1_research")
                ) is not None
            }
            if existing_ratings:
                continue

        fallback = dict(convergence_row)
        fallback["performance_rating_v6_1_research"] = convergence_rating
        fallback["source_file"] = (
            "edgeiq_historical_epi_final_convergence_v25.csv:"
            "performance_rating"
        )
        fallback["_edgeiq_epi_master_fallback"] = "1"
        fallback["built_at_v6_1_research"] = clean(
            convergence_row.get("built_at")
        )

        grouped[convergence_key] = [fallback]
        final_convergence_added += 1

    print(
        f"HISTORICAL_EPI_V25_FINAL_CONVERGENCE_ADDED="
        f"{final_convergence_added}"
    )

    # EDGEIQ_HISTORICAL_EPI_INTEGRATED_CONVERGENCE_FALLBACK_V27
    integrated_convergence_added = 0

    for integrated_row in read_csv_rows(HISTORICAL_INTEGRATED_CONVERGENCE_V27) or []:
        integrated_key = (
            runner_match_key(integrated_row.get("horse")),
            clean(integrated_row.get("race_date")),
            canonical_track(
                integrated_row.get("canonical_track")
                or integrated_row.get("track")
            ),
            number_text(integrated_row.get("distance")),
        )

        if integrated_key not in required_keys:
            continue

        existing_rows = grouped.get(integrated_key, [])
        existing_ratings = {
            metric_float(existing.get("performance_rating_v6_1_research"))
            for existing in existing_rows
            if metric_float(
                existing.get("performance_rating_v6_1_research")
            ) is not None
        }

        if existing_ratings:
            continue

        integrated_rating = metric_float(
            integrated_row.get("performance_rating")
        )
        if integrated_rating is None:
            continue

        fallback = dict(integrated_row)
        fallback["performance_rating_v6_1_research"] = integrated_rating
        fallback["source_file"] = (
            "edgeiq_historical_epi_integrated_convergence_v27.csv:"
            "performance_rating"
        )
        fallback["_edgeiq_epi_master_fallback"] = "1"
        fallback["built_at_v6_1_research"] = clean(
            integrated_row.get("built_at")
        )

        grouped[integrated_key] = [fallback]
        integrated_convergence_added += 1

    print(
        f"HISTORICAL_EPI_V27_INTEGRATED_CONVERGENCE_ADDED="
        f"{integrated_convergence_added}"
    )

    # EDGEIQ_HISTORICAL_EPI_ITERATIVE_COMPONENT_FALLBACK_V29
    iterative_component_added = 0

    for iterative_row in read_csv_rows(HISTORICAL_ITERATIVE_COMPONENT_V29) or []:
        iterative_key = (
            runner_match_key(iterative_row.get("horse")),
            clean(iterative_row.get("race_date")),
            canonical_track(
                iterative_row.get("canonical_track")
                or iterative_row.get("track")
            ),
            number_text(iterative_row.get("distance")),
        )

        if iterative_key not in required_keys:
            continue

        existing_rows = grouped.get(iterative_key, [])
        existing_ratings = {
            metric_float(existing.get("performance_rating_v6_1_research"))
            for existing in existing_rows
            if metric_float(
                existing.get("performance_rating_v6_1_research")
            ) is not None
        }

        if existing_ratings:
            continue

        iterative_rating = metric_float(
            iterative_row.get("performance_rating")
        )
        if iterative_rating is None:
            continue

        fallback = dict(iterative_row)
        fallback["performance_rating_v6_1_research"] = iterative_rating
        fallback["source_file"] = (
            "edgeiq_historical_epi_iterative_component_convergence_v29.csv:"
            "performance_rating"
        )
        fallback["_edgeiq_epi_master_fallback"] = "1"
        fallback["built_at_v6_1_research"] = clean(
            iterative_row.get("built_at")
        )

        grouped[iterative_key] = [fallback]
        iterative_component_added += 1

    print(
        f"HISTORICAL_EPI_V29_ITERATIVE_COMPONENT_ADDED="
        f"{iterative_component_added}"
    )

    # EDGEIQ_HISTORICAL_EPI_FINAL_RAW_RECOVERY_V33
    v33_added = 0

    for v33_row in read_csv_rows(HISTORICAL_FINAL_RAW_RECOVERY_V33) or []:
        v33_key = (
            runner_match_key(v33_row.get("horse")),
            clean(v33_row.get("race_date")),
            canonical_track(v33_row.get("canonical_track") or v33_row.get("track")),
            number_text(v33_row.get("distance")),
        )

        if v33_key not in required_keys:
            continue

        existing_rows = grouped.get(v33_key, [])
        existing_ratings = {
            metric_float(existing.get("performance_rating_v6_1_research"))
            for existing in existing_rows
            if metric_float(existing.get("performance_rating_v6_1_research")) is not None
        }

        if existing_ratings:
            continue

        v33_rating = metric_float(v33_row.get("performance_rating"))
        if v33_rating is None:
            continue

        fallback = dict(v33_row)
        fallback["performance_rating_v6_1_research"] = v33_rating
        fallback["source_file"] = (
            "edgeiq_historical_epi_final_raw_recovery_v33.csv:"
            "performance_rating"
        )
        fallback["_edgeiq_epi_master_fallback"] = "1"
        fallback["built_at_v6_1_research"] = clean(v33_row.get("built_at"))

        grouped[v33_key] = [fallback]
        v33_added += 1

    print(f"HISTORICAL_EPI_V33_FINAL_RAW_RECOVERY_ADDED={v33_added}")

    # EDGEIQ_HISTORICAL_EPI_FINAL_ORCHESTRATOR_V34
    v34_added = 0

    for v34_row in read_csv_rows(HISTORICAL_FINAL_ORCHESTRATOR_V34) or []:
        v34_key = (
            runner_match_key(v34_row.get("horse")),
            clean(v34_row.get("race_date")),
            canonical_track(v34_row.get("canonical_track") or v34_row.get("track")),
            number_text(v34_row.get("distance")),
        )

        if v34_key not in required_keys:
            continue

        existing_rows = grouped.get(v34_key, [])
        existing_ratings = {
            metric_float(existing.get("performance_rating_v6_1_research"))
            for existing in existing_rows
            if metric_float(existing.get("performance_rating_v6_1_research")) is not None
        }

        if existing_ratings:
            continue

        v34_rating = metric_float(v34_row.get("performance_rating"))
        if v34_rating is None:
            continue

        fallback = dict(v34_row)
        fallback["performance_rating_v6_1_research"] = v34_rating
        fallback["source_file"] = (
            "edgeiq_historical_epi_final_orchestrator_v34.csv:"
            "performance_rating"
        )
        fallback["_edgeiq_epi_master_fallback"] = "1"
        fallback["built_at_v6_1_research"] = clean(v34_row.get("built_at"))

        grouped[v34_key] = [fallback]
        v34_added += 1

    print(f"HISTORICAL_EPI_V34_FINAL_ORCHESTRATOR_ADDED={v34_added}")

    # EDGEIQ_HISTORICAL_EPI_EXTERNAL_RESULTS_SUPPLEMENT_V37
    # Exact last-priority supplement for current Form Guide historical starts.
    # It only fills keys with no existing numeric governed rating and never
    # weakens the public historical_epi_for_run contract.
    v37_added = 0

    for v37_row in read_csv_rows(HISTORICAL_EXTERNAL_RESULTS_SUPPLEMENT_V37) or []:
        v37_key = (
            runner_match_key(
                v37_row.get("horse")
                or v37_row.get("runner_name")
            ),
            clean(v37_row.get("race_date")),
            canonical_track(v37_row.get("canonical_track") or v37_row.get("track")),
            number_text(v37_row.get("distance")),
        )

        if v37_key not in required_keys:
            continue

        if clean(v37_row.get("validation_status")) != "PASS":
            continue

        if clean(v37_row.get("match_status")) not in {
            "MATCHED",
            "ACCEPTED",
        }:
            continue

        existing_rows = grouped.get(v37_key, [])
        existing_ratings = {
            metric_float(existing.get("performance_rating_v6_1_research"))
            for existing in existing_rows
            if metric_float(existing.get("performance_rating_v6_1_research")) is not None
        }

        if existing_ratings:
            continue

        v37_rating = metric_float(v37_row.get("performance_rating"))
        if v37_rating is None:
            continue

        fallback = dict(v37_row)
        fallback["performance_rating_v6_1_research"] = v37_rating
        fallback["source_file"] = (
            "edgeiq_historical_epi_external_results_supplement_v37.csv:"
            "performance_rating"
        )
        fallback["epi_source"] = fallback["source_file"]
        fallback["built_at_v6_1_research"] = clean(
            v37_row.get("built_at")
            or v37_row.get("retrieved_at")
        )

        grouped[v37_key] = [fallback]
        v37_added += 1

    print(f"HISTORICAL_EPI_V37_EXTERNAL_RESULTS_SUPPLEMENT_ADDED={v37_added}")

    # EDGEIQ_HISTORICAL_EPI_RATEABLE_SUPPLEMENT_V38
    # Targeted suffix-normalized recovery for V37 NO_EXACT_RUNNER_EVIDENCE rows.
    # It remains exact-key, does not override any existing numeric governed row,
    # and uses only rows that pass the existing V3 formula requirements.
    v38_added = 0

    for v38_row in read_csv_rows(HISTORICAL_RATEABLE_SUPPLEMENT_V38) or []:
        v38_key = (
            runner_match_key(
                v38_row.get("horse")
                or v38_row.get("runner_name")
            ),
            clean(v38_row.get("race_date")),
            canonical_track(v38_row.get("canonical_track") or v38_row.get("track")),
            number_text(v38_row.get("distance")),
        )

        if v38_key not in required_keys:
            continue

        if clean(v38_row.get("validation_status")) != "PASS":
            continue

        if clean(v38_row.get("match_status")) not in {
            "MATCHED",
            "ACCEPTED",
        }:
            continue

        existing_rows = grouped.get(v38_key, [])
        existing_ratings = {
            metric_float(existing.get("performance_rating_v6_1_research"))
            for existing in existing_rows
            if metric_float(existing.get("performance_rating_v6_1_research")) is not None
        }

        if existing_ratings:
            continue

        v38_rating = metric_float(v38_row.get("performance_rating"))
        if v38_rating is None:
            continue

        fallback = dict(v38_row)
        fallback["performance_rating_v6_1_research"] = v38_rating
        fallback["source_file"] = (
            "edgeiq_historical_epi_rateable_supplement_v38.csv:"
            "performance_rating"
        )
        fallback["epi_source"] = fallback["source_file"]
        fallback["built_at_v6_1_research"] = clean(v38_row.get("built_at"))

        grouped[v38_key] = [fallback]
        v38_added += 1

    print(f"HISTORICAL_EPI_V38_RATEABLE_SUPPLEMENT_ADDED={v38_added}")

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

            is_master_fallback = any(
                clean(row.get("_edgeiq_epi_master_fallback")) == "1"
                for _, row in rated_rows
            )
            fallback_epi_sources = sorted(
                {
                    clean(row.get("epi_source"))
                    for _, row in rated_rows
                    if clean(row.get("epi_source"))
                }
            )

            governed[key] = {
                "status": "UNIQUE" if len(rows) == 1 else "SAME_RATING_MULTIPLE_ROWS",
                "rating": rating,
                "source_files": source_files,
                "built_at": built_values[-1] if built_values else "",
                "match_count": len(rows),
                "epi_source": (
                    fallback_epi_sources[0]
                    if len(fallback_epi_sources) == 1
                    else "edgeiq_historical_run_ratings_master_v1.csv:performance_rating"
                    if is_master_fallback
                    else ""
                ),
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
            clean(result.get("epi_source"))
            or (
                "edgeiq_historical_performance_rating_v6_1_research.csv:"
                "performance_rating_v6_1_research"
                f"{source_suffix}"
            )
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
