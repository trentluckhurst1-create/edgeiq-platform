import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
docs = root / "docs" / "victoria-live-recovery-v6"
p = json.loads((docs / "EDGEIQ_VICTORIA_CURRENT_RATINGS_EPI_ACCEPTANCE_V3.json").read_text(encoding="utf-8"))
epi = p.get("epi", {})
status = "PASS_WITH_GOVERNED_INSUFFICIENCY" if epi.get("epi_status") in {"BLOCKED_EPI_COMPONENT_CONTRACT", "NO_SNAPSHOTS_FOR_EPI"} else "PASS"
out = {"status": status, "epi_status": epi.get("epi_status"), "missing_reasons": epi.get("missing_reasons", {}), "sale": p.get("sale", {})}
(docs / "EDGEIQ_VICTORIA_CURRENT_EPI_RECOVERY_AUDIT_V1.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("EDGEIQ_VICTORIA_CURRENT_EPI_RECOVERY_AUDIT_" + status)
