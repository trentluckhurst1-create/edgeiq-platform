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
    "evidence": DATA / "edgeiq_temporal_evidence_accumulator_v1.csv",
    "longitudinal": DATA / "edgeiq_temporal_pattern_longitudinal_v1.csv",
    "race_shape": DATA / "edgeiq_race_shape_response_v1.csv",
    "results_truth": DATA / "edgeiq_canonical_results_truth_v1.csv",
    "fields": DATA / "edgeiq_vic_three_day_race_fields.csv",
    "market_entity_summary": DATA / "edgeiq_market_entity_resolution_summary_v1.csv",
    "market_entity_graph": DATA / "edgeiq_canonical_market_entity_graph_v1.csv",
}

OUT = DATA / "edgeiq_temporal_research_regime_engine_v1.csv"
SUMMARY = DATA / "edgeiq_temporal_research_regime_summary_v1.csv"
OPPORTUNITY = DATA / "edgeiq_temporal_regime_opportunity_map_v1.csv"

REGIME_FIELDS = [
    "phase_transition_pattern",
    "energy_curve_type",
    "temporal_stability_grade",
    "regime_type",
    "regime_value",
    "sample_size",
    "wins",
    "places",
    "top4",
    "avg_finish",
    "win_rate",
    "place_rate",
    "top4_rate",
    "variance_score",
    "stability_score",
    "regime_signal_grade",
    "regime_signal_label",
    "research_interpretation",
    "sample_status",
    "trusted_for_live_modelling",
    "trusted_for_live_execution",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

OPPORTUNITY_FIELDS = [
    "priority",
    "phase_transition_pattern",
    "regime_type",
    "regime_value",
    "sample_size",
    "place_rate",
    "top4_rate",
    "variance_score",
    "opportunity_type",
    "research_next_step",
    "notes",
]

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


def race_key(row: dict[str, object]) -> str:
    date = normalise_date(row.get("race_date"))
    track = normalise_track(row.get("track"))
    race_no = normalise_race_no(row.get("race_no"))
    return f"{date}|{track}|{race_no}" if date and track and race_no else ""


def runner_key(row: dict[str, object]) -> str:
    supplied = clean(row.get("canonical_runner_key"))
    if supplied and "|" in supplied:
        return supplied
    key = race_key(row)
    horse = normalise_text(row.get("horse"))
    return f"{key}|{horse}" if key and horse else ""


def to_int(value: object) -> int | None:
    text = clean(value)
    if not text:
        return None
    try:
        numeric = int(round(float(re.sub(r"[^0-9.\-]", "", text))))
    except ValueError:
        return None
    return numeric if numeric > 0 else None


def to_float(value: object) -> float:
    text = clean(value)
    if not text:
        return math.nan
    try:
        return float(re.sub(r"[^0-9.\-]", "", text))
    except ValueError:
        return math.nan


def rate(part: int, whole: int) -> float:
    return 0.0 if whole <= 0 else (part / whole) * 100.0


def fmt(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.2f}"


def bucket_distance(value: object) -> str:
    distance = to_float(value)
    if math.isnan(distance):
        return "UNKNOWN"
    if distance <= 1200:
        return "SPRINT"
    if distance <= 1600:
        return "MILE"
    if distance <= 2000:
        return "MIDDLE"
    return "STAYING"


def bucket_field_size(value: object) -> str:
    size = to_int(value)
    if size is None:
        return "UNKNOWN"
    if size <= 7:
        return "SMALL"
    if size <= 11:
        return "MEDIUM"
    return "LARGE"


def safe_result_keys(rows: list[dict[str, str]]) -> set[str]:
    keys: set[str] = set()
    for row in rows:
        if clean(row.get("safe_for_model_validation")) != "YES":
            continue
        if not clean(row.get("finish_position")):
            continue
        key = runner_key(row)
        if key:
            keys.add(key)
    return keys


def build_field_context(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    context: dict[str, dict[str, str]] = {}
    for row in rows:
        key = race_key(row)
        if not key or key in context:
            continue
        context[key] = {
            "distance_bucket": bucket_distance(row.get("distance")),
            "field_size_bucket": bucket_field_size(row.get("_field_size_active") or row.get("field_size")),
            "track": normalise_track(row.get("track")),
        }
    return context


def build_shape_context(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    context: dict[str, dict[str, str]] = {}
    for row in rows:
        key = race_key(row)
        if not key:
            continue
        context[key] = {
            "race_shape_label": clean(row.get("race_shape_label")) or "UNKNOWN",
            "race_shape_risk": clean(row.get("race_shape_risk")) or "UNKNOWN",
            "field_size_bucket": bucket_field_size(row.get("field_size")),
        }
    return context


def validated_rows(validation_rows: list[dict[str, str]], safe_keys: set[str], field_context: dict[str, dict[str, str]], shape_context: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in validation_rows:
        key = runner_key(row)
        finish = to_int(row.get("finish_position"))
        if not key or key not in safe_keys or finish is None:
            continue
        rkey = race_key(row)
        field = field_context.get(rkey, {})
        shape = shape_context.get(rkey, {})
        track = normalise_track(row.get("track"))
        rows.append(
            {
                "phase_transition_pattern": clean(row.get("phase_transition_pattern")) or "UNKNOWN",
                "energy_curve_type": clean(row.get("energy_curve_type")) or "UNKNOWN",
                "temporal_stability_grade": clean(row.get("temporal_stability_grade")) or "UNKNOWN",
                "track": track or "UNKNOWN",
                "distance_bucket": field.get("distance_bucket", "UNKNOWN"),
                "field_size_bucket": shape.get("field_size_bucket") or field.get("field_size_bucket", "UNKNOWN"),
                "race_shape_label": shape.get("race_shape_label", "UNKNOWN"),
                "race_shape_risk": shape.get("race_shape_risk", "UNKNOWN"),
                "finish_position": finish,
                "win": 1 if finish == 1 else 0,
                "place": 1 if finish <= 3 else 0,
                "top4": 1 if finish <= 4 else 0,
            }
        )
    return rows


def stability_and_variance(finishes: list[int]) -> tuple[float, float]:
    if not finishes:
        return 0.0, 0.0
    if len(finishes) == 1:
        return 100.0, 0.0
    variance = statistics.pvariance(finishes)
    variance_score = min(100.0, variance * 6.0)
    return max(0.0, 100.0 - variance_score), variance_score


def classify_regime(sample: int, place_rate: float, top4_rate: float, variance_score: float) -> tuple[str, str, str, str]:
    if sample < 20:
        return (
            "INSUFFICIENT_SAMPLE",
            "INSUFFICIENT_SAMPLE",
            "Sample below research threshold; retain as evidence queue only.",
            "LOW",
        )
    if top4_rate >= 55 and place_rate < 22:
        return (
            "REGIME_HIGH_VARIANCE",
            "HIGH_VARIANCE_TEMPORAL_REGIME",
            "Top-four presence without place conversion suggests volatile conditional behaviour.",
            "MEDIUM",
        )
    if variance_score >= 70:
        return (
            "REGIME_HIGH_VARIANCE",
            "HIGH_VARIANCE_TEMPORAL_REGIME",
            "Finish distribution remains too dispersed for stable interpretation.",
            "MEDIUM",
        )
    if place_rate >= 35 or top4_rate >= 55:
        return (
            "REGIME_POSITIVE_EARLY",
            "EARLY_POSITIVE_CONDITIONAL_EVIDENCE",
            "Conditional environment has early positive outcome relationship, research only.",
            "MEDIUM",
        )
    if place_rate <= 18 and top4_rate <= 35:
        return (
            "REGIME_NEGATIVE_EARLY",
            "EARLY_NEGATIVE_CONDITIONAL_EVIDENCE",
            "Conditional environment has weak early outcome relationship, research only.",
            "MEDIUM",
        )
    return (
        "REGIME_NEUTRAL",
        "NEUTRAL_CONDITIONAL_EVIDENCE",
        "Conditional environment has no clear directional outcome relationship yet.",
        "MEDIUM",
    )


def regime_values(row: dict[str, object]) -> list[tuple[str, str]]:
    return [
        ("TRACK", str(row.get("track") or "UNKNOWN")),
        ("DISTANCE_BUCKET", str(row.get("distance_bucket") or "UNKNOWN")),
        ("FIELD_SIZE_BUCKET", str(row.get("field_size_bucket") or "UNKNOWN")),
        ("RACE_SHAPE_LABEL", str(row.get("race_shape_label") or "UNKNOWN")),
        ("RACE_SHAPE_RISK", str(row.get("race_shape_risk") or "UNKNOWN")),
        ("TEMPORAL_STABILITY_GRADE", str(row.get("temporal_stability_grade") or "UNKNOWN")),
        ("ENERGY_CURVE_TYPE", str(row.get("energy_curve_type") or "UNKNOWN")),
        ("PHASE_PATTERN", str(row.get("phase_transition_pattern") or "UNKNOWN")),
    ]


def build_regime_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        for regime_type, regime_value in regime_values(row):
            key = (
                str(row["phase_transition_pattern"]),
                str(row["energy_curve_type"]),
                str(row["temporal_stability_grade"]),
                regime_type,
                regime_value,
            )
            grouped[key].append(row)

    output: list[dict[str, object]] = []
    for (pattern, curve, grade, regime_type, regime_value), group in sorted(grouped.items()):
        finishes = [int(row["finish_position"]) for row in group]
        sample = len(group)
        wins = sum(int(row["win"]) for row in group)
        places = sum(int(row["place"]) for row in group)
        top4 = sum(int(row["top4"]) for row in group)
        win_rate = rate(wins, sample)
        place_rate = rate(places, sample)
        top4_rate = rate(top4, sample)
        stability, variance = stability_and_variance(finishes)
        signal, label, interpretation, sample_status = classify_regime(sample, place_rate, top4_rate, variance)
        output.append(
            {
                "phase_transition_pattern": pattern,
                "energy_curve_type": curve,
                "temporal_stability_grade": grade,
                "regime_type": regime_type,
                "regime_value": regime_value,
                "sample_size": sample,
                "wins": wins,
                "places": places,
                "top4": top4,
                "avg_finish": fmt(sum(finishes) / sample if sample else math.nan),
                "win_rate": fmt(win_rate),
                "place_rate": fmt(place_rate),
                "top4_rate": fmt(top4_rate),
                "variance_score": fmt(variance),
                "stability_score": fmt(stability),
                "regime_signal_grade": signal,
                "regime_signal_label": label,
                "research_interpretation": interpretation,
                "sample_status": sample_status,
                "trusted_for_live_modelling": "NO",
                "trusted_for_live_execution": "NO",
                "notes": "Temporal research regime analytics only. No betting signal, overlay, rating, or execution impact.",
            }
        )
    return output


def build_opportunity_map(regime_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    opportunities: list[dict[str, object]] = []
    for row in regime_rows:
        sample = int(row.get("sample_size") or 0)
        signal = clean(row.get("regime_signal_grade"))
        if signal == "REGIME_POSITIVE_EARLY" and sample >= 20:
            priority = "HIGH"
            opportunity_type = "CONDITIONAL_POSITIVE_RESEARCH_THREAD"
            next_step = "Accumulate additional settled samples and test persistence across adjacent regimes."
        elif signal == "REGIME_HIGH_VARIANCE":
            priority = "MEDIUM"
            opportunity_type = "VOLATILITY_RESEARCH_THREAD"
            next_step = "Investigate whether variance comes from field shape, track, or sample identity drift."
        elif signal == "INSUFFICIENT_SAMPLE":
            priority = "LOW"
            opportunity_type = "SAMPLE_BUILD_QUEUE"
            next_step = "Wait for more settled canonical results before interpreting this regime."
        else:
            continue
        opportunities.append(
            {
                "priority": priority,
                "phase_transition_pattern": row.get("phase_transition_pattern", ""),
                "regime_type": row.get("regime_type", ""),
                "regime_value": row.get("regime_value", ""),
                "sample_size": sample,
                "place_rate": row.get("place_rate", ""),
                "top4_rate": row.get("top4_rate", ""),
                "variance_score": row.get("variance_score", ""),
                "opportunity_type": opportunity_type,
                "research_next_step": next_step,
                "notes": "Research opportunity only. Not eligible for live modelling or execution.",
            }
        )

    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(opportunities, key=lambda row: (priority_order.get(str(row["priority"]), 9), -int(row["sample_size"])))


def build_summary(regime_rows: list[dict[str, object]], opportunities: list[dict[str, object]], validated_count: int, source_counts: Counter, missing: list[str]) -> list[dict[str, object]]:
    signals = Counter(str(row.get("regime_signal_grade")) for row in regime_rows)
    summary: list[dict[str, object]] = [
        {"metric": "regime_rows", "value": len(regime_rows)},
        {"metric": "validated_rows", "value": validated_count},
        {"metric": "opportunity_rows", "value": len(opportunities)},
        {"metric": "positive_regimes", "value": signals.get("REGIME_POSITIVE_EARLY", 0)},
        {"metric": "negative_regimes", "value": signals.get("REGIME_NEGATIVE_EARLY", 0)},
        {"metric": "high_variance_regimes", "value": signals.get("REGIME_HIGH_VARIANCE", 0)},
        {"metric": "insufficient_sample_regimes", "value": signals.get("INSUFFICIENT_SAMPLE", 0)},
        {"metric": "neutral_regimes", "value": signals.get("REGIME_NEUTRAL", 0)},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]
    for name in missing:
        summary.append({"metric": f"missing_input::{name}", "value": 1})
    for name, count in source_counts.most_common():
        summary.append({"metric": f"source_rows::{name}", "value": count})
    for signal, count in signals.most_common():
        summary.append({"metric": f"regime_signal::{signal}", "value": count})
    for priority, count in Counter(str(row.get("priority")) for row in opportunities).most_common():
        summary.append({"metric": f"opportunity_priority::{priority}", "value": count})
    return summary


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


def main() -> None:
    inputs, source_counts, missing = load_inputs()
    safe_keys = safe_result_keys(inputs["results_truth"])
    field_context = build_field_context(inputs["fields"])
    shape_context = build_shape_context(inputs["race_shape"])
    validated = validated_rows(inputs["validation"], safe_keys, field_context, shape_context)
    regime_rows = build_regime_rows(validated)
    opportunities = build_opportunity_map(regime_rows)
    summary = build_summary(regime_rows, opportunities, len(validated), source_counts, missing)

    write_csv(OUT, regime_rows, REGIME_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    write_csv(OPPORTUNITY, opportunities, OPPORTUNITY_FIELDS)

    signals = Counter(str(row.get("regime_signal_grade")) for row in regime_rows)
    print("=" * 88)
    print("EDGEIQ TEMPORAL RESEARCH REGIME ENGINE V1")
    print("=" * 88)
    print(f"validated rows: {len(validated)}")
    print(f"regime rows: {len(regime_rows)}")
    print(f"opportunity rows: {len(opportunities)}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {OPPORTUNITY}")
    for signal, count in signals.most_common():
        print(f"  {signal}: {count}")
    print("live modelling/execution: 0 / 0")


if __name__ == "__main__":
    main()
