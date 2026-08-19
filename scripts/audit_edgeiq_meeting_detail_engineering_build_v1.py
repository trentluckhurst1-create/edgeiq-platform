from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "public" / "data" / "edgeiq_meeting_detail_engineering_build_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_meeting_detail_engineering_build_v1_audit.txt"

AUDITS = [
    "scripts/audit_edgeiq_engineering_specification_library_v1.py",
    "scripts/audit_edgeiq_meeting_detail_data_contract_v1.py",
    "scripts/audit_edgeiq_meeting_detail_visual_structure_v1.py",
    "scripts/audit_edgeiq_meeting_races_tab_v1.py",
]


def run_audit(relative: str) -> dict[str, object]:
    path = ROOT / relative
    if not path.exists():
        return {
            "audit": relative,
            "pass": False,
            "returncode": None,
            "output": "Audit script missing.",
        }
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return {
        "audit": relative,
        "pass": completed.returncode == 0,
        "returncode": completed.returncode,
        "output": completed.stdout.strip(),
    }


def main() -> int:
    results = [run_audit(audit) for audit in AUDITS]
    passed = all(item["pass"] for item in results)
    status = (
        "EDGEIQ_MEETING_DETAIL_ENGINEERING_BUILD_V1_AUDIT_PASS"
        if passed
        else "EDGEIQ_MEETING_DETAIL_ENGINEERING_BUILD_V1_AUDIT_FAIL"
    )
    result = {"status": status, "audits": results}

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    OUT_TXT.write_text(
        "\n".join(
            [
                status,
                "",
                *[
                    f"{'PASS' if item['pass'] else 'FAIL'} {item['audit']} rc={item['returncode']}\n{item['output']}"
                    for item in results
                ],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(status)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
