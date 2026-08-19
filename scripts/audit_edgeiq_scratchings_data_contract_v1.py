from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "scratchingsFeed.ts"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_scratchings_data_contract_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_scratchings_data_contract_v1_audit.txt"

text = SERVICE.read_text(encoding="utf-8", errors="replace") if SERVICE.exists() else ""

required_exports = [
    "MeetingScratchingsViewModel",
    "ScratchingsRaceGroupViewModel",
    "ScratchingRecordViewModel",
    "ScratchingEventViewModel",
    "ScratchingsDataStatusViewModel",
    "buildMeetingScratchingsViewModel",
    "calculateEffectiveBarriers",
]

required_record_fields = [
    "eventKey",
    "meetingKey",
    "raceKey",
    "raceNumber",
    "runnerKey",
    "runnerNumber",
    "silk",
    "horse",
    "trainer",
    "jockey",
    "scratchedAt",
    "reason",
    "source",
    "status",
    "originalBarrier",
    "effectiveBarrierBefore",
    "effectiveBarrierAfter",
    "fieldSizeBefore",
    "fieldSizeAfter",
    "emergencyPromotion",
    "downstream",
]

required_statuses = [
    "SCRATCHED",
    "LATE_SCRATCHING",
    "EMERGENCY_PROMOTED",
    "EMERGENCY_NOT_REQUIRED",
    "WITHDRAWN",
    "UNAVAILABLE",
]

checks = {
    "service_exists": SERVICE.exists(),
    "required_exports_present": all(item in text for item in required_exports),
    "required_record_fields_present": all(re.search(rf"\b{field}\b", text) for field in required_record_fields),
    "required_statuses_present": all(status in text for status in required_statuses),
    "summary_contract_present": all(
        item in text
        for item in [
            "totalScratchings",
            "racesAffected",
            "newSinceCount",
            "materiallyChangedFields",
            "emergenciesPromoted",
            "officialUpdatedAt",
        ]
    ),
    "source_status_contract_present": all(
        item in text for item in ["sourceUpdatedAt", "builderVersion", "coverageStatus", "sourceUnavailable"]
    ),
    "no_warehouse_fetch_in_service": "fetch(" not in text and "edgeiq_results_master" not in text,
}

payload = {
    "status": "EDGEIQ_SCRATCHINGS_DATA_CONTRACT_V1_AUDIT_PASS"
    if all(checks.values())
    else "EDGEIQ_SCRATCHINGS_DATA_CONTRACT_V1_AUDIT_FAIL",
    "checks": checks,
    "required_exports": required_exports,
    "required_record_fields": required_record_fields,
    "required_statuses": required_statuses,
}

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join([payload["status"], "", *[f"{key}: {value}" for key, value in checks.items()]]),
    encoding="utf-8",
)
print(payload["status"])
