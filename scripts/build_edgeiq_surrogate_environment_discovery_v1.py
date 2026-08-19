from __future__ import annotations

import csv
import math
import re
import time
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = {
    "targets": DATA / "edgeiq_targeted_sectional_harvest_targets_v1.csv",
    "payload_quality": DATA / "edgeiq_sectional_payload_quality_v1.csv",
    "walkforward": DATA / "edgeiq_temporal_walkforward_stability_v1.csv",
    "stable": DATA / "edgeiq_stable_regime_isolation_v1.csv",
    "shadow": DATA / "edgeiq_shadow_environment_state_v1.csv",
}

OUT = DATA / "edgeiq_surrogate_environment_discovery_v1.csv"
SUMMARY = DATA / "edgeiq_surrogate_environment_summary_v1.csv"

OUT_FIELDS = [
    "source_environment",
    "candidate_surrogate_environment",
    "similarity_score",
    "sectional_quality_grade",
    "walkforward_status",
    "stable_research_status",
    "payload_advantage_score",
    "phase_similarity_score",
    "variance_similarity_score",
    "recommended_surrogate_rank",
    "recommended_usage",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

GRADE_SCORE = {"A": 100.0, "B": 78.0, "C": 55.0, "D": 30.0, "F": 5.0, "UNKNOWN": 0.0, "": 0.0}
GRADE_RANK = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1, "UNKNOWN": 0, "": 0}
SURROGATE_RANK = {"HIGH_VALUE_SURROGATE": 4, "USABLE_SURROGATE": 3, "WEAK_SURROGATE": 2, "REJECT_SURROGATE": 1}
COUNTRY_TRACKS = {
    "HORSHAM",
    "STAWELL",
    "WARRNAMBOOL",
    "WANGARATTA",
    "WODONGA",
    "SWAN HILL",
    "ECHA",
    "ECHUCA",
    "MILDURA",
    "CASTERTON",
    "COLERAINE",
    "CAMPERDOWN",
    "TERANG",
    "BET365 HAMILTON",
    "HAMILTON",
    "KYNETON",
    "ARARAT",
    "BENALLA",
    "BAIRNSDALE",
    "MOE",
    "TRARALGON",
    "YARRA VALLEY",
}
PROVINCIAL_TRACKS = {
    "PAKENHAM",
    "CRANBOURNE",
    "BALLARAT",
    "BENDIGO",
    "GEELONG",
    "SEYMOUR",
    "SALE",
    "MORNINGTON",
    "WERRIBEE",
}
METRO_TRACKS = {"FLEMINGTON", "CAULFIELD", "CAULFIELD HEATH", "MOONEE VALLEY", "SANDOWN"}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{time.time_ns()}.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    tmp.replace(path)


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def parse_float(value: object, default: float = 0.0) -> float:
    try:
        text = clean(value).replace("%", "")
        if not text:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def parse_int(value: object, default: int = 0) -> int:
    try:
        text = clean(value).replace(",", "")
        if not text:
            return default
        return int(float(text))
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def env_key(segment_type: object, segment_value: object) -> str:
    return f"{clean(segment_type).lower()}:{upper(segment_value)}"


def split_env_key(value: object) -> tuple[str, str]:
    text = clean(value)
    if ":" not in text:
        return "", upper(text)
    left, right = text.split(":", 1)
    return left.strip().lower(), upper(right)


def normalize_track(track: object) -> str:
    text = upper(track)
    text = re.sub(r"\s+", " ", text)
    aliases = {
        "THE VALLEY": "MOONEE VALLEY",
        "SPORTSBET PAKENHAM": "PAKENHAM",
        "SOUTHSIDE PAKENHAM": "PAKENHAM",
        "PAKENHAM SYNTHETIC": "PAKENHAM",
        "BALLARAT SYNTHETIC": "BALLARAT",
        "GEELONG SYNTHETIC": "GEELONG",
        "SANDOWN HILLSIDE": "SANDOWN",
        "SANDOWN LAKESIDE": "SANDOWN",
    }
    return aliases.get(text, text)


def track_family(track: object) -> str:
    value = normalize_track(track)
    if value in METRO_TRACKS:
        return "METRO"
    if value in PROVINCIAL_TRACKS:
        return "PROVINCIAL"
    if value in COUNTRY_TRACKS:
        return "COUNTRY"
    return "COUNTRY" if value else "UNKNOWN"


