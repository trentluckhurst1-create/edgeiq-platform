from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CONFIG_DIR = ROOT / "config" / "performance-intelligence"
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating" / "method-governance"

BASE_FACT = DATA / "edgeiq_performance_intelligence_base_fact_v1.csv"
RATING_BASE = DATA / "edgeiq_performance_rating_base_fact_v1.csv"
CANDIDATE = CONFIG_DIR / "edgeiq_horse_performance_identity_map_v1_CANDIDATE.csv"
PROMOTED = CONFIG_DIR / "edgeiq_horse_performance_identity_map_v1.csv"
AUDIT_CSV = DOC_DIR / "edgeiq_horse_performance_identity_map_v1_audit.csv"
SOURCE_CSV = DOC_DIR / "edgeiq_horse_performance_identity_map_v1_source_evidence.csv"
REPORT_MD = DOC_DIR / "EDGEIQ_HORSE_PERFORMANCE_IDENTITY_MAP_RECOVERY_V1.md"

RAW_ROOTS = [
    ROOT / "outputs" / "performance-intelligence" / "racingcom-ingestion-v2" / "raw" / "graphql-acquisition",
    ROOT / "outputs" / "performance-intelligence" / "racingcom-source-discovery" / "raw" / "network-capture",
    ROOT / "outputs" / "performance-intelligence" / "racingcom-v2" / "raw",
]

IDENTITY_FIELDS = [
    "source_horse_name",
    "canonical_horse_id",
    "canonical_horse_name",
    "identity_status",
    "evidence_reference",
    "evidence_sha256",
]


def text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def sha256_payload(parts: list[Any]) -> str:
    return hashlib.sha256("\x1f".join(text(p) for p in parts).encode("utf-8")).hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: text(row.get(field, "")) for field in fields})


def target_runner_ids() -> dict[str, dict[str, str]]:
    targets: dict[str, dict[str, str]] = {}
    for source in [RATING_BASE, BASE_FACT]:
        for row in read_rows(source):
            raw = text(row.get("source_horse_name") or row.get("winner_horse_name"))
            if not raw:
                continue
            if not raw.isdigit():
                continue
            targets.setdefault(raw, {
                "source_runner_id": raw,
                "source_file": source.as_posix(),
                "race_key": text(row.get("race_key")),
                "race_date": text(row.get("race_date")),
                "track_name": text(row.get("track_name")),
            })
    return targets


def extract_horse_code_from_url(url: str) -> str:
    match = re.search(r"-(\d+)(?:$|[/?#])", text(url))
    return match.group(1) if match else ""


