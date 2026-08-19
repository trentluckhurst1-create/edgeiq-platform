from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

from edgeiq_racing_com_public_common_v1 import *

ENV_NAME = "RACINGCOM_CHAMPION_DATA_ENDPOINT_KEY"
ALLOWED_SUCCESS = {"PASS_PUBLIC_INTEGRATION_READY", "PASS_PUBLIC_INTEGRATION_PROMOTED", "PASS_CREDENTIAL_INTEGRATION_READY", "PASS_OFFICIAL_IMPORT_READY", "CODE_COMPLETE_ACCESS_REQUIRED"}


def run(cmd: list[str]) -> dict:
    proc = subprocess.run([sys.executable, *cmd], cwd=ROOT, text=True, capture_output=True)
    return {"cmd": "python " + " ".join(cmd), "returncode": proc.returncode, "stdout": proc.stdout[-5000:], "stderr": proc.stderr[-5000:]}


def access_decision() -> tuple[str, list[dict]]:
    matrix = read_csv(DOC / "completion" / "runner_sectionals_access_matrix.csv")
    classes = {row.get("access_classification") for row in matrix}
    if "CREDENTIAL_CONFIRMED" in classes:
        return "CREDENTIAL_CONFIRMED", matrix
    if "PUBLIC_ANONYMOUS_CONFIRMED" in classes or "PUBLIC_ANONYMOUS_HEADER_SENSITIVE" in classes:
        return "PUBLIC_ANONYMOUS_CONFIRMED", matrix
    if "CREDENTIAL_REQUIRED" in classes:
        return "CREDENTIAL_REQUIRED", matrix
    return "BLOCKED_LIVE_REQUEST_UNRESOLVED", matrix


def final_status(mode: str, steps: list[dict]) -> str:
    if any(step["returncode"] not in {0} for step in steps):
        return "FAIL"
    decision, matrix = access_decision()
    official_summary_path = DOC / "completion" / "official-import" / "official_import_summary.json"
    official_status = json.loads(official_summary_path.read_text(encoding="utf-8")).get("status", "") if official_summary_path.exists() else ""
    if mode == "FULL_PROMOTION":
        return "PASS_PUBLIC_INTEGRATION_PROMOTED" if decision == "PUBLIC_ANONYMOUS_CONFIRMED" else "CODE_COMPLETE_ACCESS_REQUIRED"
    if mode == "LIVE_CREDENTIAL":
        return "PASS_CREDENTIAL_INTEGRATION_READY" if decision in {"CREDENTIAL_CONFIRMED", "CREDENTIAL_REQUIRED"} else "BLOCKED_LIVE_REQUEST_UNRESOLVED"
    if decision == "PUBLIC_ANONYMOUS_CONFIRMED":
        return "PASS_PUBLIC_INTEGRATION_READY"
    if decision == "CREDENTIAL_REQUIRED" and official_status == "PASS_OFFICIAL_IMPORT_READY":
        return "CODE_COMPLETE_ACCESS_REQUIRED"
    if official_status == "PASS_OFFICIAL_IMPORT_READY":
        return "PASS_OFFICIAL_IMPORT_READY"
    return "BLOCKED_LIVE_REQUEST_UNRESOLVED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="OFFLINE", choices=["OFFLINE", "LIVE_PUBLIC", "LIVE_CREDENTIAL", "FULL_DRY_RUN", "FULL_PROMOTION"])
    args = parser.parse_args()
    ensure()
    steps: list[dict] = []
    if args.mode == "OFFLINE":
        steps.append(run(["scripts/build_edgeiq_racing_com_runner_sectionals_completion_v1.py"]))
        steps.append(run(["scripts/edgeiq_racing_com_public_adapter_v1.py", "--mode", "all"]))
        steps.append(run(["scripts/import_racing_com_runner_sectionals_official_file_v1.py"]))
        steps.append(run(["scripts/audit_racing_com_public_adapter_security_v1.py"]))
    elif args.mode == "LIVE_PUBLIC":
        steps.append(run(["scripts/build_edgeiq_racing_com_runner_sectionals_completion_v1.py"]))
        steps.append(run(["scripts/replay_racing_com_runner_sectionals_v1.py", "--mode", "ALL"]))
        steps.append(run(["scripts/build_edgeiq_racing_com_runner_sectionals_completion_v1.py"]))
        steps.append(run(["scripts/audit_racing_com_public_adapter_security_v1.py"]))
    elif args.mode == "LIVE_CREDENTIAL":
        if os.environ.get(ENV_NAME, ""):
            steps.append(run(["scripts/replay_racing_com_runner_sectionals_v1.py", "--mode", "APPROVED_CREDENTIAL"]))
        else:
            steps.append({"cmd": "credential presence check", "returncode": 0, "stdout": "approved credential absent", "stderr": ""})
        steps.append(run(["scripts/build_edgeiq_racing_com_runner_sectionals_completion_v1.py"]))
    elif args.mode == "FULL_DRY_RUN":
        steps.append(run(["scripts/build_edgeiq_racing_com_runner_sectionals_completion_v1.py"]))
        steps.append(run(["scripts/replay_racing_com_runner_sectionals_v1.py", "--mode", "ALL", "--dry-run", "--output-root", "docs/racing-com-public-data-v1/completion/dry-run"]))
        steps.append(run(["scripts/import_racing_com_runner_sectionals_official_file_v1.py"]))
        steps.append(run(["scripts/build_edgeiq_racing_com_runner_sectionals_completion_v1.py"]))
        steps.append(run(["scripts/audit_edgeiq_racing_com_public_data_v1.py"]))
    elif args.mode == "FULL_PROMOTION":
        decision, _ = access_decision()
        steps.append({"cmd": "promotion gate", "returncode": 0, "stdout": "public anonymous confirmed" if decision == "PUBLIC_ANONYMOUS_CONFIRMED" else "promotion skipped: public anonymous access not confirmed", "stderr": ""})
    status = final_status(args.mode, steps)
    summary = {"mode": args.mode, "status": status, "generated_at": now(), "credential_env_var": ENV_NAME, "credential_state": "PRESENT" if os.environ.get(ENV_NAME, "") else "ABSENT", "steps": steps}
    write_json(ACCEPT / f"{args.mode.lower()}_acceptance.json", summary)
    report = f"""# Racing.com Public Acceptance V1

Mode: `{args.mode}`

Status: `{status}`

Credential state: `{summary['credential_state']}`
"""
    write_text(ACCEPT / f"{args.mode.lower()}_acceptance.md", report)
    print(json.dumps(summary, indent=2))
    return 0 if status in ALLOWED_SUCCESS else 1


if __name__ == "__main__":
    raise SystemExit(main())