def best_grade(counter: Counter[str]) -> str:
    if not counter:
        return "UNKNOWN"
    total = sum(counter.values())
    usable = counter.get("A", 0) + counter.get("B", 0)
    partial = counter.get("C", 0)
    degraded = counter.get("D", 0)
    unsafe = counter.get("F", 0)
    if total <= 0:
        return "UNKNOWN"
    if usable / total >= 0.45:
        return "A" if counter.get("A", 0) / total >= 0.15 else "B"
    if usable / total >= 0.18:
        return "B"
    if (usable + partial) / total >= 0.55:
        return "C"
    if unsafe / total >= 0.35:
        return "F"
    if degraded + unsafe > 0:
        return "D"
    return "UNKNOWN"


def environment_from_target(row: dict[str, str]) -> tuple[str, str]:
    if clean(row.get("track")):
        return "track", upper(row.get("track"))
    if clean(row.get("race_class")):
        return "race_class", upper(row.get("race_class"))
    if clean(row.get("distance_bucket")):
        return "distance_bucket", upper(row.get("distance_bucket"))
    if clean(row.get("tempo_bucket")):
        return "tempo_bucket", upper(row.get("tempo_bucket"))
    reason = clean(row.get("target_reason"))
    match = re.search(r"([A-Z_]+)=([A-Z0-9 _-]+)", reason.upper())
    if match:
        left = match.group(1).lower()
        right = match.group(2).split(";")[0].strip()
        return left, right
    return "", ""


def build_quality_profiles(rows: list[dict[str, str]]) -> dict[str, dict[str, object]]:
    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        track = normalize_track(row.get("track"))
        source = clean(row.get("source_file"))
        if track:
            buckets[f"track:{track}"].append(row)
            buckets[f"track_family:{track_family(track)}"].append(row)
        if source:
            buckets[f"source_file:{source}"].append(row)

    profiles: dict[str, dict[str, object]] = {}
    for key, values in buckets.items():
        grades = Counter(upper(row.get("source_quality_grade")) or "UNKNOWN" for row in values)
        blockers = Counter(upper(row.get("quality_blocker")) or "UNKNOWN" for row in values)
        safe_shadow = sum(1 for row in values if upper(row.get("safe_for_shadow_research")) == "YES")
        safe_temporal = sum(1 for row in values if upper(row.get("safe_for_temporal_research")) == "YES")
        total = len(values)
        completeness = sum(parse_float(row.get("payload_completeness_score")) for row in values) / total if total else 0.0
        phase_conf = sum(parse_float(row.get("phase_confidence_score")) for row in values) / total if total else 0.0
        physics = sum(parse_float(row.get("physics_consistency_score")) for row in values) / total if total else 0.0
        grade = best_grade(grades)
        profiles[key.lower()] = {
            "environment_key": key,
            "quality_grade": grade,
            "quality_score": GRADE_SCORE.get(grade, 0.0),
            "rows": total,
            "safe_shadow_rows": safe_shadow,
            "safe_temporal_rows": safe_temporal,
            "shadow_rate": safe_shadow / total * 100.0 if total else 0.0,
            "temporal_rate": safe_temporal / total * 100.0 if total else 0.0,
            "dominant_blocker": blockers.most_common(1)[0][0] if blockers else "UNKNOWN",
            "payload_completeness_score": completeness,
            "phase_confidence_score": phase_conf,
            "physics_consistency_score": physics,
        }
    return profiles


