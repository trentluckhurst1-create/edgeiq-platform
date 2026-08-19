from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
APPLY = DATA / "edgeiq_current_analytical_matching_repair_v1_apply.json"
OUT_TXT = DATA / "edgeiq_current_analytical_matching_repair_v1_audit.txt"
OUT_JSON = DATA / "edgeiq_current_analytical_matching_repair_v1_audit.json"
MARKER = "EDGEIQ_CURRENT_ANALYTICAL_MATCHING_REPAIR_V1_AUDIT_PASS"

REQUIRED_FIELDS = ["EPI", "Suitability", "Form Momentum", "EDGEiQ Price", "Early Speed", "Late Speed"]


def main() -> None:
    failures: list[str] = []
    apply = json.loads(APPLY.read_text(encoding="utf-8")) if APPLY.exists() else {}
    fields = apply.get("fields", {}) if isinstance(apply, dict) else {}
    for field in REQUIRED_FIELDS:
        if field not in fields:
            failures.append(f"Missing field audit: {field}")
            continue
        item = fields[field]
        if item.get("covered_after", 0) < item.get("covered_before", 0):
            failures.append(f"Coverage decreased for {field}")
        if item.get("changed"):
            failures.append(f"Apply unexpectedly modified coverage for {field}; this run should not fabricate values")

    status = "PASS" if not failures else "FAIL"
    payload = {
        "marker": MARKER if status == "PASS" else "EDGEIQ_CURRENT_ANALYTICAL_MATCHING_REPAIR_V1_AUDIT_FAIL",
        "status": status,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "fields": fields,
        "failures": failures,
    }
    lines = [payload["marker"], f"status={status}", "before_after_counts:"]
    for field in REQUIRED_FIELDS:
        item = fields.get(field, {})
        lines.append(
            f"- {field}: before={item.get('covered_before', 0)}/{item.get('catalog_runners', 0)} after={item.get('covered_after', 0)}/{item.get('catalog_runners', 0)} remaining={item.get('remaining_missing', 0)} reason={item.get('remaining_reason', '')}"
        )
    if failures:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in failures)
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("\n".join(lines))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
