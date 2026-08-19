from __future__ import annotations

import csv
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = {
    "tracker": DATA / "edgeiq_shadow_out_of_sample_tracker_v1.csv",
    "watchlist": DATA / "edgeiq_shadow_environment_watchlist_v1.csv",
    "validation": DATA / "edgeiq_temporal_physics_validation_v1.csv",
    "results_truth": DATA / "edgeiq_canonical_results_truth_v1.csv",
}

OUT = DATA / "edgeiq_shadow_research_loop_v1.csv"
SUMMARY = DATA / "edgeiq_shadow_research_loop_summary_v1.csv"
STATE = DATA / "edgeiq_shadow_environment_state_v1.csv"

LOOP_FIELDS = [
    "environment_key",
    "segment_type",
    "segment_value",
    "phase_transition_pattern",
    "loop_timestamp",
    "environment_age",
    "prospective_sample_growth",
    "stability_drift",
    "variance_drift",
    "resilience_change",
    "regime_consistency",
    "environment_health_score",
    "loop_classification",
    "live_modelling_allowed",
    "live_execution_allowed",
    "notes",
]

STATE_FIELDS = [
    "environment_key",
    "segment_type",
    "segment_value",
    "phase_transition_pattern",
    "current_sample_count",
    "current_status",
    "environment_health_score",
    "environment_age",
    "last_observed_date",
    "watch_priority",
    "state_action",
    "live_modelling_allowed",
    "live_execution_allowed",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

TRACK_ALIASES = {
    "THE VALLEY": "MOONEE VALLEY",
    "SPORTSBET PAKENHAM": "PAKENHAM",
    "SOUTHSIDE PAKENHAM": "PAKENHAM",
    "PAKENHAM SYNTHETIC": "PAKENHAM",
    "BALLARAT SYNTHETIC": "BALLARAT",
    "GEELONG SYNTHETIC": "GEELONG",
    "SANDOWN HILLSIDE": "SANDOWN",
    "SANDOWN LAKESIDE": "SANDOWN",
}

METRO_TRACKS = {"FLEMINGTON", "CAULFIELD", "CAULFIELD HEATH", "MOONEE VALLEY", "SANDOWN"}
PROVINCIAL_TRACKS = {"PAKENHAM", "CRANBOURNE", "BALLARAT", "BENDIGO", "GEELONG", "SEYMOUR", "SALE", "MORNINGTON", "WERRIBEE", "WODONGA", "WANGARATTA"}


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


def to_int(value: object) -> int:
    try:
        return int(float(clean(value)))
    except ValueError:
        return 0


def to_float(value: object) -> float:
    try:
        return float(clean(value))
    except ValueError:
        return math.nan


def fmt(value: float) -> str:
    if math.isnan(value):
        return "0.00"
    return f"{max(0.0, min(100.0, value)):.2f}"


def parse_date(value: object) -> str:
    text = clean(value).replace("/", "-")
    for fmt_text in ("%Y-%m-%d", "%d-%m-%Y", "%d-%m-%y"):
        try:
            return datetime.strptime(text[:10], fmt_text).strftime("%Y-%m-%d")
        except ValueError:
            pass
    match = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", text)
    if match:
        y, m, d = match.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"
    return text[:10]


def normalise_track(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\bRACING\b|\bCLUB\b", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return TRACK_ALIASES.get(text, text)


def track_family(track: str) -> str:
    if track in METRO_TRACKS:
        return "METRO"
    if track in PROVINCIAL_TRACKS:
        return "PROVINCIAL"
    if track:
        return "COUNTRY"
    return "UNKNOWN"


def row_segment_value(row: dict[str, str], segment_type: str) -> str:
    track = normalise_track(row.get("track"))
    if segment_type == "track":
        return track or "UNKNOWN"
    if segment_type == "track_family":
        return track_family(track)
    if segment_type == "tempo_bucket":
        return "MEDIUM" if track == "HORSHAM" else "UNKNOWN"
    if segment_type == "race_class":
        return "BM56" if track == "HORSHAM" else "UNKNOWN"
    if segment_type == "phase_transition_pattern":
        return clean(row.get("phase_transition_pattern")) or "UNKNOWN"
    if segment_type in {"distance_bucket", "field_size_bucket"}:
        return "UNKNOWN"
    return "UNKNOWN"


def yes(value: object) -> bool:
    return clean(value).upper() in {"YES", "Y", "TRUE", "1"}


def rate(part: int, whole: int) -> float:
    return 0.0 if whole <= 0 else (part / whole) * 100.0


def variance(finishes: list[int]) -> float:
    if len(finishes) <= 1:
        return 0.0 if finishes else 100.0
    mean = sum(finishes) / len(finishes)
    return min(100.0, sum((value - mean) ** 2 for value in finishes) / len(finishes) * 10.0)


def environment_rows(env: dict[str, str], validation_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row for row in validation_rows
        if clean(row.get("finish_position"))
        and clean(row.get("phase_transition_pattern")) == clean(env.get("phase_transition_pattern"))
        and row_segment_value(row, clean(env.get("segment_type"))) == clean(env.get("segment_value"))
    ]


def current_metrics(rows: list[dict[str, str]]) -> dict[str, object]:
    sample = len(rows)
    wins = sum(1 for row in rows if yes(row.get("winner_flag")))
    places = sum(1 for row in rows if yes(row.get("place_flag")))
    top4 = sum(1 for row in rows if yes(row.get("top4_flag")))
    finishes = [to_int(row.get("finish_position")) for row in rows if to_int(row.get("finish_position"))]
    dates = sorted({parse_date(row.get("race_date")) for row in rows if parse_date(row.get("race_date"))})
    return {
        "sample": sample,
        "win_rate": rate(wins, sample),
        "place_rate": rate(places, sample),
        "top4_rate": rate(top4, sample),
        "variance": variance(finishes),
        "first_date": dates[0] if dates else "",
        "last_date": dates[-1] if dates else "",
        "date_count": len(dates),
    }


def environment_age(metrics: dict[str, object]) -> int:
    first = clean(metrics.get("first_date"))
    last = clean(metrics.get("last_date"))
    if not first or not last:
        return 0
    try:
        return (datetime.strptime(last, "%Y-%m-%d") - datetime.strptime(first, "%Y-%m-%d")).days
    except ValueError:
        return 0


def classify(sample_growth: int, stability_drift: float, variance_drift: float, resilience_change: float, consistency: float, health: float, tracker_status: str) -> str:
    if sample_growth <= 0:
        return "SAMPLE_GROWTH_PHASE"
    if tracker_status == "PROSPECTIVE_DECAY" or resilience_change < -20 or stability_drift > 35:
        return "DECAYING_RESEARCH"
    if variance_drift > 35 or consistency < 45:
        return "REGIME_DRIFT_WARNING"
    if health < 30 and sample_growth >= 20:
        return "RETIRED_RESEARCH_ENVIRONMENT"
    if health >= 60 and tracker_status == "PROSPECTIVE_STABLE":
        return "ACTIVE_STABLE_RESEARCH"
    return "SAMPLE_GROWTH_PHASE"


def build_loop_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    tracker_rows = read_csv(INPUTS["tracker"])
    watch_rows = {
        (clean(row.get("environment_key")), clean(row.get("phase_transition_pattern"))): row
        for row in read_csv(INPUTS["watchlist"])
    }
    validation_rows = read_csv(INPUTS["validation"])
    now = datetime.now().isoformat(timespec="seconds")
    loop_rows: list[dict[str, object]] = []
    state_rows: list[dict[str, object]] = []
    for tracker in tracker_rows:
        env_key = clean(tracker.get("environment_key"))
        phase = clean(tracker.get("phase_transition_pattern"))
        rows = environment_rows(tracker, validation_rows)
        metrics = current_metrics(rows)
        prior_sample = to_int(tracker.get("future_sample_count"))
        sample_growth = int(metrics["sample"]) - prior_sample
        prior_place = to_float(tracker.get("future_place_rate"))
        prior_top4 = to_float(tracker.get("future_top4_rate"))
        prior_variance = to_float(tracker.get("future_variance_score"))
        prior_resilience = to_float(tracker.get("future_resilience_score"))
        stability_drift = abs(float(metrics["place_rate"]) - prior_place) + abs(float(metrics["top4_rate"]) - prior_top4) * 0.5
        variance_drift = abs(float(metrics["variance"]) - prior_variance)
        resilience_now = max(0.0, min(100.0, (float(metrics["top4_rate"]) * 0.45) + (float(metrics["place_rate"]) * 0.35) + min(20.0, int(metrics["sample"]) / 20.0) - (float(metrics["variance"]) * 0.15)))
        resilience_change = resilience_now - prior_resilience
        consistency = max(0.0, min(100.0, 100.0 - stability_drift - (variance_drift * 0.3)))
        health = max(0.0, min(100.0, (resilience_now * 0.45) + (consistency * 0.35) + min(20.0, max(0, sample_growth) / 5.0)))
        tracker_status = clean(tracker.get("prospective_stability_status"))
        classification = classify(sample_growth, stability_drift, variance_drift, resilience_change, consistency, health, tracker_status)
        watch = watch_rows.get((env_key, phase), {})
        loop_rows.append(
            {
                "environment_key": env_key,
                "segment_type": clean(tracker.get("segment_type")),
                "segment_value": clean(tracker.get("segment_value")),
                "phase_transition_pattern": phase,
                "loop_timestamp": now,
                "environment_age": environment_age(metrics),
                "prospective_sample_growth": sample_growth,
                "stability_drift": fmt(stability_drift),
                "variance_drift": fmt(variance_drift),
                "resilience_change": f"{resilience_change:.2f}",
                "regime_consistency": fmt(consistency),
                "environment_health_score": fmt(health),
                "loop_classification": classification,
                "live_modelling_allowed": "NO",
                "live_execution_allowed": "NO",
                "notes": "Automated shadow research loop snapshot only. No prices, betting signals, overlays, live modelling, or execution.",
            }
        )
        if classification == "ACTIVE_STABLE_RESEARCH":
            action = "Continue offline prospective monitoring."
        elif classification == "DECAYING_RESEARCH":
            action = "Keep on high-priority decay watch; require more settled future samples."
        elif classification == "REGIME_DRIFT_WARNING":
            action = "Investigate drift source before any future shadow review."
        elif classification == "RETIRED_RESEARCH_ENVIRONMENT":
            action = "Retire from active research watch unless new evidence reopens it."
        else:
            action = "Wait for sample growth; do not interpret yet."
        state_rows.append(
            {
                "environment_key": env_key,
                "segment_type": clean(tracker.get("segment_type")),
                "segment_value": clean(tracker.get("segment_value")),
                "phase_transition_pattern": phase,
                "current_sample_count": metrics["sample"],
                "current_status": classification,
                "environment_health_score": fmt(health),
                "environment_age": environment_age(metrics),
                "last_observed_date": metrics["last_date"],
                "watch_priority": clean(watch.get("priority")) or "UNSET",
                "state_action": action,
                "live_modelling_allowed": "NO",
                "live_execution_allowed": "NO",
                "notes": "Environment state is offline research governance only.",
            }
        )
    return loop_rows, state_rows


def build_summary(loop_rows: list[dict[str, object]], state_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    classes = Counter(str(row["loop_classification"]) for row in loop_rows)
    priorities = Counter(str(row["watch_priority"]) for row in state_rows)
    results_safe = sum(1 for row in read_csv(INPUTS["results_truth"]) if yes(row.get("safe_for_model_validation")))
    values: list[dict[str, object]] = [
        {"metric": "loop_rows", "value": len(loop_rows)},
        {"metric": "environment_state_rows", "value": len(state_rows)},
        {"metric": "active_stable_research", "value": classes.get("ACTIVE_STABLE_RESEARCH", 0)},
        {"metric": "decaying_research", "value": classes.get("DECAYING_RESEARCH", 0)},
        {"metric": "regime_drift_warning", "value": classes.get("REGIME_DRIFT_WARNING", 0)},
        {"metric": "sample_growth_phase", "value": classes.get("SAMPLE_GROWTH_PHASE", 0)},
        {"metric": "retired_research_environment", "value": classes.get("RETIRED_RESEARCH_ENVIRONMENT", 0)},
        {"metric": "high_priority_states", "value": priorities.get("HIGH", 0)},
        {"metric": "medium_priority_states", "value": priorities.get("MEDIUM", 0)},
        {"metric": "low_priority_states", "value": priorities.get("LOW", 0)},
        {"metric": "canonical_safe_results_available", "value": results_safe},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    for path in INPUTS.values():
        if not path.exists():
            values.append({"metric": f"missing_input::{path.name}", "value": "YES"})
    return values


def main() -> None:
    loop_rows, state_rows = build_loop_rows()
    summary = build_summary(loop_rows, state_rows)
    write_csv(OUT, loop_rows, LOOP_FIELDS)
    write_csv(STATE, state_rows, STATE_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 88)
    print("EDGEIQ SHADOW RESEARCH LOOP V1")
    print("=" * 88)
    print(f"loop rows: {len(loop_rows)}")
    print(f"environment state rows: {len(state_rows)}")
    for row in summary:
        if row["metric"] in {"active_stable_research", "decaying_research", "regime_drift_warning", "sample_growth_phase", "live_modelling_yes", "live_execution_yes"}:
            print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {STATE}")


if __name__ == "__main__":
    main()