def build_stable_profiles(stable_rows: list[dict[str, str]], walk_rows: list[dict[str, str]], shadow_rows: list[dict[str, str]]) -> dict[str, dict[str, object]]:
    profiles: dict[str, dict[str, object]] = defaultdict(dict)

    stable_grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in stable_rows:
        key = env_key(row.get("segment_type"), row.get("segment_value"))
        if key:
            stable_grouped[key.lower()].append(row)
    for key, rows in stable_grouped.items():
        statuses = Counter(upper(row.get("isolation_status")) for row in rows if clean(row.get("isolation_status")))
        phase = Counter(upper(row.get("phase_transition_pattern")) for row in rows if clean(row.get("phase_transition_pattern")))
        profiles[key].update(
            {
                "stable_research_status": statuses.most_common(1)[0][0] if statuses else "UNKNOWN",
                "stable_sample_size": sum(parse_int(row.get("sample_size")) for row in rows),
                "stability_score": max((parse_float(row.get("stability_score")) for row in rows), default=0.0),
                "survival_score": max((parse_float(row.get("survival_score")) for row in rows), default=0.0),
                "variance_decay_score": max((parse_float(row.get("variance_decay_score")) for row in rows), default=0.0),
                "phase_patterns": set(phase.keys()),
            }
        )

    walk_grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in walk_rows:
        key = clean(row.get("environment_key")) or env_key(row.get("segment_type"), row.get("segment_value"))
        if key:
            walk_grouped[key.lower()].append(row)
    for key, rows in walk_grouped.items():
        statuses = Counter(upper(row.get("walkforward_classification")) for row in rows if clean(row.get("walkforward_classification")))
        if any(status == "SURVIVED_WALKFORWARD" for status in statuses):
            walk_status = "SURVIVED_WALKFORWARD"
        elif any(status == "TEMPORALLY_STABLE" for status in statuses):
            walk_status = "TEMPORALLY_STABLE"
        elif statuses:
            walk_status = statuses.most_common(1)[0][0]
        else:
            walk_status = "UNKNOWN"
        phase_set = profiles[key].get("phase_patterns", set())
        if not isinstance(phase_set, set):
            phase_set = set()
        phase_set.update(upper(row.get("phase_transition_pattern")) for row in rows if clean(row.get("phase_transition_pattern")))
        profiles[key].update(
            {
                "walkforward_status": walk_status,
                "walk_sample_size": sum(parse_int(row.get("window_sample_size")) for row in rows if upper(row.get("window_name")) in {"FULL", ""}),
                "walkforward_stability_score": max((parse_float(row.get("walkforward_stability_score")) for row in rows), default=0.0),
                "variance_drift": sum(parse_float(row.get("variance_drift")) for row in rows) / len(rows) if rows else 0.0,
                "resilience_score": max((parse_float(row.get("resilience_score")) for row in rows), default=0.0),
                "phase_patterns": phase_set,
            }
        )

    for row in shadow_rows:
        key = (clean(row.get("environment_key")) or env_key(row.get("segment_type"), row.get("segment_value"))).lower()
        if not key:
            continue
        profiles[key].update(
            {
                "shadow_research_status": upper(row.get("current_status")) or "UNKNOWN",
                "shadow_priority": upper(row.get("watch_priority")) or "LOW",
                "environment_health_score": parse_float(row.get("environment_health_score")),
            }
        )

    for key, profile in profiles.items():
        profile.setdefault("stable_research_status", "UNKNOWN")
        profile.setdefault("walkforward_status", "UNKNOWN")
        profile.setdefault("shadow_research_status", "UNKNOWN")
        profile.setdefault("phase_patterns", set())
        profile.setdefault("variance_drift", 0.0)
        profile.setdefault("stability_score", 0.0)
        profile.setdefault("resilience_score", 0.0)
    return profiles


def dimension_similarity(source_type: str, source_value: str, candidate_type: str, candidate_value: str) -> float:
    source_type = source_type.lower()
    candidate_type = candidate_type.lower()
    source_value = upper(source_value)
    candidate_value = upper(candidate_value)
    if source_type == candidate_type and source_value == candidate_value:
        return 100.0
    if source_type == "track" and candidate_type == "track_family" and track_family(source_value) == candidate_value:
        return 78.0
    if source_type == "track_family" and candidate_type == "track" and source_value == track_family(candidate_value):
        return 78.0
    if source_type == "race_class" and candidate_type == "race_class":
        if source_value.startswith("BM") and candidate_value.startswith("BM"):
            return 86.0 if abs(parse_int(source_value[2:]) - parse_int(candidate_value[2:])) <= 8 else 62.0
    if source_type == "distance_bucket" and candidate_type == "distance_bucket":
        return 65.0
    if source_type == "tempo_bucket" and candidate_type == "tempo_bucket":
        return 70.0
    return 35.0 if source_type == candidate_type else 22.0


def phase_similarity(source_profile: dict[str, object], candidate_profile: dict[str, object]) -> float:
    source = source_profile.get("phase_patterns", set())
    candidate = candidate_profile.get("phase_patterns", set())
    if not isinstance(source, set):
        source = set()
    if not isinstance(candidate, set):
        candidate = set()
    if not source or not candidate:
        return 45.0
    overlap = len(source & candidate)
    union = len(source | candidate)
    return overlap / union * 100.0 if union else 45.0


def variance_similarity(source_profile: dict[str, object], candidate_profile: dict[str, object]) -> float:
    source_variance = parse_float(source_profile.get("variance_drift"))
    candidate_variance = parse_float(candidate_profile.get("variance_drift"))
    source_stability = parse_float(source_profile.get("stability_score") or source_profile.get("walkforward_stability_score"))
    candidate_stability = parse_float(candidate_profile.get("stability_score") or candidate_profile.get("walkforward_stability_score"))
    variance_gap = abs(source_variance - candidate_variance)
    stability_gap = abs(source_stability - candidate_stability)
    return clamp(100.0 - (variance_gap * 2.2) - (stability_gap * 0.55))


