from __future__ import annotations

import csv
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TEMPORAL = DATA / "edgeiq_temporal_physics_engine_v1.csv"
CANONICAL_RESULTS = DATA / "edgeiq_canonical_results_truth_v1.csv"
RAW_RESULTS_FALLBACK = DATA / "race_results.csv"
ENTITY_GRAPH = DATA / "edgeiq_canonical_market_entity_graph_v1.csv"

OUT = DATA / "edgeiq_temporal_physics_validation_v1.csv"
SUMMARY = DATA / "edgeiq_temporal_physics_validation_summary_v1.csv"
PERFORMANCE = DATA / "edgeiq_temporal_pattern_performance_v1.csv"

VALIDATION_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "phase_transition_pattern",
    "energy_curve_type",
    "temporal_stability_grade",
    "temporal_physics_score",
    "finish_position",
    "winner_flag",
    "place_flag",
    "top4_flag",
    "validation_grade",
    "validation_label",
    "pattern_effectiveness",
    "pattern_risk",
    "predictive_research_status",
    "trusted_for_live_modelling",
    "trusted_for_live_execution",
    "notes",
]

PERFORMANCE_FIELDS = [
    "phase_transition_pattern",
    "energy_curve_type",
    "sample_size",
    "matched_rows",
    "pending_or_missing_results",
    "wins",
    "places",
    "top4",
    "avg_finish",
    "win_strike_rate",
    "place_strike_rate",
    "top4_strike_rate",
    "pattern_effectiveness",
    "pattern_risk",
    "validation_grade",
    "validation_label",
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


def canonical_runner_key(row: dict[str, object], horse_field: str = "horse") -> str:
    supplied = clean(row.get("canonical_runner_key"))
    if supplied and "|" in supplied:
        return supplied
    race_date = normalise_date(row.get("race_date"))
    track = normalise_track(row.get("track"))
    race_no = normalise_race_no(row.get("race_no"))
    horse = normalise_text(row.get(horse_field))
    return f"{race_date}|{track}|{race_no}|{horse}" if race_date and track and race_no and horse else ""


def to_float(value: object) -> float:
    text = clean(value).replace(",", "")
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


def pct(part: int, whole: int) -> str:
    return "" if whole <= 0 else f"{(part / whole) * 100:.2f}"


def avg(values: list[int]) -> str:
    return "" if not values else f"{sum(values) / len(values):.2f}"


def raw_result_finish(row: dict[str, str]) -> int | None:
    for field in ["finish_position", "finish_pos", "finish_pos_num", "position", "place", "placing", "result", "finish", "rank", "fin_pos"]:
        value = clean(row.get(field))
        if not value:
            continue
        norm = normalise_text(value)
        if norm in {"WON", "WINNER", "WIN"}:
            return 1
        if norm in {"LOST", "PENDING", "SCRATCHED", "SCR"}:
            continue
        finish = to_int(value)
        if finish is not None:
            return finish
    return None


def build_result_index(canonical_rows: list[dict[str, str]], raw_rows: list[dict[str, str]]) -> tuple[dict[str, dict[str, object]], Counter]:
    index: dict[str, dict[str, object]] = {}
    diagnostics: Counter = Counter()

    if canonical_rows:
        for row in canonical_rows:
            key = canonical_runner_key(row)
            if not key:
                diagnostics["canonical_rows_missing_key"] += 1
                continue
            finish = to_int(row.get("finish_position"))
            if finish is None:
                diagnostics["canonical_rows_without_finish"] += 1
            if clean(row.get("safe_for_model_validation")) != "YES":
                diagnostics["canonical_rows_not_safe_for_model_validation"] += 1
                if finish is None:
                    continue
            if key in index:
                diagnostics["duplicate_canonical_result_keys"] += 1
                existing_finish = to_int(index[key].get("finish_position"))
                if existing_finish is None and finish is not None:
                    index[key] = dict(row)
                continue
            index[key] = dict(row)
        return index, diagnostics

    for row in raw_rows:
        key = canonical_runner_key(row)
        if not key:
            diagnostics["raw_rows_missing_key"] += 1
            continue
        finish = raw_result_finish(row)
        if finish is None:
            diagnostics["raw_rows_without_finish"] += 1
        if key in index:
            diagnostics["duplicate_raw_result_keys"] += 1
            existing_finish = to_int(index[key].get("finish_position"))
            if existing_finish is None and finish is not None:
                index[key] = {**row, "finish_position": str(finish)}
            continue
        index[key] = {**row, "finish_position": str(finish) if finish is not None else ""}

    return index, diagnostics


def index_entity_results(rows: list[dict[str, str]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in rows:
        key = canonical_runner_key(row)
        result_runner = clean(row.get("results_runner"))
        if key and result_runner:
            mapping[key] = result_runner
    return mapping


def classify_performance(sample_size: int, win_rate: float, place_rate: float, top4_rate: float, avg_finish_value: float) -> tuple[str, str, str, str]:
    if sample_size < 25:
        return ("LOW_SAMPLE_PATTERN", "HIGH", "INSUFFICIENT_OUTCOME_SAMPLE", "Research only: not enough settled results to validate this temporal pattern.")
    if sample_size < 100:
        return ("LOW_SAMPLE_PATTERN", "MEDIUM", "LOW_SAMPLE_TEMPORAL_EVIDENCE", "Research only: early evidence sample, not live modelling evidence.")
    if win_rate >= 0.16 or place_rate >= 0.42 or top4_rate >= 0.62:
        return ("HISTORICALLY_POSITIVE", "MEDIUM", "POSITIVE_TEMPORAL_OUTCOME_RELATIONSHIP", "Research only: measured temporal pattern has shown positive historical outcome relationship.")
    if win_rate <= 0.06 and place_rate <= 0.22 and top4_rate <= 0.38:
        return ("HISTORICALLY_NEGATIVE", "HIGH", "NEGATIVE_TEMPORAL_OUTCOME_RELATIONSHIP", "Research only: measured temporal pattern has shown weak historical outcome relationship.")
    if avg_finish_value > 7.5 and top4_rate < 0.45:
        return ("HIGH_VARIANCE_PATTERN", "HIGH", "HIGH_VARIANCE_TEMPORAL_PATTERN", "Research only: temporal pattern shows high outcome variance.")
    return ("HISTORICALLY_NEUTRAL", "MEDIUM", "NEUTRAL_TEMPORAL_OUTCOME_RELATIONSHIP", "Research only: no clear historical outcome edge from this temporal pattern.")


def build_validation_rows(temporal_rows: list[dict[str, str]], result_index: dict[str, dict[str, object]], entity_results: dict[str, str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for row in temporal_rows:
        key = canonical_runner_key(row)
        result = result_index.get(key)
        finish = to_int(result.get("finish_position")) if result else None
        entity_result_name = entity_results.get(key, "")

        if finish is None:
            validation_grade = "LOW_SAMPLE_PATTERN"
            validation_label = "NO_SETTLED_RESULT_AVAILABLE"
            pattern_effectiveness = "UNVALIDATED"
            pattern_risk = "UNKNOWN"
            predictive_status = "RESEARCH_ONLY_PENDING_RESULT"
            notes = "No canonical settled finish position available for this runner. Temporal pattern preserved for future validation only."
            if entity_result_name:
                notes = f"{notes} Entity graph suggested result runner '{entity_result_name}', but canonical result truth did not provide a safe settled finish."
        else:
            validation_grade = "HISTORICALLY_NEUTRAL"
            validation_label = "ROW_MATCHED_PENDING_PATTERN_AGGREGATE"
            pattern_effectiveness = "PENDING_PATTERN_LEVEL_CLASSIFICATION"
            pattern_risk = "PENDING_PATTERN_LEVEL_CLASSIFICATION"
            predictive_status = "RESEARCH_ONLY_OUTCOME_MATCHED"
            notes = "Runner matched to canonical settled result truth. Pattern-level effectiveness is assigned in the performance output."

        rows.append(
            {
                "race_date": clean(row.get("race_date")),
                "track": clean(row.get("track")),
                "race_no": clean(row.get("race_no")),
                "horse": clean(row.get("horse")),
                "phase_transition_pattern": clean(row.get("phase_transition_pattern")),
                "energy_curve_type": clean(row.get("energy_curve_type")),
                "temporal_stability_grade": clean(row.get("temporal_stability_grade")),
                "temporal_physics_score": clean(row.get("temporal_physics_score")),
                "finish_position": finish if finish is not None else "",
                "winner_flag": "YES" if finish == 1 else "NO" if finish is not None else "",
                "place_flag": "YES" if finish is not None and finish <= 3 else "NO" if finish is not None else "",
                "top4_flag": "YES" if finish is not None and finish <= 4 else "NO" if finish is not None else "",
                "validation_grade": validation_grade,
                "validation_label": validation_label,
                "pattern_effectiveness": pattern_effectiveness,
                "pattern_risk": pattern_risk,
                "predictive_research_status": predictive_status,
                "trusted_for_live_modelling": "NO",
                "trusted_for_live_execution": "NO",
                "notes": notes,
            }
        )

    return rows


def build_pattern_stats(validation_rows: list[dict[str, object]]) -> dict[tuple[str, str], dict[str, object]]:
    grouped: dict[tuple[str, str], dict[str, object]] = defaultdict(
        lambda: {"sample_size": 0, "matched_rows": 0, "pending_or_missing_results": 0, "wins": 0, "places": 0, "top4": 0, "finishes": []}
    )
    for row in validation_rows:
        key = (str(row.get("phase_transition_pattern", "")), str(row.get("energy_curve_type", "")))
        group = grouped[key]
        finish = to_int(row.get("finish_position"))
        if finish is None:
            group["pending_or_missing_results"] += 1
            continue
        group["sample_size"] += 1
        group["matched_rows"] += 1
        group["finishes"].append(finish)
        if finish == 1:
            group["wins"] += 1
        if finish <= 3:
            group["places"] += 1
        if finish <= 4:
            group["top4"] += 1
    return grouped


def apply_pattern_classification(rows: list[dict[str, object]], stats: dict[tuple[str, str], dict[str, object]]) -> list[dict[str, object]]:
    classifications: dict[tuple[str, str], tuple[str, str, str, str]] = {}
    for key, group in stats.items():
        sample = int(group["sample_size"])
        wins = int(group["wins"])
        places = int(group["places"])
        top4 = int(group["top4"])
        finishes = list(group["finishes"])
        avg_finish_value = sum(finishes) / len(finishes) if finishes else math.nan
        classifications[key] = classify_performance(
            sample,
            wins / sample if sample else 0.0,
            places / sample if sample else 0.0,
            top4 / sample if sample else 0.0,
            avg_finish_value,
        )

    for row in rows:
        finish = to_int(row.get("finish_position"))
        key = (str(row.get("phase_transition_pattern", "")), str(row.get("energy_curve_type", "")))
        if finish is None or key not in classifications:
            continue
        grade_name, risk, label, note = classifications[key]
        row["validation_grade"] = grade_name
        row["validation_label"] = label
        row["pattern_effectiveness"] = grade_name
        row["pattern_risk"] = risk
        row["predictive_research_status"] = "RESEARCH_ONLY_VALIDATED_HISTORY"
        row["notes"] = note
    return rows


def build_performance_rows(stats: dict[tuple[str, str], dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for (pattern, curve), group in sorted(stats.items()):
        sample = int(group["sample_size"])
        wins = int(group["wins"])
        places = int(group["places"])
        top4 = int(group["top4"])
        finishes = list(group["finishes"])
        avg_finish_value = sum(finishes) / len(finishes) if finishes else math.nan
        effectiveness, risk, label, notes = classify_performance(
            sample,
            wins / sample if sample else 0.0,
            places / sample if sample else 0.0,
            top4 / sample if sample else 0.0,
            avg_finish_value,
        )
        rows.append(
            {
                "phase_transition_pattern": pattern,
                "energy_curve_type": curve,
                "sample_size": sample,
                "matched_rows": int(group["matched_rows"]),
                "pending_or_missing_results": int(group["pending_or_missing_results"]),
                "wins": wins,
                "places": places,
                "top4": top4,
                "avg_finish": avg(finishes),
                "win_strike_rate": pct(wins, sample),
                "place_strike_rate": pct(places, sample),
                "top4_strike_rate": pct(top4, sample),
                "pattern_effectiveness": effectiveness,
                "pattern_risk": risk,
                "validation_grade": effectiveness,
                "validation_label": label,
                "trusted_for_live_modelling": "NO",
                "trusted_for_live_execution": "NO",
                "notes": notes,
            }
        )
    return rows


def build_summary(
    temporal_rows: list[dict[str, str]],
    canonical_result_rows: list[dict[str, str]],
    raw_result_rows: list[dict[str, str]],
    validation_rows: list[dict[str, object]],
    performance_rows: list[dict[str, object]],
    diagnostics: Counter,
) -> list[dict[str, object]]:
    matched = sum(1 for row in validation_rows if clean(row.get("finish_position")))
    summary: list[dict[str, object]] = [
        {"metric": "temporal_input_rows", "value": len(temporal_rows)},
        {"metric": "canonical_result_rows", "value": len(canonical_result_rows)},
        {"metric": "raw_result_fallback_rows", "value": len(raw_result_rows)},
        {"metric": "validation_rows", "value": len(validation_rows)},
        {"metric": "outcome_matched_rows", "value": matched},
        {"metric": "pending_or_missing_result_rows", "value": len(validation_rows) - matched},
        {"metric": "wins", "value": sum(1 for row in validation_rows if row.get("winner_flag") == "YES")},
        {"metric": "places", "value": sum(1 for row in validation_rows if row.get("place_flag") == "YES")},
        {"metric": "top4", "value": sum(1 for row in validation_rows if row.get("top4_flag") == "YES")},
        {"metric": "pattern_performance_rows", "value": len(performance_rows)},
        {"metric": "trusted_for_live_modelling_yes", "value": 0},
        {"metric": "trusted_for_live_execution_yes", "value": 0},
    ]
    for key, value in diagnostics.items():
        summary.append({"metric": f"result_diagnostic::{key}", "value": value})
    for key, value in Counter(str(row.get("validation_grade", "")) for row in validation_rows).most_common():
        summary.append({"metric": f"validation_grade::{key}", "value": value})
    for key, value in Counter(str(row.get("validation_label", "")) for row in validation_rows).most_common():
        summary.append({"metric": f"validation_label::{key}", "value": value})
    for key, value in Counter(str(row.get("phase_transition_pattern", "")) for row in validation_rows).most_common():
        summary.append({"metric": f"pattern::{key}", "value": value})
    for key, value in Counter(str(row.get("pattern_effectiveness", "")) for row in performance_rows).most_common():
        summary.append({"metric": f"pattern_effectiveness::{key}", "value": value})
    return summary


def main() -> None:
    temporal_rows = read_csv(TEMPORAL)
    canonical_result_rows = read_csv(CANONICAL_RESULTS)
    raw_result_rows = read_csv(RAW_RESULTS_FALLBACK)
    entity_rows = read_csv(ENTITY_GRAPH)

    result_index, diagnostics = build_result_index(canonical_result_rows, raw_result_rows)
    entity_results = index_entity_results(entity_rows)
    validation_rows = build_validation_rows(temporal_rows, result_index, entity_results)
    stats = build_pattern_stats(validation_rows)
    validation_rows = apply_pattern_classification(validation_rows, stats)
    performance_rows = build_performance_rows(stats)
    summary_rows = build_summary(temporal_rows, canonical_result_rows, raw_result_rows, validation_rows, performance_rows, diagnostics)

    write_csv(OUT, validation_rows, VALIDATION_FIELDS)
    write_csv(PERFORMANCE, performance_rows, PERFORMANCE_FIELDS)
    write_csv(SUMMARY, summary_rows, SUMMARY_FIELDS)

    matched = sum(1 for row in validation_rows if clean(row.get("finish_position")))
    print("=" * 88)
    print("EDGEIQ TEMPORAL PHYSICS VALIDATION ENGINE V1")
    print("=" * 88)
    print(f"temporal rows: {len(temporal_rows)}")
    print(f"canonical result rows: {len(canonical_result_rows)}")
    print(f"raw result fallback rows: {len(raw_result_rows)}")
    print(f"validation rows: {len(validation_rows)}")
    print(f"outcome matched rows: {matched}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {PERFORMANCE}")
    for key, value in Counter(str(row.get("validation_grade", "")) for row in validation_rows).most_common():
        print(f"  {key}: {value}")
    print("live modelling/execution: 0 / 0")


if __name__ == "__main__":
    main()
