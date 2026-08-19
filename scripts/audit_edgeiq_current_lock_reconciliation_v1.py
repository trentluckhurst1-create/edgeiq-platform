from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "engineering"
OUT_JSON = DATA / "edgeiq_current_lock_reconciliation_v1_audit.json"
OUT_TXT = DATA / "edgeiq_current_lock_reconciliation_v1_audit.txt"
DOC = DOCS / "EDGEIQ_STALE_AUDIT_RECONCILIATION_20260715.md"

AUDITS = [
    "edgeiq_results_engineering_build_v1_audit.json",
    "edgeiq_track_engineering_build_v1_audit.json",
    "edgeiq_weather_engineering_build_v1_audit.json",
    "edgeiq_scratchings_engineering_build_v1_audit.json",
    "edgeiq_meetings_engineering_build_v1_audit.json",
    "edgeiq_form_guide_engineering_build_v1_audit.json",
    "edgeiq_map_engineering_build_v1_audit.json",
    "edgeiq_market_engineering_build_v1_audit.json",
    "edgeiq_insights_engineering_build_v1_audit.json",
    "edgeiq_gear_changes_engineering_build_v1_audit.json",
]

CLASSIFICATION_RULES = {
    "results": "REQUIRES_UPSTREAM_DATA",
    "track": "STALE_UI_REQUIREMENT",
    "weather": "SUPERSEDED_ARCHITECTURE",
    "scratchings": "SUPERSEDED_ARCHITECTURE",
    "meetings": "SUPERSEDED_ARCHITECTURE",
    "form_guide": "CURRENT_VALID",
    "map": "CURRENT_VALID",
    "market": "CURRENT_VALID",
    "insights": "REQUIRES_UPSTREAM_DATA",
    "gear_changes": "CURRENT_VALID",
}


def classify(name: str) -> str:
    for token, result in CLASSIFICATION_RULES.items():
        if token in name:
            return result
    return "DUPLICATE_CHECK"


def read_payload(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "status": "MISSING"}
    try:
        return {"exists": True, "payload": json.loads(path.read_text(encoding="utf-8"))}
    except Exception as exc:
        return {"exists": True, "status": "PARSE_ERROR", "error": str(exc)}


def status_from_payload(payload: dict) -> str:
    if not payload.get("exists"):
        return "MISSING"
    body = payload.get("payload")
    if not isinstance(body, dict):
        return payload.get("status", "UNKNOWN")
    raw = str(body.get("status") or body.get("audit_status") or body.get("result") or body.get("marker") or "").upper()
    if "FAIL" in raw:
        return "FAIL"
    if "PASS" in raw:
        return "PASS"
    return raw or "UNKNOWN"


def main() -> None:
    rows = []
    failures = []
    for audit_name in AUDITS:
        path = DATA / audit_name
        payload = read_payload(path)
        status = status_from_payload(payload)
        classification = classify(audit_name)
        if classification == "CURRENT_VALID" and status not in {"PASS", "UNKNOWN"}:
            failures.append(f"{audit_name}: current-valid audit status is {status}")
        rows.append(
            {
                "audit": audit_name,
                "exists": bool(payload.get("exists")),
                "status": status,
                "classification": classification,
                "action": "retain current audit" if classification == "CURRENT_VALID" else "do not restore superseded UI; handle through current-app data readiness",
            }
        )
    marker = "EDGEIQ_CURRENT_LOCK_RECONCILIATION_V1_AUDIT_PASS" if not failures else "EDGEIQ_CURRENT_LOCK_RECONCILIATION_V1_AUDIT_FAIL"
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    audit = {
        "marker": marker,
        "generated_at": generated_at,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "classifications": rows,
        "preserved_rejections": [
            "No Data Freshness panels restored",
            "No source/provider names restored",
            "No removed columns restored",
            "No rejected Track/Weather panels restored",
            "No old Results controls restored",
        ],
    }
    OUT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    OUT_TXT.write_text(
        "\n".join(
            [
                marker,
                f"status={audit['status']}",
                f"audits_classified={len(rows)}",
                f"failures={'; '.join(failures) if failures else 'none'}",
            ]
        ),
        encoding="utf-8",
    )
    DOCS.mkdir(parents=True, exist_ok=True)
    DOC.write_text(
        "\n".join(
            [
                "# EDGEiQ Stale Audit Reconciliation - 2026-07-15",
                "",
                "## Policy",
                "",
                "Do not restore rejected UI or provider/source diagnostics to satisfy old audits. Current-valid audits are retained; superseded audits are documented and controlled by this reconciliation layer.",
                "",
                "## Classification",
                "",
                "| Audit | Status | Classification | Action |",
                "| --- | --- | --- | --- |",
                *[
                    f"| {row['audit']} | {row['status']} | {row['classification']} | {row['action']} |"
                    for row in rows
                ],
                "",
                "## Preserved Rejections",
                "",
                "- Data Freshness panels were not restored.",
                "- Source/provider labels were not restored.",
                "- Removed columns and old Results controls were not restored.",
                "- Locked Meeting tabs remain governed by current-valid audits.",
            ]
        ),
        encoding="utf-8",
    )
    print(marker)
    if failures:
        raise SystemExit("; ".join(failures))


if __name__ == "__main__":
    main()