def payload_advantage(source_grade: str, candidate_grade: str, candidate_quality: dict[str, object]) -> float:
    grade_gain = (GRADE_RANK.get(upper(candidate_grade), 0) - GRADE_RANK.get(upper(source_grade), 0)) * 18.0
    shadow_bonus = min(parse_float(candidate_quality.get("shadow_rate")) * 0.35, 20.0)
    phase_bonus = min(parse_float(candidate_quality.get("phase_confidence_score")) * 0.25, 20.0)
    return clamp(grade_gain + shadow_bonus + phase_bonus)


def classify_surrogate(score: float, payload_adv: float, candidate_grade: str) -> str:
    grade_rank = GRADE_RANK.get(upper(candidate_grade), 0)
    if score >= 76.0 and payload_adv >= 20.0 and grade_rank >= 4:
        return "HIGH_VALUE_SURROGATE"
    if score >= 62.0 and payload_adv >= 8.0 and grade_rank >= 3:
        return "USABLE_SURROGATE"
    if score >= 48.0 and grade_rank >= 3:
        return "WEAK_SURROGATE"
    return "REJECT_SURROGATE"


def usage_for(rank: str) -> str:
    if rank == "HIGH_VALUE_SURROGATE":
        return "Use as first surrogate acquisition environment for fuller split ladders and direct payload comparison."
    if rank == "USABLE_SURROGATE":
        return "Use as secondary surrogate sample expansion; keep separate from target environment conclusions."
    if rank == "WEAK_SURROGATE":
        return "Monitor only; structural similarity or payload advantage is not strong enough for active backfill priority."
    return "Reject for surrogate acquisition; insufficient similarity or no payload quality advantage."


def candidate_environments(quality_profiles: dict[str, dict[str, object]], stable_profiles: dict[str, dict[str, object]]) -> set[str]:
    keys = set(stable_profiles.keys())
    for key, quality in quality_profiles.items():
        if key.startswith("track:") or key.startswith("track_family:"):
            if GRADE_RANK.get(upper(quality.get("quality_grade")), 0) >= 3:
                keys.add(key)
    return keys


def build_rows(
    targets: list[dict[str, str]],
    quality_profiles: dict[str, dict[str, object]],
    stable_profiles: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    candidates = candidate_environments(quality_profiles, stable_profiles)
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()

    for target in targets:
        source_type, source_value = environment_from_target(target)
        if not source_type or not source_value:
            continue
        source_key = f"{source_type}:{source_value}".lower()
        source_env = f"{source_type}:{source_value}"
        source_quality_grade = upper(target.get("current_quality_grade")) or upper(quality_profiles.get(source_key, {}).get("quality_grade")) or "UNKNOWN"
        source_profile = stable_profiles.get(source_key, {})

        for candidate_key in sorted(candidates):
            if candidate_key == source_key:
                continue
            candidate_type, candidate_value = split_env_key(candidate_key)
            if not candidate_type or not candidate_value:
                continue
            candidate_quality = quality_profiles.get(candidate_key, {})
            candidate_profile = stable_profiles.get(candidate_key, {})
            candidate_grade = upper(candidate_quality.get("quality_grade")) or "UNKNOWN"
            if GRADE_RANK.get(candidate_grade, 0) < max(3, GRADE_RANK.get(source_quality_grade, 0)):
                continue

            dim_score = dimension_similarity(source_type, source_value, candidate_type, candidate_value)
            phase_score = phase_similarity(source_profile, candidate_profile)
            var_score = variance_similarity(source_profile, candidate_profile)
            walk_status = upper(candidate_profile.get("walkforward_status")) or "UNKNOWN"
            stable_status = upper(candidate_profile.get("stable_research_status")) or "UNKNOWN"
            walk_bonus = 8.0 if walk_status in {"SURVIVED_WALKFORWARD", "TEMPORALLY_STABLE"} else 0.0
            stable_bonus = 8.0 if stable_status in {"PERSISTENT_STABLE_RESEARCH_ENVIRONMENT", "STABLE_RESEARCH_POCKET", "WATCHLIST_STABLE_POCKET"} else 0.0
            payload_score = payload_advantage(source_quality_grade, candidate_grade, candidate_quality)
            similarity = clamp((dim_score * 0.30) + (phase_score * 0.24) + (var_score * 0.22) + (payload_score * 0.14) + walk_bonus + stable_bonus)
            rank = classify_surrogate(similarity, payload_score, candidate_grade)
            candidate_env = f"{candidate_type}:{candidate_value}"
            key = (source_env, candidate_env)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "source_environment": source_env,
                    "candidate_surrogate_environment": candidate_env,
                    "similarity_score": f"{similarity:.2f}",
                    "sectional_quality_grade": candidate_grade,
                    "walkforward_status": walk_status,
                    "stable_research_status": stable_status,
                    "payload_advantage_score": f"{payload_score:.2f}",
                    "phase_similarity_score": f"{phase_score:.2f}",
                    "variance_similarity_score": f"{var_score:.2f}",
                    "recommended_surrogate_rank": rank,
                    "recommended_usage": usage_for(rank),
                    "notes": "Offline surrogate discovery only. No predictions, overlays, live modelling, ratings, or execution enabled.",
                    "_rank": SURROGATE_RANK.get(rank, 0),
                    "_score": similarity,
                    "_payload": payload_score,
                }
            )

    rows.sort(key=lambda row: (-parse_int(row.get("_rank")), -parse_float(row.get("_score")), -parse_float(row.get("_payload")), clean(row.get("source_environment")), clean(row.get("candidate_surrogate_environment"))))
    for row in rows:
        row.pop("_rank", None)
        row.pop("_score", None)
        row.pop("_payload", None)
    return rows


