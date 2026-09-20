from __future__ import annotations

import copy
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
WORK_RESTORE = ROOT / "work" / "all-runner-epi-restore-v1"
WORK = ROOT / "work" / "all-runner-epi-product-bridge-v1"

FORM_CANDIDATES = [
    ROOT / "public" / "data" / "edgeiq_form_guide_enriched_v2.json",
    ROOT / "dist" / "data" / "edgeiq_form_guide_enriched_v2.json",
]
FORM = next((path for path in FORM_CANDIDATES if path.exists()), FORM_CANDIDATES[0])
EPI = WORK_RESTORE / "edgeiq_epi_performance_fact_v1.csv"
STANDARD = WORK_RESTORE / "edgeiq_standard_time_fact_v1_july26_rebuilt.csv"
WAREHOUSE = ROOT / "docs" / "performance-intelligence" / "warehouse" / "edgeiq_performance_fact_warehouse_v1.csv"
HPR = DATA / "edgeiq_horse_performance_observation_fact_v1.csv"

CANDIDATE = WORK / "edgeiq_form_guide_enriched_v2.ALL_RUNNER_EPI_BRIDGE_CANDIDATE.json"
DETAIL_CSV = WORK / "edgeiq_all_runner_epi_product_bridge_v1_slot_classification.csv"
DETAIL_JSON = WORK / "edgeiq_all_runner_epi_product_bridge_v1_slot_classification.json"
SUMMARY_JSON = WORK / "edgeiq_all_runner_epi_product_bridge_v1_summary.json"
VALIDATION_JSON = WORK / "edgeiq_all_runner_epi_product_bridge_v1_validation.json"
ACCEPTANCE_MD = WORK / "EDGEIQ_ALL_RUNNER_EPI_PRODUCT_BRIDGE_V1_ACCEPTANCE.md"

CERTIFIED_EPI_SHA256 = "EF4FAD0F0A1B10D78CC72CFB62E2CF097AA5F70119AED99C563B9AFB31980F41"

ALIASES = {
    "FLEMINGTON": "FLEM",
    "CAULFIELD": "CAUL",
    "CAULFIELDHEATH": "CAUH",
    "SANDOWN": "SANL",
    "SPORTSBETSANDOWNLAKESIDE": "SANL",
    "SANDOWNLAKESIDE": "SANL",
    "SPORTSBETSANDOWNHILLSIDE": "SANH",
    "SANDOWNHILLSIDE": "SANH",
    "PAKENHAM": "PAKM",
    "SOUTHSIDEPAKENHAM": "PAKM",
    "PAKENHAMSYNTHETIC": "PAKS",
    "SPORTSBETPAKENHAMSYNTHETIC": "PAKS",
    "CRANBOURNE": "CRAN",
    "SOUTHSIDECRANBOURNE": "CRAN",
    "GEELONG": "GEEL",
    "LADBROKESGEELONG": "GEEL",
    "BALLARAT": "BRAT",
    "SPORTSBETBALLARAT": "BRAT",
    "BALLARATSYNTHETIC": "BALS",
    "SPORTSBETBALLARATSYNTHETIC": "BALS",
    "WARRNAMBOOL": "WNBL",
    "WERRIBEE": "WERR",
    "PICKLEBETPARKWERRIBEE": "WERR",
    "MORNINGTON": "MORN",
    "WANGARATTA": "WANG",
    "SPORTSBETWANGARATTA": "WANG",
    "KYNETON": "KYNE",
    "BET365PARKKYNETON": "KYNE",
    "ECHUCA": "ECHA",
    "BET365ECHUCA": "ECHA",
    "SEYMOUR": "SEYM",
    "BET365SEYMOUR": "SEYM",
    "HORSHAM": "HSHM",
    "TERANG": "TER",
    "BET365TERANG": "TER",
    "COLAC": "CLAC",
    "BET365COLAC": "CLAC",
    "DONALD": "DON",
    "TATURA": "TAT",
    "ARARAT": "ARAT",
    "BENDIGO": "BDGO",
    "SALE": "SALE",
    "MOE": "MOE",
    "BENALLA": "BEN",
    "HAMILTON": "HAM",
    "SWANHILL": "SWAN",
    "MILDURA": "MILD",
    "STAWELL": "STAW",
    "CASTERTON": "CAST",
}


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def norm(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper())


