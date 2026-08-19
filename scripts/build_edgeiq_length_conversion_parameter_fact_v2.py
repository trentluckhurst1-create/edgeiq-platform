from __future__ import annotations

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
