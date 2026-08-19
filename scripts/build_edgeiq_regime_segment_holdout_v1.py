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

INPUTS = {
    "validation": DATA / "edgeiq_temporal_physics_validation_v1.csv",
    "pattern_performance": DATA / "edgeiq_temporal_pattern_performance_v1.csv",
    "regime": DATA / "edgeiq_temporal_research_regime_engine_v1.csv",
    "shadow_controls": DATA / "edgeiq_shadow_stability_controls_v1.csv",
    "fields": DATA / "edgeiq_vic_three_day_race_fields.csv",
    "race_shape": DATA / "edgeiq_race_shape_response_v1.csv",
    "race_shape_v2": DATA / "edgeiq_race_shape_engine_v2.csv",
}

OUT = DATA / "edgeiq_regime_segment_holdout_v1.csv"
SUMMARY = DATA / "edgeiq_regime_segment_holdout_summary_v1.csv"
STABILITY_MAP = DATA / "edgeiq_regime_segment_stability_map_v1.csv"

OUT_FIELDS = [
    "segment_type",
    "segment_value",
    "phase_transition_pattern",
    "sample_size",
    "wins",
    "places",
    "top4",
    "win_rate",
    "place_rate",
    "top4_rate",
    "variance_score",
    "stability_score",
    "positive_repeatability",
    "negative_repeatability",
    "regime_conflict_score",
    "holdout_classification",
    "holdout_status",
    "live_modelling_allowed",
    "live_execution_allowed",
    "notes",
]

