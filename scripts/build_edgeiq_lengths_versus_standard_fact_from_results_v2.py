from __future__ import annotations

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


def integer_text(value: object) -> str:
    raw = clean(value)
    if not raw:
        return ""
    try:
        return str(int(float(raw)))
    except ValueError:
        digits = "".join(ch for ch in raw if ch.isdigit())
        return str(int(digits)) if digits else ""


def warehouse_index(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], list[dict[str, str]]]:
    index: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = (clean(row.get("race_date")), norm(row.get("track")), integer_text(row.get("race_no")), distance_text(row.get("distance")))
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
