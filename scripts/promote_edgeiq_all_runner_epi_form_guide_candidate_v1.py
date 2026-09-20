from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work" / "all-runner-epi-product-bridge-v1"
TARGET = ROOT / "public" / "data" / "edgeiq_form_guide_enriched_v2.json"
CANDIDATE = WORK / "edgeiq_form_guide_enriched_v2.ALL_RUNNER_EPI_BRIDGE_CANDIDATE.json"
VALIDATION = WORK / "edgeiq_all_runner_epi_product_bridge_v1_validation.json"
SUMMARY = WORK / "edgeiq_all_runner_epi_product_bridge_v1_summary.json"
BACKUP_DIR = WORK / "production-backups"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def count_slots(payload: dict) -> int:
    return sum(
        len(runner.get("fullForm", []) or [])
        for race in payload.get("races", []) or []
        for runner in race.get("runners", []) or []
    )


def main() -> None:
    missing = [str(p.relative_to(ROOT)) for p in (TARGET, CANDIDATE, VALIDATION, SUMMARY) if not p.exists()]
    if missing:
        raise SystemExit("FAIL_CLOSED_MISSING_INPUTS=" + json.dumps(missing))

    validation = load_json(VALIDATION)
    summary = load_json(SUMMARY)
    required = {
        "validation_pass": validation.get("status") == "PASS",
        "summary_pass": summary.get("status") == "PASS",
        "slot_count": summary.get("final_classification_sum") == 2044,
        "populated_plus_blank": validation.get("populated_plus_governed_blank_equals_2044") is True,
        "certified_epi_unchanged": validation.get("certified_epi_unchanged") is True,
        "warehouse_unchanged": validation.get("warehouse_unchanged") is True,
        "hpr_unchanged": validation.get("hpr_unchanged") is True,
        "zero_conflicting_epi_promoted": validation.get("zero_conflicting_epi_promoted") is True,
        "zero_ambiguous_identity_matches_promoted": validation.get("zero_ambiguous_identity_matches_promoted") is True,
        "traceability": validation.get("every_populated_traces_to_certified_canonical_performance_id") is True,
    }
    failed = [key for key, ok in required.items() if not ok]
    if failed:
        raise SystemExit("FAIL_CLOSED_PROMOTION_PRECHECKS=" + json.dumps(failed))

    candidate_payload = load_json(CANDIDATE)
    target_payload = load_json(TARGET)
    if count_slots(candidate_payload) != 2044 or count_slots(target_payload) != 2044:
        raise SystemExit("FAIL_CLOSED_SLOT_COUNT_MISMATCH")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = BACKUP_DIR / f"edgeiq_form_guide_enriched_v2.backup_before_all_runner_epi_bridge.{stamp}.json"
    shutil.copy2(TARGET, backup)
    shutil.copy2(CANDIDATE, TARGET)

    promoted_payload = load_json(TARGET)
    if count_slots(promoted_payload) != 2044:
        shutil.copy2(backup, TARGET)
        raise SystemExit("FAIL_CLOSED_PROMOTED_SLOT_COUNT_ROLLBACK_COMPLETE")

    print(
        json.dumps(
            {
                "status": "PROMOTED",
                "target": str(TARGET.relative_to(ROOT)),
                "backup": str(backup.relative_to(ROOT)),
                "candidate": str(CANDIDATE.relative_to(ROOT)),
                "slots": count_slots(promoted_payload),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
