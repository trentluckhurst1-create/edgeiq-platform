from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
TIMING_PATH = DATA / "edgeiq_canonical_historical_timing_warehouse_v1.csv"
OBSERVATION_PATH = DATA / "edgeiq_benchmark_observation_fact_v1.csv"
ELIGIBILITY_PATH = DATA / "edgeiq_benchmark_eligibility_fact_v1.csv"
MEMBERSHIP_PATH = DATA / "edgeiq_benchmark_accumulation_membership_fact_v1.csv"
STANDARD_TIME_PATH = DATA / "edgeiq_standard_time_fact_v1.csv"
DELTA_PATH = DATA / "edgeiq_race_time_delta_versus_standard_fact_v1.csv"
AUDIT_PATH = DATA / "edgeiq_race_time_delta_versus_standard_fact_v1_audit.json"
CONTRACT_PATH = ROOT / "contracts" / "performance-intelligence" / "edgeiq_race_time_delta_versus_standard_fact_v1_contract.json"
CONTRACT_VERSION = "1.0.0"
OLD_CALCULATION_METHOD = "WINNER_RACE_TIME_MINUS_STANDARD_TIME_SECONDS"
RECOVERED_CALCULATION_METHOD = "WINNER_RACE_TIME_MINUS_RECOVERED_STANDARD_TIME_SECONDS"
ELIGIBLE_CLASS = "STANDARD_TIME_ELIGIBLE"


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def dec(value: object) -> Decimal:
    return Decimal(text(value))


