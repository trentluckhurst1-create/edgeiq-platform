from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOC = ROOT / "docs" / "engineering" / "EDGEIQ_BETA_READINESS_REPORT_20260715.md"
REPORT = DATA / "edgeiq_beta_readiness_report_v2_audit.json"
OUT_TXT = DATA / "edgeiq_beta_readiness_report_v2_audit.txt"


def main() -> None:
    failures: list[str] = []
    if not REPORT.exists():
        failures.append("MISSING_REPORT_JSON")
        payload = {}
    else:
        payload = json.loads(REPORT.read_text(encoding="utf-8"))
    if not DOC.exists():
        failures.append("MISSING_REPORT_DOC")
    if payload.get("overall_status") not in {"READY", "PARTIAL / STABILISED", "BLOCKED"}:
        failures.append("INVALID_OVERALL_STATUS")
    if not payload.get("fields"):
        failures.append("NO_FIELD_ROWS")
    if any(field.get("covered_rows", 0) and not field.get("source_builder") for field in payload.get("fields", [])):
        failures.append("COVERED_FIELD_WITHOUT_SOURCE")
    marker = "EDGEIQ_BETA_READINESS_REPORT_V2_AUDIT_PASS" if not failures else "EDGEIQ_BETA_READINESS_REPORT_V2_AUDIT_FAIL"
    payload["audit_marker"] = marker
    payload["audit_failures"] = failures
    REPORT.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    OUT_TXT.write_text(
        "\n".join(
            [
                marker,
                f"overall_status={payload.get('overall_status', '')}",
                f"fields={len(payload.get('fields', []))}",
                f"failures={','.join(failures) if failures else 'none'}",
            ]
        ),
        encoding="utf-8",
    )
    print(marker)
    if failures:
        raise SystemExit("; ".join(failures))


if __name__ == "__main__":
    main()
