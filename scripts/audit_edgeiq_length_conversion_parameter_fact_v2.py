from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FACT = ROOT / "public" / "data" / "edgeiq_length_conversion_parameter_fact_v2.csv"
CONTRACT = ROOT / "contracts" / "performance-intelligence" / "edgeiq_length_conversion_parameter_fact_v2_contract.json"
AUDIT = ROOT / "public" / "data" / "edgeiq_length_conversion_parameter_fact_v2_audit.json"


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def main() -> int:
    checks: dict[str, dict[str, object]] = {}
    def check(name: str, passed: bool, detail: object) -> None:
        checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}
    missing = [str(path.relative_to(ROOT)) for path in [FACT, CONTRACT] if not path.exists()]
    check("required_files_exist", not missing, missing)
    if missing:
        payload = {"audit_name": "edgeiq_length_conversion_parameter_fact_v2", "status": "FAIL", "checks": checks}
        AUDIT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 1
    fields, rows = read_csv(FACT)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    check("contract_fields_exact", fields == contract["required_fields"], {"actual": fields, "expected": contract["required_fields"]})
    ids = [clean(row.get("length_conversion_parameter_id")) for row in rows]
    check("unique_parameter_ids", len(ids) == len(set(ids)), ids)
    required_keys = {("TURF", "FIRM"), ("TURF", "GOOD"), ("TURF", "SOFT"), ("TURF", "HEAVY"), ("AUSTRALIAN_SYNTHETIC", "STANDARD_SYNTHETIC")}
    actual_keys = {(clean(row.get("surface_group")), clean(row.get("track_condition_group"))) for row in rows}
    check("required_surface_condition_rows", required_keys.issubset(actual_keys), sorted(required_keys - actual_keys))
    arithmetic_errors = []
    governance_errors = []
    for row in rows:
        try:
            lps = Decimal(clean(row.get("lengths_per_second")))
            spl = Decimal(clean(row.get("seconds_per_length")))
            if abs((Decimal("1") / lps) - spl) > Decimal("0.000000001"):
                arithmetic_errors.append(clean(row.get("length_conversion_parameter_id")))
        except Exception:
            arithmetic_errors.append(clean(row.get("length_conversion_parameter_id")))
        if clean(row.get("conversion_scope")) != "SURFACE_CONDITION" or clean(row.get("parameter_status")) != "AVAILABLE" or clean(row.get("conversion_model_version")) != "EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2":
            governance_errors.append(clean(row.get("length_conversion_parameter_id")))
    check("seconds_per_length_inverse", not arithmetic_errors, arithmetic_errors)
    check("governance_values", not governance_errors, governance_errors)
    failed = [name for name, result in checks.items() if result["status"] != "PASS"]
    payload = {
        "audit_name": "edgeiq_length_conversion_parameter_fact_v2",
        "status": "PASS" if not failed else "FAIL",
        "counts": {"parameter_rows": len(rows)},
        "failed_checks": failed,
        "checks": checks,
    }
    AUDIT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