def horse_key(value: Any) -> str:
    key = norm(value)
    for suffix in ("AUS", "NZ", "GB", "IRE", "USA", "FR", "JPN"):
        if key.endswith(suffix) and len(key) > len(suffix) + 2:
            return key[: -len(suffix)]
    return key


def track_key(value: Any) -> str:
    key = norm(value)
    return ALIASES.get(key, key)


def track_base(value: Any) -> str:
    key = norm(value)
    key = re.sub(r"^(BET365|SPORTSBET|LADBROKES|TAB|THE)", "", key)
    key = key.replace("RACECOURSE", "").replace("RACING", "").replace("TRACK", "")
    return key


def distance_key(value: Any) -> str:
    match = re.search(r"\d+(?:\.\d+)?", clean(value).replace(",", ""))
    if not match:
        return ""
    parsed = float(match.group(0))
    return str(int(parsed)) if parsed.is_integer() else str(parsed)


def date_key(value: Any) -> str:
    return clean(value).split("T", 1)[0].split(" ", 1)[0]


def race_number_key(value: Any) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def number(value: Any) -> float | None:
    text = re.sub(r"[^0-9.\-]+", "", clean(value))
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def same_number(left: Any, right: Any, tolerance: float = 0.01) -> bool:
    a = number(left)
    b = number(right)
    return a is not None and b is not None and abs(a - b) <= tolerance


def condition_group(value: Any) -> str:
    key = norm(value)
    if "HEAVY" in key:
        return "HEAVY"
    if "SOFT" in key or "SLOW" in key:
        return "SOFT"
    if "GOOD" in key or "FIRM" in key or "FAST" in key:
        return "GOOD"
    if "SYN" in key or "POLY" in key or "TAPETA" in key:
        return "SYNTHETIC"
    return "UNKNOWN"


def surface(row: dict[str, Any]) -> str:
    text = f"{clean(row.get('track'))} {clean(row.get('track_condition'))}".upper()
    return "SYNTHETIC" if re.search(r"SYNTH|POLY|TAPETA", text) else "TURF_OR_UNKNOWN"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def csv_count(path: Path) -> int:
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def require_inputs() -> None:
    missing = [str(p.relative_to(ROOT)) for p in (FORM, EPI, STANDARD, WAREHOUSE, HPR) if not p.exists()]
    if missing:
        raise SystemExit("FAIL_CLOSED_MISSING_INPUTS=" + json.dumps(missing))


def load_epi() -> dict[str, dict[str, str]]:
    with EPI.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        return {clean(row["canonical_performance_id"]): row for row in csv.DictReader(handle)}


def load_standard_keys() -> set[tuple[str, str, str, str, str]]:
    keys: set[tuple[str, str, str, str, str]] = set()
    with STANDARD.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle):
            keys.add(
                (
                    clean(row.get("canonical_track_id")),
                    distance_key(row.get("distance_metres")),
                    norm(row.get("track_condition_group")),
                    clean(row.get("jurisdiction")) or "VIC",
                    clean(row.get("surface")) or "TURF_OR_UNKNOWN",
                )
            )
    return keys


def compact_warehouse_row(row: dict[str, str], epi_row: dict[str, str] | None = None) -> dict[str, Any]:
    source_key = clean(row.get("source_record_key")).split("|")
    return {
        **row,
        "_horse_key": horse_key(source_key[-1] if source_key else ""),
        "_date": date_key(row.get("race_date")),
        "_track": track_key(row.get("track")),
        "_track_base": track_base(row.get("track")),
        "_distance": distance_key(row.get("distance_metres")),
        "_race_number": race_number_key(row.get("race_number")),
        "_epi": epi_row,
    }


