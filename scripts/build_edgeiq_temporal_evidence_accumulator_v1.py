from __future__ import annotations

import csv
import math
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

VALIDATION = DATA / "edgeiq_temporal_physics_validation_v1.csv"
RESULTS_TRUTH = DATA / "edgeiq_canonical_results_truth_v1.csv"
TEMPORAL_ENGINE = DATA / "edgeiq_temporal_physics_engine_v1.csv"

OUT = DATA / "edgeiq_temporal_evidence_accumulator_v1.csv"
SUMMARY = DATA / "edgeiq_temporal_evidence_summary_v1.csv"
LONGITUDINAL = DATA / "edgeiq_temporal_pattern_longitudinal_v1.csv"

ACCUMULATOR_FIELDS = [
    "phase_transition_pattern",
    "energy_curve_type",
    "temporal_stability_grade",
    "sample_size",
    "matched_result_rows",
    "wins",
    "places",
    "top4",
    "avg_finish",
    "win_rate",
    "place_rate",
    "top4_rate",
    "rolling_7d_sample",
    "rolling_30d_sample",
    "rolling_90d_sample",
    "rolling_lifetime_sample",
    "sample_growth_rate",
    "result_stability_score",
    "variance_score",
    "evidence_confidence_grade",
    "evidence_status",
    "predictive_research_status",
    "trusted_for_live_modelling",
    "trusted_for_live_execution",
    "notes",
]

