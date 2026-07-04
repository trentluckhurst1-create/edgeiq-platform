from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

SOURCE = PUBLIC / "edgeiq_qld_telemetry_ontology_fragments_v1.csv"

OUT_CHAINS = PUBLIC / "edgeiq_qld_race_state_transition_chains_v1.csv"
OUT_PROFILES = PUBLIC / "edgeiq_qld_race_state_transition_profiles_v1.csv"
OUT_MEMORY = PUBLIC / "edgeiq_qld_race_state_transition_memory_v1.csv"
OUT_SUMMARY = PUBLIC / "edgeiq_qld_race_state_transition_summary_v1.csv"
OUT_FAILURES = PUBLIC / "edgeiq_qld_race_state_transition_failures_v1.csv"

ENGINE_VERSION = "EDGEIQ_QQLD_RACE_STATE_TRANSITION_ENGINE_V1"

DISTANCE_RE = re.compile(r"^\d{3,4}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d+$")
DECIMAL_RE = re.compile(r"^\d+\.\d+$")
INTEGER_RE = re.compile(r"^\d+$")

DISTANCE_SET = {200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000, 2200, 2400, 2600, 2800, 3000, 3200}

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

def safe_float(x: str) -> float | None:
    try:
        return float(str(x).strip())
    except Exception:
        return None

def seconds_from_timecode(value: str) -> float | None:
    text = str(value or "").strip()
    if not TIME_RE.match(text):
        return None
    try:
        hh, mm, ss = text.split(":")
        return int(hh) * 3600 + int(mm) * 60 + float(ss)
    except Exception:
        return None

def classify_fragment(value: str) -> str:
    text = str(value or "").strip().lower()

    if not text:
        return "EMPTY"

    if TIME_RE.match(text):
        return "SEGMENT_TIME"

    if DECIMAL_RE.match(text):
        f = safe_float(text)
        if f is not None and 5 <= f <= 40:
            return "SPEED_OR_SPLIT_NUMERIC"
        return "DECIMAL_NUMERIC"

    if INTEGER_RE.match(text):
        i = int(text)
        if i in DISTANCE_SET:
            return "DISTANCE_MARKER"
        if 1 <= i <= 30:
            return "RUNNER_NUMBER_OR_POSITION"
        return "INTEGER_NUMERIC"

    if re.search(r"[a-z]", text):
        return "RUNNER_OR_LABEL"

    return "UNKNOWN"

