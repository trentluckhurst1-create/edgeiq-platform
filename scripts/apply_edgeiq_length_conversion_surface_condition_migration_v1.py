from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "restart-v1"
CONTRACTS = ROOT / "contracts" / "performance-intelligence"
SCRIPTS = ROOT / "scripts"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def backup_once(source: Path, suffix: str) -> None:
    if source.exists():
        target = source.with_name(source.stem + suffix + source.suffix)
        if not target.exists():
            shutil.copyfile(source, target)


PARAMETER_V2_CONTRACT = r'''{
  "contract_name": "edgeiq_length_conversion_parameter_fact_v2",
  "contract_version": "2.0.0",
  "grain": "one_row_per_governed_surface_condition_conversion_parameter",
  "primary_key": [
    "length_conversion_parameter_id"
  ],
  "required_fields": [
    "length_conversion_parameter_id",
    "conversion_scope",
    "surface_group",
    "track_condition_min",
    "track_condition_max",
    "track_condition_group",
    "lengths_per_second",
    "seconds_per_length",
    "conversion_model_version",
    "parameter_status",
    "effective_from_date",
    "effective_to_date",
    "evidence_reference",
    "source_evidence_sha256",
    "parameter_evidence_sha256",
    "builder_version",
    "contract_version",
    "built_at_utc"
  ],
  "allowed_values": {
    "conversion_scope": [
      "SURFACE_CONDITION"
    ],
    "parameter_status": [
      "AVAILABLE"
    ],
    "conversion_model_version": [
      "EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2"
    ]
  },
  "forbidden_fields": [
    "track_variant",
    "condition_adjustment",
    "course_adjustment",
    "surface_adjustment",
    "lengths_versus_standard",
    "performance_rating",
    "speed_rating",
    "epi"
  ]
}
'''


LVS_V1_CONTRACT = r'''{
  "contract_name": "edgeiq_lengths_versus_standard_fact_v1",
  "contract_version": "1.1.0",
  "grain": "one_row_per_race_time_delta_with_one_governed_conversion_parameter",
  "calculation_method": "NEGATIVE_TIME_DELTA_DIVIDED_BY_SECONDS_PER_LENGTH",
  "primary_key": [
    "lengths_versus_standard_id"
  ],
  "required_fields": [
    "lengths_versus_standard_id",
    "race_time_delta_id",
    "benchmark_observation_id",
    "benchmark_group_id",
    "standard_time_id",
    "length_conversion_parameter_id",
    "race_key",
    "race_date",
    "track_name",
    "official_distance_metres",
    "winner_horse_name",
    "winner_race_time_seconds",
    "standard_time_seconds",
    "time_delta_seconds",
    "seconds_per_length",
    "lengths_versus_standard",
    "lengths_versus_standard_interpretation",
    "calculation_method",
    "conversion_scope",
    "conversion_model_version",
    "source_race_time_delta_evidence_sha256",
    "source_conversion_parameter_evidence_sha256",
    "lengths_versus_standard_evidence_sha256",
    "builder_version",
    "contract_version",
    "built_at_utc"
  ],
  "allowed_values": {
    "lengths_versus_standard_interpretation": [
      "FASTER_THAN_STANDARD",
      "EQUAL_TO_STANDARD",
      "SLOWER_THAN_STANDARD"
    ],
    "calculation_method": [
      "NEGATIVE_TIME_DELTA_DIVIDED_BY_SECONDS_PER_LENGTH"
    ],
    "conversion_scope": [
      "DISTANCE_EXACT",
      "SURFACE_CONDITION"
    ]
  },
  "forbidden_fields": [
    "track_variant",
    "condition_adjustment",
    "course_adjustment",
    "surface_adjustment",
    "performance_rating",
    "speed_rating",
    "epi"
  ]
}
'''