def load_warehouse(epi: dict[str, dict[str, str]]) -> dict[str, Any]:
    indexes: dict[str, defaultdict[Any, list[dict[str, Any]]]] = {
        "all_exact": defaultdict(list),
        "epi_exact": defaultdict(list),
        "all_race": defaultdict(list),
        "epi_race": defaultdict(list),
        "all_horse": defaultdict(list),
        "epi_horse": defaultdict(list),
        "epi_hdd": defaultdict(list),
        "epi_hdt": defaultdict(list),
        "epi_htd": defaultdict(list),
        "epi_hd": defaultdict(list),
        "epi_hdr": defaultdict(list),
    }
    rows = 0
    warehouse_track_keys: set[str] = set()
    with WAREHOUSE.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        for raw in csv.DictReader(handle):
            rows += 1
            pid = clean(raw.get("canonical_performance_id"))
            row = compact_warehouse_row(raw, epi.get(pid))
            warehouse_track_keys.add(row["_track"])
            h = row["_horse_key"]
            exact = (h, row["_date"], row["_track"], row["_distance"])
            race = (h, row["_date"], row["_track"], row["_race_number"])
            indexes["all_exact"][exact].append(row)
            indexes["all_race"][race].append(row)
            indexes["all_horse"][h].append(row)
            if pid in epi:
                indexes["epi_exact"][exact].append(row)
                indexes["epi_race"][race].append(row)
                indexes["epi_horse"][h].append(row)
                indexes["epi_hdd"][(h, row["_date"], row["_distance"])].append(row)
                indexes["epi_hdt"][(h, row["_date"], row["_track"])].append(row)
                indexes["epi_htd"][(h, row["_track"], row["_distance"])].append(row)
                indexes["epi_hd"][(h, row["_date"])].append(row)
                indexes["epi_hdr"][(h, row["_date"], row["_race_number"])].append(row)
    indexes["warehouse_rows"] = rows  # type: ignore[assignment]
    indexes["warehouse_track_keys"] = warehouse_track_keys  # type: ignore[assignment]
    return indexes


def no_epi_reason(row: dict[str, Any], standard_keys: set[tuple[str, str, str, str, str]]) -> str:
    key = (
        clean(row.get("canonical_track_id")),
        distance_key(row.get("distance_metres")),
        condition_group(row.get("track_condition_group") or row.get("track_condition")),
        clean(row.get("jurisdiction")) or "VIC",
        surface(row),
    )
    if key not in standard_keys:
        return "LEGITIMATE_NO_EPI_UNMATCHED_BENCHMARK"
    if not clean(row.get("official_race_time_seconds")) or not clean(row.get("finish_margin")):
        return "LEGITIMATE_NO_EPI_INVALID_CALCULATION"
    if not clean(row.get("canonical_race_id")) or not clean(row.get("canonical_performance_id")):
        return "LEGITIMATE_NO_EPI_INVALID_CALCULATION"
    return "OTHER_GOVERNED_BLANK"


def has_hard_conflict(run: dict[str, Any], row: dict[str, Any]) -> bool:
    form_race = race_number_key(run.get("raceNumber"))
    if form_race and row["_race_number"] and form_race != row["_race_number"]:
        return True
    if clean(run.get("position")) and not same_number(run.get("position"), row.get("finish_position")):
        return True
    if clean(run.get("margin")) and not same_number(run.get("margin"), row.get("finish_margin"), 0.05):
        return True
    return False