def fmt(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.000001')):.6f}"


def key_hash(parts: Iterable[object], n: int = 24) -> str:
    payload = "\x1f".join(text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:n].upper()


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def recovered_evidence(obs_hash: str, standard_hash: str, delta: Decimal) -> str:
    return hashlib.sha256((obs_hash + standard_hash + fmt(delta)).encode("utf-8")).hexdigest()


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


def expected_interpretation(delta: Decimal) -> str:
    if delta < 0:
        return "FASTER_THAN_STANDARD"
    if delta > 0:
        return "SLOWER_THAN_STANDARD"
    return "EQUAL_TO_STANDARD"


def race_key(row: dict[str, str]) -> str:
    return f"{text(row.get('race_date'))}|{text(row.get('track')).upper()}|R{text(row.get('race_number')).zfill(2)}"


def standard_key_from_timing(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (text(row.get("track")).upper(), text(row.get("distance_metres")), text(row.get("surface_group")), text(row.get("track_condition_group")))


def standard_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (text(row.get("track_name")).upper(), text(row.get("official_distance_metres")), text(row.get("surface")), text(row.get("track_condition")))


def main() -> None:
    checks: dict[str, dict[str, object]] = {}

    def check(name: str, passed: bool, detail: object) -> None:
        checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}

    delta_mode = "RECOVERED_CANONICAL" if TIMING_PATH.exists() else "LEGACY_THIN_WINDOW"
    required_paths = [STANDARD_TIME_PATH, DELTA_PATH, CONTRACT_PATH]
    if delta_mode == "RECOVERED_CANONICAL":
        required_paths.append(TIMING_PATH)
    else:
        required_paths.extend([OBSERVATION_PATH, ELIGIBILITY_PATH, MEMBERSHIP_PATH])
    missing_paths = [str(path.relative_to(ROOT)) for path in required_paths if not path.exists()]
    check("required_files_exist", not missing_paths, missing_paths)
    if missing_paths:
        payload = {"audit_name": "edgeiq_race_time_delta_versus_standard_fact_v1", "audit_version": "1.1.0", "status": "FAIL", "delta_mode": delta_mode, "checks": checks}
        atomic_write_json(AUDIT_PATH, payload)
        raise SystemExit("EDGEIQ_RACE_TIME_DELTA_VERSUS_STANDARD_V1_AUDIT_FAIL")

    _, standard_rows = read_csv(STANDARD_TIME_PATH)
    delta_fields, delta_rows = read_csv(DELTA_PATH)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    check("contract_fields_exact", delta_fields == contract["required_fields"], {"actual": delta_fields, "expected": contract["required_fields"]})
    duplicate_ids = sorted(value for value, count in Counter(text(row.get("race_time_delta_id")) for row in delta_rows).items() if value and count != 1)
    duplicate_observations = sorted(value for value, count in Counter(text(row.get("benchmark_observation_id")) for row in delta_rows).items() if value and count != 1)
    check("unique_race_time_delta_ids", not duplicate_ids, duplicate_ids[:50])
    check("one_row_per_observation", not duplicate_observations, duplicate_observations[:50])

    calculation_errors: list[str] = []
    identity_errors: list[str] = []
    lineage_errors: list[str] = []
    interpretation_errors: list[str] = []
    governance_errors: list[str] = []

    if delta_mode == "RECOVERED_CANONICAL":
        _, timing_rows = read_csv(TIMING_PATH)
        timing_by_id = {text(row.get("recovered_timing_observation_id")): row for row in timing_rows}
        standard_by_id = {text(row.get("standard_time_id")): row for row in standard_rows}
        standard_by_key = {standard_key(row): row for row in standard_rows}
        expected_ids: set[str] = set()
        for timing in timing_rows:
            standard = standard_by_key.get(standard_key_from_timing(timing))
            if standard is None:
                continue
            if not text(timing.get("official_race_time_seconds")) or not text(standard.get("standard_time_seconds")):
                continue
            expected_ids.add(text(timing.get("recovered_timing_observation_id")))
        output_ids = {text(row.get("benchmark_observation_id")) for row in delta_rows}
        check("expected_population_exact", expected_ids == output_ids, {"expected_count": len(expected_ids), "output_count": len(output_ids), "missing_sample": sorted(expected_ids - output_ids)[:50], "unexpected_sample": sorted(output_ids - expected_ids)[:50]})
        for row in delta_rows:
            observation_id = text(row.get("benchmark_observation_id"))
            timing = timing_by_id.get(observation_id)
            standard = standard_by_id.get(text(row.get("standard_time_id")))
            if timing is None:
                lineage_errors.append(f"{observation_id}: unknown recovered timing observation")
                continue
            if standard is None:
                lineage_errors.append(f"{observation_id}: unknown standard time")
                continue
            winner_time = dec(row.get("winner_race_time_seconds"))
            standard_time = dec(row.get("standard_time_seconds"))
            delta = dec(row.get("time_delta_seconds"))
            if fmt(winner_time - standard_time) != fmt(delta):
                calculation_errors.append(observation_id)
            if text(row.get("time_delta_interpretation")) != expected_interpretation(delta):
                interpretation_errors.append(observation_id)
            expected_id = "RTDR-" + key_hash([race_key(timing), timing.get("canonical_race_id"), standard.get("standard_time_id")])
            expected_hash = recovered_evidence(text(timing.get("source_row_evidence_sha256")), text(standard.get("standard_time_evidence_sha256")), delta)
            if text(row.get("race_time_delta_id")) != expected_id or text(row.get("race_time_delta_evidence_sha256")) != expected_hash:
                identity_errors.append(observation_id)
            if text(row.get("source_observation_sha256")) != text(timing.get("source_row_evidence_sha256")) or text(row.get("source_standard_time_evidence_sha256")) != text(standard.get("standard_time_evidence_sha256")):
                lineage_errors.append(observation_id)
            if text(row.get("calculation_method")) != RECOVERED_CALCULATION_METHOD or text(row.get("contract_version")) != CONTRACT_VERSION:
                governance_errors.append(observation_id)
    else:
        _, observation_rows = read_csv(OBSERVATION_PATH)
        _, eligibility_rows = read_csv(ELIGIBILITY_PATH)
        _, membership_rows = read_csv(MEMBERSHIP_PATH)
        observation_by_id = {text(row["benchmark_observation_id"]): row for row in observation_rows}
        eligibility_by_id = {text(row["benchmark_observation_id"]): row for row in eligibility_rows}
        group_by_observation = {text(row["benchmark_observation_id"]): text(row["benchmark_group_id"]) for row in membership_rows}
        standard_by_group = {text(row["benchmark_group_id"]): row for row in standard_rows}
        standard_by_track_distance = {(text(row["track_name"]).upper(), text(row["official_distance_metres"])): row for row in standard_rows}
        def standard_for_observation(observation_id: str) -> dict[str, str] | None:
            observation = observation_by_id.get(observation_id)
            if observation is None:
                return None
            standard = standard_by_group.get(group_by_observation.get(observation_id, ""))
            if standard is not None:
                return standard
            return standard_by_track_distance.get((text(observation["track_name"]).upper(), text(observation["official_distance_metres"])))
        expected_ids = {obs_id for obs_id, eligibility in eligibility_by_id.items() if text(eligibility["benchmark_use_class"]) == ELIGIBLE_CLASS and standard_for_observation(obs_id) is not None}
        output_ids = {text(row["benchmark_observation_id"]) for row in delta_rows}
        check("expected_population_exact", expected_ids == output_ids, {"expected_count": len(expected_ids), "output_count": len(output_ids), "missing_sample": sorted(expected_ids - output_ids)[:50], "unexpected_sample": sorted(output_ids - expected_ids)[:50]})
        for row in delta_rows:
            observation_id = text(row["benchmark_observation_id"])
            observation = observation_by_id.get(observation_id)
            standard = standard_for_observation(observation_id)
            if observation is None or standard is None:
                lineage_errors.append(observation_id)
                continue
            winner_time = dec(row["winner_race_time_seconds"])
            standard_time = dec(row["standard_time_seconds"])
            delta = dec(row["time_delta_seconds"])
            if fmt(winner_time - standard_time) != fmt(delta):
                calculation_errors.append(observation_id)
            if text(row["time_delta_interpretation"]) != expected_interpretation(delta):
                interpretation_errors.append(observation_id)
            expected_identity_hash = sha256_payload([CONTRACT_VERSION, observation_id, text(standard["standard_time_id"]), OLD_CALCULATION_METHOD])
            expected_id = f"RTD1-{expected_identity_hash[:24].upper()}"
            expected_hash = sha256_payload([expected_id, fmt(winner_time), fmt(standard_time), fmt(delta)])
            if text(row["race_time_delta_id"]) != expected_id or text(row["race_time_delta_evidence_sha256"]) != expected_hash:
                identity_errors.append(observation_id)
            expected_observation_hash = sha256_payload([text(observation["race_source_row_sha256"]), text(observation["winner_source_row_sha256"])])
            if text(row["source_observation_sha256"]) != expected_observation_hash or text(row["source_standard_time_evidence_sha256"]) != text(standard["standard_time_evidence_sha256"]):
                lineage_errors.append(observation_id)
            if text(row["calculation_method"]) != OLD_CALCULATION_METHOD or text(row["contract_version"]) != CONTRACT_VERSION:
                governance_errors.append(observation_id)

    check("calculation_reproducible", not calculation_errors, calculation_errors[:50])
    check("time_delta_interpretation", not interpretation_errors, interpretation_errors[:50])
    check("deterministic_identity_and_evidence", not identity_errors, identity_errors[:50])
    check("canonical_lineage", not lineage_errors, lineage_errors[:50])
    check("calculation_governance", not governance_errors, governance_errors[:50])
    forbidden_fields = set(contract.get("forbidden_fields", []))
    present_forbidden_fields = sorted(forbidden_fields.intersection(delta_fields))
    check("no_forbidden_fields", not present_forbidden_fields, present_forbidden_fields)
    check("current_population_expected", checks.get("expected_population_exact", {}).get("status") == "PASS", {"standard_time_rows": len(standard_rows), "race_time_delta_rows": len(delta_rows), "delta_mode": delta_mode})
    failed = [name for name, result in checks.items() if result["status"] != "PASS"]
    payload = {"audit_name": "edgeiq_race_time_delta_versus_standard_fact_v1", "audit_version": "1.1.0", "audited_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"), "status": "PASS" if not failed else "FAIL", "delta_mode": delta_mode, "counts": {"standard_time_rows": len(standard_rows), "race_time_delta_rows": len(delta_rows)}, "failed_checks": failed, "checks": checks}
    atomic_write_json(AUDIT_PATH, payload)
    print(json.dumps(payload, indent=2))
    if failed:
        raise SystemExit("EDGEIQ_RACE_TIME_DELTA_VERSUS_STANDARD_V1_AUDIT_FAIL")


if __name__ == "__main__":
    main()