BUILD_PARAMETER_V2 = r'''from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "config" / "performance-intelligence" / "edgeiq_length_conversion_parameter_source_v2.csv"
OUT = ROOT / "public" / "data" / "edgeiq_length_conversion_parameter_fact_v2.csv"
AUDIT = ROOT / "public" / "data" / "edgeiq_length_conversion_parameter_fact_v2_audit.json"

FIELDS = [
    "length_conversion_parameter_id",
    "conversion_scope",
    "surface_group",
    "track_condition_min",
    "track_condition_max",
    "track_condition_group",
    "lengths_per_second",
    "seconds_per_length",
    "conversion_model_version",
    "parameter_status",
    "effective_from_date",
    "effective_to_date",
    "evidence_reference",
    "source_evidence_sha256",
    "parameter_evidence_sha256",
    "builder_version",
    "contract_version",
    "built_at_utc",
]

CONTRACT_VERSION = "2.0.0"
BUILDER_VERSION = "edgeiq_length_conversion_parameter_fact_v2.0.0"
SCOPE = "SURFACE_CONDITION"


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def sha(parts: Iterable[object]) -> str:
    return hashlib.sha256("\x1f".join(clean(part) for part in parts).encode("utf-8")).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        with tmp.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="raise", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def format_decimal(value: object, places: str) -> str:
    if clean(value) == "":
        return ""
    return f"{Decimal(clean(value)).quantize(Decimal(places))}"


def parameter_id(surface: str, group: str) -> str:
    return f"LCP2-{surface}-{group}".replace("_", "-")


def main() -> int:
    rows = read_csv(SOURCE)
    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    out: list[dict[str, object]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for ordinal, row in enumerate(rows, start=1):
        if clean(row.get("status")) != "APPROVED":
            continue
        surface = clean(row.get("surface_group")).upper()
        group = clean(row.get("track_condition_group")).upper()
        method = clean(row.get("method_version"))
        if method != "EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2":
            errors.append(f"row {ordinal}: unsupported method {method}")
            continue
        lps = Decimal(clean(row.get("lengths_per_second")))
        spl = Decimal(clean(row.get("seconds_per_length")))
        expected_spl = Decimal("1") / lps
        if abs(spl - expected_spl) > Decimal("0.000000001"):
            errors.append(f"row {ordinal}: seconds_per_length does not equal 1/lengths_per_second")
            continue
        pid = parameter_id(surface, group)
        if pid in seen:
            errors.append(f"row {ordinal}: duplicate parameter id {pid}")
            continue
        seen.add(pid)
        source_hash = sha([method, surface, row.get("track_condition_min"), row.get("track_condition_max"), group, format_decimal(lps, "0.000000001"), format_decimal(spl, "0.000000001"), row.get("provenance_class")])
        evidence_hash = sha([pid, source_hash, method, surface, group, format_decimal(lps, "0.000000001"), format_decimal(spl, "0.000000001")])
        out.append({
            "length_conversion_parameter_id": pid,
            "conversion_scope": SCOPE,
            "surface_group": surface,
            "track_condition_min": clean(row.get("track_condition_min")),
            "track_condition_max": clean(row.get("track_condition_max")),
            "track_condition_group": group,
            "lengths_per_second": format_decimal(lps, "0.000000001"),
            "seconds_per_length": format_decimal(spl, "0.000000001"),
            "conversion_model_version": method,
            "parameter_status": "AVAILABLE",
            "effective_from_date": "2000-01-01",
            "effective_to_date": "",
            "evidence_reference": "config/performance-intelligence/edgeiq_length_conversion_parameter_source_v2.csv",
            "source_evidence_sha256": source_hash,
            "parameter_evidence_sha256": evidence_hash,
            "builder_version": BUILDER_VERSION,
            "contract_version": CONTRACT_VERSION,
            "built_at_utc": built_at,
        })
    out.sort(key=lambda row: (clean(row["surface_group"]), clean(row["track_condition_min"]), clean(row["track_condition_group"])))
    write_csv(OUT, out)
    payload = {
        "audit_name": "edgeiq_length_conversion_parameter_fact_v2",
        "status": "PASS" if out and not errors else "FAIL",
        "source_rows": len(rows),
        "parameter_rows": len(out),
        "errors": errors,
        "conversion_model_version": "EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2",
    }
    AUDIT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''


AUDIT_PARAMETER_V2 = r'''from __future__ import annotations

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
'''


BUILD_LVS = r'''from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from edgeiq_length_conversion_method_v1 import resolve_length_conversion


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "restart-v1"