def candidate_from_dict(node: dict[str, Any], source_path: Path, target_ids: set[str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    runner_id = text(node.get("id") or node.get("Id") or node.get("ID") or node.get("runner_id") or node.get("raceEntryId"))
    if runner_id not in target_ids:
        return out

    horse_id = ""
    horse_name = ""
    source_kind = ""

    horse = node.get("horse") or node.get("Horse")
    if isinstance(horse, dict):
        horse_id = text(horse.get("id") or horse.get("Id") or horse.get("horseId") or horse.get("HorseId"))
        horse_name = text(horse.get("name") or horse.get("Name") or horse.get("fullName") or horse.get("FullName"))
        source_kind = "FORM_RACE_ENTRY_HORSE_OBJECT"

    if not horse_name:
        horse_name = text(node.get("FullName") or node.get("fullName") or node.get("horseName") or node.get("HorseName") or node.get("name") or node.get("Name"))
        if horse_name:
            source_kind = source_kind or "SECTIONALTIMES_HORSE_FULLNAME"

    if not horse_id:
        horse_id = text(node.get("horseId") or node.get("HorseId") or node.get("horse_id"))
    if not horse_id:
        horse_id = extract_horse_code_from_url(text(node.get("HorseUrl") or node.get("horseUrl") or node.get("url") or node.get("Url")))

    if horse_name:
        canonical_id = f"RCOM_HORSE_{horse_id}" if horse_id else f"RCOM_RACE_ENTRY_{runner_id}"
        evidence_reference = f"{source_path.as_posix()}#runner_id={runner_id}"
        evidence_sha = sha256_payload([runner_id, canonical_id, horse_name, evidence_reference, source_kind])
        out.append({
            "source_runner_id": runner_id,
            "source_horse_name": runner_id,
            "canonical_horse_id": canonical_id,
            "canonical_horse_name": horse_name,
            "horse_code": horse_id,
            "identity_status": "APPROVED",
            "evidence_reference": evidence_reference,
            "evidence_sha256": evidence_sha,
            "source_kind": source_kind or "AUTHORITATIVE_RACINGCOM_PAYLOAD",
            "source_payload_file": source_path.as_posix(),
        })
    return out


def walk_json(node: Any, source_path: Path, target_ids: set[str], out: list[dict[str, str]]) -> None:
    if isinstance(node, dict):
        out.extend(candidate_from_dict(node, source_path, target_ids))
        for value in node.values():
            walk_json(value, source_path, target_ids, out)
    elif isinstance(node, list):
        for item in node:
            walk_json(item, source_path, target_ids, out)


def parse_payload(path: Path) -> Any | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = raw.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Some captured .txt files contain raw JSON embedded after headers; keep this strict for JSON files.
        return None


def collect_evidence(targets: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    target_ids = set(targets)
    rows: list[dict[str, str]] = []
    paths: list[Path] = []
    for root in RAW_ROOTS:
        if root.exists():
            paths.extend(root.rglob("*.json"))
    for path in sorted(set(paths)):
        payload = parse_payload(path)
        if payload is None:
            continue
        walk_json(payload, path, target_ids, rows)
    return rows


def main() -> None:
    targets = target_runner_ids()
    evidence = collect_evidence(targets)

    by_runner: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in evidence:
        by_runner[row["source_runner_id"]].append(row)

    chosen: list[dict[str, str]] = []
    audit_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []

    for runner_id in sorted(targets):
        candidates = by_runner.get(runner_id, [])
        unique_ids: dict[str, list[dict[str, str]]] = defaultdict(list)
        for cand in candidates:
            unique_ids[cand["canonical_horse_id"]].append(cand)
            source_rows.append(cand)
        if len(unique_ids) == 1:
            same_id_candidates = next(iter(unique_ids.values()))
            selected = sorted(
                same_id_candidates,
                key=lambda cand: (
                    0 if cand.get("source_kind") == "FORM_RACE_ENTRY_HORSE_OBJECT" else 1,
                    len(cand.get("canonical_horse_name", "")),
                    cand.get("source_payload_file", ""),
                ),
            )[0]
            chosen.append({field: selected[field] for field in IDENTITY_FIELDS})
            status = "IDENTITY_READY"
            distinct_names = sorted({cand["canonical_horse_name"] for cand in same_id_candidates})
            if len(distinct_names) > 1:
                reason = "single_authoritative_horse_id_with_name_variant_preferred_form_race_entry"
            else:
                reason = "single_authoritative_runner_id_mapping"
        elif len(unique_ids) == 0:
            status = "IDENTITY_MISSING"
            reason = "no_authoritative_payload_for_runner_id"
        else:
            status = "IDENTITY_CONFLICTED"
            reason = "runner_id_maps_to_multiple_horse_ids"
        audit_rows.append({
            "source_runner_id": runner_id,
            "race_key": targets[runner_id].get("race_key", ""),
            "candidate_count": len(candidates),
            "unique_identity_count": len(unique_ids),
            "status": status,
            "reason": reason,
            "selected_canonical_horse_id": chosen[-1]["canonical_horse_id"] if status == "IDENTITY_READY" else "",
            "selected_canonical_horse_name": chosen[-1]["canonical_horse_name"] if status == "IDENTITY_READY" else "",
        })

    source_fields = [
        "source_runner_id", "source_horse_name", "canonical_horse_id", "canonical_horse_name",
        "horse_code", "identity_status", "evidence_reference", "evidence_sha256",
        "source_kind", "source_payload_file",
    ]
    write_csv(SOURCE_CSV, source_rows, source_fields)
    write_csv(AUDIT_CSV, audit_rows, [
        "source_runner_id", "race_key", "candidate_count", "unique_identity_count", "status", "reason",
        "selected_canonical_horse_id", "selected_canonical_horse_name",
    ])
    write_csv(CANDIDATE, sorted(chosen, key=lambda r: r["source_horse_name"]), IDENTITY_FIELDS)

    ready = sum(1 for row in audit_rows if row["status"] == "IDENTITY_READY")
    missing = sum(1 for row in audit_rows if row["status"] == "IDENTITY_MISSING")
    conflicted = sum(1 for row in audit_rows if row["status"] == "IDENTITY_CONFLICTED")
    candidate_has_duplicate_source = len({r["source_horse_name"] for r in chosen}) != len(chosen)
    target_count = len(targets)
    promoted = False
    if target_count and ready == target_count and missing == 0 and conflicted == 0 and not candidate_has_duplicate_source:
        PROMOTED.parent.mkdir(parents=True, exist_ok=True)
        PROMOTED.write_text(CANDIDATE.read_text(encoding="utf-8"), encoding="utf-8")
        status = "IDENTITY_MAP_READY"
        promoted = True
    elif ready > 0 and conflicted == 0:
        status = "IDENTITY_MAP_PARTIAL"
    elif conflicted > 0:
        status = "IDENTITY_MAP_CONFLICTED"
    else:
        status = "IDENTITY_MAP_BLOCKED_BY_MISSING_SOURCE_CODE"

    report = f"""# EDGEiQ Horse Performance Identity Map Recovery V1

Status: {status}

## Scope

This recovery uses only exact Racing.com race-entry identifiers already present in the governed historical performance base. No fuzzy horse-name matching, threshold reduction, fabricated horse IDs, rating changes, V6.1 changes, V7.2G2 changes, pricing changes, or UI changes were made.

## Results

- Target source identifiers: {target_count}
- Identity-ready identifiers: {ready}
- Missing identifiers: {missing}
- Conflicted identifiers: {conflicted}
- Candidate rows: {len(chosen)}
- Candidate duplicate source IDs: {'YES' if candidate_has_duplicate_source else 'NO'}
- Governed config promoted: {'YES' if promoted else 'NO'}

## Method

The active performance base currently stores Racing.com race-entry IDs in the field consumed by the observation builder as `source_horse_name`. The recovery therefore maps each exact source ID to canonical Racing.com horse identity from authoritative raw GraphQL payload evidence.

The generated config follows the active consumer schema exactly:

`source_horse_name, canonical_horse_id, canonical_horse_name, identity_status, evidence_reference, evidence_sha256`

## Governance Note

This recovers the identity governance source only. It does not recover the missing normalisation or aggregation methodology parameters, so downstream horse performance ratings remain blocked until those methodological sources receive owner-approved provenance.
"""
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(report, encoding="utf-8")

    print(f"status={status}")
    print(f"target_source_identifiers={target_count}")
    print(f"identity_ready={ready}")
    print(f"identity_missing={missing}")
    print(f"identity_conflicted={conflicted}")
    print(f"candidate_rows={len(chosen)}")
    print(f"governed_config_promoted={'YES' if promoted else 'NO'}")


if __name__ == "__main__":
    main()