MAP_FIELDS = [
    "segment_type",
    "segment_value",
    "sample_size",
    "dominant_classification",
    "stable_segments",
    "unstable_segments",
    "high_variance_segments",
    "low_sample_segments",
    "conflicted_segments",
    "avg_place_rate",
    "avg_top4_rate",
    "avg_variance_score",
    "regime_conflict_score",
    "live_modelling_allowed",
    "live_execution_allowed",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

TRACK_ALIASES = {
    "BET365 YARRA VALLEY": "YARRA VALLEY",
    "SPORTSBET WANGARATTA": "WANGARATTA",
    "SOUTHSIDE PAKENHAM": "PAKENHAM",
    "SPORTSBET PAKENHAM": "PAKENHAM",
    "PAKENHAM SYNTHETIC": "PAKENHAM",
    "BALLARAT SYNTHETIC": "BALLARAT",
    "GEELONG SYNTHETIC": "GEELONG",
    "THE VALLEY": "MOONEE VALLEY",
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
    track = re.sub(r"\bRACING\b|\bCLUB\b", "", track)
    track = re.sub(r"\s+", " ", track).strip()
    return TRACK_ALIASES.get(track, track)


def normalise_date(value: object) -> str:
    text = clean(value).replace("/", "-")
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%m-%y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    match = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return text[:10]


def normalise_race_no(value: object) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def race_key(row: dict[str, object]) -> str:
    date = normalise_date(row.get("race_date"))
    track = normalise_track(row.get("track"))
    race_no = normalise_race_no(row.get("race_no"))
    return f"{date}|{track}|{race_no}" if date and track and race_no else ""


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


def rate(part: int, whole: int) -> float:
    return 0.0 if whole <= 0 else (part / whole) * 100.0


def fmt(value: float) -> str:
    return f"{value:.2f}"


def distance_bucket(value: object) -> str:
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


def field_size_bucket(value: int) -> str:
    if value <= 0:
        return "UNKNOWN"
    if value <= 7:
        return "SMALL"
    if value <= 11:
        return "MEDIUM"
    return "LARGE"


def track_family(track: str) -> str:
    if track in METRO_TRACKS:
        return "METRO"
    if track in PROVINCIAL_TRACKS:
        return "PROVINCIAL"
    if track:
        return "COUNTRY"
    return "UNKNOWN"


def tempo_bucket(value: object) -> str:
    number = to_float(value)
    if math.isnan(number):
        text = normalise_text(value)
        if any(token in text for token in ["HIGH", "FAST", "PRESSURE", "COLLAPSE"]):
            return "HIGH"
        if any(token in text for token in ["LOW", "SOFT", "SLOW"]):
            return "LOW"
        if text:
            return "MEDIUM"
        return "UNKNOWN"
    if number >= 7:
        return "HIGH"
    if number >= 4:
        return "MEDIUM"
    return "LOW"


def yes(value: object) -> bool:
    return clean(value).upper() in {"YES", "Y", "TRUE", "1"}


def build_context() -> dict[str, dict[str, str]]:
    context: dict[str, dict[str, str]] = {}
    field_counts: Counter[str] = Counter()
    for row in read_csv(INPUTS["fields"]):
        key = race_key(row)
        if not key:
            continue
        field_counts[key] += 1
        track = normalise_track(row.get("track"))
        context.setdefault(
            key,
            {
                "track": track,
                "track_family": track_family(track),
                "distance_bucket": distance_bucket(row.get("distance")),
                "race_class": clean(row.get("race_class")) or "UNKNOWN",
                "tempo_bucket": tempo_bucket(row.get("pace_profile") or row.get("race_state")),
            },
        )
    for key, count in field_counts.items():
        context.setdefault(key, {})
        context[key]["field_size_bucket"] = field_size_bucket(count)
    for row in read_csv(INPUTS["race_shape"]):
        key = race_key(row)
        if not key:
            continue
        context.setdefault(key, {})
        context[key]["tempo_bucket"] = tempo_bucket(row.get("pace_pressure_index") or row.get("race_shape_label"))
        context[key]["field_size_bucket"] = field_size_bucket(to_int(row.get("field_size")))
    return context


class SegmentStats:
    def __init__(self) -> None:
        self.sample_size = 0
        self.wins = 0
        self.places = 0
        self.top4 = 0
        self.finish_positions: list[int] = []
        self.positive = 0
        self.negative = 0

    def add(self, row: dict[str, str]) -> None:
        if not clean(row.get("finish_position")):
            return
        self.sample_size += 1
        self.wins += 1 if yes(row.get("winner_flag")) else 0
        self.places += 1 if yes(row.get("place_flag")) else 0
        self.top4 += 1 if yes(row.get("top4_flag")) else 0
        finish = to_int(row.get("finish_position"))
        if finish:
            self.finish_positions.append(finish)
        grade = clean(row.get("validation_grade"))
        if grade == "HISTORICALLY_POSITIVE":
            self.positive += 1
        if grade in {"HISTORICALLY_NEGATIVE", "LOW_SAMPLE_PATTERN"}:
            self.negative += 1


def variance_score(finishes: list[int]) -> float:
    if len(finishes) <= 1:
        return 100.0 if finishes else 0.0
    mean = sum(finishes) / len(finishes)
    variance = sum((value - mean) ** 2 for value in finishes) / len(finishes)
    return min(100.0, variance * 10.0)


def stability_score(sample_size: int, variance: float, positive_repeat: float, conflict: float) -> float:
    sample_component = min(40.0, sample_size / 25.0)
    repeat_component = min(35.0, positive_repeat * 0.35)
    variance_component = max(0.0, 20.0 - variance * 0.2)
    conflict_penalty = min(25.0, conflict * 0.25)
    return max(0.0, min(100.0, sample_component + repeat_component + variance_component - conflict_penalty))


def classify(sample_size: int, place_rate: float, top4_rate: float, variance: float, stability: float, pos_repeat: float, neg_repeat: float, conflict: float) -> str:
    if sample_size < 20:
        return "LOW_SAMPLE_ENVIRONMENT"
    if conflict >= 35 or (pos_repeat >= 45 and neg_repeat >= 15):
        return "CONFLICTED_ENVIRONMENT"
    if variance >= 45:
        return "HIGH_VARIANCE_ENVIRONMENT"
    if stability >= 60 and place_rate >= 35 and top4_rate >= 55 and neg_repeat < 12:
        return "STABLE_HOLDOUT_ENVIRONMENT"
    if place_rate <= 20 or top4_rate <= 35 or neg_repeat >= 25:
        return "UNSTABLE_HOLDOUT_ENVIRONMENT"
    return "CONFLICTED_ENVIRONMENT"


def build_segments() -> list[dict[str, object]]:
    context = build_context()
    buckets: dict[tuple[str, str, str], SegmentStats] = defaultdict(SegmentStats)
    for row in read_csv(INPUTS["validation"]):
        if not clean(row.get("finish_position")):
            continue
        key = race_key(row)
        ctx = context.get(key, {})
        track = normalise_track(row.get("track")) or "UNKNOWN"
        segment_values = {
            "track": track,
            "track_family": ctx.get("track_family") or track_family(track),
            "distance_bucket": ctx.get("distance_bucket") or "UNKNOWN",
            "field_size_bucket": ctx.get("field_size_bucket") or "UNKNOWN",
            "tempo_bucket": ctx.get("tempo_bucket") or "UNKNOWN",
            "race_class": ctx.get("race_class") or "UNKNOWN",
            "phase_transition_pattern": clean(row.get("phase_transition_pattern")) or "UNKNOWN",
        }
        phase = clean(row.get("phase_transition_pattern")) or "UNKNOWN"
        for segment_type, segment_value in segment_values.items():
            buckets[(segment_type, segment_value, phase)].add(row)

    rows: list[dict[str, object]] = []
    for (segment_type_name, segment_value, phase), stats in sorted(buckets.items()):
        sample = stats.sample_size
        win_rate = rate(stats.wins, sample)
        place_rate = rate(stats.places, sample)
        top4_rate = rate(stats.top4, sample)
        variance = variance_score(stats.finish_positions)
        positive_repeat = rate(stats.positive, sample)
        negative_repeat = rate(stats.negative, sample)
        conflict = min(100.0, negative_repeat + (variance * 0.35))
        stability = stability_score(sample, variance, positive_repeat, conflict)
        classification = classify(sample, place_rate, top4_rate, variance, stability, positive_repeat, negative_repeat, conflict)
        rows.append(
            {
                "segment_type": segment_type_name,
                "segment_value": segment_value,
                "phase_transition_pattern": phase,
                "sample_size": sample,
                "wins": stats.wins,
                "places": stats.places,
                "top4": stats.top4,
                "win_rate": fmt(win_rate),
                "place_rate": fmt(place_rate),
                "top4_rate": fmt(top4_rate),
                "variance_score": fmt(variance),
                "stability_score": fmt(stability),
                "positive_repeatability": fmt(positive_repeat),
                "negative_repeatability": fmt(negative_repeat),
                "regime_conflict_score": fmt(conflict),
                "holdout_classification": classification,
                "holdout_status": "RESEARCH_ONLY",
                "live_modelling_allowed": "NO",
                "live_execution_allowed": "NO",
                "notes": "Offline regime segment holdout only. No promotion, predictions, overlays, ratings, or execution.",
            }
        )
    return rows


def build_stability_map(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["segment_type"]), str(row["segment_value"]))].append(row)
    out: list[dict[str, object]] = []
    for (segment_type_name, segment_value), items in sorted(grouped.items()):
        classes = Counter(str(item["holdout_classification"]) for item in items)
        dominant = classes.most_common(1)[0][0] if classes else ""
        sample = sum(to_int(item.get("sample_size")) for item in items)
        avg_place = sum(to_float(item.get("place_rate")) for item in items) / len(items)
        avg_top4 = sum(to_float(item.get("top4_rate")) for item in items) / len(items)
        avg_variance = sum(to_float(item.get("variance_score")) for item in items) / len(items)
        avg_conflict = sum(to_float(item.get("regime_conflict_score")) for item in items) / len(items)
        out.append(
            {
                "segment_type": segment_type_name,
                "segment_value": segment_value,
                "sample_size": sample,
                "dominant_classification": dominant,
                "stable_segments": classes.get("STABLE_HOLDOUT_ENVIRONMENT", 0),
                "unstable_segments": classes.get("UNSTABLE_HOLDOUT_ENVIRONMENT", 0),
                "high_variance_segments": classes.get("HIGH_VARIANCE_ENVIRONMENT", 0),
                "low_sample_segments": classes.get("LOW_SAMPLE_ENVIRONMENT", 0),
                "conflicted_segments": classes.get("CONFLICTED_ENVIRONMENT", 0),
                "avg_place_rate": fmt(avg_place),
                "avg_top4_rate": fmt(avg_top4),
                "avg_variance_score": fmt(avg_variance),
                "regime_conflict_score": fmt(avg_conflict),
                "live_modelling_allowed": "NO",
                "live_execution_allowed": "NO",
                "notes": "Segment stability map is research-only and cannot authorise live modelling.",
            }
        )
    return out