def evidence_text(run: dict[str, Any], row: dict[str, Any], mode: str) -> str:
    evidence = [mode, "horse_name_exact_candidate"]
    if date_key(run.get("date")) == row["_date"]:
        evidence.append("date_exact")
    if track_key(run.get("track")) == row["_track"]:
        evidence.append("canonical_track_exact")
    elif track_base(run.get("track")) and track_base(run.get("track")) in row["_track_base"]:
        evidence.append("track_base_contains_form_track")
    if distance_key(run.get("distance")) and distance_key(run.get("distance")) == row["_distance"]:
        evidence.append("distance_exact")
    elif not distance_key(run.get("distance")):
        evidence.append("form_distance_missing_recovered_from_unique_race")
    if race_number_key(run.get("raceNumber")) and race_number_key(run.get("raceNumber")) == row["_race_number"]:
        evidence.append("race_number_exact")
    if clean(run.get("position")) and same_number(run.get("position"), row.get("finish_position")):
        evidence.append("finish_position_exact")
    if clean(run.get("margin")) and same_number(run.get("margin"), row.get("finish_margin"), 0.05):
        evidence.append("finish_margin_exact")
    return "|".join(evidence)


def historical_epi_payload(row: dict[str, Any], state: str) -> dict[str, Any]:
    epi = row["_epi"] or {}
    return {
        "value": number(epi.get("epi_value")),
        "source": "edgeiq_epi_performance_fact_v1.csv:epi_value",
        "version": "ALL_RUNNER_EPI_RESTORE_V1",
        "asAt": None,
        "status": state,
        "canonicalPerformanceId": clean(row.get("canonical_performance_id")),
        "canonicalRaceId": clean(row.get("canonical_race_id")),
        "canonicalHorseId": clean(row.get("canonical_horse_id")),
        "methodology": clean(epi.get("epi_methodology")),
        "weightAdjustmentStatus": clean(epi.get("weight_adjustment_status")),
        "weightAdjustmentMethodology": clean(epi.get("weight_adjustment_methodology")),
    }


def deterministic_representation_match(
    h: str,
    dt: str,
    tr: str,
    d: str,
    rn: str,
    run: dict[str, Any],
    indexes: dict[str, Any],
) -> tuple[dict[str, Any] | None, str, str]:
    if not d and rn:
        candidates = indexes["epi_race"].get((h, dt, tr, rn), [])
        if len(candidates) == 1 and not has_hard_conflict(run, candidates[0]):
            return candidates[0], "CERTIFIED_EPI_DETERMINISTIC_REPRESENTATION_MATCH", "FORM_DISTANCE_MISSING_UNIQUE_RACE"

    track_candidates = indexes["epi_hdd"].get((h, dt, d), []) if d else []
    if len(track_candidates) == 1:
        row = track_candidates[0]
        form_base = track_base(run.get("track"))
        row_base = row["_track_base"]
        synthetic_abbrev = form_base.endswith("SYN") and row_base == f"{form_base}THETIC"
        if synthetic_abbrev and not has_hard_conflict(run, row):
            return row, "CERTIFIED_EPI_DETERMINISTIC_REPRESENTATION_MATCH", "TRACK_SYN_ABBREVIATION_TO_SYNTHETIC"

    if not d and rn:
        candidates = indexes["epi_hdr"].get((h, dt, rn), [])
        candidates = [row for row in candidates if track_base(run.get("track")) and track_base(run.get("track")) in row["_track_base"]]
        if len(candidates) == 1 and not has_hard_conflict(run, candidates[0]):
            return candidates[0], "CERTIFIED_EPI_DETERMINISTIC_REPRESENTATION_MATCH", "TRACK_LAYOUT_AND_DISTANCE_MISSING_UNIQUE_RACE"

    return None, "", ""