def transition_profile(times: list[float]) -> dict:
    if not times:
        return {
            "transition_count": 0,
            "avg_segment_seconds": "",
            "min_segment_seconds": "",
            "max_segment_seconds": "",
            "range_seconds": "",
            "transition_shape": "NO_TIMING_CHAIN",
        }

    avg = sum(times) / len(times)
    mn = min(times)
    mx = max(times)
    rg = mx - mn

    if len(times) >= 3:
        first = sum(times[: max(1, len(times)//3)]) / max(1, len(times[: max(1, len(times)//3)]))
        last = sum(times[-max(1, len(times)//3):]) / max(1, len(times[-max(1, len(times)//3):]))

        if last <= first - 0.35:
            shape = "LATE_ACCELERATION_STRUCTURE"
        elif last >= first + 0.35:
            shape = "LATE_DECELERATION_STRUCTURE"
        elif rg <= 0.45:
            shape = "STABLE_SECTIONAL_STRUCTURE"
        else:
            shape = "VARIABLE_SECTIONAL_STRUCTURE"
    elif rg <= 0.45:
        shape = "STABLE_SHORT_CHAIN"
    else:
        shape = "VARIABLE_SHORT_CHAIN"

    return {
        "transition_count": len(times),
        "avg_segment_seconds": round(avg, 3),
        "min_segment_seconds": round(mn, 3),
        "max_segment_seconds": round(mx, 3),
        "range_seconds": round(rg, 3),
        "transition_shape": shape,
    }

def main() -> None:
    print("=" * 88)
    print("EDGEIQ QLD RACE-STATE TRANSITION ENGINE V1")
    print("=" * 88)

    rows = read_csv(SOURCE)

    grouped = defaultdict(list)
    failures = []

    for r in rows:
        track = r.get("track", "")
        fragment = str(r.get("raw_fragment", "")).strip()
        try:
            idx = int(r.get("fragment_index", "0"))
        except Exception:
            idx = 0

        grouped[track].append({
            "track": track,
            "fragment_index": idx,
            "raw_fragment": fragment,
            "fragment_type": classify_fragment(fragment),
            "time_seconds": seconds_from_timecode(fragment),
        })

    chain_rows = []
    profile_rows = []
    memory_rows = []

    summary = Counter()

    for track, fragments in grouped.items():
        fragments = sorted(fragments, key=lambda x: x["fragment_index"])
        current_runner = None
        current_runner_no = None
        active_chain = []
        chain_no = 0

        def flush_chain() -> None:
            nonlocal chain_no, active_chain, current_runner, current_runner_no
            if not active_chain:
                return

            times = [x["segment_seconds"] for x in active_chain if x.get("segment_seconds") is not None]
            if not times:
                active_chain = []
                return

            chain_no += 1
            profile = transition_profile(times)

            for step_no, step in enumerate(active_chain, start=1):
                chain_rows.append({
                    "track": track,
                    "chain_no": chain_no,
                    "runner_name_or_label": current_runner or "",
                    "runner_number_or_position": current_runner_no or "",
                    "step_no": step_no,
                    "distance_marker": step.get("distance_marker", ""),
                    "speed_or_split_numeric": step.get("speed_or_split_numeric", ""),
                    "segment_time": step.get("segment_time", ""),
                    "segment_seconds": step.get("segment_seconds", ""),
                    "transition_shape": profile["transition_shape"],
                    "research_boundary": "OFFLINE_RESEARCH_ONLY",
                    "live_modelling_yes": 0,
                    "live_execution_yes": 0,
                    "engine_version": ENGINE_VERSION,
                })

            profile_rows.append({
                "track": track,
                "chain_no": chain_no,
                "runner_name_or_label": current_runner or "",
                "runner_number_or_position": current_runner_no or "",
                **profile,
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
                "live_modelling_yes": 0,
                "live_execution_yes": 0,
                "engine_version": ENGINE_VERSION,
                "timestamp_utc": now_iso(),
            })

            active_chain = []

        pending_distance = None
        pending_numeric = None

        for frag in fragments:
            ftype = frag["fragment_type"]
            value = frag["raw_fragment"]

            if ftype == "RUNNER_OR_LABEL":
                flush_chain()
                current_runner = value
                current_runner_no = None
                pending_distance = None
                pending_numeric = None
                continue

            if ftype == "RUNNER_NUMBER_OR_POSITION":
                if current_runner is not None and current_runner_no is None:
                    current_runner_no = value
                    continue

            if ftype == "DISTANCE_MARKER":
                pending_distance = value
                continue

            if ftype == "SPEED_OR_SPLIT_NUMERIC":
                pending_numeric = value
                continue

            if ftype == "SEGMENT_TIME":
                if pending_distance is not None:
                    active_chain.append({
                        "distance_marker": pending_distance,
                        "speed_or_split_numeric": pending_numeric or "",
                        "segment_time": value,
                        "segment_seconds": frag["time_seconds"],
                    })
                    pending_distance = None
                    pending_numeric = None
                else:
                    failures.append({
                        "track": track,
                        "raw_fragment": value,
                        "failure_reason": "SEGMENT_TIME_WITHOUT_DISTANCE_MARKER",
                        "research_boundary": "OFFLINE_RESEARCH_ONLY",
                    })

        flush_chain()

    shape_counter = Counter(r["transition_shape"] for r in profile_rows)

    for shape, count in shape_counter.most_common():
        memory_rows.append({
            "transition_shape": shape,
            "observed_chain_count": count,
            "memory_strength": "HIGH" if count >= 20 else "MEDIUM" if count >= 8 else "LOW",
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "live_modelling_yes": 0,
            "live_execution_yes": 0,
            "engine_version": ENGINE_VERSION,
            "timestamp_utc": now_iso(),
        })

    summary_rows = [
        {"metric": "input_fragments", "value": len(rows)},
        {"metric": "tracks_observed", "value": len(grouped)},
        {"metric": "transition_chain_rows", "value": len(chain_rows)},
        {"metric": "transition_profiles", "value": len(profile_rows)},
        {"metric": "transition_memory_rows", "value": len(memory_rows)},
        {"metric": "failure_rows", "value": len(failures)},
        {"metric": "offline_research_only", "value": "YES"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]

    write_csv(OUT_CHAINS, chain_rows, [
        "track",
        "chain_no",
        "runner_name_or_label",
        "runner_number_or_position",
        "step_no",
        "distance_marker",
        "speed_or_split_numeric",
        "segment_time",
        "segment_seconds",
        "transition_shape",
        "research_boundary",
        "live_modelling_yes",
        "live_execution_yes",
        "engine_version",
    ])

    write_csv(OUT_PROFILES, profile_rows, [
        "track",
        "chain_no",
        "runner_name_or_label",
        "runner_number_or_position",
        "transition_count",
        "avg_segment_seconds",
        "min_segment_seconds",
        "max_segment_seconds",
        "range_seconds",
        "transition_shape",
        "research_boundary",
        "live_modelling_yes",
        "live_execution_yes",
        "engine_version",
        "timestamp_utc",
    ])

    write_csv(OUT_MEMORY, memory_rows, [
        "transition_shape",
        "observed_chain_count",
        "memory_strength",
        "research_boundary",
        "live_modelling_yes",
        "live_execution_yes",
        "engine_version",
        "timestamp_utc",
    ])

    write_csv(OUT_SUMMARY, summary_rows, ["metric", "value"])

    write_csv(OUT_FAILURES, failures, [
        "track",
        "raw_fragment",
        "failure_reason",
        "research_boundary",
    ])

    for r in summary_rows:
        print(f"{r['metric']}: {r['value']}")

    print("=" * 88)
    print("TRANSITION MEMORY")
    print("=" * 88)
    for r in memory_rows:
        print(f"{r['transition_shape']}: {r['observed_chain_count']} ({r['memory_strength']})")

    print("=" * 88)
    print("OUTPUTS")
    print("=" * 88)
    print(OUT_CHAINS)
    print(OUT_PROFILES)
    print(OUT_MEMORY)
    print(OUT_SUMMARY)
    print(OUT_FAILURES)

if __name__ == "__main__":
    main()
