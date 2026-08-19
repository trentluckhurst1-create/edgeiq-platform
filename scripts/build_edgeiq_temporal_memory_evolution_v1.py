from __future__ import annotations

import csv
import math
import re
import statistics
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = {
    "identity_memory": DATA / "edgeiq_temporal_identity_memory_v1.csv",
    "temporal_engine": DATA / "edgeiq_temporal_physics_engine_v1.csv",
    "validation": DATA / "edgeiq_temporal_physics_validation_v1.csv",
    "results_truth": DATA / "edgeiq_canonical_results_truth_v1.csv",
    "evidence": DATA / "edgeiq_temporal_evidence_accumulator_v1.csv",
}

OUT = DATA / "edgeiq_temporal_memory_evolution_v1.csv"
SUMMARY = DATA / "edgeiq_temporal_memory_evolution_summary_v1.csv"
WATCHLIST = DATA / "edgeiq_temporal_identity_evolution_watchlist_v1.csv"

EVOLUTION_FIELDS = [
    "horse",
    "horse_key",
    "starts_tracked",
    "career_phase",
    "early_career_pattern",
    "mid_career_pattern",
    "late_career_pattern",
    "pattern_shift_detected",
    "pattern_shift_type",
    "energy_curve_shift",
    "consistency_trend",
    "volatility_trend",
    "finish_position_trend",
    "temporal_score_trend",
    "evolution_stability_grade",
    "evolution_label",
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
    "evolution_label",
    "pattern_shift_type",
    "energy_curve_shift",
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


def parse_date(value: object) -> datetime:
    text = normalise_date(value)
    try:
        return datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return datetime.min


def horse_key(value: object) -> str:
    return normalise_text(value)


def start_key(row: dict[str, object]) -> str:
    date = normalise_date(row.get("race_date"))
    track = normalise_track(row.get("track"))
    race_no = normalise_race_no(row.get("race_no"))
    horse = horse_key(row.get("horse"))
    return f"{date}|{track}|{race_no}|{horse}" if date and track and race_no and horse else ""


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


def mode(values: list[str]) -> str:
    cleaned = [value for value in values if value]
    if not cleaned:
        return "UNKNOWN"
    return Counter(cleaned).most_common(1)[0][0]


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


def safe_results(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    safe: dict[str, dict[str, str]] = {}
    for row in rows:
        if clean(row.get("safe_for_model_validation")) != "YES":
            continue
        if not clean(row.get("finish_position")):
            continue
        key = clean(row.get("canonical_runner_key")) or start_key(row)
        if key:
            safe[key] = row
    return safe


def build_start_profiles(temporal_rows: list[dict[str, str]], safe: dict[str, dict[str, str]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in temporal_rows:
        key = start_key(row)
        if not key:
            continue
        grouped.setdefault(key, []).append(row)

    by_horse: dict[str, list[dict[str, object]]] = {}
    for key, rows in grouped.items():
        first = rows[0]
        hkey = horse_key(first.get("horse"))
        scores = [to_float(row.get("temporal_physics_score")) for row in rows if not math.isnan(to_float(row.get("temporal_physics_score")))]
        finish = to_int(safe.get(key, {}).get("finish_position")) if key in safe else None
        profile = {
            "horse": clean(first.get("horse")),
            "horse_key": hkey,
            "race_date": parse_date(first.get("race_date")),
            "phase_pattern": mode([clean(row.get("phase_transition_pattern")) for row in rows]),
            "energy_curve": mode([clean(row.get("energy_curve_type")) for row in rows]),
            "temporal_score": sum(scores) / len(scores) if scores else math.nan,
            "finish_position": finish,
        }
        by_horse.setdefault(hkey, []).append(profile)

    for profiles in by_horse.values():
        profiles.sort(key=lambda row: row["race_date"])
    return by_horse


def split_phases(starts: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    n = len(starts)
    if n == 0:
        return [], [], []
    first_cut = max(1, math.ceil(n / 3))
    second_cut = max(first_cut + 1, math.ceil((2 * n) / 3)) if n > 1 else first_cut
    return starts[:first_cut], starts[first_cut:second_cut], starts[second_cut:]


def phase_pattern(starts: list[dict[str, object]]) -> str:
    return mode([str(start.get("phase_pattern") or "") for start in starts])


def phase_curve(starts: list[dict[str, object]]) -> str:
    return mode([str(start.get("energy_curve") or "") for start in starts])


def phase_volatility(starts: list[dict[str, object]]) -> float:
    patterns = {str(start.get("phase_pattern")) for start in starts if start.get("phase_pattern")}
    if not starts:
        return 0.0
    return (max(0, len(patterns) - 1) / max(1, len(starts))) * 100.0


def avg_score(starts: list[dict[str, object]]) -> float:
    scores = [float(start["temporal_score"]) for start in starts if not math.isnan(float(start["temporal_score"]))]
    return sum(scores) / len(scores) if scores else math.nan


def avg_finish(starts: list[dict[str, object]]) -> float:
    finishes = [int(start["finish_position"]) for start in starts if start.get("finish_position") is not None]
    return sum(finishes) / len(finishes) if finishes else math.nan


def is_collapse(pattern: str, curve: str) -> bool:
    return pattern == "LATE_COLLAPSE" or curve == "COLLAPSE_CURVE"


def is_stable(pattern: str, curve: str) -> bool:
    return pattern in {"MIDRACE_SUSTAIN_TO_LATE_HOLD", "NEUTRAL_PHASE_PATTERN"} or curve == "STABLE_ENERGY_CURVE"


def is_positive(pattern: str, curve: str) -> bool:
    return pattern in {"EARLY_TO_LATE_ACCELERATION", "MIDRACE_SUSTAIN_TO_LATE_HOLD"} or curve in {"POSITIVE_ENERGY_CURVE", "STABLE_ENERGY_CURVE"}


def shift_type(early_pattern: str, late_pattern: str, early_curve: str, late_curve: str, early_vol: float, late_vol: float) -> str:
    if early_pattern == "UNKNOWN" or late_pattern == "UNKNOWN":
        return "INSUFFICIENT_EVOLUTION_DATA"
    if early_pattern == "EARLY_TO_LATE_ACCELERATION" and late_pattern == "MIDRACE_SUSTAIN_TO_LATE_HOLD":
        return "ACCELERATION_TO_SUSTAIN"
    if is_collapse(early_pattern, early_curve) and is_positive(late_pattern, late_curve):
        return "COLLAPSE_TO_STABLE"
    if is_stable(early_pattern, early_curve) and (late_pattern == "VOLATILE_PHASE_PATTERN" or late_curve == "UNSTABLE_CURVE"):
        return "STABLE_TO_VOLATILE"
    if (early_pattern == "VOLATILE_PHASE_PATTERN" or early_curve == "UNSTABLE_CURVE" or early_vol >= 50) and is_stable(late_pattern, late_curve):
        return "VOLATILE_TO_STABLE"
    return "NO_MAJOR_SHIFT"


def trend_from_delta(delta: float, inverse: bool = False) -> str:
    if math.isnan(delta) or abs(delta) < 3.0:
        return "STABLE"
    if inverse:
        return "IMPROVING" if delta < 0 else "DECLINING"
    return "IMPROVING" if delta > 0 else "DECLINING"


def volatility_trend(early_vol: float, late_vol: float) -> str:
    delta = late_vol - early_vol
    if abs(delta) < 15:
        return "STABLE"
    return "VOLATILE" if delta > 0 else "IMPROVING"


def classify_evolution(starts_tracked: int, shift: str, early_pattern: str, late_pattern: str, early_curve: str, late_curve: str, early_vol: float, late_vol: float) -> tuple[str, str, str]:
    if starts_tracked < 5:
        return (
            "INSUFFICIENT_EVOLUTION_SAMPLE",
            "INSUFFICIENT_EVOLUTION_DATA",
            "Research only: fewer than five tracked temporal starts.",
        )
    if is_collapse(early_pattern, early_curve) and is_positive(late_pattern, late_curve):
        return (
            "POSITIVE_BEHAVIOURAL_EVOLUTION",
            "COLLAPSE_TO_POSITIVE_TEMPORAL_BEHAVIOUR",
            "Research only: early collapse profile has shifted toward sustain or acceleration.",
        )
    if is_positive(early_pattern, early_curve) and is_collapse(late_pattern, late_curve):
        return (
            "NEGATIVE_BEHAVIOURAL_EVOLUTION",
            "POSITIVE_TO_COLLAPSE_TEMPORAL_BEHAVIOUR",
            "Research only: stable or positive profile has shifted toward collapse.",
        )
    if late_vol - early_vol >= 20:
        return (
            "VOLATILE_BEHAVIOURAL_PROFILE",
            "RISING_TEMPORAL_VOLATILITY",
            "Research only: measured temporal behaviour has become materially more volatile.",
        )
    if shift == "NO_MAJOR_SHIFT":
        return (
            "STABLE_BEHAVIOURAL_PROFILE",
            "STABLE_TEMPORAL_BEHAVIOURAL_PROFILE",
            "Research only: no major measured temporal behaviour shift detected.",
        )
    return (
        "VOLATILE_BEHAVIOURAL_PROFILE",
        "TEMPORAL_BEHAVIOURAL_TRANSITION",
        "Research only: measured temporal behaviour is shifting but needs more evidence.",
    )


def stability_grade(label: str, starts_tracked: int, early_vol: float, late_vol: float) -> str:
    if starts_tracked < 5:
        return "F"
    if label == "STABLE_BEHAVIOURAL_PROFILE" and max(early_vol, late_vol) <= 25:
        return "B"
    if label in {"POSITIVE_BEHAVIOURAL_EVOLUTION", "NEGATIVE_BEHAVIOURAL_EVOLUTION"}:
        return "C"
    return "D"


def build_evolution_rows(identity_rows: list[dict[str, str]], by_horse: dict[str, list[dict[str, object]]]) -> list[dict[str, object]]:
    names = {horse_key(row.get("horse")): clean(row.get("horse")) for row in identity_rows}
    all_keys = sorted(set(names) | set(by_horse))
    output: list[dict[str, object]] = []

    for hkey in all_keys:
        starts = by_horse.get(hkey, [])
        starts_tracked = len(starts)
        early, mid, late = split_phases(starts)
        early_pattern = phase_pattern(early)
        mid_pattern = phase_pattern(mid)
        late_pattern = phase_pattern(late)
        early_curve = phase_curve(early)
        late_curve = phase_curve(late)
        early_vol = phase_volatility(early)
        late_vol = phase_volatility(late)
        shift = shift_type(early_pattern, late_pattern, early_curve, late_curve, early_vol, late_vol)
        score_delta = avg_score(late) - avg_score(early)
        finish_delta = avg_finish(late) - avg_finish(early)
        label, evolution_label, note = classify_evolution(starts_tracked, shift, early_pattern, late_pattern, early_curve, late_curve, early_vol, late_vol)
        grade = stability_grade(label, starts_tracked, early_vol, late_vol)

        output.append(
            {
                "horse": names.get(hkey) or (starts[0]["horse"] if starts else ""),
                "horse_key": hkey,
                "starts_tracked": starts_tracked,
                "career_phase": "FULL_CAREER",
                "early_career_pattern": early_pattern,
                "mid_career_pattern": mid_pattern,
                "late_career_pattern": late_pattern,
                "pattern_shift_detected": "YES" if shift not in {"NO_MAJOR_SHIFT", "INSUFFICIENT_EVOLUTION_DATA"} else "NO",
                "pattern_shift_type": shift if starts_tracked >= 5 else "INSUFFICIENT_EVOLUTION_DATA",
                "energy_curve_shift": f"{early_curve}_TO_{late_curve}" if early_curve != "UNKNOWN" and late_curve != "UNKNOWN" else "INSUFFICIENT_EVOLUTION_DATA",
                "consistency_trend": "STABLE" if shift == "NO_MAJOR_SHIFT" else "VOLATILE" if shift in {"STABLE_TO_VOLATILE", "VOLATILE_TO_STABLE"} else "STABLE",
                "volatility_trend": volatility_trend(early_vol, late_vol),
                "finish_position_trend": trend_from_delta(finish_delta, inverse=True),
                "temporal_score_trend": trend_from_delta(score_delta),
                "evolution_stability_grade": grade,
                "evolution_label": label,
                "research_status": "RESEARCH_ONLY_TEMPORAL_EVOLUTION",
                "trusted_for_live_modelling": "NO",
                "trusted_for_live_execution": "NO",
                "notes": note + " No betting signal, overlay, rating, or execution impact.",
            }
        )
    return output


def build_watchlist(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    watch: list[dict[str, object]] = []
    for row in rows:
        starts = int(row.get("starts_tracked") or 0)
        label = clean(row.get("evolution_label"))
        shift = clean(row.get("pattern_shift_type"))
        if label == "POSITIVE_BEHAVIOURAL_EVOLUTION" and starts >= 5:
            priority = "HIGH"
            reason = "Positive measured behavioural evolution with at least five tracked starts."
            next_step = "Monitor persistence across future starts and regime contexts before any modelling review."
        elif label == "NEGATIVE_BEHAVIOURAL_EVOLUTION" or shift in {"STABLE_TO_VOLATILE"}:
            priority = "MEDIUM"
            reason = "Negative or rising-volatility measured behavioural transition."
            next_step = "Track whether the deterioration persists across distance and race-shape changes."
        elif label == "VOLATILE_BEHAVIOURAL_PROFILE":
            priority = "LOW"
            reason = "Volatile temporal transition requiring more observation."
            next_step = "Accumulate more measured starts before interpretation."
        else:
            continue
        watch.append(
            {
                "priority": priority,
                "horse": row.get("horse", ""),
                "horse_key": row.get("horse_key", ""),
                "starts_tracked": starts,
                "evolution_label": label,
                "pattern_shift_type": row.get("pattern_shift_type", ""),
                "energy_curve_shift": row.get("energy_curve_shift", ""),
                "watchlist_reason": reason,
                "research_next_step": next_step,
                "trusted_for_live_modelling": "NO",
                "trusted_for_live_execution": "NO",
                "notes": "Research watchlist only. No live modelling or execution trust.",
            }
        )
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(watch, key=lambda row: (priority_order.get(str(row["priority"]), 9), -int(row["starts_tracked"]), str(row["horse"])))


def build_summary(rows: list[dict[str, object]], watchlist: list[dict[str, object]], source_counts: Counter, missing: list[str]) -> list[dict[str, object]]:
    labels = Counter(str(row.get("evolution_label")) for row in rows)
    summary: list[dict[str, object]] = [
        {"metric": "identity_evolution_rows", "value": len(rows)},
        {"metric": "positive_behavioural_evolution", "value": labels.get("POSITIVE_BEHAVIOURAL_EVOLUTION", 0)},
        {"metric": "negative_behavioural_evolution", "value": labels.get("NEGATIVE_BEHAVIOURAL_EVOLUTION", 0)},
        {"metric": "stable_profiles", "value": labels.get("STABLE_BEHAVIOURAL_PROFILE", 0)},
        {"metric": "volatile_profiles", "value": labels.get("VOLATILE_BEHAVIOURAL_PROFILE", 0)},
        {"metric": "insufficient_sample", "value": labels.get("INSUFFICIENT_EVOLUTION_SAMPLE", 0)},
        {"metric": "watchlist_rows", "value": len(watchlist)},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]
    for name in missing:
        summary.append({"metric": f"missing_input::{name}", "value": 1})
    for name, count in source_counts.most_common():
        summary.append({"metric": f"source_rows::{name}", "value": count})
    for label, count in labels.most_common():
        summary.append({"metric": f"evolution_label::{label}", "value": count})
    return summary


def main() -> None:
    inputs, source_counts, missing = load_inputs()
    safe = safe_results(inputs["results_truth"])
    profiles = build_start_profiles(inputs["temporal_engine"], safe)
    evolution_rows = build_evolution_rows(inputs["identity_memory"], profiles)
    watchlist_rows = build_watchlist(evolution_rows)
    summary_rows = build_summary(evolution_rows, watchlist_rows, source_counts, missing)

    write_csv(OUT, evolution_rows, EVOLUTION_FIELDS)
    write_csv(SUMMARY, summary_rows, SUMMARY_FIELDS)
    write_csv(WATCHLIST, watchlist_rows, WATCHLIST_FIELDS)

    labels = Counter(str(row.get("evolution_label")) for row in evolution_rows)
    print("=" * 88)
    print("EDGEIQ TEMPORAL MEMORY EVOLUTION V1")
    print("=" * 88)
    print(f"identity evolution rows: {len(evolution_rows)}")
    print(f"watchlist rows: {len(watchlist_rows)}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {WATCHLIST}")
    for label, count in labels.most_common():
        print(f"  {label}: {count}")
    print("live modelling/execution: 0 / 0")


if __name__ == "__main__":
    main()