LONGITUDINAL_FIELDS = [
    "race_date",
    "phase_transition_pattern",
    "energy_curve_type",
    "temporal_stability_grade",
    "daily_sample",
    "daily_wins",
    "daily_places",
    "daily_top4",
    "daily_avg_finish",
    "cumulative_sample",
    "cumulative_wins",
    "cumulative_places",
    "cumulative_top4",
    "cumulative_avg_finish",
    "cumulative_win_rate",
    "cumulative_place_rate",
    "cumulative_top4_rate",
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


def parse_date(value: object) -> datetime | None:
    text = normalise_date(value)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return None


def canonical_runner_key(row: dict[str, object]) -> str:
    supplied = clean(row.get("canonical_runner_key"))
    if supplied and "|" in supplied:
        return supplied
    race_date = normalise_date(row.get("race_date"))
    track = normalise_track(row.get("track"))
    race_no = normalise_race_no(row.get("race_no"))
    horse = normalise_text(row.get("horse"))
    return f"{race_date}|{track}|{race_no}|{horse}" if race_date and track and race_no and horse else ""


def to_int(value: object) -> int | None:
    text = clean(value)
    if not text:
        return None
    try:
        numeric = int(round(float(re.sub(r"[^0-9.\-]", "", text))))
    except ValueError:
        return None
    return numeric if numeric > 0 else None


def pct(part: int, whole: int) -> str:
    return "" if whole <= 0 else f"{(part / whole) * 100:.2f}"


def avg_finish(finishes: list[int]) -> str:
    return "" if not finishes else f"{sum(finishes) / len(finishes):.2f}"


def safe_result_keys(rows: list[dict[str, str]]) -> set[str]:
    keys: set[str] = set()
    for row in rows:
        if clean(row.get("safe_for_model_validation")) != "YES":
            continue
        if not clean(row.get("finish_position")):
            continue
        key = canonical_runner_key(row)
        if key:
            keys.add(key)
    return keys


def validated_rows(validation_rows: list[dict[str, str]], safe_keys: set[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in validation_rows:
        key = canonical_runner_key(row)
        finish = to_int(row.get("finish_position"))
        race_date = parse_date(row.get("race_date"))
        if not key or key not in safe_keys or finish is None or race_date is None:
            continue
        rows.append(
            {
                "race_date": race_date,
                "race_date_text": race_date.strftime("%Y-%m-%d"),
                "phase_transition_pattern": clean(row.get("phase_transition_pattern")) or "UNKNOWN_PATTERN",
                "energy_curve_type": clean(row.get("energy_curve_type")) or "UNKNOWN_CURVE",
                "temporal_stability_grade": clean(row.get("temporal_stability_grade")) or "UNKNOWN",
                "finish_position": finish,
                "winner": 1 if finish == 1 else 0,
                "place": 1 if finish <= 3 else 0,
                "top4": 1 if finish <= 4 else 0,
            }
        )
    return rows


def group_key(row: dict[str, object]) -> tuple[str, str, str]:
    return (
        str(row["phase_transition_pattern"]),
        str(row["energy_curve_type"]),
        str(row["temporal_stability_grade"]),
    )


def result_stability(finishes: list[int]) -> tuple[float, float]:
    if len(finishes) < 2:
        return 0.0, 100.0 if finishes else 0.0
    variance = statistics.pvariance(finishes)
    stability = max(0.0, 100.0 - min(100.0, variance * 6.0))
    variance_score = min(100.0, variance * 6.0)
    return stability, variance_score


def evidence_grade(sample_size: int, stability: float, variance: float) -> str:
    if sample_size < 25:
        return "F"
    if sample_size < 100:
        return "D"
    if stability >= 72 and variance <= 35:
        return "B"
    if stability >= 55:
        return "C"
    return "D"


def evidence_status(sample_size: int, win_rate: float, place_rate: float, top4_rate: float, variance: float, growth_rate: float) -> str:
    if sample_size < 25:
        return "INSUFFICIENT_EVIDENCE"
    if variance >= 70:
        return "HIGH_VARIANCE_PATTERN"
    if sample_size < 100 and growth_rate > 20:
        return "EMERGING_PATTERN"
    if win_rate >= 16 or place_rate >= 42 or top4_rate >= 62:
        return "EARLY_POSITIVE_SIGNAL"
    if win_rate <= 6 and place_rate <= 22 and top4_rate <= 38:
        return "NEGATIVE_PATTERN"
    return "STABLE_NEUTRAL_PATTERN"


def build_accumulator(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    if not rows:
        return []

    max_date = max(row["race_date"] for row in rows)
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[group_key(row)].append(row)

    output: list[dict[str, object]] = []
    for (pattern, curve, grade), group_rows in sorted(grouped.items()):
        finishes = [int(row["finish_position"]) for row in group_rows]
        sample = len(group_rows)
        wins = sum(int(row["winner"]) for row in group_rows)
        places = sum(int(row["place"]) for row in group_rows)
        top4 = sum(int(row["top4"]) for row in group_rows)
        rolling_7 = [row for row in group_rows if row["race_date"] >= max_date - timedelta(days=7)]
        rolling_30 = [row for row in group_rows if row["race_date"] >= max_date - timedelta(days=30)]
        rolling_90 = [row for row in group_rows if row["race_date"] >= max_date - timedelta(days=90)]
        prior_30 = [row for row in group_rows if max_date - timedelta(days=60) <= row["race_date"] < max_date - timedelta(days=30)]
        growth = ((len(rolling_30) - len(prior_30)) / max(1, len(prior_30))) * 100.0
        stability, variance = result_stability(finishes)
        win_rate = (wins / sample) * 100.0 if sample else 0.0
        place_rate = (places / sample) * 100.0 if sample else 0.0
        top4_rate = (top4 / sample) * 100.0 if sample else 0.0
        status = evidence_status(sample, win_rate, place_rate, top4_rate, variance, growth)

        output.append(
            {
                "phase_transition_pattern": pattern,
                "energy_curve_type": curve,
                "temporal_stability_grade": grade,
                "sample_size": sample,
                "matched_result_rows": sample,
                "wins": wins,
                "places": places,
                "top4": top4,
                "avg_finish": avg_finish(finishes),
                "win_rate": f"{win_rate:.2f}",
                "place_rate": f"{place_rate:.2f}",
                "top4_rate": f"{top4_rate:.2f}",
                "rolling_7d_sample": len(rolling_7),
                "rolling_30d_sample": len(rolling_30),
                "rolling_90d_sample": len(rolling_90),
                "rolling_lifetime_sample": sample,
                "sample_growth_rate": f"{growth:.2f}",
                "result_stability_score": f"{stability:.2f}",
                "variance_score": f"{variance:.2f}",
                "evidence_confidence_grade": evidence_grade(sample, stability, variance),
                "evidence_status": status,
                "predictive_research_status": "RESEARCH_ONLY_EVIDENCE_ACCUMULATION",
                "trusted_for_live_modelling": "NO",
                "trusted_for_live_execution": "NO",
                "notes": "Longitudinal temporal physics evidence only. No betting signal, overlay, rated price, or execution impact.",
            }
        )
    return output


def build_longitudinal(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    daily: dict[tuple[str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = (
            str(row["race_date_text"]),
            str(row["phase_transition_pattern"]),
            str(row["energy_curve_type"]),
            str(row["temporal_stability_grade"]),
        )
        daily[key].append(row)

    running: dict[tuple[str, str, str], dict[str, object]] = defaultdict(
        lambda: {"sample": 0, "wins": 0, "places": 0, "top4": 0, "finishes": []}
    )
    output: list[dict[str, object]] = []

    for (race_date, pattern, curve, grade), day_rows in sorted(daily.items()):
        run_key = (pattern, curve, grade)
        day_finishes = [int(row["finish_position"]) for row in day_rows]
        day_wins = sum(int(row["winner"]) for row in day_rows)
        day_places = sum(int(row["place"]) for row in day_rows)
        day_top4 = sum(int(row["top4"]) for row in day_rows)
        run = running[run_key]
        run["sample"] = int(run["sample"]) + len(day_rows)
        run["wins"] = int(run["wins"]) + day_wins
        run["places"] = int(run["places"]) + day_places
        run["top4"] = int(run["top4"]) + day_top4
        run["finishes"].extend(day_finishes)
        cumulative_sample = int(run["sample"])

        output.append(
            {
                "race_date": race_date,
                "phase_transition_pattern": pattern,
                "energy_curve_type": curve,
                "temporal_stability_grade": grade,
                "daily_sample": len(day_rows),
                "daily_wins": day_wins,
                "daily_places": day_places,
                "daily_top4": day_top4,
                "daily_avg_finish": avg_finish(day_finishes),
                "cumulative_sample": cumulative_sample,
                "cumulative_wins": int(run["wins"]),
                "cumulative_places": int(run["places"]),
                "cumulative_top4": int(run["top4"]),
                "cumulative_avg_finish": avg_finish(list(run["finishes"])),
                "cumulative_win_rate": pct(int(run["wins"]), cumulative_sample),
                "cumulative_place_rate": pct(int(run["places"]), cumulative_sample),
                "cumulative_top4_rate": pct(int(run["top4"]), cumulative_sample),
                "trusted_for_live_modelling": "NO",
                "trusted_for_live_execution": "NO",
                "notes": "Daily cumulative research trace for measured temporal physics evidence only.",
            }
        )
    return output


def build_summary(accumulator_rows: list[dict[str, object]], validated: list[dict[str, object]], temporal_rows: list[dict[str, str]], truth_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    statuses = Counter(str(row.get("evidence_status")) for row in accumulator_rows)
    grades = Counter(str(row.get("evidence_confidence_grade")) for row in accumulator_rows)
    summary: list[dict[str, object]] = [
        {"metric": "total_patterns", "value": len(accumulator_rows)},
        {"metric": "temporal_input_rows", "value": len(temporal_rows)},
        {"metric": "canonical_truth_rows", "value": len(truth_rows)},
        {"metric": "validated_rows", "value": len(validated)},
        {"metric": "total_wins", "value": sum(int(row["winner"]) for row in validated)},
        {"metric": "total_places", "value": sum(int(row["place"]) for row in validated)},
        {"metric": "total_top4", "value": sum(int(row["top4"]) for row in validated)},
        {"metric": "emerging_patterns", "value": statuses.get("EMERGING_PATTERN", 0)},
        {"metric": "stable_neutral_patterns", "value": statuses.get("STABLE_NEUTRAL_PATTERN", 0)},
        {"metric": "high_variance_patterns", "value": statuses.get("HIGH_VARIANCE_PATTERN", 0)},
        {"metric": "insufficient_evidence_patterns", "value": statuses.get("INSUFFICIENT_EVIDENCE", 0)},
        {"metric": "early_positive_signal_patterns", "value": statuses.get("EARLY_POSITIVE_SIGNAL", 0)},
        {"metric": "negative_patterns", "value": statuses.get("NEGATIVE_PATTERN", 0)},
        {"metric": "trusted_for_live_modelling_yes", "value": 0},
        {"metric": "trusted_for_live_execution_yes", "value": 0},
    ]
    for key, value in statuses.most_common():
        summary.append({"metric": f"evidence_status::{key}", "value": value})
    for key, value in grades.most_common():
        summary.append({"metric": f"evidence_confidence_grade::{key}", "value": value})
    return summary


def main() -> None:
    validation_rows = read_csv(VALIDATION)
    truth_rows = read_csv(RESULTS_TRUTH)
    temporal_rows = read_csv(TEMPORAL_ENGINE)
    safe_keys = safe_result_keys(truth_rows)
    safe_validated_rows = validated_rows(validation_rows, safe_keys)
    accumulator_rows = build_accumulator(safe_validated_rows)
    longitudinal_rows = build_longitudinal(safe_validated_rows)
    summary_rows = build_summary(accumulator_rows, safe_validated_rows, temporal_rows, truth_rows)

    write_csv(OUT, accumulator_rows, ACCUMULATOR_FIELDS)
    write_csv(LONGITUDINAL, longitudinal_rows, LONGITUDINAL_FIELDS)
    write_csv(SUMMARY, summary_rows, SUMMARY_FIELDS)

    statuses = Counter(str(row.get("evidence_status")) for row in accumulator_rows)
    print("=" * 88)
    print("EDGEIQ TEMPORAL EVIDENCE ACCUMULATOR V1")
    print("=" * 88)
    print(f"validated safe rows: {len(safe_validated_rows)}")
    print(f"pattern rows: {len(accumulator_rows)}")
    print(f"longitudinal rows: {len(longitudinal_rows)}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {LONGITUDINAL}")
    for key, value in statuses.most_common():
        print(f"  {key}: {value}")
    print("live modelling/execution: 0 / 0")


if __name__ == "__main__":
    main()
