from __future__ import annotations

import csv
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

STANDARD_TIME_PATH = DATA / "edgeiq_standard_time_fact_v1.csv"
ACCUMULATION_PATH = DATA / "edgeiq_benchmark_accumulation_fact_v1.csv"
AUDIT_PATH = DATA / "edgeiq_standard_time_fact_v1_audit.json"
CONTRACT_PATH = ROOT / "contracts/performance-intelligence" / "edgeiq_standard_time_fact_v1_contract.json"

MINIMUM_REQUIRED_SAMPLE = 20
HISTORICAL_BRIDGE_VERSION = "edgeiq_standard_time_historical_results_bridge_v1.0.0"


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def truthy(value: object) -> bool:
    return text(value).lower() in {"true", "1", "yes"}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"Missing CSV header: {path}")
        return list(reader.fieldnames), list(reader)


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temporary_path = Path(temporary_name)
    try:
        temporary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def decimal_ok(value: object) -> bool:
    try:
        return Decimal(text(value)) > 0
    except Exception:
        return False


def main() -> None:
    checks: dict[str, dict[str, object]] = {}

    def check(name: str, passed: bool, detail: object) -> None:
        checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}

    required_paths = [STANDARD_TIME_PATH, ACCUMULATION_PATH, CONTRACT_PATH]
    missing = [str(path.relative_to(ROOT)) for path in required_paths if not path.exists()]
    check("required_files_exist", not missing, missing)
    if missing:
        payload = {"audit_name": "edgeiq_standard_time_fact_v1", "audit_version": "1.1.0", "status": "FAIL", "checks": checks}
        atomic_write_json(AUDIT_PATH, payload)
        raise SystemExit("EDGEIQ_STANDARD_TIME_ENGINE_V1_AUDIT_FAIL")

    standard_fields, standard_rows = read_csv(STANDARD_TIME_PATH)
    _, accumulation_rows = read_csv(ACCUMULATION_PATH)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    check("contract_fields_exact", standard_fields == contract["required_fields"], {"actual": standard_fields, "expected": contract["required_fields"]})

    ids = [text(row["standard_time_id"]) for row in standard_rows]
    groups = [text(row["benchmark_group_id"]) for row in standard_rows]
    check("unique_standard_time_ids", not [key for key, count in Counter(ids).items() if key and count > 1], Counter(ids))
    check("one_row_per_benchmark_group", not [key for key, count in Counter(groups).items() if key and count > 1], Counter(groups))

    numeric_errors = []
    governance_errors = []
    bridge_rows = 0
    accumulation_rows_out = 0
    for row in standard_rows:
        if not decimal_ok(row["standard_time_seconds"]) or not decimal_ok(row["sample_minimum_time_seconds"]) or not decimal_ok(row["sample_maximum_time_seconds"]):
            numeric_errors.append(text(row["benchmark_group_id"]))
        if int(text(row["sample_observation_count"])) < MINIMUM_REQUIRED_SAMPLE or int(text(row["minimum_required_sample"])) != MINIMUM_REQUIRED_SAMPLE:
            governance_errors.append(text(row["benchmark_group_id"]))
        if text(row["benchmark_group_basis"]) != "TRACK_DISTANCE" or text(row["standard_time_method"]) != "MEDIAN_WINNER_RACE_TIME_SECONDS" or text(row["standard_time_status"]) != "AVAILABLE":
            governance_errors.append(text(row["benchmark_group_id"]))
        if text(row["course_name_status"]) != "NOT_AVAILABLE_IN_SOURCE" or text(row["surface_status"]) != "NOT_AVAILABLE_IN_SOURCE" or text(row["track_condition_status"]) != "NOT_AVAILABLE_IN_SOURCE":
            governance_errors.append(text(row["benchmark_group_id"]))
        if text(row["source_accumulation_builder_version"]) == HISTORICAL_BRIDGE_VERSION:
            bridge_rows += 1
        else:
            accumulation_rows_out += 1

    ready_groups = [
        row for row in accumulation_rows
        if truthy(row.get("benchmark_ready"))
        and text(row.get("accumulation_status")) == "READY"
        and int(text(row.get("eligible_observation_count") or "0")) >= MINIMUM_REQUIRED_SAMPLE
    ]
    source_mode = "HISTORICAL_RESULTS_BRIDGE" if bridge_rows and not accumulation_rows_out else "BENCHMARK_ACCUMULATION"

    check("numeric_fields_valid", not numeric_errors, numeric_errors[:20])
    check("readiness_governance", not governance_errors, governance_errors[:20])
    check("source_mode_valid", source_mode in {"HISTORICAL_RESULTS_BRIDGE", "BENCHMARK_ACCUMULATION"}, source_mode)
    check("historical_bridge_used_only_when_no_ready_accumulation_groups", not (bridge_rows and ready_groups), {"bridge_rows": bridge_rows, "ready_accumulation_groups": len(ready_groups)})
    check("standard_time_rows_populated", len(standard_rows) > 0, len(standard_rows))

    forbidden_fields = set(contract["forbidden_fields"])
    present_forbidden_fields = sorted(forbidden_fields.intersection(standard_fields))
    check("no_forbidden_fields", not present_forbidden_fields, present_forbidden_fields)

    failed_checks = [name for name, result in checks.items() if result["status"] != "PASS"]
    status = "PASS" if not failed_checks else "FAIL"
    payload = {
        "audit_name": "edgeiq_standard_time_fact_v1",
        "audit_version": "1.1.0",
        "audited_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": status,
        "counts": {
            "accumulation_groups": len(accumulation_rows),
            "ready_accumulation_groups": len(ready_groups),
            "standard_time_rows": len(standard_rows),
            "historical_bridge_rows": bridge_rows,
            "benchmark_accumulation_output_rows": accumulation_rows_out,
        },
        "failed_checks": failed_checks,
        "checks": checks,
    }
    atomic_write_json(AUDIT_PATH, payload)
    if status != "PASS":
        print(json.dumps(payload, indent=2))
        raise SystemExit("EDGEIQ_STANDARD_TIME_ENGINE_V1_AUDIT_FAIL")
    print("EDGEIQ_STANDARD_TIME_ENGINE_V1_AUDIT_PASS")
    for name, value in payload["counts"].items():
        print(f"{name}={value}")
    print(f"audit_output={AUDIT_PATH}")


if __name__ == "__main__":
    main()
