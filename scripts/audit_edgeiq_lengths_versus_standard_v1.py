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

DELTA = DATA / "edgeiq_race_time_delta_versus_standard_fact_v1.csv"
LVS = DATA / "edgeiq_lengths_versus_standard_fact_v1.csv"
REJECTED = DATA / "edgeiq_lengths_versus_standard_fact_v1_rejections.csv"
PARAMETER_V2 = DATA / "edgeiq_length_conversion_parameter_fact_v2.csv"
AUDIT = DATA / "edgeiq_lengths_versus_standard_fact_v1_audit.json"
CONTRACT = ROOT / "contracts" / "performance-intelligence" / "edgeiq_lengths_versus_standard_fact_v1_contract.json"

CALCULATION_METHOD = "NEGATIVE_TIME_DELTA_DIVIDED_BY_SECONDS_PER_LENGTH"


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def sha(parts: Iterable[object]) -> str:
    return hashlib.sha256("\x1f".join(clean(part) for part in parts).encode("utf-8")).hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def interp(value: Decimal) -> str:
    if value > 0:
        return "FASTER_THAN_STANDARD"
    if value < 0:
        return "SLOWER_THAN_STANDARD"
    return "EQUAL_TO_STANDARD"


def main() -> int:
    checks: dict[str, dict[str, object]] = {}
    def check(name: str, passed: bool, detail: object) -> None:
        checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}
    required = [DELTA, LVS, REJECTED, PARAMETER_V2, CONTRACT]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    check("required_files_exist", not missing, missing)
    if missing:
        payload = {"audit_name": "edgeiq_lengths_versus_standard_fact_v1", "status": "FAIL", "checks": checks}
        write_json(AUDIT, payload)
        return 1
    _, delta_rows = read_csv(DELTA)
    fields, rows = read_csv(LVS)
    _, rejected = read_csv(REJECTED)
    _, params = read_csv(PARAMETER_V2)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    check("contract_fields_exact", fields == contract["required_fields"], {"actual": fields, "expected": contract["required_fields"]})
    canonical_field_count = fields.count("winner_canonical_horse_id")
    canonical_field_index = fields.index("winner_canonical_horse_id") if canonical_field_count == 1 else -1
    winner_name_index = fields.index("winner_horse_name") if "winner_horse_name" in fields else -1
    check(
        "winner_canonical_horse_id_field_order",
        canonical_field_count == 1 and canonical_field_index == 10 and winner_name_index == 11,
        {
            "winner_canonical_horse_id_count": canonical_field_count,
            "winner_canonical_horse_id_index": canonical_field_index,
            "winner_horse_name_index": winner_name_index,
        },
    )
    check("row_funnel_exact", len(delta_rows) == len(rows) + len(rejected), {"delta_rows": len(delta_rows), "converted": len(rows), "rejected": len(rejected)})
    ids = [clean(row.get("lengths_versus_standard_id")) for row in rows]
    delta_ids = [clean(row.get("race_time_delta_id")) for row in rows]
    check("unique_lengths_versus_standard_ids", len(ids) == len(set(ids)), [])
    check("one_output_per_race_time_delta", len(delta_ids) == len(set(delta_ids)), [])
    delta_by_id = {clean(row.get("race_time_delta_id")): row for row in delta_rows}
    param_by_id = {clean(row.get("length_conversion_parameter_id")): row for row in params}
    calc_errors: list[str] = []
    lineage_errors: list[str] = []
    governance_errors: list[str] = []
    evidence_errors: list[str] = []
    canonical_identity_errors: list[str] = []
    canonical_identity_blanks: list[str] = []
    canonical_identity_conflicts: list[str] = []
    horse_ids_by_delta: dict[str, set[str]] = {}
    for row in rows:
        delta_id = clean(row.get("race_time_delta_id"))
        source = delta_by_id.get(delta_id)
        parameter = param_by_id.get(clean(row.get("length_conversion_parameter_id")))
        if not source or not parameter:
            lineage_errors.append(clean(row.get("lengths_versus_standard_id")))
            continue
        source_horse_id = clean(source.get("winner_canonical_horse_id"))
        output_horse_id = clean(row.get("winner_canonical_horse_id"))
        if source_horse_id and not output_horse_id:
            canonical_identity_blanks.append(clean(row.get("lengths_versus_standard_id")))
        if output_horse_id != source_horse_id:
            canonical_identity_errors.append(
                f"{clean(row.get('lengths_versus_standard_id'))}:source={source_horse_id}:output={output_horse_id}"
            )
        if delta_id:
            horse_ids_by_delta.setdefault(delta_id, set()).add(output_horse_id)
        td = Decimal(clean(row.get("time_delta_seconds")))
        spl = Decimal(clean(row.get("seconds_per_length")))
        lengths = Decimal(clean(row.get("lengths_versus_standard")))
        expected = -(td / spl)
        if abs(expected - lengths) > Decimal("0.000001"):
            calc_errors.append(clean(row.get("lengths_versus_standard_id")))
        if interp(lengths) != clean(row.get("lengths_versus_standard_interpretation")):
            calc_errors.append(clean(row.get("lengths_versus_standard_id")) + ":interpretation")
        if clean(row.get("source_race_time_delta_evidence_sha256")) != clean(source.get("race_time_delta_evidence_sha256")) or clean(row.get("source_conversion_parameter_evidence_sha256")) != clean(parameter.get("parameter_evidence_sha256")):
            lineage_errors.append(clean(row.get("lengths_versus_standard_id")))
        if clean(row.get("calculation_method")) != CALCULATION_METHOD or clean(row.get("conversion_scope")) != "SURFACE_CONDITION" or clean(row.get("conversion_model_version")) != "EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2" or clean(row.get("contract_version")) != contract["contract_version"]:
            governance_errors.append(clean(row.get("lengths_versus_standard_id")))
        legacy_evidence = sha([row.get("lengths_versus_standard_id"), source.get("race_time_delta_evidence_sha256"), parameter.get("parameter_evidence_sha256"), f"{lengths.quantize(Decimal('0.000001')):.6f}"])
        recovered_evidence = hashlib.sha256((clean(source.get("race_time_delta_evidence_sha256")) + clean(parameter.get("parameter_evidence_sha256")) + f"{lengths.quantize(Decimal('0.000001')):.6f}").encode("utf-8")).hexdigest()
        if clean(row.get("lengths_versus_standard_evidence_sha256")) not in {legacy_evidence, recovered_evidence}:
            evidence_errors.append(clean(row.get("lengths_versus_standard_id")))
    for delta_id, horse_ids in horse_ids_by_delta.items():
        nonblank_ids = {horse_id for horse_id in horse_ids if horse_id}
        if len(nonblank_ids) > 1:
            canonical_identity_conflicts.append(f"{delta_id}:{sorted(nonblank_ids)}")
    check("calculation_reproducible", not calc_errors, calc_errors[:20])
    check("canonical_lineage", not lineage_errors, lineage_errors[:20])
    check("winner_canonical_horse_id_direct_pass_through", not canonical_identity_errors, canonical_identity_errors[:50])
    check("winner_canonical_horse_id_nonblank_when_source_present", not canonical_identity_blanks, canonical_identity_blanks[:50])
    check("winner_canonical_horse_id_no_duplicate_conflict", not canonical_identity_conflicts, canonical_identity_conflicts[:50])
    check("conversion_parameter_governance", not governance_errors, governance_errors[:20])
    check("deterministic_evidence", not evidence_errors, evidence_errors[:20])
    rejected_reasons = Counter(clean(row.get("rejection_reason")) for row in rejected)
    check("rejections_are_explicit", all(clean(row.get("rejection_reason")) for row in rejected), dict(rejected_reasons))
    failed = [name for name, result in checks.items() if result["status"] != "PASS"]
    payload = {
        "audit_name": "edgeiq_lengths_versus_standard_fact_v1",
        "audit_version": "1.1.0",
        "audited_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "PASS" if not failed else "FAIL",
        "counts": {
            "race_time_delta_rows": len(delta_rows),
            "lengths_versus_standard_rows": len(rows),
            "rejected_rows": len(rejected),
            "conversion_parameter_v2_rows": len(params),
        },
        "rejection_reasons": dict(rejected_reasons),
        "failed_checks": failed,
        "checks": checks,
    }
    write_json(AUDIT, payload)
    print(json.dumps(payload, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
