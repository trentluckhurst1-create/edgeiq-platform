from __future__ import annotations

import csv
import math
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = {
    "validation": DATA / "edgeiq_temporal_physics_validation_v1.csv",
    "temporal_engine": DATA / "edgeiq_temporal_physics_engine_v1.csv",
    "regime_engine": DATA / "edgeiq_temporal_research_regime_engine_v1.csv",
    "results_truth": DATA / "edgeiq_canonical_results_truth_v1.csv",
    "market_entity_graph": DATA / "edgeiq_canonical_market_entity_graph_v1.csv",
}

OUT = DATA / "edgeiq_temporal_identity_memory_v1.csv"
SUMMARY = DATA / "edgeiq_temporal_identity_memory_summary_v1.csv"
WATCHLIST = DATA / "edgeiq_temporal_identity_watchlist_v1.csv"

MEMORY_FIELDS = [
    "horse",
    "horse_key",
    "starts_tracked",
    "validated_result_starts",
    "phase_patterns_seen",
    "dominant_phase_pattern",
    "energy_curve_types_seen",
    "dominant_energy_curve_type",
    "avg_temporal_physics_score",
    "avg_finish_position",
    "wins",
    "places",
    "top4",
    "win_rate",
    "place_rate",
    "top4_rate",
    "temporal_consistency_score",
    "temporal_volatility_score",
    "late_acceleration_repeat_count",
    "collapse_repeat_count",
    "sustain_repeat_count",
    "identity_memory_grade",
    "identity_memory_label",
    "research_status",
    "trusted_for_live_modelling",
    "trusted_for_live_execution",
    "notes",
]

WATCHLIST_FIELDS = [
    "priority",
    "horse",
    "horse_key",
    "starts_tracked",
    "validated_result_starts",
    "dominant_phase_pattern",
    "dominant_energy_curve_type",
    "identity_memory_grade",
    "identity_memory_label",
    "watchlist_reason",
    "research_next_step",
    "trusted_for_live_modelling",
    "trusted_for_live_execution",
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
    "PAKENHAM": "PAKENHAM",
    "PAKENHAM SYNTHETIC": "PAKENHAM",
    "CAULFIELD HEATH": "CAULFIELD HEATH",
    "CAULFIELD": "CAULFIELD",
    "FLEMINGTON": "FLEMINGTON",
    "MOONEE VALLEY": "MOONEE VALLEY",
    "THE VALLEY": "MOONEE VALLEY",
    "SANDOWN": "SANDOWN",
    "SANDOWN HILLSIDE": "SANDOWN",
    "SANDOWN LAKESIDE": "SANDOWN",
    "CRANBOURNE": "CRANBOURNE",
    "BALLARAT": "BALLARAT",
    "BALLARAT SYNTHETIC": "BALLARAT",
    "BENDIGO": "BENDIGO",
    "GEELONG": "GEELONG",
    "GEELONG SYNTHETIC": "GEELONG",
    "SEYMOUR": "SEYMOUR",
    "WARRNAMBOOL": "WARRNAMBOOL",
    "SALE": "SALE",
    "MORNINGTON": "MORNINGTON",
    "HORSHAM": "HORSHAM",
    "STAWELL": "STAWELL",
    "ARARAT": "ARARAT",
}


