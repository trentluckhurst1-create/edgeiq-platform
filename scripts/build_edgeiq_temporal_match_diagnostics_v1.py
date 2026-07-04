from __future__ import annotations

import csv
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from edgeiq_memory_safe_io import stream_csv_rows, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = {
    "validation": DATA / "edgeiq_temporal_physics_validation_v1.csv",
    "results_truth": DATA / "edgeiq_canonical_results_truth_v1.csv",
    "physics": DATA / "edgeiq_real_sectional_physics_features_v1.csv",
    "market_entity": DATA / "edgeiq_canonical_market_entity_graph_v1.csv",
    "fields": DATA / "edgeiq_vic_three_day_race_fields.csv",
}

OUT = DATA / "edgeiq_temporal_match_diagnostics_v1.csv"
SUMMARY = DATA / "edgeiq_temporal_match_diagnostics_summary_v1.csv"
EXAMPLES = DATA / "edgeiq_temporal_match_failure_examples_v1.csv"
REPAIR = DATA / "edgeiq_temporal_match_repair_queue_v1.csv"

DIAGNOSTIC_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "canonical_runner_key",
    "diagnostic_status",
    "match_stage_reached",
    "failure_class",
    "failure_reason",
    "results_candidate_count",
    "sectional_candidate_count",
    "track_normalised",
    "horse_normalised",
    "date_normalised",
    "race_no_normalised",
    "repair_recommendation",
    "repair_priority",
    "notes",
]

EXAMPLE_FIELDS = DIAGNOSTIC_FIELDS

