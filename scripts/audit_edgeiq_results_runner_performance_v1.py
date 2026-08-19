from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingResultsWorkspace.tsx"
OUT_JSON = DATA / "edgeiq_results_runner_performance_v1_audit.json"
OUT_TXT = DATA / "edgeiq_results_runner_performance_v1_audit.txt"


def main() -> None:
    source = WORKSPACE.read_text(encoding="utf-8", errors="replace") if WORKSPACE.exists() else ""
    lower = source.lower()
    checks = {
        "component_exists": WORKSPACE.exists(),
        "individual_view_present": "function IndividualRaceResult" in source,
        "runner_performance_present": "Runner Performance" in source and "Benchmark sectionals" in source,
        "identity_columns_present": all(text in source for text in ["No</th>", "Horse</th>", "Jockey</th>", "Bar</th>", "Wt</th>", "SP</th>", "Finish</th>", "Margin</th>"]),
        "epi_eri_present": "EPI</th>" in source and "ERI</th>" in source,
        "finishing_order_present": "Finishing Order" in source and "SP (TAB)</th>" in source,
        "stewards_pending_copy": "Stewards comments will display only when the official report is published." in source,
        "prohibited_result_widgets_absent": "race replay" not in lower
        and "epi versus sp" not in lower
        and "epi vs sp" not in lower
        and "race tempo visual" not in lower,
    }
    status = (
        "EDGEIQ_RESULTS_RUNNER_PERFORMANCE_V1_AUDIT_PASS"
        if all(checks.values())
        else "EDGEIQ_RESULTS_RUNNER_PERFORMANCE_V1_AUDIT_FAIL"
    )
    payload = {"status": status, "checks": checks}
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_TXT.write_text("\n".join([status, "", *[f"{key}: {value}" for key, value in checks.items()]]) + "\n", encoding="utf-8")
    print(status)
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
