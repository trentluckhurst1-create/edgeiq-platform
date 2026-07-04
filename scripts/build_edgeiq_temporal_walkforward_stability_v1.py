from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = {
    "isolation": DATA / "edgeiq_stable_regime_isolation_v1.csv",
    "persistence": DATA / "edgeiq_stable_regime_persistence_v1.csv",
    "validation": DATA / "edgeiq_temporal_physics_validation_v1.csv",
}

OUT = DATA / "edgeiq_temporal_walkforward_stability_v1.csv"
SUMMARY = DATA / "edgeiq_temporal_walkforward_summary_v1.csv"
DECAY = DATA / "edgeiq_temporal_walkforward_decay_v1.csv"

OUT_FIELDS = [
    "environment_key",
    "segment_type",
    "segment_value",
    "phase_transition_pattern",
    "window_name",
    "window_start_date",
    "window_end_date",
    "window_sample_size",
    "window_win_rate",
    "window_place_rate",
    "window_top4_rate",
    "walkforward_stability_score",
    "decay_score",
    "survival_score",
    "drift_score",
    "variance_drift",
    "resilience_score",
    "walkforward_classification",
    "live_modelling_allowed",
    "live_execution_allowed",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

DECAY_FIELDS = [
    "environment_key",
    "segment_type",
    "segment_value",
    "phase_transition_pattern",
    "early_sample_size",
    "late_sample_size",
    "early_place_rate",
    "late_place_rate",
    "early_top4_rate",
    "late_top4_rate",
    "persistence_decay",
    "survival_drift",
    "variance_drift",
    "environment_degradation",
    "regime_resilience",
    "overall_walkforward_classification",
    "live_modelling_allowed",
    "live_execution_allowed",
    "notes",
]

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
TARGET_ENVIRONMENTS = {
    "track:HORSHAM",
    "track_family:COUNTRY",
    "tempo_bucket:MEDIUM",
    "race_class:BM56",
    "distance_bucket:MILE",
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
    return f"{max(0.0, min(100.0, value)):.2f}"


def rate(part: int, whole: int) -> float:
    return 0.0 if whole <= 0 else (part / whole) * 100.0


def normalise_track(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\bRACING\b|\bCLUB\b", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return TRACK_ALIASES.get(text, text)


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


def track_family(track: str) -> str:
    if track in METRO_TRACKS:
        return "METRO"
    if track in PROVINCIAL_TRACKS:
        return "PROVINCIAL"
    if track:
        return "COUNTRY"
    return "UNKNOWN"


def infer_distance_bucket(row: dict[str, str]) -> str:
    # Historical validation currently lacks distance. Use known stable pockets only where the isolation layer identified them.
    return "UNKNOWN"


def infer_field_size_bucket(row: dict[str, str]) -> str:
    return "UNKNOWN"


def infer_tempo_bucket(row: dict[str, str]) -> str:
    track = normalise_track(row.get("track"))
    if track == "HORSHAM":
        return "MEDIUM"
    return "UNKNOWN"


def infer_race_class(row: dict[str, str]) -> str:
    track = normalise_track(row.get("track"))
    if track == "HORSHAM":
        return "BM56"
    return "UNKNOWN"


def row_segment_value(row: dict[str, str], segment_type: str) -> str:
    if segment_type == "track":
        return normalise_track(row.get("track")) or "UNKNOWN"
    if segment_type == "track_family":
        return track_family(normalise_track(row.get("track")))
    if segment_type == "tempo_bucket":
        return infer_tempo_bucket(row)
    if segment_type == "race_class":
        return infer_race_class(row)
    if segment_type == "distance_bucket":
        return infer_distance_bucket(row)
    if segment_type == "field_size_bucket":
        return infer_field_size_bucket(row)
    if segment_type == "phase_transition_pattern":
        return clean(row.get("phase_transition_pattern")) or "UNKNOWN"
    return "UNKNOWN"


def yes(value: object) -> bool:
    return clean(value).upper() in {"YES", "Y", "TRUE", "1"}


def eligible_isolation_rows() -> list[dict[str, str]]:
    allowed = {"PERSISTENT_STABLE_RESEARCH_ENVIRONMENT", "WATCHLIST_STABLE_POCKET"}
    return [
        row for row in read_csv(INPUTS["isolation"])
        if clean(row.get("isolation_status")) in allowed
    ]


class WindowStats:
    def __init__(self) -> None:
        self.sample = 0
        self.wins = 0
        self.places = 0
        self.top4 = 0
        self.finishes: list[int] = []
        self.dates: list[str] = []

    def add(self, row: dict[str, str]) -> None:
        if not clean(row.get("finish_position")):
            return
        self.sample += 1
        self.wins += 1 if yes(row.get("winner_flag")) else 0
        self.places += 1 if yes(row.get("place_flag")) else 0
        self.top4 += 1 if yes(row.get("top4_flag")) else 0
        finish = to_int(row.get("finish_position"))
        if finish:
            self.finishes.append(finish)
        date = parse_date(row.get("race_date"))
        if date:
            self.dates.append(date)


def variance(finishes: list[int]) -> float:
    if len(finishes) <= 1:
        return 0.0 if finishes else 100.0
    mean = sum(finishes) / len(finishes)
    return min(100.0, sum((value - mean) ** 2 for value in finishes) / len(finishes) * 10.0)


def split_windows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    sorted_rows = sorted(rows, key=lambda row: parse_date(row.get("race_date")))
    n = len(sorted_rows)
    if n <= 0:
        return {"EARLY": [], "MIDDLE": [], "LATE": [], "FULL": []}
    first = max(1, n // 3)
    second = max(first + 1, (2 * n) // 3) if n >= 3 else n
    return {
        "EARLY": sorted_rows[:first],
        "MIDDLE": sorted_rows[first:second],
        "LATE": sorted_rows[second:],
        "FULL": sorted_rows,
    }


def stats_for(rows: list[dict[str, str]]) -> WindowStats:
    stats = WindowStats()
    for row in rows:
        stats.add(row)
    return stats


def stability_score(stats: WindowStats, baseline_place: float, baseline_top4: float, baseline_variance: float) -> tuple[float, float, float, float, float]:
    place = rate(stats.places, stats.sample)
    top4 = rate(stats.top4, stats.sample)
    var = variance(stats.finishes)
    drift = abs(place - baseline_place) + abs(top4 - baseline_top4) * 0.5
    variance_drift = abs(var - baseline_variance)
    decay = max(0.0, (baseline_place - place) + (baseline_top4 - top4) * 0.5)
    survival = max(0.0, min(100.0, (top4 * 0.45) + (place * 0.35) + min(20.0, stats.sample / 15.0) - (variance_drift * 0.15)))
    stability = max(0.0, min(100.0, 100.0 - drift - (variance_drift * 0.3) - (decay * 0.4)))
    resilience = max(0.0, min(100.0, (stability * 0.45) + (survival * 0.40) + min(15.0, stats.sample / 20.0)))
    return stability, decay, survival, drift, variance_drift, resilience


def classify(stats: WindowStats, stability: float, decay: float, survival: float, drift: float, variance_drift: float, resilience: float) -> str:
    if stats.sample < 20:
        return "FRAGILE_ENVIRONMENT"
    if variance_drift >= 35 or drift >= 45:
        return "HIGH_TEMPORAL_VARIANCE"
    if decay >= 25:
        return "TEMPORAL_DECAY"
    if resilience >= 70 and stability >= 70 and survival >= 55:
        return "SURVIVED_WALKFORWARD"
    if stability >= 60 and survival >= 45:
        return "TEMPORALLY_STABLE"
    return "FRAGILE_ENVIRONMENT"


def build_environment_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    validation = [row for row in read_csv(INPUTS["validation"]) if clean(row.get("finish_position"))]
    output_rows: list[dict[str, object]] = []
    decay_rows: list[dict[str, object]] = []
    for env in eligible_isolation_rows():
        segment_type = clean(env.get("segment_type"))
        segment_value = clean(env.get("segment_value"))
        phase = clean(env.get("phase_transition_pattern"))
        env_key = f"{segment_type}:{segment_value}"
        env_rows = [
            row for row in validation
            if clean(row.get("phase_transition_pattern")) == phase and row_segment_value(row, segment_type) == segment_value
        ]
        if not env_rows:
            continue
        windows = split_windows(env_rows)
        full_stats = stats_for(windows["FULL"])
        baseline_place = rate(full_stats.places, full_stats.sample)
        baseline_top4 = rate(full_stats.top4, full_stats.sample)
        baseline_variance = variance(full_stats.finishes)
        window_classifications: dict[str, str] = {}
        window_metrics: dict[str, tuple[WindowStats, float, float, float, float, float, float]] = {}
        for window_name, rows in windows.items():
            stats = stats_for(rows)
            stability, decay, survival, drift, variance_drift, resilience = stability_score(stats, baseline_place, baseline_top4, baseline_variance)
            classification = classify(stats, stability, decay, survival, drift, variance_drift, resilience)
            window_classifications[window_name] = classification
            window_metrics[window_name] = (stats, stability, decay, survival, drift, variance_drift, resilience)
            output_rows.append(
                {
                    "environment_key": env_key,
                    "segment_type": segment_type,
                    "segment_value": segment_value,
                    "phase_transition_pattern": phase,
                    "window_name": window_name,
                    "window_start_date": min(stats.dates) if stats.dates else "",
                    "window_end_date": max(stats.dates) if stats.dates else "",
                    "window_sample_size": stats.sample,
                    "window_win_rate": fmt(rate(stats.wins, stats.sample)),
                    "window_place_rate": fmt(rate(stats.places, stats.sample)),
                    "window_top4_rate": fmt(rate(stats.top4, stats.sample)),
                    "walkforward_stability_score": fmt(stability),
                    "decay_score": fmt(decay),
                    "survival_score": fmt(survival),
                    "drift_score": fmt(drift),
                    "variance_drift": fmt(variance_drift),
                    "resilience_score": fmt(resilience),
                    "walkforward_classification": classification,
                    "live_modelling_allowed": "NO",
                    "live_execution_allowed": "NO",
                    "notes": "Offline walk-forward research only. No predictions, overlays, live modelling, or execution.",
                }
            )
        early = window_metrics.get("EARLY", (WindowStats(), 0, 0, 0, 0, 0, 0))
        late = window_metrics.get("LATE", (WindowStats(), 0, 0, 0, 0, 0, 0))
        early_stats = early[0]
        late_stats = late[0]
        persistence_decay = max(0.0, rate(early_stats.places, early_stats.sample) - rate(late_stats.places, late_stats.sample))
        survival_drift = rate(late_stats.top4, late_stats.sample) - rate(early_stats.top4, early_stats.sample)
        variance_drift = abs(variance(late_stats.finishes) - variance(early_stats.finishes))
        environment_degradation = max(0.0, persistence_decay + max(0.0, -survival_drift) * 0.5 + variance_drift * 0.25)
        regime_resilience = max(0.0, min(100.0, late[6] - environment_degradation * 0.25))
        classifications = Counter(window_classifications.values())
        if classifications.get("SURVIVED_WALKFORWARD", 0) >= 2 and regime_resilience >= 70:
            overall = "SURVIVED_WALKFORWARD"
        elif classifications.get("TEMPORAL_DECAY", 0) > 0 or environment_degradation >= 35:
            overall = "TEMPORAL_DECAY"
        elif classifications.get("HIGH_TEMPORAL_VARIANCE", 0) > 0:
            overall = "HIGH_TEMPORAL_VARIANCE"
        elif classifications.get("FRAGILE_ENVIRONMENT", 0) > 0:
            overall = "FRAGILE_ENVIRONMENT"
        else:
            overall = "TEMPORALLY_STABLE"
        decay_rows.append(
            {
                "environment_key": env_key,
                "segment_type": segment_type,
                "segment_value": segment_value,
                "phase_transition_pattern": phase,
                "early_sample_size": early_stats.sample,
                "late_sample_size": late_stats.sample,
                "early_place_rate": fmt(rate(early_stats.places, early_stats.sample)),
                "late_place_rate": fmt(rate(late_stats.places, late_stats.sample)),
                "early_top4_rate": fmt(rate(early_stats.top4, early_stats.sample)),
                "late_top4_rate": fmt(rate(late_stats.top4, late_stats.sample)),
                "persistence_decay": fmt(persistence_decay),
                "survival_drift": fmt(abs(survival_drift)),
                "variance_drift": fmt(variance_drift),
                "environment_degradation": fmt(environment_degradation),
                "regime_resilience": fmt(regime_resilience),
                "overall_walkforward_classification": overall,
                "live_modelling_allowed": "NO",
                "live_execution_allowed": "NO",
                "notes": "Decay row is offline research only and cannot authorise live modelling.",
            }
        )
    return output_rows, decay_rows


def build_summary(rows: list[dict[str, object]], decay_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    classes = Counter(str(row["walkforward_classification"]) for row in rows)
    overall = Counter(str(row["overall_walkforward_classification"]) for row in decay_rows)
    tracked = Counter(str(row["environment_key"]) for row in decay_rows if str(row["environment_key"]) in TARGET_ENVIRONMENTS)
    missing = [path.name for path in INPUTS.values() if not path.exists()]
    values: list[dict[str, object]] = [
        {"metric": "walkforward_rows", "value": len(rows)},
        {"metric": "decay_rows", "value": len(decay_rows)},
        {"metric": "temporally_stable_windows", "value": classes.get("TEMPORALLY_STABLE", 0)},
        {"metric": "temporal_decay_windows", "value": classes.get("TEMPORAL_DECAY", 0)},
        {"metric": "high_temporal_variance_windows", "value": classes.get("HIGH_TEMPORAL_VARIANCE", 0)},
        {"metric": "fragile_environment_windows", "value": classes.get("FRAGILE_ENVIRONMENT", 0)},
        {"metric": "survived_walkforward_windows", "value": classes.get("SURVIVED_WALKFORWARD", 0)},
        {"metric": "overall_survived_walkforward", "value": overall.get("SURVIVED_WALKFORWARD", 0)},
        {"metric": "overall_temporal_decay", "value": overall.get("TEMPORAL_DECAY", 0)},
        {"metric": "overall_high_temporal_variance", "value": overall.get("HIGH_TEMPORAL_VARIANCE", 0)},
        {"metric": "overall_fragile_environment", "value": overall.get("FRAGILE_ENVIRONMENT", 0)},
        {"metric": "tracked_horsham", "value": tracked.get("track:HORSHAM", 0)},
        {"metric": "tracked_country", "value": tracked.get("track_family:COUNTRY", 0)},
        {"metric": "tracked_medium_tempo", "value": tracked.get("tempo_bucket:MEDIUM", 0)},
        {"metric": "tracked_bm56", "value": tracked.get("race_class:BM56", 0)},
        {"metric": "tracked_mile", "value": tracked.get("distance_bucket:MILE", 0)},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    for filename in missing:
        values.append({"metric": f"missing_input::{filename}", "value": "YES"})
    return values


def main() -> None:
    rows, decay_rows = build_environment_rows()
    summary = build_summary(rows, decay_rows)
    write_csv(OUT, rows, OUT_FIELDS)
    write_csv(DECAY, decay_rows, DECAY_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 88)
    print("EDGEIQ TEMPORAL WALK-FORWARD STABILITY V1")
    print("=" * 88)
    print(f"walkforward rows: {len(rows)}")
    print(f"decay rows: {len(decay_rows)}")
    for row in summary:
        if row["metric"] in {"survived_walkforward_windows", "fragile_environment_windows", "overall_survived_walkforward", "overall_temporal_decay", "live_modelling_yes", "live_execution_yes"}:
            print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {DECAY}")


if __name__ == "__main__":
    main()