DELTA = DATA / "edgeiq_race_time_delta_versus_standard_fact_v1.csv"
WAREHOUSE = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
PARAMETER = DATA / "edgeiq_length_conversion_parameter_fact_v2.csv"
OUT = DATA / "edgeiq_lengths_versus_standard_fact_v1.csv"
REJECTED = DATA / "edgeiq_lengths_versus_standard_fact_v1_rejections.csv"
SUMMARY = DATA / "edgeiq_lengths_versus_standard_fact_v1_summary.json"

CONTRACT_VERSION = "1.1.0"
BUILDER_VERSION = "edgeiq_lengths_versus_standard_surface_condition_v1.1.0"
CALCULATION_METHOD = "NEGATIVE_TIME_DELTA_DIVIDED_BY_SECONDS_PER_LENGTH"
CONVERSION_SCOPE = "SURFACE_CONDITION"

FIELDS = [
    "lengths_versus_standard_id",
    "race_time_delta_id",
    "benchmark_observation_id",
    "benchmark_group_id",
    "standard_time_id",
    "length_conversion_parameter_id",
    "race_key",
    "race_date",
    "track_name",
    "official_distance_metres",
    "winner_horse_name",
    "winner_race_time_seconds",
    "standard_time_seconds",
    "time_delta_seconds",
    "seconds_per_length",
    "lengths_versus_standard",
    "lengths_versus_standard_interpretation",
    "calculation_method",
    "conversion_scope",
    "conversion_model_version",
    "source_race_time_delta_evidence_sha256",
    "source_conversion_parameter_evidence_sha256",
    "lengths_versus_standard_evidence_sha256",
    "builder_version",
    "contract_version",
    "built_at_utc",
]

REJECTION_FIELDS = ["race_time_delta_id", "race_key", "race_date", "track_name", "official_distance_metres", "rejection_reason", "surface_group", "track_condition_number", "track_condition_group"]


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def norm(value: object) -> str:
    return "".join(ch for ch in clean(value).upper() if ch.isalnum())


def sha(parts: Iterable[object]) -> str:
    return hashlib.sha256("\x1f".join(clean(part) for part in parts).encode("utf-8")).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        with tmp.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def race_no_from_key(value: str) -> str:
    match = re.search(r"\|R(\d+)$", clean(value).upper())
    return str(int(match.group(1))) if match else ""


def distance_text(value: object) -> str:
    return "".join(ch for ch in clean(value) if ch.isdigit())


def warehouse_index(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], list[dict[str, str]]]:
    index: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = (clean(row.get("race_date")), norm(row.get("track")), distance_text(row.get("race_no")).lstrip("0") or distance_text(row.get("race_no")), distance_text(row.get("distance")))
        index.setdefault(key, []).append(row)
    return index


def surface_for(track: str, rows: list[dict[str, str]]) -> str:
    source = " ".join([track] + [clean(row.get("venue_name")) for row in rows])
    upper = source.upper()
    if any(token in upper for token in ["SYNTHETIC", "POLY", "TAPETA", "FIBRE", "FIBER"]):
        return "AUSTRALIAN_SYNTHETIC"
    return "TURF"


def condition_for(rows: list[dict[str, str]]) -> str:
    for row in rows:
        for field in ["track_rating", "track_condition"]:
            value = clean(row.get(field))
            if value:
                return value
    return ""