REPAIR_FIELDS = [
    "priority",
    "failure_class",
    "affected_rows",
    "estimated_match_gain",
    "repair_action",
    "required_source",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

TRACK_ALIASES = {
    "BET365 YARRA VALLEY": "YARRA VALLEY",
    "YARRA VALLEY": "YARRA VALLEY",
    "SPORTSBET WANGARATTA": "WANGARATTA",
    "WANGARATTA": "WANGARATTA",
    "SOUTHSIDE PAKENHAM": "PAKENHAM",
    "SPORTSBET PAKENHAM": "PAKENHAM",
    "PAKENHAM SYNTHETIC": "PAKENHAM",
    "PAKENHAM": "PAKENHAM",
    "BALLARAT SYNTHETIC": "BALLARAT",
    "BALLARAT": "BALLARAT",
    "GEELONG SYNTHETIC": "GEELONG",
    "GEELONG": "GEELONG",
    "THE VALLEY": "MOONEE VALLEY",
    "MOONEE VALLEY": "MOONEE VALLEY",
    "SANDOWN HILLSIDE": "SANDOWN",
    "SANDOWN LAKESIDE": "SANDOWN",
    "SANDOWN": "SANDOWN",
    "CAULFIELD HEATH": "CAULFIELD HEATH",
    "CAULFIELD": "CAULFIELD",
    "FLEMINGTON": "FLEMINGTON",
    "CRANBOURNE": "CRANBOURNE",
    "BENDIGO": "BENDIGO",
    "SEYMOUR": "SEYMOUR",
    "WARRNAMBOOL": "WARRNAMBOOL",
    "SALE": "SALE",
    "MORNINGTON": "MORNINGTON",
    "HORSHAM": "HORSHAM",
    "STAWELL": "STAWELL",
}


def clean(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"}:
        return ""
    return text


def normalise_text(value: object) -> str:
    text = clean(value).upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.replace("&", " AND ")
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"['`’‘]", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def compact_text(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", normalise_text(value))


def normalise_track(value: object) -> str:
    track = normalise_text(value)
    track = re.sub(r"\bRACING\b", "", track)
    track = re.sub(r"\bCLUB\b", "", track)
    track = re.sub(r"\s+", " ", track).strip()
    return TRACK_ALIASES.get(track, track)


def normalise_date(value: object) -> str:
    text = clean(value)
    if not text:
        return ""
    text = text.replace("/", "-")
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%m-%y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    match = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return text[:10]


def normalise_race_no(value: object) -> str:
    text = clean(value).upper()
    match = re.search(r"\d+", text)
    return str(int(match.group(0))) if match else ""


def raw_key(row: dict[str, object]) -> str:
    date = clean(row.get("race_date"))
    track = clean(row.get("track")).upper()
    race_no = clean(row.get("race_no")).upper()
    horse = clean(row.get("horse")).upper()
    return f"{date}|{track}|{race_no}|{horse}" if date and track and race_no and horse else ""


def race_key(row: dict[str, object]) -> str:
    date = normalise_date(row.get("race_date"))
    track = normalise_track(row.get("track"))
    race_no = normalise_race_no(row.get("race_no"))
    return f"{date}|{track}|{race_no}" if date and track and race_no else ""


def canonical_runner_key(row: dict[str, object]) -> str:
    supplied = clean(row.get("canonical_runner_key"))
    if supplied and supplied.count("|") >= 3:
        parts = supplied.split("|")
        return f"{normalise_date(parts[0])}|{normalise_track(parts[1])}|{normalise_race_no(parts[2])}|{normalise_text(parts[3])}"
    key = race_key(row)
    horse = normalise_text(row.get("horse"))
    return f"{key}|{horse}" if key and horse else ""


def date_track_key(row: dict[str, object]) -> str:
    date = normalise_date(row.get("race_date"))
    track = normalise_track(row.get("track"))
    return f"{date}|{track}" if date and track else ""


def date_track_horse_key(row: dict[str, object]) -> str:
    key = date_track_key(row)
    horse = normalise_text(row.get("horse"))
    return f"{key}|{horse}" if key and horse else ""


def track_race_horse_key(row: dict[str, object]) -> str:
    track = normalise_track(row.get("track"))
    race_no = normalise_race_no(row.get("race_no"))
    horse = normalise_text(row.get("horse"))
    return f"{track}|{race_no}|{horse}" if track and race_no and horse else ""


def date_race_horse_key(row: dict[str, object]) -> str:
    date = normalise_date(row.get("race_date"))
    race_no = normalise_race_no(row.get("race_no"))
    horse = normalise_text(row.get("horse"))
    return f"{date}|{race_no}|{horse}" if date and race_no and horse else ""


def race_horse_compact_key(row: dict[str, object]) -> str:
    key = race_key(row)
    horse = compact_text(row.get("horse"))
    return f"{key}|{horse}" if key and horse else ""


def date_track_race_key(row: dict[str, object]) -> str:
    return race_key(row)


def horse_only_key(row: dict[str, object]) -> str:
    return normalise_text(row.get("horse"))


def yes(value: object) -> bool:
    return clean(value).upper() in {"YES", "Y", "TRUE", "1", "SAFE", "TRUSTED_RESULT"}


def finish_present(row: dict[str, object]) -> bool:
    text = clean(row.get("finish_position"))
    if not text:
        return False
    try:
        return not math.isnan(float(re.sub(r"[^0-9.\-]", "", text)))
    except ValueError:
        return False


def safe_rows(path: Path):
    if not path.exists():
        return
    try:
        yield from stream_csv_rows(path)
    except Exception:
        return


class Index:
    def __init__(self) -> None:
        self.by_raw: Counter[str] = Counter()
        self.by_runner: Counter[str] = Counter()
        self.by_safe_runner: Counter[str] = Counter()
        self.by_race: Counter[str] = Counter()
        self.by_date_track_horse: Counter[str] = Counter()
        self.by_track_race_horse: Counter[str] = Counter()
        self.by_date_race_horse: Counter[str] = Counter()
        self.by_compact_runner: Counter[str] = Counter()
        self.by_horse: Counter[str] = Counter()
        self.duplicate_runner_keys: set[str] = set()
        self.total_rows = 0

    def add(self, row: dict[str, str], safe_only_counter: bool = False) -> None:
        self.total_rows += 1
        keys = {
            "raw": raw_key(row),
            "runner": canonical_runner_key(row),
            "race": date_track_race_key(row),
            "date_track_horse": date_track_horse_key(row),
            "track_race_horse": track_race_horse_key(row),
            "date_race_horse": date_race_horse_key(row),
            "compact_runner": race_horse_compact_key(row),
            "horse": horse_only_key(row),
        }
        if keys["raw"]:
            self.by_raw[keys["raw"]] += 1
        if keys["runner"]:
            self.by_runner[keys["runner"]] += 1
        if keys["race"]:
            self.by_race[keys["race"]] += 1
        if keys["date_track_horse"]:
            self.by_date_track_horse[keys["date_track_horse"]] += 1
        if keys["track_race_horse"]:
            self.by_track_race_horse[keys["track_race_horse"]] += 1
        if keys["date_race_horse"]:
            self.by_date_race_horse[keys["date_race_horse"]] += 1
        if keys["compact_runner"]:
            self.by_compact_runner[keys["compact_runner"]] += 1
        if keys["horse"]:
            self.by_horse[keys["horse"]] += 1
        if safe_only_counter and keys["runner"]:
            self.by_safe_runner[keys["runner"]] += 1

    def finalise(self) -> None:
        self.duplicate_runner_keys = {key for key, count in self.by_runner.items() if key and count > 1}


def build_results_index() -> Index:
    index = Index()
    for row in safe_rows(INPUTS["results_truth"]):
        index.add(row, safe_only_counter=yes(row.get("safe_for_model_validation")) and finish_present(row))
    index.finalise()
    return index


def build_sectional_index() -> Index:
    index = Index()
    for row in safe_rows(INPUTS["physics"]):
        index.add(row)
    index.finalise()
    return index


def failure_metadata(failure_class: str, affected_rows: int = 0) -> tuple[str, str, str, str]:
    if failure_class in {"TRACK_ALIAS_MISMATCH", "HORSE_NORMALISATION_MISMATCH", "SAFE_RESULTS_AVAILABLE_BUT_NOT_LINKED", "DUPLICATE_RUNNER_KEYS"}:
        priority = "HIGH"
    elif failure_class in {"PARTIAL_MATCH_ONLY", "DATE_MISMATCH", "RACE_NO_MISMATCH"}:
        priority = "MEDIUM"
    elif failure_class == "SUCCESSFUL_MATCH":
        priority = "LOW"
    else:
        priority = "LOW"

    actions = {
        "NO_RESULTS_ROW": "Backfill settled results truth for this race/runner; do not infer finish positions.",
        "NO_SECTIONAL_ROW": "Reconcile temporal validation source back to real sectional physics source lineage.",
        "TRACK_ALIAS_MISMATCH": "Add or correct track alias mapping, then rebuild canonical results and temporal validation.",
        "HORSE_NORMALISATION_MISMATCH": "Improve horse alias/normalisation rules and rerun canonical result joins.",
        "DATE_MISMATCH": "Audit race_date lineage between sectional and results sources.",
        "RACE_NO_MISMATCH": "Audit race number lineage and source race identifiers.",
        "DUPLICATE_RUNNER_KEYS": "Resolve duplicate canonical runner keys before trusting validation joins.",
        "PARTIAL_MATCH_ONLY": "Review partial candidates manually; do not promote until race and horse identity agree.",
        "MISSING_CANONICAL_KEY": "Repair missing date/track/race/horse fields before attempting result linkage.",
        "SAFE_RESULTS_AVAILABLE_BUT_NOT_LINKED": "Rerun temporal validation against canonical results truth; safe result exists but validation row is stale.",
        "SUCCESSFUL_MATCH": "No repair required.",
    }
    sources = {
        "NO_RESULTS_ROW": "edgeiq_canonical_results_truth_v1.csv",
        "NO_SECTIONAL_ROW": "edgeiq_real_sectional_physics_features_v1.csv",
        "TRACK_ALIAS_MISMATCH": "track alias engine and canonical results truth",
        "HORSE_NORMALISATION_MISMATCH": "horse alias engine and canonical results truth",
        "DATE_MISMATCH": "sectional lineage and results truth race dates",
        "RACE_NO_MISMATCH": "sectional lineage and results truth race numbers",
        "DUPLICATE_RUNNER_KEYS": "canonical results truth duplicate diagnostics",
        "PARTIAL_MATCH_ONLY": "canonical results truth plus sectional identity diagnostics",
        "MISSING_CANONICAL_KEY": "temporal validation row identity fields",
        "SAFE_RESULTS_AVAILABLE_BUT_NOT_LINKED": "temporal physics validation engine",
        "SUCCESSFUL_MATCH": "none",
    }
    estimated = str(affected_rows if failure_class != "NO_RESULTS_ROW" else 0)
    return priority, estimated, actions.get(failure_class, "Inspect diagnostic examples."), sources.get(failure_class, "research identity sources")


def diagnose_row(row: dict[str, str], results: Index, sectionals: Index) -> dict[str, object]:
    runner = canonical_runner_key(row)
    raw = raw_key(row)
    race = date_track_race_key(row)
    compact = race_horse_compact_key(row)
    date_track_horse = date_track_horse_key(row)
    track_race_horse = track_race_horse_key(row)
    date_race_horse = date_race_horse_key(row)
    horse = horse_only_key(row)

    results_exact = results.by_runner.get(runner, 0)
    results_safe = results.by_safe_runner.get(runner, 0)
    sectionals_exact = sectionals.by_runner.get(runner, 0)

    diagnostic_status = "FAILED"
    stage = "1_RAW_KEY"
    failure_class = "NO_RESULTS_ROW"
    reason = "No canonical settled results row matched this temporal runner."

    if not runner:
        failure_class = "MISSING_CANONICAL_KEY"
        stage = "1_RAW_KEY"
        reason = "Could not reconstruct canonical runner key from race_date, track, race_no and horse."
    elif sectionals_exact <= 0:
        failure_class = "NO_SECTIONAL_ROW"
        stage = "6_CANONICAL_RUNNER_KEY"
        reason = "Temporal validation row did not map back to a real sectional physics row."
    elif results.by_runner.get(runner, 0) > 1 or runner in results.duplicate_runner_keys:
        failure_class = "DUPLICATE_RUNNER_KEYS"
        stage = "6_CANONICAL_RUNNER_KEY"
        reason = "Multiple canonical results rows share the same reconstructed runner key."
    elif finish_present(row):
        diagnostic_status = "SUCCESS"
        failure_class = "SUCCESSFUL_MATCH"
        stage = "8_VALIDATED_MATCH"
        reason = "Temporal validation row already contains a settled finish position."
    elif results_safe > 0:
        failure_class = "SAFE_RESULTS_AVAILABLE_BUT_NOT_LINKED"
        stage = "7_SAFE_RESULTS_LINK"
        reason = "Canonical results truth has a safe settled result for this runner, but temporal validation did not link it."
    elif results_exact > 0:
        failure_class = "PARTIAL_MATCH_ONLY"
        stage = "6_CANONICAL_RUNNER_KEY"
        reason = "A results row exists for the canonical runner, but no safe settled finish position is available."
    elif raw and results.by_raw.get(raw, 0) > 0:
        failure_class = "PARTIAL_MATCH_ONLY"
        stage = "1_RAW_KEY"
        reason = "Raw identity matched a result row, but canonical safe result linkage did not complete."
    elif compact and results.by_compact_runner.get(compact, 0) > 0:
        failure_class = "HORSE_NORMALISATION_MISMATCH"
        stage = "5_HORSE_NORMALISATION"
        reason = "Race key and compact horse text found candidates; normalised horse key did not align."
    elif date_race_horse and results.by_date_race_horse.get(date_race_horse, 0) > 0:
        failure_class = "TRACK_ALIAS_MISMATCH"
        stage = "2_TRACK_NORMALISATION"
        reason = "Date, race number and horse matched results candidates, but track did not align."
    elif track_race_horse and results.by_track_race_horse.get(track_race_horse, 0) > 0:
        failure_class = "DATE_MISMATCH"
        stage = "3_DATE_NORMALISATION"
        reason = "Track, race number and horse matched results candidates, but date did not align."
    elif date_track_horse and results.by_date_track_horse.get(date_track_horse, 0) > 0:
        failure_class = "RACE_NO_MISMATCH"
        stage = "4_RACE_NO_NORMALISATION"
        reason = "Date, track and horse matched results candidates, but race number did not align."
    elif race and results.by_race.get(race, 0) > 0:
        failure_class = "HORSE_NORMALISATION_MISMATCH"
        stage = "5_HORSE_NORMALISATION"
        reason = "Race exists in results truth, but this horse did not match the settled result field."
    elif horse and results.by_horse.get(horse, 0) > 0:
        failure_class = "PARTIAL_MATCH_ONLY"
        stage = "5_HORSE_NORMALISATION"
        reason = "Horse exists somewhere in results truth, but not with matching date, track and race number."

    priority, _, action, _ = failure_metadata(failure_class)
    if failure_class == "SUCCESSFUL_MATCH":
        diagnostic_status = "SUCCESS"
    elif failure_class in {"TRACK_ALIAS_MISMATCH", "HORSE_NORMALISATION_MISMATCH", "DATE_MISMATCH", "RACE_NO_MISMATCH", "PARTIAL_MATCH_ONLY", "SAFE_RESULTS_AVAILABLE_BUT_NOT_LINKED"}:
        diagnostic_status = "REPAIRABLE"

    return {
        "race_date": clean(row.get("race_date")),
        "track": clean(row.get("track")),
        "race_no": clean(row.get("race_no")),
        "horse": clean(row.get("horse")),
        "canonical_runner_key": runner,
        "diagnostic_status": diagnostic_status,
        "match_stage_reached": stage,
        "failure_class": failure_class,
        "failure_reason": reason,
        "results_candidate_count": results_exact or results.by_race.get(race, 0) or results.by_horse.get(horse, 0),
        "sectional_candidate_count": sectionals_exact,
        "track_normalised": normalise_track(row.get("track")),
        "horse_normalised": normalise_text(row.get("horse")),
        "date_normalised": normalise_date(row.get("race_date")),
        "race_no_normalised": normalise_race_no(row.get("race_no")),
        "repair_recommendation": action,
        "repair_priority": priority,
        "notes": "Offline temporal match diagnostic only. No modelling, pricing, ratings, or execution impact.",
    }


def build_diagnostics(results: Index, sectionals: Index) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in safe_rows(INPUTS["validation"]):
        rows.append(diagnose_row(row, results, sectionals))
    return rows


def build_examples(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    examples: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    for row in rows:
        klass = clean(row.get("failure_class"))
        if klass == "SUCCESSFUL_MATCH":
            continue
        if counts[klass] >= 10:
            continue
        examples.append(row)
        counts[klass] += 1
    return examples


def build_repair_queue(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    counts = Counter(clean(row.get("failure_class")) for row in rows if clean(row.get("failure_class")) != "SUCCESSFUL_MATCH")
    queue: list[dict[str, object]] = []
    for klass, count in counts.items():
        priority, estimated, action, source = failure_metadata(klass, count)
        if klass == "NO_RESULTS_ROW":
            estimated = "0"
        queue.append(
            {
                "priority": priority,
                "failure_class": klass,
                "affected_rows": count,
                "estimated_match_gain": estimated,
                "repair_action": action,
                "required_source": source,
                "notes": "Repair queue is diagnostic only; no trust thresholds changed and no results are fabricated.",
            }
        )
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    queue.sort(key=lambda item: (priority_order.get(str(item["priority"]), 3), -int(item["affected_rows"]), str(item["failure_class"])))
    return queue


def missing_inputs() -> list[str]:
    return [path.name for path in INPUTS.values() if not path.exists()]


def build_summary(rows: list[dict[str, object]], repair_queue: list[dict[str, object]]) -> list[dict[str, object]]:
    counts = Counter(clean(row.get("failure_class")) for row in rows)
    total = len(rows)
    successful = counts.get("SUCCESSFUL_MATCH", 0)
    failed = total - successful
    rate = 0.0 if total <= 0 else (successful / total) * 100.0
    highest = repair_queue[0]["failure_class"] if repair_queue else ""
    values: list[dict[str, object]] = [
        {"metric": "validation_rows", "value": total},
        {"metric": "successful_matches", "value": successful},
        {"metric": "failed_matches", "value": failed},
        {"metric": "validated_match_rate", "value": f"{rate:.2f}"},
        {"metric": "track_alias_failures", "value": counts.get("TRACK_ALIAS_MISMATCH", 0)},
        {"metric": "horse_normalisation_failures", "value": counts.get("HORSE_NORMALISATION_MISMATCH", 0)},
        {"metric": "date_failures", "value": counts.get("DATE_MISMATCH", 0)},
        {"metric": "race_no_failures", "value": counts.get("RACE_NO_MISMATCH", 0)},
        {"metric": "safe_results_unlinked", "value": counts.get("SAFE_RESULTS_AVAILABLE_BUT_NOT_LINKED", 0)},
        {"metric": "duplicate_key_failures", "value": counts.get("DUPLICATE_RUNNER_KEYS", 0)},
        {"metric": "missing_results_rows", "value": counts.get("NO_RESULTS_ROW", 0)},
        {"metric": "missing_sectional_rows", "value": counts.get("NO_SECTIONAL_ROW", 0)},
        {"metric": "partial_match_only", "value": counts.get("PARTIAL_MATCH_ONLY", 0)},
        {"metric": "highest_leverage_repair", "value": highest},
        {"metric": "research_pipeline_offline_only", "value": "YES"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]
    for klass, count in sorted(counts.items()):
        values.append({"metric": f"failure_class::{klass}", "value": count})
    for filename in missing_inputs():
        values.append({"metric": f"missing_input::{filename}", "value": "YES"})
    return values


def main() -> None:
    results = build_results_index()
    sectionals = build_sectional_index()
    diagnostics = build_diagnostics(results, sectionals)
    examples = build_examples(diagnostics)
    repair_queue = build_repair_queue(diagnostics)
    summary = build_summary(diagnostics, repair_queue)
    write_csv_atomic(OUT, diagnostics, DIAGNOSTIC_FIELDS)
    write_csv_atomic(EXAMPLES, examples, EXAMPLE_FIELDS)
    write_csv_atomic(REPAIR, repair_queue, REPAIR_FIELDS)
    write_csv_atomic(SUMMARY, summary, SUMMARY_FIELDS)
    print(f"Wrote {OUT}")
    print(f"Wrote {SUMMARY}")
    print(f"Wrote {EXAMPLES}")
    print(f"Wrote {REPAIR}")
    print(f"validation_rows={len(diagnostics)} repair_classes={len(repair_queue)}")


if __name__ == "__main__":
    main()
