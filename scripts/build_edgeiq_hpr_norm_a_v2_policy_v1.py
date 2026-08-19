from apply_edgeiq_historical_normalisation_authority_v1 import policy_doc, DOCS, aw_json, aw_text, POLICY
import json

p = policy_doc()
aw_json(DOCS / "EDGEIQ_HPR_NORM_A_V2_POLICY.json", p)
aw_text(DOCS / "EDGEIQ_HPR_NORM_A_V2_POLICY.md", "# EDGEIQ HPR-NORM-A-v2 Policy\n\n" + json.dumps(p, indent=2, sort_keys=True) + "\n")
print("EDGEIQ_HPR_NORM_A_V2_POLICY_BUILT")
print("policy_id=" + POLICY)