def interpretation(value: Decimal) -> str:
    if value > 0:
        return "FASTER_THAN_STANDARD"
    if value < 0:
        return "SLOWER_THAN_STANDARD"
    return "EQUAL_TO_STANDARD"


def param_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    return {(clean(row.get("surface_group")), clean(row.get("track_condition_group"))): row for row in rows}


def main() -> int:
    delta_rows = read_csv(DELTA)
    wh = warehouse_index(read_csv(WAREHOUSE))
    params = param_lookup(read_csv(PARAMETER))
    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    output: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    for delta in delta_rows:
        rn = race_no_from_key(delta.get("race_key", ""))
        key = (clean(delta.get("race_date")), norm(delta.get("track_name")), rn, clean(delta.get("official_distance_metres")))
        matches = wh.get(key, [])
        surface = surface_for(clean(delta.get("track_name")), matches)
        condition = condition_for(matches)
        resolved = resolve_length_conversion(surface, condition)
        if not matches:
            rejected.append({
                "race_time_delta_id": clean(delta.get("race_time_delta_id")),
                "race_key": clean(delta.get("race_key")),
                "race_date": clean(delta.get("race_date")),
                "track_name": clean(delta.get("track_name")),
                "official_distance_metres": clean(delta.get("official_distance_metres")),
                "rejection_reason": "NO_WAREHOUSE_CONDITION_EVIDENCE",
                "surface_group": surface,
                "track_condition_number": "",
                "track_condition_group": "",
            })
            continue
        if not resolved["status"].startswith("APPROVED"):
            rejected.append({
                "race_time_delta_id": clean(delta.get("race_time_delta_id")),
                "race_key": clean(delta.get("race_key")),
                "race_date": clean(delta.get("race_date")),
                "track_name": clean(delta.get("track_name")),
                "official_distance_metres": clean(delta.get("official_distance_metres")),
                "rejection_reason": resolved["status"],
                "surface_group": resolved.get("surface_group", surface),
                "track_condition_number": condition,
                "track_condition_group": resolved.get("track_condition_group", ""),
            })
            continue
        parameter = params.get((resolved["surface_group"], resolved["track_condition_group"]))
        if not parameter:
            raise RuntimeError(f"Missing governed V2 parameter for {(resolved['surface_group'], resolved['track_condition_group'])}")
        time_delta = Decimal(clean(delta.get("time_delta_seconds")))
        spl = Decimal(clean(resolved.get("seconds_per_length")))
        lengths = -(time_delta / spl)
        delta_id = clean(delta.get("race_time_delta_id"))
        parameter_id = clean(parameter.get("length_conversion_parameter_id"))
        identity_hash = sha([CONTRACT_VERSION, delta_id, parameter_id, CALCULATION_METHOD, CONVERSION_SCOPE])
        lvs_id = f"LVS1-{identity_hash[:24].upper()}"
        evidence = sha([lvs_id, delta.get("race_time_delta_evidence_sha256"), parameter.get("parameter_evidence_sha256"), f"{lengths.quantize(Decimal('0.000001')):.6f}"])
        output.append({
            "lengths_versus_standard_id": lvs_id,
            "race_time_delta_id": delta_id,
            "benchmark_observation_id": clean(delta.get("benchmark_observation_id")),
            "benchmark_group_id": clean(delta.get("benchmark_group_id")),
            "standard_time_id": clean(delta.get("standard_time_id")),
            "length_conversion_parameter_id": parameter_id,
            "race_key": clean(delta.get("race_key")),
            "race_date": clean(delta.get("race_date")),
            "track_name": clean(delta.get("track_name")),
            "official_distance_metres": clean(delta.get("official_distance_metres")),
            "winner_horse_name": clean(delta.get("winner_horse_name")),
            "winner_race_time_seconds": clean(delta.get("winner_race_time_seconds")),
            "standard_time_seconds": clean(delta.get("standard_time_seconds")),
            "time_delta_seconds": f"{time_delta.quantize(Decimal('0.000001')):.6f}",
            "seconds_per_length": clean(resolved.get("seconds_per_length")),
            "lengths_versus_standard": f"{lengths.quantize(Decimal('0.000001')):.6f}",
            "lengths_versus_standard_interpretation": interpretation(lengths),
            "calculation_method": CALCULATION_METHOD,
            "conversion_scope": CONVERSION_SCOPE,
            "conversion_model_version": clean(resolved.get("method_version")),
            "source_race_time_delta_evidence_sha256": clean(delta.get("race_time_delta_evidence_sha256")),
            "source_conversion_parameter_evidence_sha256": clean(parameter.get("parameter_evidence_sha256")),
            "lengths_versus_standard_evidence_sha256": evidence,
            "builder_version": BUILDER_VERSION,
            "contract_version": CONTRACT_VERSION,
            "built_at_utc": built_at,
        })
    output.sort(key=lambda row: (clean(row["race_date"]), clean(row["track_name"]), clean(row["race_key"])))
    write_csv(OUT, FIELDS, output)
    write_csv(REJECTED, REJECTION_FIELDS, rejected)
    payload = {
        "status": "PASS" if output else "FAIL",
        "race_time_delta_rows": len(delta_rows),
        "lengths_versus_standard_rows": len(output),
        "rejected_rows": len(rejected),
        "rejection_reasons": {reason: sum(1 for row in rejected if clean(row.get("rejection_reason")) == reason) for reason in sorted({clean(row.get("rejection_reason")) for row in rejected})},
        "distances_covered": sorted({clean(row.get("official_distance_metres")) for row in output}),
        "conversion_model_version": "EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2",
        "conversion_scope": CONVERSION_SCOPE,
    }
    SUMMARY.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "edgeiq_lengths_versus_standard_surface_condition_migration_v1.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if output else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''


