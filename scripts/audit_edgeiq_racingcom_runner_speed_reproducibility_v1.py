from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]

BUILDER = ROOT / "scripts" / "build_edgeiq_racingcom_runner_speed_warehouse_v1.py"

FILES = [
    ROOT / "public" / "data" / "edgeiq_racingcom_runner_speed_fact_v1.csv",
    ROOT / "public" / "data" / "edgeiq_racingcom_runner_sectional_fact_v1.csv",
    ROOT / "public" / "data" / "edgeiq_racingcom_runner_split_fact_v1.csv",
    ROOT / "public" / "data" / "edgeiq_racingcom_race_speed_summary_v1.csv",
]

OUT = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_racingcom_runner_speed_reproducibility_v1_audit.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def snapshot() -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}

    for path in FILES:
        relative = path.relative_to(ROOT).as_posix()

        if not path.exists():
            result[relative] = {
                "exists": False,
                "size": 0,
                "sha256": "",
            }
            continue

        result[relative] = {
            "exists": True,
            "size": path.stat().st_size,
            "sha256": sha256(path),
        }

    return result


def main() -> int:
    before = snapshot()

    process = subprocess.run(
        [sys.executable, "-u", str(BUILDER)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    after = snapshot()

    mismatches = []

    for relative in sorted(set(before) | set(after)):
        if before.get(relative) != after.get(relative):
            mismatches.append({
                "file": relative,
                "before": before.get(relative),
                "after": after.get(relative),
            })

    missing_files = [
        relative
        for relative, details in after.items()
        if not details["exists"]
    ]

    status = "PASS"

    failures = []

    if process.returncode != 0:
        status = "FAIL"
        failures.append("BUILDER_FAILED")

    if missing_files:
        status = "FAIL"
        failures.append("OUTPUT_FILES_MISSING")

    if mismatches:
        status = "FAIL"
        failures.append("NON_DETERMINISTIC_OUTPUT")

    audit = {
        "audit_name": (
            "EDGEIQ_RACINGCOM_RUNNER_SPEED_REPRODUCIBILITY_V1"
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "status": status,
        "failures": failures,
        "builder": BUILDER.relative_to(ROOT).as_posix(),
        "builder_return_code": process.returncode,
        "builder_stdout": process.stdout,
        "builder_stderr": process.stderr,
        "before": before,
        "after": after,
        "missing_files": missing_files,
        "mismatches": mismatches,
        "semantic_control": {
            "same_source_payloads_required": True,
            "output_hashes_must_remain_identical": True,
            "audit_timestamp_excluded_from_comparison": True,
        },
    }

    OUT.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        "[runner_speed_reproducibility_v1] "
        f"builder return code: {process.returncode}"
    )
    print(
        "[runner_speed_reproducibility_v1] "
        f"files checked: {len(FILES)}"
    )
    print(
        "[runner_speed_reproducibility_v1] "
        f"mismatches: {len(mismatches)}"
    )
    print(
        "[runner_speed_reproducibility_v1] "
        f"audit status: {status}"
    )
    print(
        "[runner_speed_reproducibility_v1] "
        f"wrote {OUT.relative_to(ROOT)}"
    )

    if status != "PASS":
        return 1

    print(
        "EDGEIQ_RACINGCOM_RUNNER_SPEED_"
        "REPRODUCIBILITY_V1_AUDIT_PASS"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
