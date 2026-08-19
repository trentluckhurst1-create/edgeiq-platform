from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "performance-intelligence" / "edgeiq_horse_performance_identity_map_v1.csv"
BASE = ROOT / "public" / "data" / "edgeiq_performance_intelligence_base_fact_v1.csv"
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating" / "method-governance"
VALIDATION = DOC_DIR / "edgeiq_horse_performance_identity_map_v1_validation.csv"
REPORT = DOC_DIR / "edgeiq_horse_performance_identity_map_v1_validation_report.md"
FIELDS = ["source_horse_name", "canonical_horse_id", "canonical_horse_name", "identity_status", "evidence_reference", "evidence_sha256"]
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def read_rows(path: Path):
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def text(v):
    return str(v if v is not None else "").strip()


def main() -> None:
    config_fields, config_rows = read_rows(CONFIG)
    _, base_rows = read_rows(BASE)
    target_ids = sorted({text(row.get("winner_horse_name")) for row in base_rows if text(row.get("winner_horse_name")).isdigit()})
    by_source = {text(row.get("source_horse_name")): row for row in config_rows}
    statuses = []
    duplicate_count = len(config_rows) - len({text(row.get("source_horse_name")) for row in config_rows})
    schema_ok = config_fields == FIELDS
    for source_id in target_ids:
        row = by_source.get(source_id)
        if row is None:
            statuses.append({"source_horse_name": source_id, "status": "MISSING", "reason": "target_source_id_absent_from_identity_map"})
            continue
        problems = []
        if text(row.get("identity_status")) != "APPROVED":
            problems.append("identity_status_not_approved")
        if not text(row.get("canonical_horse_id")):
            problems.append("blank_canonical_horse_id")
        if not text(row.get("canonical_horse_name")):
            problems.append("blank_canonical_horse_name")
        if not text(row.get("evidence_reference")):
            problems.append("blank_evidence_reference")
        if not SHA_RE.match(text(row.get("evidence_sha256"))):
            problems.append("invalid_evidence_sha256")
        statuses.append({
            "source_horse_name": source_id,
            "canonical_horse_id": text(row.get("canonical_horse_id")),
            "canonical_horse_name": text(row.get("canonical_horse_name")),
            "status": "OK" if not problems else "INVALID",
            "reason": ";".join(problems),
        })
    if not schema_ok:
        verdict = "IDENTITY_MAP_INVALID_SCHEMA"
    elif duplicate_count:
        verdict = "IDENTITY_MAP_DUPLICATE_SOURCE_IDS"
    elif any(row["status"] != "OK" for row in statuses):
        verdict = "IDENTITY_MAP_INCOMPLETE"
    else:
        verdict = "IDENTITY_MAP_VALIDATED"
    VALIDATION.parent.mkdir(parents=True, exist_ok=True)
    fields = ["source_horse_name", "canonical_horse_id", "canonical_horse_name", "status", "reason"]
    with VALIDATION.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(statuses)
    report = f"""# EDGEiQ Horse Performance Identity Map Validation V1

Verdict: {verdict}

- Config exists: {'YES' if CONFIG.exists() else 'NO'}
- Schema OK: {'YES' if schema_ok else 'NO'}
- Target source IDs: {len(target_ids)}
- Config rows: {len(config_rows)}
- Duplicate source IDs: {duplicate_count}
- OK rows: {sum(1 for row in statuses if row['status'] == 'OK')}
- Invalid/missing rows: {sum(1 for row in statuses if row['status'] != 'OK')}

No pricing, probability, V6.1, V7.2G2, UI, or rating-method changes were made.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"verdict={verdict}")
    print(f"target_source_ids={len(target_ids)}")
    print(f"config_rows={len(config_rows)}")
    print(f"ok_rows={sum(1 for row in statuses if row['status'] == 'OK')}")


if __name__ == "__main__":
    main()