def classify_slot(
    h: str,
    run: dict[str, Any],
    indexes: dict[str, Any],
    standard_keys: set[tuple[str, str, str, str, str]],
) -> tuple[str, dict[str, Any] | None, str, str]:
    dt = date_key(run.get("date"))
    tr = track_key(run.get("track"))
    d = distance_key(run.get("distance"))
    rn = race_number_key(run.get("raceNumber"))
    exact = (h, dt, tr, d)
    race = (h, dt, tr, rn)

    exact_epi = indexes["epi_exact"].get(exact, [])
    if len(exact_epi) == 1:
        return "CERTIFIED_EPI_UNIQUE_MATCH", exact_epi[0], "DIRECT_EXACT_HORSE_DATE_TRACK_DISTANCE", evidence_text(run, exact_epi[0], "direct")
    if len(exact_epi) > 1:
        values = {clean(row["_epi"].get("epi_value")) for row in exact_epi if row.get("_epi")}
        if len(values) > 1:
            return "CONFLICTING_EPI", None, "MULTIPLE_CERTIFIED_EPI_VALUES", ""
        return "AMBIGUOUS_MATCH", None, "MULTIPLE_CERTIFIED_ROWS_SAME_EPI", ""

    rep_row, rep_state, rep_reason = deterministic_representation_match(h, dt, tr, d, rn, run, indexes)
    if rep_row:
        return rep_state, rep_row, rep_reason, evidence_text(run, rep_row, rep_reason)

    exact_all = indexes["all_exact"].get(exact, [])
    no_epi_exact = [row for row in exact_all if not row.get("_epi")]
    if no_epi_exact:
        reasons = {no_epi_reason(row, standard_keys) for row in no_epi_exact}
        state = sorted(reasons)[0] if len(reasons) == 1 else "OTHER_GOVERNED_BLANK"
        return state, no_epi_exact[0], "PHYSICAL_WAREHOUSE_RUN_NOT_CERTIFIED_EPI", evidence_text(run, no_epi_exact[0], "blank_exact")

    if not d and rn:
        race_all = indexes["all_race"].get(race, [])
        no_epi_race = [row for row in race_all if not row.get("_epi")]
        if len(no_epi_race) == 1 and not has_hard_conflict(run, no_epi_race[0]):
            state = no_epi_reason(no_epi_race[0], standard_keys)
            return state, no_epi_race[0], "PHYSICAL_WAREHOUSE_RUN_DISTANCE_MISSING_NOT_CERTIFIED_EPI", evidence_text(run, no_epi_race[0], "blank_distance_missing")
        if len(no_epi_race) > 1:
            return "AMBIGUOUS_MATCH", None, "MULTIPLE_WAREHOUSE_ROWS_FOR_DISTANCE_MISSING_RACE", ""

    date_conflict = indexes["epi_htd"].get((h, tr, d), []) if d else []
    if date_conflict:
        return "SOURCE_HISTORY_MISMATCH_DATE_CONFLICT", None, "CERTIFIED_EPI_ONLY_ON_DIFFERENT_DATE_NO_DATE_TOLERANCE", ""

    same_date = indexes["epi_hd"].get((h, dt), [])
    if same_date:
        return "SOURCE_HISTORY_MISMATCH_REPRESENTATION_UNPROVEN", None, "SAME_HORSE_DATE_BUT_TRACK_OR_DISTANCE_UNPROVEN", ""

    warehouse_horse = indexes["all_horse"].get(h, [])
    epi_horse = indexes["epi_horse"].get(h, [])
    known_tracks = {row["_track"] for row in indexes["all_horse"].get(h, [])}
    if tr not in indexes["warehouse_track_keys"]:
        return "OUTSIDE_WAREHOUSE_SOURCE_COVERAGE", None, "FORM_TRACK_NOT_PRESENT_IN_CERTIFIED_WAREHOUSE_TRACK_UNIVERSE", ""
    if epi_horse:
        return "SOURCE_HISTORY_MISMATCH", None, "HORSE_HAS_CERTIFIED_EPI_OTHER_RUNS_BUT_REQUESTED_RUN_NOT_PRESENT", ""
    if warehouse_horse:
        if known_tracks and tr not in known_tracks:
            return "OUTSIDE_WAREHOUSE_SOURCE_COVERAGE", None, "HORSE_IN_WAREHOUSE_OTHER_RUNS_ONLY_REQUESTED_TRACK_OUTSIDE_HORSE_COVERAGE", ""
        return "OTHER_GOVERNED_BLANK", None, "HORSE_IN_WAREHOUSE_OTHER_RUNS_ONLY", ""
    return "IDENTITY_UNRESOLVED", None, "HORSE_NOT_PRESENT_WAREHOUSE_NO_DURABLE_IDENTITY_BRIDGE", ""