def build_summary(rows: list[dict[str, object]], stability_map: list[dict[str, object]]) -> list[dict[str, object]]:
    classes = Counter(str(row["holdout_classification"]) for row in rows)
    segment_types = Counter(str(row["segment_type"]) for row in rows)
    shadow_controls = read_csv(INPUTS["shadow_controls"])
    shadow_overall = "UNKNOWN"
    for row in shadow_controls:
        if clean(row.get("stability_classification")) in {"UNSTABLE_SHADOW_RESEARCH", "CONCENTRATED_SAMPLE_RISK", "INSUFFICIENT_STABILITY"}:
            shadow_overall = clean(row.get("stability_classification"))
            break
    missing = [path.name for path in INPUTS.values() if not path.exists()]
    values: list[dict[str, object]] = [
        {"metric": "holdout_rows", "value": len(rows)},
        {"metric": "stability_map_rows", "value": len(stability_map)},
        {"metric": "stable_holdout_environments", "value": classes.get("STABLE_HOLDOUT_ENVIRONMENT", 0)},
        {"metric": "unstable_holdout_environments", "value": classes.get("UNSTABLE_HOLDOUT_ENVIRONMENT", 0)},
        {"metric": "high_variance_environments", "value": classes.get("HIGH_VARIANCE_ENVIRONMENT", 0)},
        {"metric": "low_sample_environments", "value": classes.get("LOW_SAMPLE_ENVIRONMENT", 0)},
        {"metric": "conflicted_environments", "value": classes.get("CONFLICTED_ENVIRONMENT", 0)},
        {"metric": "shadow_stability_blocker", "value": shadow_overall},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    for segment_type_name, count in sorted(segment_types.items()):
        values.append({"metric": f"segment_type::{segment_type_name}", "value": count})
    for filename in missing:
        values.append({"metric": f"missing_input::{filename}", "value": "YES"})
    return values


def main() -> None:
    rows = build_segments()
    stability_map = build_stability_map(rows)
    summary = build_summary(rows, stability_map)
    write_csv(OUT, rows, OUT_FIELDS)
    write_csv(STABILITY_MAP, stability_map, MAP_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 88)
    print("EDGEIQ REGIME SEGMENT HOLDOUT ENGINE V1")
    print("=" * 88)
    print(f"holdout rows: {len(rows)}")
    print(f"stability map rows: {len(stability_map)}")
    for row in summary:
        if row["metric"] in {"stable_holdout_environments", "unstable_holdout_environments", "high_variance_environments", "low_sample_environments", "conflicted_environments", "live_modelling_yes", "live_execution_yes"}:
            print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {STABILITY_MAP}")


if __name__ == "__main__":
    main()