def build_summary(rows: list[dict[str, object]], missing_inputs: list[str]) -> list[dict[str, object]]:
    counts = Counter(upper(row.get("recommended_surrogate_rank")) for row in rows)
    high = [row for row in rows if upper(row.get("recommended_surrogate_rank")) == "HIGH_VALUE_SURROGATE"]
    usable = [row for row in rows if upper(row.get("recommended_surrogate_rank")) == "USABLE_SURROGATE"]
    weak = [row for row in rows if upper(row.get("recommended_surrogate_rank")) == "WEAK_SURROGATE"]
    reject = [row for row in rows if upper(row.get("recommended_surrogate_rank")) == "REJECT_SURROGATE"]
    avg_similarity = sum(parse_float(row.get("similarity_score")) for row in rows) / len(rows) if rows else 0.0

    summary = [
        {"metric": "surrogate_rows", "value": len(rows)},
        {"metric": "high_value_surrogates", "value": len(high)},
        {"metric": "usable_surrogates", "value": len(usable)},
        {"metric": "weak_surrogates", "value": len(weak)},
        {"metric": "rejected_surrogates", "value": len(reject)},
        {"metric": "avg_similarity_score", "value": f"{avg_similarity:.2f}"},
        {"metric": "best_surrogate", "value": f"{rows[0].get('source_environment')}->{rows[0].get('candidate_surrogate_environment')}" if rows else ""},
        {"metric": "best_surrogate_rank", "value": rows[0].get("recommended_surrogate_rank") if rows else ""},
        {"metric": "best_surrogate_similarity", "value": rows[0].get("similarity_score") if rows else ""},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    for rank, count in sorted(counts.items()):
        summary.append({"metric": f"rank_count::{rank}", "value": count})
    for filename in missing_inputs:
        summary.append({"metric": f"missing_input::{filename}", "value": "YES"})
    return summary


def main() -> None:
    missing_inputs = [path.name for path in INPUTS.values() if not path.exists()]
    targets = read_csv(INPUTS["targets"])
    payload_quality = read_csv(INPUTS["payload_quality"])
    walkforward = read_csv(INPUTS["walkforward"])
    stable = read_csv(INPUTS["stable"])
    shadow = read_csv(INPUTS["shadow"])

    quality_profiles = build_quality_profiles(payload_quality)
    stable_profiles = build_stable_profiles(stable, walkforward, shadow)
    rows = build_rows(targets, quality_profiles, stable_profiles)
    summary = build_summary(rows, missing_inputs)

    write_csv(OUT, rows, OUT_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)

    print("=" * 88)
    print("EDGEIQ SURROGATE ENVIRONMENT DISCOVERY V1")
    print("=" * 88)
    for row in summary:
        if not clean(row.get("metric")).startswith("missing_input::"):
            print(f"{row['metric']}: {row['value']}")
    if missing_inputs:
        print("missing inputs:", ", ".join(missing_inputs))
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")


if __name__ == "__main__":
    main()