def iter_slots(payload: dict[str, Any]):
    for race_index, race in enumerate(payload.get("races", []) or []):
        for runner_index, runner in enumerate(race.get("runners", []) or []):
            for run_index, run in enumerate(runner.get("fullForm", []) or []):
                yield race_index, runner_index, run_index, race, runner, run


def validate_candidate(original: dict[str, Any], candidate: dict[str, Any], matched_paths: set[tuple[int, int, int]]) -> dict[str, Any]:
    input_slots = sum(1 for _ in iter_slots(original))
    output_slots = sum(1 for _ in iter_slots(candidate))
    unrelated_changes: list[str] = []
    for race_index, runner_index, run_index, _race, _runner, original_run in iter_slots(original):
        candidate_run = candidate["races"][race_index]["runners"][runner_index]["fullForm"][run_index]
        original_other = {k: v for k, v in original_run.items() if k != "historicalEpi"}
        candidate_other = {k: v for k, v in candidate_run.items() if k != "historicalEpi"}
        if original_other != candidate_other:
            unrelated_changes.append(f"races[{race_index}].runners[{runner_index}].fullForm[{run_index}]")
        if (race_index, runner_index, run_index) not in matched_paths and original_run.get("historicalEpi") != candidate_run.get("historicalEpi"):
            unrelated_changes.append(f"unexpected_historicalEpi_change[{race_index},{runner_index},{run_index}]")

    populated = 0
    blanks = 0
    for *_prefix, run in iter_slots(candidate):
        hist = run.get("historicalEpi")
        if isinstance(hist, dict) and hist.get("value") is not None:
            populated += 1
        else:
            blanks += 1

    return {
        "status": "PASS" if input_slots == output_slots and not unrelated_changes else "FAIL",
        "input_form_historical_slots": input_slots,
        "output_form_historical_slots": output_slots,
        "historical_epi_populated": populated,
        "historical_epi_blank": blanks,
        "populated_plus_blank": populated + blanks,
        "unrelated_value_changes": unrelated_changes[:25],
        "unrelated_value_change_count": len(unrelated_changes),
    }


