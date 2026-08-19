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
    "walkforward_decay": DATA / "edgeiq_temporal_walkforward_decay_v1.csv",
    "walkforward": DATA / "edgeiq_temporal_walkforward_stability_v1.csv",
    "validation": DATA / "edgeiq_temporal_physics_validation_v1.csv",
    "isolation": DATA / "edgeiq_stable_regime_isolation_v1.csv",
}

OUT = DATA / "edgeiq_shadow_out_of_sample_tracker_v1.csv"
SUMMARY = DATA / "edgeiq_shadow_out_of_sample_summary_v1.csv"
WATCHLIST = DATA / "edgeiq_shadow_environment_watchlist_v1.csv"

OUT_FIELDS = [
    "environment_key",
    "segment_type",
    "segment_value",
    "phase_transition_pattern",
    "future_window_start",
    "future_window_end",
    "future_sample_count",
    "future_win_rate",
    "future_place_rate",
    "future_top4_rate",
    "future_decay_score",
    "future_variance_score",
    "future_resilience_score",
    "prospective_stability_status",
    "live_modelling_allowed",
    "live_execution_allowed",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

WATCHLIST_FIELDS = [
    "priority",
    "environment_key",
    "segment_type",
    "segment_value",
    "phase_transition_pattern",
    "source_status",
    "future_sample_count",
    "prospective_stability_status",
    "watch_reason",
    "next_observation_action",
    "live_modelling_allowed",
    "live_execution_allowed",
    "notes",
]

ALLOWED_DECAY_CLASSES = {"SURVIVED_WALKFORWARD", "TEMPORALLY_STABLE"}
ALLOWED_ISOLATION_CLASSES = {"WATCHLIST_STABLE_POCKET", "PERSISTENT_STABLE_RESEARCH_ENVIRONMENT"}

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
    return f"{max(0.0, min(100.0, value)):.2f}"


def rate(part: int, whole: int) -> float:
    return 0.0 if whole <= 0 else (part / whole) * 100.0


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
    if segment_type == "distance_bucket":
        return "UNKNOWN"
    if segment_type == "field_size_bucket":
        return "UNKNOWN"
    return "UNKNOWN"


def yes(value: object) -> bool:
    return clean(value).upper() in {"YES", "Y", "TRUE", "1"}


def build_watch_environments() -> list[dict[str, str]]:
    envs: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in read_csv(INPUTS["walkforward_decay"]):
        if clean(row.get("overall_walkforward_classification")) not in ALLOWED_DECAY_CLASSES:
            continue
        key = (clean(row.get("environment_key")), clean(row.get("segment_type")), clean(row.get("phase_transition_pattern")))
        envs[key] = {
            "environment_key": clean(row.get("environment_key")),
            "segment_type": clean(row.get("segment_type")),
            "segment_value": clean(row.get("segment_value")),
            "phase_transition_pattern": clean(row.get("phase_transition_pattern")),
            "source_status": clean(row.get("overall_walkforward_classification")),
        }
    for row in read_csv(INPUTS["isolation"]):
        if clean(row.get("isolation_status")) not in ALLOWED_ISOLATION_CLASSES:
            continue
        environment_key = f"{clean(row.get('segment_type'))}:{clean(row.get('segment_value'))}"
        key = (environment_key, clean(row.get("segment_type")), clean(row.get("phase_transition_pattern")))
        envs.setdefault(
            key,
            {
                "environment_key": environment_key,
                "segment_type": clean(row.get("segment_type")),
                "segment_value": clean(row.get("segment_value")),
                "phase_transition_pattern": clean(row.get("phase_transition_pattern")),
                "source_status": clean(row.get("isolation_status")),
            },
        )
    return sorted(envs.values(), key=lambda item: (item["environment_key"], item["phase_transition_pattern"]))


def future_rows_for(env: dict[str, str], validation_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    matching = [
        row for row in validation_rows
        if clean(row.get("finish_position"))
        and clean(row.get("phase_transition_pattern")) == env["phase_transition_pattern"]
        and row_segment_value(row, env["segment_type"]) == env["segment_value"]
    ]
    if not matching:
        return []
    dates = sorted({parse_date(row.get("race_date")) for row in matching if parse_date(row.get("race_date"))})
    if len(dates) >= 2:
        cutoff = dates[-1]
        return [row for row in matching if parse_date(row.get("race_date")) == cutoff]
    # Same-day dominated research: reserve the final chronological third as the prospective shadow slice.
    matching = sorted(matching, key=lambda row: parse_date(row.get("race_date")))
    start = max(0, (len(matching) * 2) // 3)
    return matching[start:]


def variance(finishes: list[int]) -> float:
    if len(finishes) <= 1:
        return 0.0 if finishes else 100.0
    mean = sum(finishes) / len(finishes)
    return min(100.0, sum((value - mean) ** 2 for value in finishes) / len(finishes) * 10.0)


def classify(sample: int, place_rate: float, top4_rate: float, decay: float, variance_score: float, resilience: float) -> str:
    if sample < 20:
        return "PROSPECTIVE_INSUFFICIENT_SAMPLE"
    if variance_score >= 45:
        return "PROSPECTIVE_VARIANCE_WARNING"
    if decay >= 25 or place_rate < 25:
        return "PROSPECTIVE_DECAY"
    if resilience >= 65 and top4_rate >= 55:
        return "PROSPECTIVE_STABLE"
    return "PROSPECTIVE_VARIANCE_WARNING"


def build_tracker_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    validation_rows = read_csv(INPUTS["validation"])
    tracker: list[dict[str, object]] = []
    watchlist: list[dict[str, object]] = []
    for env in build_watch_environments():
        rows = future_rows_for(env, validation_rows)
        sample = len(rows)
        wins = sum(1 for row in rows if yes(row.get("winner_flag")))
        places = sum(1 for row in rows if yes(row.get("place_flag")))
        top4 = sum(1 for row in rows if yes(row.get("top4_flag")))
        finishes = [to_int(row.get("finish_position")) for row in rows if to_int(row.get("finish_position"))]
        win_rate = rate(wins, sample)
        place_rate = rate(places, sample)
        top4_rate = rate(top4, sample)
        variance_score = variance(finishes)
        decay_score = max(0.0, 35.0 - place_rate) + max(0.0, 55.0 - top4_rate) * 0.5
        resilience = max(0.0, min(100.0, (top4_rate * 0.45) + (place_rate * 0.35) + min(20.0, sample / 15.0) - (variance_score * 0.15)))
        status = classify(sample, place_rate, top4_rate, decay_score, variance_score, resilience)
        dates = [parse_date(row.get("race_date")) for row in rows if parse_date(row.get("race_date"))]
        tracker.append(
            {
                "environment_key": env["environment_key"],
                "segment_type": env["segment_type"],
                "segment_value": env["segment_value"],
                "phase_transition_pattern": env["phase_transition_pattern"],
                "future_window_start": min(dates) if dates else "",
                "future_window_end": max(dates) if dates else "",
                "future_sample_count": sample,
                "future_win_rate": fmt(win_rate),
                "future_place_rate": fmt(place_rate),
                "future_top4_rate": fmt(top4_rate),
                "future_decay_score": fmt(decay_score),
                "future_variance_score": fmt(variance_score),
                "future_resilience_score": fmt(resilience),
                "prospective_stability_status": status,
                "live_modelling_allowed": "NO",
                "live_execution_allowed": "NO",
                "notes": "Prospective shadow tracking only. No prices, overlays, recommendations, live modelling, or execution.",
            }
        )
        if status == "PROSPECTIVE_STABLE":
            priority = "MEDIUM"
            reason = "Surviving environment remains stable in current prospective shadow slice."
        elif status == "PROSPECTIVE_INSUFFICIENT_SAMPLE":
            priority = "LOW"
            reason = "Needs more unseen future samples before stability can be assessed."
        else:
            priority = "HIGH"
            reason = "Prospective shadow slice shows decay or variance warning."
        watchlist.append(
            {
                "priority": priority,
                "environment_key": env["environment_key"],
                "segment_type": env["segment_type"],
                "segment_value": env["segment_value"],
                "phase_transition_pattern": env["phase_transition_pattern"],
                "source_status": env["source_status"],
                "future_sample_count": sample,
                "prospective_stability_status": status,
                "watch_reason": reason,
                "next_observation_action": "Continue offline shadow observation on future settled races; do not promote or execute.",
                "live_modelling_allowed": "NO",
                "live_execution_allowed": "NO",
                "notes": "Watchlist is research-only and cannot authorise live modelling.",
            }
        )
    return tracker, watchlist


def build_summary(tracker: list[dict[str, object]], watchlist: list[dict[str, object]]) -> list[dict[str, object]]:
    statuses = Counter(str(row["prospective_stability_status"]) for row in tracker)
    priorities = Counter(str(row["priority"]) for row in watchlist)
    missing = [path.name for path in INPUTS.values() if not path.exists()]
    values: list[dict[str, object]] = [
        {"metric": "tracker_rows", "value": len(tracker)},
        {"metric": "watchlist_rows", "value": len(watchlist)},
        {"metric": "prospective_stable", "value": statuses.get("PROSPECTIVE_STABLE", 0)},
        {"metric": "prospective_decay", "value": statuses.get("PROSPECTIVE_DECAY", 0)},
        {"metric": "prospective_variance_warning", "value": statuses.get("PROSPECTIVE_VARIANCE_WARNING", 0)},
        {"metric": "prospective_insufficient_sample", "value": statuses.get("PROSPECTIVE_INSUFFICIENT_SAMPLE", 0)},
        {"metric": "high_priority_watchlist", "value": priorities.get("HIGH", 0)},
        {"metric": "medium_priority_watchlist", "value": priorities.get("MEDIUM", 0)},
        {"metric": "low_priority_watchlist", "value": priorities.get("LOW", 0)},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    for filename in missing:
        values.append({"metric": f"missing_input::{filename}", "value": "YES"})
    return values


def main() -> None:
    tracker, watchlist = build_tracker_rows()
    summary = build_summary(tracker, watchlist)
    write_csv(OUT, tracker, OUT_FIELDS)
    write_csv(WATCHLIST, watchlist, WATCHLIST_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 88)
    print("EDGEIQ SHADOW OUT-OF-SAMPLE TRACKER V1")
    print("=" * 88)
    print(f"tracker rows: {len(tracker)}")
    print(f"watchlist rows: {len(watchlist)}")
    for row in summary:
        if row["metric"] in {"prospective_stable", "prospective_decay", "prospective_variance_warning", "prospective_insufficient_sample", "live_modelling_yes", "live_execution_yes"}:
            print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {WATCHLIST}")


if __name__ == "__main__":
    main()
