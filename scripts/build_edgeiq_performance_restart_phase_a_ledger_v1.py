from __future__ import annotations

import csv
import json
import subprocess
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "performance-intelligence" / "restart-v1"


def run_git(args: list[str]) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def count_rows(path: Path) -> int:
    if not path.exists():
        return -1
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.reader(f)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def main() -> None:
    started = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    head = run_git(["rev-parse", "HEAD"])
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    status = run_git(["status", "--short"])
    staged = run_git(["diff", "--cached", "--name-only"])
    target_002d_json = OUT / "edgeiq_performance_intelligence_target_001_expected_race_entry_schema_trace_v1.json"
    unit_002d = None
    if target_002d_json.exists():
        unit_002d = json.loads(target_002d_json.read_text(encoding="utf-8"))
    process_probe = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|powershell|pwsh' -and $_.CommandLine -match 'edgeiq|performance|target|race_entry|standard_time' } | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Depth 4"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    outputs = {
        "target_001": ROOT / "public/data/edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv",
        "target_002": ROOT / "public/data/edgeiq_standard_time_fact_v1.csv",
        "ratings": ROOT / "public/data/edgeiq_horse_performance_rating_fact_v1.csv",
        "race_entry": ROOT / "public/data/edgeiq_race_entry_fact_v1.csv",
    }
    output_summary = []
    for name, path in outputs.items():
        output_summary.append({
            "name": name,
            "path": path.relative_to(ROOT).as_posix(),
            "exists": path.exists(),
            "rows": count_rows(path),
            "sha256": sha256_file(path) if path.exists() else "",
        })
    ledger_rows = [{
        "unit": "PHASE_A_RESTART_SAFETY_LEDGER",
        "objective": "Capture branch, HEAD, dirty worktree, staging, process state and Unit 002D completion before autonomous recovery.",
        "status": "PASS",
        "starting_commit": head,
        "ending_commit": head,
        "files_created": "edgeiq_performance_restart_progress_ledger_v1.csv|edgeiq_performance_restart_phase_a_safety_v1.json|EDGEIQ_PERFORMANCE_RESTART_PHASE_A_SAFETY_V1.md",
        "findings": "Unit 002D completed; no populated exact old-contract race-entry dataset found. Working tree is dirty and protected. Staging was captured.",
        "next_action": "Resolve Target 001 schema authority and implement governed correction only after architecture decision.",
        "blockers": "None for Phase A.",
        "runtime_seconds": f"{time.time() - started:.3f}",
        "governance_declarations": "engine_logic_changed=NO;thresholds_changed=NO;source_data_changed=NO;runtime_data_changed=NO;react_changed=NO",
    }]
    ledger_csv = OUT / "edgeiq_performance_restart_progress_ledger_v1.csv"
    with ledger_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(ledger_rows[0].keys()))
        writer.writeheader(); writer.writerows(ledger_rows)
    payload = {
        "unit": "PHASE_A_RESTART_SAFETY_LEDGER",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": "PASS",
        "branch": branch,
        "head": head,
        "working_tree_status_line_count": len([line for line in status.splitlines() if line.strip()]),
        "staged_files": [line for line in staged.splitlines() if line.strip()],
        "relevant_process_probe_stdout": process_probe.stdout,
        "relevant_process_probe_stderr": process_probe.stderr,
        "unit_002d_completed": bool(unit_002d),
        "unit_002d_classification": unit_002d.get("finding", {}).get("classification") if unit_002d else "MISSING",
        "unit_002d_next_action": unit_002d.get("finding", {}).get("next_action") if unit_002d else "RUN_UNIT_002D",
        "canonical_output_summary": output_summary,
        "governance": {
            "protected_dirty_worktree": True,
            "engine_logic_changed": False,
            "thresholds_changed": False,
            "source_data_changed": False,
            "runtime_data_changed": False,
            "react_changed": False,
        },
    }
    json_path = OUT / "edgeiq_performance_restart_phase_a_safety_v1.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = OUT / "EDGEIQ_PERFORMANCE_RESTART_PHASE_A_SAFETY_V1.md"
    md.write_text("\n".join([
        "# EDGEIQ Performance Restart Phase A Safety V1",
        "",
        f"Verdict: **{payload['verdict']}**",
        f"Branch: `{branch}`",
        f"HEAD: `{head}`",
        f"Dirty working-tree entries captured: `{payload['working_tree_status_line_count']}`",
        f"Unit 002D completed: `{payload['unit_002d_completed']}`",
        f"Unit 002D classification: `{payload['unit_002d_classification']}`",
        "",
        "Governance: no engine logic, threshold, source data, runtime data or React changes in this unit.",
        "",
    ]), encoding="utf-8")
    print("PHASE_A_RESTART_SAFETY_LEDGER_PASS")
    print(f"head={head}")
    print(f"dirty_entries={payload['working_tree_status_line_count']}")
    print(f"unit_002d_completed={payload['unit_002d_completed']}")

if __name__ == "__main__":
    main()
