from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT_DIR = ROOT / "docs" / "performance-intelligence" / "results-recovery-v40"
WAREHOUSE = DATA / "edgeiq_racingcom_results_warehouse_v2.csv"
BACKUP_DIR = DATA / "backups" / "results-warehouse-v40"
QUARANTINE = OUT_DIR / "edgeiq_invalid_r8_identity_quarantine_v41.csv"
AUDIT = OUT_DIR / "edgeiq_invalid_r8_identity_quarantine_v41_audit.json"
PAGES = OUT_DIR / "edgeiq_target_r8_rendered_pages_v40.json"

TARGETS = {
    ("2026-08-01", "BET365 HAMILTON", "8"),
    ("2026-08-09", "CASTERTON", "8"),
}


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    tmp.replace(path)


def key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (clean(row.get("meeting_date")), clean(row.get("track")).upper(), clean(row.get("race_no")))


def main() -> None:
    if not PAGES.exists():
        raise FileNotFoundError(f"Run repair_edgeiq_target_r8_results_v40.py first to capture page evidence: {PAGES}")

    page_evidence = json.loads(PAGES.read_text(encoding="utf-8"))
    mismatches = [
        item
        for item in page_evidence
        if (clean(item.get("meeting_date")), clean(item.get("track")).upper(), clean(item.get("race_no"))) in TARGETS
        and clean(item.get("status")) == "GRAPHQL_RACE_IDENTITY_MISMATCH"
    ]

    if len(mismatches) != 2:
        raise RuntimeError(f"Expected two target R8 identity mismatches before quarantine, got {len(mismatches)}")

    fields, rows = read_csv(WAREHOUSE)
    quarantine_fields = fields + ["quarantine_reason", "quarantined_at"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    built_at = datetime.now(timezone.utc).isoformat()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / f"edgeiq_racingcom_results_warehouse_v2.pre_v41_quarantine_{stamp}.csv"
    shutil.copy2(WAREHOUSE, backup)

    retained = []
    quarantined = []
    for row in rows:
        if key(row) in TARGETS:
            q = dict(row)
            q["quarantine_reason"] = "REQUESTED_R8_RETURNED_GRAPHQL_RACE_1_DO_NOT_RELABEL"
            q["quarantined_at"] = built_at
            quarantined.append(q)
        else:
            retained.append(row)

    if len(quarantined) != 19:
        raise RuntimeError(f"Expected to quarantine 19 invalid R8 rows, got {len(quarantined)}")

    write_csv(QUARANTINE, quarantined, quarantine_fields)
    tmp = WAREHOUSE.with_suffix(WAREHOUSE.suffix + ".v41.tmp")
    write_csv(tmp, retained, fields)
    tmp.replace(WAREHOUSE)

    audit = {
        "status": "PASS",
        "backup": str(backup),
        "warehouse": str(WAREHOUSE),
        "quarantine": str(QUARANTINE),
        "rows_before": len(rows),
        "rows_quarantined": len(quarantined),
        "rows_after": len(retained),
        "page_identity_mismatches": mismatches,
        "built_at": built_at,
    }
    AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    print("EDGEIQ_INVALID_R8_IDENTITY_QUARANTINE_V41=PASS")
    print(f"BACKUP={backup}")
    print(f"QUARANTINED_ROWS={len(quarantined)}")
    print(f"WAREHOUSE_ROWS_AFTER={len(retained)}")


if __name__ == "__main__":
    main()