def clean(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"}:
        return ""
    return text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{int(datetime.now().timestamp() * 1000)}.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def normalise_text(value: object) -> str:
    text = clean(value).upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.replace("&", " AND ")
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"['`’‘]", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalise_track(value: object) -> str:
    track = normalise_text(value)
    track = re.sub(r"\bRACING\b", "", track)
    track = re.sub(r"\bCLUB\b", "", track)
    track = re.sub(r"\s+", " ", track).strip()
    return TRACK_ALIASES.get(track, track)


def normalise_race_no(value: object) -> str:
    text = clean(value).upper()
    match = re.search(r"\d+", text)
    return str(int(match.group(0))) if match else ""


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


def horse_key(value: object) -> str:
    return normalise_text(value)


def canonical_runner_key(row: dict[str, object]) -> str:
    supplied = clean(row.get("canonical_runner_key"))
    if supplied and "|" in supplied:
        return supplied
    race_date = normalise_date(row.get("race_date"))
    track = normalise_track(row.get("track"))
    race_no = normalise_race_no(row.get("race_no"))
    horse = horse_key(row.get("horse"))
    return f"{race_date}|{track}|{race_no}|{horse}" if race_date and track and race_no and horse else ""


def start_key(row: dict[str, object]) -> str:
    key = canonical_runner_key(row)
    if key:
        return key
    return "|".join(
        [
            normalise_date(row.get("race_date")),
            normalise_track(row.get("track")),
            normalise_race_no(row.get("race_no")),
            horse_key(row.get("horse")),
        ]
    )


def to_float(value: object) -> float:
    text = clean(value)
    if not text:
        return math.nan
    try:
        return float(re.sub(r"[^0-9.\-]", "", text))
    except ValueError:
        return math.nan


def to_int(value: object) -> int | None:
    numeric = to_float(value)
    if math.isnan(numeric) or numeric <= 0:
        return None
    return int(round(numeric))


def fmt(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.2f}"


def pct(part: int, whole: int) -> str:
    return "" if whole <= 0 else f"{(part / whole) * 100:.2f}"


def mode(counter: Counter) -> str:
    if not counter:
        return ""
    return counter.most_common(1)[0][0]


def safe_results(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    safe: dict[str, dict[str, str]] = {}
    for row in rows:
        key = canonical_runner_key(row)
        if not key:
            continue
        if clean(row.get("safe_for_model_validation")) != "YES":
            continue
        if not clean(row.get("finish_position")):
            continue
        safe[key] = row
    return safe


def load_inputs() -> tuple[dict[str, list[dict[str, str]]], Counter, list[str]]:
    rows: dict[str, list[dict[str, str]]] = {}
    counts: Counter = Counter()
    missing: list[str] = []
    for name, path in INPUTS.items():
        if not path.exists():
            rows[name] = []
            missing.append(path.name)
            continue
        data = read_csv(path)
        rows[name] = data
        counts[path.name] = len(data)
    return rows, counts, missing


def start_profiles(temporal_rows: list[dict[str, str]], validation_rows: list[dict[str, str]], safe: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    validation_by_start: dict[str, dict[str, str]] = {}
    for row in validation_rows:
        key = start_key(row)
        if key and key not in validation_by_start:
            validation_by_start[key] = row

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in temporal_rows:
        key = start_key(row)
        if key and horse_key(row.get("horse")):
            grouped[key].append(row)

    starts: list[dict[str, object]] = []
    for key, rows in grouped.items():
        first = rows[0]
        patterns = Counter(clean(row.get("phase_transition_pattern")) or "UNKNOWN" for row in rows)
        curves = Counter(clean(row.get("energy_curve_type")) or "UNKNOWN" for row in rows)
        grades = Counter(clean(row.get("temporal_stability_grade")) or "UNKNOWN" for row in rows)
        scores = [to_float(row.get("temporal_physics_score")) for row in rows if not math.isnan(to_float(row.get("temporal_physics_score")))]
        validation = validation_by_start.get(key, {})
        result = safe.get(key)
        finish = to_int(result.get("finish_position")) if result else None
        starts.append(
            {
                "horse": clean(first.get("horse")),
                "horse_key": horse_key(first.get("horse")),
                "start_key": key,
                "race_date": normalise_date(first.get("race_date")),
                "dominant_phase_pattern": mode(patterns),
                "dominant_energy_curve_type": mode(curves),
                "dominant_temporal_stability_grade": mode(grades),
                "avg_temporal_physics_score": sum(scores) / len(scores) if scores else math.nan,
                "measurement_count": len(rows),
                "validated_result": result is not None,
                "finish_position": finish,
                "winner": 1 if finish == 1 else 0,
                "place": 1 if finish is not None and finish <= 3 else 0,
                "top4": 1 if finish is not None and finish <= 4 else 0,
                "validation_pattern": clean(validation.get("phase_transition_pattern")),
            }
        )
    return starts


def classify_memory(starts_tracked: int, dominant_pattern: str, dominant_curve: str, dominant_share: float, unique_patterns: int, collapse_count: int) -> tuple[str, str, str]:
    collapse_share = collapse_count / starts_tracked if starts_tracked else 0.0
    if starts_tracked < 3:
        return (
            "INSUFFICIENT_MEMORY",
            "INSUFFICIENT_TEMPORAL_IDENTITY_MEMORY",
            "Research only: fewer than three tracked temporal starts.",
        )
    if dominant_share >= 0.60 and dominant_pattern == "EARLY_TO_LATE_ACCELERATION":
        return (
            "PERSISTENT_LATE_ACCELERATOR",
            "PERSISTENT_MEASURED_LATE_ACCELERATION_PROFILE",
            "Research only: repeated measured late acceleration pattern across starts.",
        )
    if dominant_share >= 0.60 and (dominant_pattern == "MIDRACE_SUSTAIN_TO_LATE_HOLD" or dominant_curve == "STABLE_ENERGY_CURVE"):
        return (
            "PERSISTENT_SUSTAINER",
            "PERSISTENT_MEASURED_SUSTAIN_PROFILE",
            "Research only: repeated measured sustain pattern across starts.",
        )
    if collapse_share >= 0.40:
        return (
            "REPEATED_COLLAPSE_RISK",
            "REPEATED_MEASURED_COLLAPSE_PROFILE",
            "Research only: repeated measured collapse pattern across starts.",
        )
    if unique_patterns >= 4:
        return (
            "VOLATILE_TEMPORAL_PROFILE",
            "VOLATILE_MEASURED_TEMPORAL_IDENTITY",
            "Research only: multiple different measured temporal patterns across starts.",
        )
    return (
        "NEUTRAL_TEMPORAL_MEMORY",
        "NEUTRAL_MEASURED_TEMPORAL_IDENTITY",
        "Research only: no persistent measured temporal identity yet.",
    )


def build_memory_rows(starts: list[dict[str, object]]) -> list[dict[str, object]]:
    by_horse: dict[str, list[dict[str, object]]] = defaultdict(list)
    names: dict[str, Counter] = defaultdict(Counter)
    for start in starts:
        key = str(start["horse_key"])
        by_horse[key].append(start)
        names[key][str(start["horse"])] += 1

    output: list[dict[str, object]] = []
    for key, horse_starts in sorted(by_horse.items()):
        starts_tracked = len(horse_starts)
        patterns = Counter(str(start["dominant_phase_pattern"]) for start in horse_starts)
        curves = Counter(str(start["dominant_energy_curve_type"]) for start in horse_starts)
        scores = [float(start["avg_temporal_physics_score"]) for start in horse_starts if not math.isnan(float(start["avg_temporal_physics_score"]))]
        validated = [start for start in horse_starts if start["validated_result"]]
        finishes = [int(start["finish_position"]) for start in validated if start["finish_position"] is not None]
        wins = sum(int(start["winner"]) for start in validated)
        places = sum(int(start["place"]) for start in validated)
        top4 = sum(int(start["top4"]) for start in validated)
        dominant_pattern = mode(patterns)
        dominant_curve = mode(curves)
        dominant_count = patterns[dominant_pattern] if dominant_pattern else 0
        dominant_share = dominant_count / starts_tracked if starts_tracked else 0.0
        unique_pattern_count = len([pattern for pattern in patterns if pattern and pattern != "UNKNOWN"])
        late_accel_count = patterns.get("EARLY_TO_LATE_ACCELERATION", 0)
        collapse_count = patterns.get("LATE_COLLAPSE", 0) + curves.get("COLLAPSE_CURVE", 0)
        sustain_count = patterns.get("MIDRACE_SUSTAIN_TO_LATE_HOLD", 0) + curves.get("STABLE_ENERGY_CURVE", 0)
        consistency = dominant_share * 100.0
        volatility = min(100.0, max(0.0, (unique_pattern_count - 1) / max(1, starts_tracked - 1) * 100.0))
        grade, label, status_note = classify_memory(starts_tracked, dominant_pattern, dominant_curve, dominant_share, unique_pattern_count, collapse_count)

        output.append(
            {
                "horse": mode(names[key]),
                "horse_key": key,
                "starts_tracked": starts_tracked,
                "validated_result_starts": len(validated),
                "phase_patterns_seen": ";".join(f"{name}:{count}" for name, count in patterns.most_common()),
                "dominant_phase_pattern": dominant_pattern,
                "energy_curve_types_seen": ";".join(f"{name}:{count}" for name, count in curves.most_common()),
                "dominant_energy_curve_type": dominant_curve,
                "avg_temporal_physics_score": fmt(sum(scores) / len(scores) if scores else math.nan),
                "avg_finish_position": fmt(sum(finishes) / len(finishes) if finishes else math.nan),
                "wins": wins,
                "places": places,
                "top4": top4,
                "win_rate": pct(wins, len(validated)),
                "place_rate": pct(places, len(validated)),
                "top4_rate": pct(top4, len(validated)),
                "temporal_consistency_score": fmt(consistency),
                "temporal_volatility_score": fmt(volatility),
                "late_acceleration_repeat_count": late_accel_count,
                "collapse_repeat_count": collapse_count,
                "sustain_repeat_count": sustain_count,
                "identity_memory_grade": grade,
                "identity_memory_label": label,
                "research_status": "RESEARCH_ONLY_IDENTITY_MEMORY",
                "trusted_for_live_modelling": "NO",
                "trusted_for_live_execution": "NO",
                "notes": status_note + " No market price, overlay, rating, or execution impact.",
            }
        )
    return output


def build_watchlist(memory_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in memory_rows:
        grade = clean(row.get("identity_memory_grade"))
        starts = int(row.get("starts_tracked") or 0)
        validated = int(row.get("validated_result_starts") or 0)
        if grade in {"PERSISTENT_LATE_ACCELERATOR", "PERSISTENT_SUSTAINER"} and validated >= 3:
            priority = "HIGH"
            reason = "Persistent measured temporal behaviour with at least three validated result starts."
            next_step = "Continue accumulating outcomes and inspect regime sensitivity before any modelling promotion."
        elif grade == "REPEATED_COLLAPSE_RISK" and starts >= 3:
            priority = "MEDIUM"
            reason = "Repeated measured collapse profile across tracked starts."
            next_step = "Track whether collapse repeats by distance, field size, and race-shape regime."
        elif grade == "INSUFFICIENT_MEMORY" and starts >= 2:
            priority = "LOW"
            reason = "Early identity memory candidate with at least two tracked starts but insufficient evidence."
            next_step = "Wait for additional measured temporal starts before interpretation."
        else:
            continue
        rows.append(
            {
                "priority": priority,
                "horse": row.get("horse", ""),
                "horse_key": row.get("horse_key", ""),
                "starts_tracked": starts,
                "validated_result_starts": validated,
                "dominant_phase_pattern": row.get("dominant_phase_pattern", ""),
                "dominant_energy_curve_type": row.get("dominant_energy_curve_type", ""),
                "identity_memory_grade": grade,
                "identity_memory_label": row.get("identity_memory_label", ""),
                "watchlist_reason": reason,
                "research_next_step": next_step,
                "trusted_for_live_modelling": "NO",
                "trusted_for_live_execution": "NO",
                "notes": "Research watchlist only. Not eligible for live modelling or execution.",
            }
        )
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(rows, key=lambda row: (order.get(str(row["priority"]), 9), -int(row["starts_tracked"]), str(row["horse"])))


def build_summary(memory_rows: list[dict[str, object]], watchlist_rows: list[dict[str, object]], starts: list[dict[str, object]], source_counts: Counter, missing: list[str]) -> list[dict[str, object]]:
    grades = Counter(str(row.get("identity_memory_grade")) for row in memory_rows)
    priorities = Counter(str(row.get("priority")) for row in watchlist_rows)
    summary: list[dict[str, object]] = [
        {"metric": "identity_rows", "value": len(memory_rows)},
        {"metric": "start_profiles", "value": len(starts)},
        {"metric": "watchlist_rows", "value": len(watchlist_rows)},
        {"metric": "persistent_late_accelerators", "value": grades.get("PERSISTENT_LATE_ACCELERATOR", 0)},
        {"metric": "persistent_sustainers", "value": grades.get("PERSISTENT_SUSTAINER", 0)},
        {"metric": "collapse_risks", "value": grades.get("REPEATED_COLLAPSE_RISK", 0)},
        {"metric": "volatile_profiles", "value": grades.get("VOLATILE_TEMPORAL_PROFILE", 0)},
        {"metric": "insufficient_memory", "value": grades.get("INSUFFICIENT_MEMORY", 0)},
        {"metric": "neutral_memory", "value": grades.get("NEUTRAL_TEMPORAL_MEMORY", 0)},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]
    for name in missing:
        summary.append({"metric": f"missing_input::{name}", "value": 1})
    for name, count in source_counts.most_common():
        summary.append({"metric": f"source_rows::{name}", "value": count})
    for grade, count in grades.most_common():
        summary.append({"metric": f"identity_memory_grade::{grade}", "value": count})
    for priority, count in priorities.most_common():
        summary.append({"metric": f"watchlist_priority::{priority}", "value": count})
    return summary


def main() -> None:
    inputs, source_counts, missing = load_inputs()
    safe = safe_results(inputs["results_truth"])
    starts = start_profiles(inputs["temporal_engine"], inputs["validation"], safe)
    memory_rows = build_memory_rows(starts)
    watchlist_rows = build_watchlist(memory_rows)
    summary_rows = build_summary(memory_rows, watchlist_rows, starts, source_counts, missing)

    write_csv(OUT, memory_rows, MEMORY_FIELDS)
    write_csv(WATCHLIST, watchlist_rows, WATCHLIST_FIELDS)
    write_csv(SUMMARY, summary_rows, SUMMARY_FIELDS)

    grades = Counter(str(row.get("identity_memory_grade")) for row in memory_rows)
    print("=" * 88)
    print("EDGEIQ TEMPORAL IDENTITY MEMORY V1")
    print("=" * 88)
    print(f"identity rows: {len(memory_rows)}")
    print(f"start profiles: {len(starts)}")
    print(f"watchlist rows: {len(watchlist_rows)}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {WATCHLIST}")
    for grade, count in grades.most_common():
        print(f"  {grade}: {count}")
    print("live modelling/execution: 0 / 0")


if __name__ == "__main__":
    main()
