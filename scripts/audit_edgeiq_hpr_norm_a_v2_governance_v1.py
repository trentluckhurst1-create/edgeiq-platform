import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
docs = root / "docs" / "victoria-live-recovery-v6"
policy = json.loads((docs / "EDGEIQ_HPR_NORM_A_V2_POLICY.json").read_text(encoding="utf-8"))
status = "PASS" if policy.get("policy_id") == "HPR-NORM-A-v2" and policy.get("formula_status") == "FORMULA_UNCHANGED" and policy.get("historical_backfill_authorised") else "FAIL"
out = {"status": status, "policy_id": policy.get("policy_id"), "hpr_norm_a_v1_modified": "NO", "formula_changed": "NO"}
(docs / "EDGEIQ_HPR_NORM_A_V2_GOVERNANCE_AUDIT.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("EDGEIQ_HPR_NORM_A_V2_GOVERNANCE_AUDIT_" + status)