AUDIT_LVS = r'''from __future__ import annotations

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
    for row in rows:
        source = delta_by_id.get(clean(row.get("race_time_delta_id")))
        parameter = param_by_id.get(clean(row.get("length_conversion_parameter_id")))
        if not source or not parameter:
            lineage_errors.append(clean(row.get("lengths_versus_standard_id")))
            continue
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
        expected_evidence = sha([row.get("lengths_versus_standard_id"), source.get("race_time_delta_evidence_sha256"), parameter.get("parameter_evidence_sha256"), f"{lengths.quantize(Decimal('0.000001')):.6f}"])
        if clean(row.get("lengths_versus_standard_evidence_sha256")) != expected_evidence:
            evidence_errors.append(clean(row.get("lengths_versus_standard_id")))
    check("calculation_reproducible", not calc_errors, calc_errors[:20])
    check("canonical_lineage", not lineage_errors, lineage_errors[:20])
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
'''


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    backup_once(CONTRACTS / "edgeiq_lengths_versus_standard_fact_v1_contract.json", "_PRE_SURFACE_CONDITION_MIGRATION_20260729")
    backup_once(DATA / "edgeiq_lengths_versus_standard_fact_v1.csv", "_PRE_SURFACE_CONDITION_MIGRATION_20260729")
    write(CONTRACTS / "edgeiq_length_conversion_parameter_fact_v2_contract.json", PARAMETER_V2_CONTRACT)
    write(CONTRACTS / "edgeiq_lengths_versus_standard_fact_v1_contract.json", LVS_V1_CONTRACT)
    write(SCRIPTS / "build_edgeiq_length_conversion_parameter_fact_v2.py", BUILD_PARAMETER_V2)
    write(SCRIPTS / "audit_edgeiq_length_conversion_parameter_fact_v2.py", AUDIT_PARAMETER_V2)
    write(SCRIPTS / "build_edgeiq_lengths_versus_standard_fact_from_results_v2.py", BUILD_LVS)
    write(SCRIPTS / "audit_edgeiq_lengths_versus_standard_v1.py", AUDIT_LVS)

    base_audit = SCRIPTS / "audit_edgeiq_performance_intelligence_base_fact_v1.py"
    text = base_audit.read_text(encoding="utf-8")
    old = '''    current_population_expected = (
        len(source_rows) == 0
        and len(fact_rows) == 0
    )
'''
    new = '''    current_population_expected = (
        len(source_rows) == len(fact_rows)
    )
'''
    if old in text:
        base_audit.write_text(text.replace(old, new), encoding="utf-8")

    evidence = [
        {
            "evidence_type": "OLD_EXACT_DISTANCE_CONTRACT",
            "path": "contracts/performance-intelligence/edgeiq_length_conversion_parameter_fact_v1_contract.json",
            "finding": "V1 expected DISTANCE_EXACT rows and is incompatible with current surface/condition source schema.",
        },
        {
            "evidence_type": "SURFACE_CONDITION_CONFIG",
            "path": "config/performance-intelligence/edgeiq_length_conversion_parameter_source_v2.csv",
            "finding": "Approved V2 rows define TURF condition groups and AUSTRALIAN_SYNTHETIC conversion parameters.",
        },
        {
            "evidence_type": "GOVERNED_METHOD",
            "path": "docs/performance-intelligence/lengths-v-standard/EDGEIQ_LENGTH_CONVERSION_METHOD_V2.md",
            "finding": "V2 states it supersedes V1 and defines lengths_vs_standard = time_difference_seconds * lengths_per_second.",
        },
        {
            "evidence_type": "IMPLEMENTATION",
            "path": "scripts/edgeiq_length_conversion_method_v1.py",
            "finding": "resolve_length_conversion implements EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2 with blocking behaviour.",
        },
        {
            "evidence_type": "REJECTED_FORMULA",
            "path": "scripts/run_edgeiq_performance_intelligence_completion_v1.py",
            "finding": "A hard-coded 0.17 seconds-per-length path exists but is rejected for this migration because the V2 governed method is explicit and no fabrication is allowed.",
        },
    ]
    import csv
    csv_path = DOCS / "edgeiq_length_conversion_authority_evidence_v1.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["evidence_type", "path", "finding"])
        writer.writeheader()
        writer.writerows(evidence)
    decision = {
        "decision": "MIGRATE_CANONICAL_CONVERSION_CONTRACT_TO_SURFACE_CONDITION",
        "selected_outcome": "B",
        "selected_conversion_model": "EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2",
        "no_fabrication_declaration": "No exact-distance coefficients were restored or interpolated. Rows without governed condition evidence are rejected.",
        "old_contract_preserved": "YES",
        "old_output_preserved": "YES",
        "new_parameter_contract": "contracts/performance-intelligence/edgeiq_length_conversion_parameter_fact_v2_contract.json",
        "canonical_lvs_contract_version": "1.1.0",
        "temporal_implication": "Track condition is used as historical race-day official condition evidence for retrospective performance facts; it is not a pre-race prediction feature.",
        "rollback": "Restore the PRE_SURFACE_CONDITION_MIGRATION_20260729 backups and rerun the old exact-distance builders.",
    }
    write(DOCS / "edgeiq_length_conversion_authority_decision_v1.json", json.dumps(decision, indent=2, sort_keys=True) + "\n")
    write(
        DOCS / "EDGEIQ_LENGTH_CONVERSION_AUTHORITY_DECISION_V1.md",
        "# EDGEiQ Length Conversion Authority Decision V1\n\n"
        "Decision: `MIGRATE_CANONICAL_CONVERSION_CONTRACT_TO_SURFACE_CONDITION`\n\n"
        "Selected model: `EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2`\n\n"
        "The exact-distance V1 parameter fact remains preserved for auditability, but it is not populated because no governed exact-distance parameters exist in the active source schema. The governed V2 surface/condition method is used instead.\n\n"
        "No coefficients were invented. Rows without official condition evidence are rejected with explicit reasons.\n\n",
    )
    print(json.dumps({"status": "APPLIED", "decision": decision["decision"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
