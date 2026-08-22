from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_edgeiq_runtime_freshness_v1.py"


def write_fixture(root: Path, operating_date: str, audit_status: str = "PASS") -> None:
    data = root / "data"
    data.mkdir(parents=True)
    (data / "edgeiq_runtime_freshness_v1.json").write_text(
        json.dumps(
            {
                "schema_version": "edgeiq_runtime_freshness_v1",
                "operating_date": operating_date,
                "timezone": "Australia/Melbourne",
                "published_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "audit_status": audit_status,
                "active_current_runners": 2,
                "epr_populated_current_runners": 1,
                "edgeiq_price_populated_current_runners": 1,
            }
        ),
        encoding="utf-8",
    )
    (data / "edgeiq_three_day_window_v1.json").write_text(
        json.dumps(
            {
                "schemaVersion": "edgeiq_three_day_window_v1",
                "timezone": "Australia/Melbourne",
                "today": operating_date,
                "tomorrow": "2026-08-23",
                "dayPlus2": "2026-08-24",
                "dates": [
                    {"key": "TODAY", "date": operating_date, "dayOffset": 0},
                    {"key": "TOMORROW", "date": "2026-08-23", "dayOffset": 1},
                    {"key": "DAY_PLUS_2", "date": "2026-08-24", "dayOffset": 2},
                ],
            }
        ),
        encoding="utf-8",
    )
    with (data / "edgeiq_vic_live_terminal_feed_v1.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["race_date", "runner", "runner_status"])
        writer.writeheader()
        writer.writerow({"race_date": operating_date, "runner": "Runner A", "runner_status": "ACTIVE"})
        writer.writerow({"race_date": operating_date, "runner": "Runner B", "runner_status": "ACTIVE"})
    (data / "edgeiq_form_guide_enriched_v2.json").write_text(
        json.dumps(
            {
                "schemaVersion": "edgeiq_form_guide_enriched_v2",
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "races": [
                    {
                        "raceDate": operating_date,
                        "meeting": "Fixture",
                        "raceNumber": 1,
                        "runners": [
                            {
                                "runnerName": "Runner A",
                                "scratched": False,
                                "epi": {"value": 50.0},
                                "edgeiqPrice": {"value": 2.0},
                            },
                            {
                                "runnerName": "Runner B",
                                "scratched": False,
                                "epi": {"value": None},
                                "edgeiqPrice": {"value": None},
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def run_fixture(root: Path, expected_date: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--data-origin",
            "https://fixture.invalid",
            "--fixture-root",
            str(root),
            "--expected-date",
            expected_date,
            "--skip-production-host",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        valid_root = Path(tmp) / "valid"
        write_fixture(valid_root, "2026-08-22")
        valid = run_fixture(valid_root, "2026-08-22")
        print("POSITIVE_FIXTURE_EXIT", valid.returncode)
        print(valid.stdout)
        if valid.returncode != 0 or "FRESHNESS_STATUS=PASS" not in valid.stdout:
            print(valid.stderr)
            return 1

        stale_root = Path(tmp) / "stale"
        write_fixture(stale_root, "2026-08-21")
        stale = run_fixture(stale_root, "2026-08-22")
        print("NEGATIVE_STALE_FIXTURE_EXIT", stale.returncode)
        print(stale.stdout)
        if stale.returncode == 0 or "FRESHNESS_STATUS=FAIL" not in stale.stdout:
            print(stale.stderr)
            return 1

    print("EDGEIQ_RUNTIME_FRESHNESS_FIXTURE_TESTS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