def main() -> None:
    require_inputs()
    WORK.mkdir(parents=True, exist_ok=True)

    pre_hashes = {
        "production_form_guide_sha256": file_sha256(FORM),
        "certified_epi_sha256": file_sha256(EPI),
        "warehouse_sha256": file_sha256(WAREHOUSE),
        "hpr_sha256": file_sha256(HPR),
    }
    if pre_hashes["certified_epi_sha256"].upper() != CERTIFIED_EPI_SHA256:
        raise SystemExit("FAIL_CLOSED_CERTIFIED_EPI_HASH_MISMATCH=" + pre_hashes["certified_epi_sha256"])

    epi = load_epi()
    standard_keys = load_standard_keys()
    indexes = load_warehouse(epi)
    original = json.loads(FORM.read_text(encoding="utf-8", errors="replace"))
    candidate = copy.deepcopy(original)

    detail_rows: list[dict[str, Any]] = []
    matched_paths: set[tuple[int, int, int]] = set()
    trace_ids: set[str] = set()
    populated_trace_count = 0

    for race_index, runner_index, run_index, race, runner, run in iter_slots(original):
        h = horse_key(runner.get("runnerName"))
        state, row, reason, evidence = classify_slot(h, run, indexes, standard_keys)
        if state in {"CERTIFIED_EPI_UNIQUE_MATCH", "CERTIFIED_EPI_DETERMINISTIC_REPRESENTATION_MATCH"}:
            if row is None or not row.get("_epi"):
                raise SystemExit("FAIL_CLOSED_POPULATED_WITHOUT_CERTIFIED_EPI")
            candidate["races"][race_index]["runners"][runner_index]["fullForm"][run_index]["historicalEpi"] = historical_epi_payload(row, state)
            matched_paths.add((race_index, runner_index, run_index))
            trace_ids.add(clean(row.get("canonical_performance_id")))
            if clean(row.get("canonical_performance_id")) in epi:
                populated_trace_count += 1

        detail_rows.append(
            {
                "slot_id": f"race{race_index + 1:03d}_runner{runner_index + 1:02d}_run{run_index + 1:02d}",
                "current_race_date": race.get("raceDate"),
                "current_meeting": race.get("meeting"),
                "current_race_number": race.get("raceNumber"),
                "runner_name": runner.get("runnerName"),
                "form_run_date": date_key(run.get("date")),
                "form_track": clean(run.get("track")),
                "form_track_key": track_key(run.get("track")),
                "form_race_number": race_number_key(run.get("raceNumber")),
                "form_distance": distance_key(run.get("distance")),
                "form_position": clean(run.get("position")),
                "form_margin": clean(run.get("margin")),
                "final_classification": state,
                "governed_reason": reason,
                "evidence": evidence,
                "canonical_performance_id": clean((row or {}).get("canonical_performance_id")),
                "canonical_race_id": clean((row or {}).get("canonical_race_id")),
                "warehouse_track": clean((row or {}).get("track")),
                "warehouse_race_number": clean((row or {}).get("race_number")),
                "warehouse_distance": clean((row or {}).get("distance_metres")),
                "epi_value": clean(((row or {}).get("_epi") or {}).get("epi_value")),
            }
        )

    validation = validate_candidate(original, candidate, matched_paths)
    post_hashes = {
        "production_form_guide_sha256_after": file_sha256(FORM),
        "certified_epi_sha256_after": file_sha256(EPI),
        "warehouse_sha256_after": file_sha256(WAREHOUSE),
        "hpr_sha256_after": file_sha256(HPR),
    }

    counts = Counter(row["final_classification"] for row in detail_rows)
    blank_count = sum(count for state, count in counts.items() if not state.startswith("CERTIFIED_EPI_"))
    populated_count = counts["CERTIFIED_EPI_UNIQUE_MATCH"] + counts["CERTIFIED_EPI_DETERMINISTIC_REPRESENTATION_MATCH"]
    summary = {
        "status": "PASS" if validation["status"] == "PASS" and sum(counts.values()) == 2044 else "FAIL",
        "form_runs": sum(counts.values()),
        "classification_counts": dict(sorted(counts.items())),
        "certified_direct_matches": counts["CERTIFIED_EPI_UNIQUE_MATCH"],
        "certified_deterministic_representation_matches": counts["CERTIFIED_EPI_DETERMINISTIC_REPRESENTATION_MATCH"],
        "total_epi_populated": populated_count,
        "legitimate_governed_blanks": blank_count,
        "identity_unresolved": counts["IDENTITY_UNRESOLVED"],
        "ambiguous_matches": counts["AMBIGUOUS_MATCH"],
        "conflicting_epi": counts["CONFLICTING_EPI"],
        "final_classification_sum": sum(counts.values()),
        "candidate_form_guide": str(CANDIDATE.relative_to(ROOT)),
        "detail_csv": str(DETAIL_CSV.relative_to(ROOT)),
        "detail_json": str(DETAIL_JSON.relative_to(ROOT)),
        "validation": str(VALIDATION_JSON.relative_to(ROOT)),
        "production_changed": pre_hashes["production_form_guide_sha256"] != post_hashes["production_form_guide_sha256_after"],
        "warehouse_changed": pre_hashes["warehouse_sha256"] != post_hashes["warehouse_sha256_after"],
        "certified_epi_changed": pre_hashes["certified_epi_sha256"] != post_hashes["certified_epi_sha256_after"],
        "hpr_changed": pre_hashes["hpr_sha256"] != post_hashes["hpr_sha256_after"],
        "certified_epi_sha256": pre_hashes["certified_epi_sha256"],
        "certified_epi_rows": len(epi),
        "warehouse_rows": indexes["warehouse_rows"],
        "hpr_rows": csv_count(HPR),
        "trace_canonical_performance_ids": len(trace_ids),
    }

    validation.update(
        {
            **pre_hashes,
            **post_hashes,
            "certified_epi_hash_matches_contract": pre_hashes["certified_epi_sha256"].upper() == CERTIFIED_EPI_SHA256,
            "warehouse_unchanged": not summary["warehouse_changed"],
            "certified_epi_unchanged": not summary["certified_epi_changed"],
            "hpr_unchanged": not summary["hpr_changed"],
            "production_unchanged": not summary["production_changed"],
            "zero_conflicting_epi_promoted": counts["CONFLICTING_EPI"] == 0,
            "zero_ambiguous_identity_matches_promoted": counts["AMBIGUOUS_MATCH"] == 0,
            "every_populated_traces_to_certified_canonical_performance_id": populated_trace_count == populated_count,
            "populated_plus_governed_blank_equals_2044": populated_count + blank_count == 2044,
            "candidate_sha256": None,
        }
    )

    CANDIDATE.write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    validation["candidate_sha256"] = file_sha256(CANDIDATE)

    fieldnames = list(detail_rows[0].keys())
    with DETAIL_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(detail_rows)
    DETAIL_JSON.write_text(json.dumps(detail_rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    VALIDATION_JSON.write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")

    acceptance = [
        "# EDGEiQ All-Runner EPI Product Bridge V1 Acceptance",
        "",
        "## Result",
        "",
        f"- Status: {summary['status']}",
        f"- Form Guide historical slots: {summary['form_runs']}",
        f"- Certified direct EPI matches: {summary['certified_direct_matches']}",
        f"- Certified deterministic representation matches: {summary['certified_deterministic_representation_matches']}",
        f"- Total historicalEpi populated in candidate: {summary['total_epi_populated']}",
        f"- Governed blanks: {summary['legitimate_governed_blanks']}",
        f"- Final classification sum: {summary['final_classification_sum']}",
        "",
        "## Governance",
        "",
        "- Certified EPI artifact was read-only and hash-checked against the certified SHA256.",
        "- Warehouse, HPR, and production Form Guide artifacts were not modified.",
        "- Market data was not used as an EPI input.",
        "- No replacement EPI values were calculated.",
        "- No fuzzy horse matching, date tolerance, or distance tolerance was used.",
        "- Deterministic representation matches were limited to source-proven blank distance recovery by unique race, Ballarat SYN to SYNTHETIC spelling, and Sandown layout expansion by unique race.",
        "",
        "## Outputs",
        "",
        f"- Candidate Form Guide: `{summary['candidate_form_guide']}`",
        f"- Slot classification CSV: `{summary['detail_csv']}`",
        f"- Slot classification JSON: `{summary['detail_json']}`",
        f"- Validation JSON: `{summary['validation']}`",
        "",
        "## Classification Counts",
        "",
    ]
    acceptance.extend(f"- {key}: {value}" for key, value in sorted(counts.items()))
    ACCEPTANCE_MD.write_text("\n".join(acceptance) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    if summary["status"] != "PASS":
        raise SystemExit("FAIL_CLOSED_BRIDGE_CANDIDATE_VALIDATION")
    print("EDGEIQ_ALL_RUNNER_EPI_PRODUCT_BRIDGE_CANDIDATE_V1_PASS")


if __name__ == "__main__":
    main()
