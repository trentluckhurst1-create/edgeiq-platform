from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
WAREHOUSE = ROOT / "docs" / "performance-intelligence" / "warehouse" / "edgeiq_performance_fact_warehouse_v1.csv"

EXPECTED = {
    "warehouse_rows": 879784,
    "unique_races": 71025,
    "timed_races": 70308,
    "standard_times": 695,
    "race_time_deltas": 54978,
    "lengths_v_standard": 52414,
    "performance_base": 52414,
}
EXPECTED_UNITS = {
    "CENTISECONDS_TO_SECONDS_V1": 712856,
    "UNSUPPORTED_TIME_UNIT": 166928,
}

RECOVERY_OUTPUTS = {
    "timed_races": DATA / "edgeiq_recovered_timing_warehouse_v1.csv",
    "standard_times": DATA / "edgeiq_standard_time_fact_recovered_v1.csv",
    "race_time_deltas": DATA / "edgeiq_race_time_delta_versus_standard_recovered_v1.csv",
    "lengths_v_standard": DATA / "edgeiq_lengths_versus_standard_recovered_v1.csv",
    "performance_base": DATA / "edgeiq_performance_intelligence_base_recovered_v1.csv",
}

CANONICAL_OUTPUTS = {
    "timed_races": DATA / "edgeiq_canonical_historical_timing_warehouse_v1.csv",
    "standard_times": DATA / "edgeiq_standard_time_fact_v1.csv",
    "race_time_deltas": DATA / "edgeiq_race_time_delta_versus_standard_fact_v1.csv",
    "lengths_v_standard": DATA / "edgeiq_lengths_versus_standard_fact_v1.csv",
    "performance_base": DATA / "edgeiq_performance_intelligence_base_fact_v1.csv",
}


def count_rows(path: Path) -> int:
    if not path.exists():
        return -1
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def warehouse_preflight() -> dict[str, object]:
    if not WAREHOUSE.exists():
        raise RuntimeError(
            "Historical Performance Fact Warehouse is missing. "
            f"Expected local governed source: {WAREHOUSE}"
        )
    rows = 0
    races: set[str] = set()
    timed: set[str] = set()
    units: Counter[str] = Counter()
    with WAREHOUSE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"canonical_race_id", "official_race_time_seconds", "time_unit"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise RuntimeError(f"Warehouse missing required fields: {sorted(missing)}")
        for row in reader:
            rows += 1
            race_id = (row.get("canonical_race_id") or "").strip()
            if race_id:
                races.add(race_id)
            unit = (row.get("time_unit") or "").strip()
            units[unit] += 1
            raw = (row.get("official_race_time_seconds") or "").strip()
            try:
                seconds = float(raw) if raw else None
            except ValueError:
                seconds = None
            if race_id and seconds is not None and seconds > 0:
                timed.add(race_id)
    observed = {
        "warehouse_rows": rows,
        "unique_races": len(races),
        "timed_races": len(timed),
        "unit_counts": dict(units),
    }
    failures = []
    for key in ("warehouse_rows", "unique_races", "timed_races"):
        if observed[key] != EXPECTED[key]:
            failures.append(f"{key}: expected={EXPECTED[key]} observed={observed[key]}")
    if dict(units) != EXPECTED_UNITS:
        failures.append(f"unit_counts: expected={EXPECTED_UNITS} observed={dict(units)}")
    if failures:
        raise RuntimeError("HISTORICAL_WAREHOUSE_PREFLIGHT_BLOCKED\n" + "\n".join(failures))
    return observed


def run(script: str) -> None:
    print(f"RUN={script}", flush=True)
    proc = subprocess.run([sys.executable, "-u", str(ROOT / script)], cwd=ROOT)
    if proc.returncode:
        raise RuntimeError(f"FAILED={script}; returncode={proc.returncode}")


def gate(paths: dict[str, Path], label: str) -> dict[str, int]:
    observed = {key: count_rows(path) for key, path in paths.items()}
    failures = [
        f"{key}: expected={EXPECTED[key]} observed={value}"
        for key, value in observed.items()
        if value != EXPECTED[key]
    ]
    if failures:
        raise RuntimeError(label + "_BLOCKED\n" + "\n".join(failures))
    return observed


def main() -> int:
    print("=" * 100)
    print("EDGEIQ HISTORICAL PERFORMANCE RESTORE V1")
    print("=" * 100)
    preflight = warehouse_preflight()
    print("WAREHOUSE_PREFLIGHT=PASS")
    print(json.dumps(preflight, indent=2, sort_keys=True))

    # Side-by-side only. No canonical files are touched before this exact gate passes.
    run("scripts/build_edgeiq_timing_warehouse_recovery_v1.py")
    recovered = gate(RECOVERY_OUTPUTS, "RECOVERY_CARDINALITY_GATE")
    print("RECOVERY_CARDINALITY_GATE=PASS")
    print(json.dumps(recovered, indent=2, sort_keys=True))

    # Existing promotion archives the old canonical/current-window contracts before replacement.
    run("scripts/promote_edgeiq_timing_warehouse_canonical_v1.py")
    canonical = gate(CANONICAL_OUTPUTS, "CANONICAL_PROMOTION_GATE")
    print("CANONICAL_PROMOTION_GATE=PASS")
    print(json.dumps(canonical, indent=2, sort_keys=True))

    # Validate the promoted historical chain with the existing governed audits.
    for script in [
        "scripts/audit_edgeiq_race_time_delta_versus_standard_v1.py",
        "scripts/audit_edgeiq_lengths_versus_standard_v1.py",
        "scripts/audit_edgeiq_lengths_standard_condition_rejections_v1.py",
        "scripts/audit_edgeiq_performance_intelligence_base_fact_v1.py",
    ]:
        run(script)

    print("=" * 100)
    print("EDGEIQ_HISTORICAL_PERFORMANCE_RESTORE_V1_PASS")
    print("TIMED_RACES=70308")
    print("STANDARD_TIMES=695")
    print("RACE_TIME_DELTAS=54978")
    print("LENGTHS_V_STANDARD=52414")
    print("PERFORMANCE_BASE=52414")
    print("CURRENT_WINDOW_39_ROW_CONTRACT=PRESERVED_SEPARATELY")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
