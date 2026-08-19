from __future__ import annotations

import csv
import json
import subprocess
import time
import urllib.request
from pathlib import Path



ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DOCS = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
OUT = DOCS / "edgeiq_performance_intelligence_program_smoke_v1.csv"
SUMMARY = DOCS / "edgeiq_performance_intelligence_program_smoke_summary_v1.json"
REPORT = DOCS / "edgeiq_performance_intelligence_program_smoke_report_v1.md"


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "value", "detail"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    port = 5199
    DOCS.mkdir(parents=True, exist_ok=True)
    log_path = DOCS / "edgeiq_performance_intelligence_program_smoke_v1_dev_server.log"
    log_handle = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(["npm.cmd", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port)], cwd=str(ROOT), stdout=log_handle, stderr=subprocess.STDOUT, text=True)
    checks = []
    try:
        body = ""
        status = "FAIL"
        for _ in range(60):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=2) as response:
                    body = response.read(2000).decode("utf-8", errors="ignore")
                    status = "PASS" if response.status == 200 and "<html" in body.lower() else "FAIL"
                    break
            except Exception:
                time.sleep(1)
        checks.append({"check": "dev_server_http_200", "status": status, "value": f"http://127.0.0.1:{port}", "detail": "Vite dev server served root HTML."})
        checks.append({"check": "html_contains_root", "status": "PASS" if "root" in body.lower() else "FAIL", "value": str("root" in body.lower()), "detail": "Root mount present in served HTML."})
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_handle.close()
    decision = "PERFORMANCE_INTELLIGENCE_PROGRAM_SMOKE_PASS" if all(c["status"] == "PASS" for c in checks) else "PERFORMANCE_INTELLIGENCE_PROGRAM_SMOKE_FAIL"
    write_csv(OUT, checks)
    SUMMARY.write_text(json.dumps({"decision": decision}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(f"# Performance Intelligence Program Smoke V1\n\nDecision: `{decision}`\n\nServed local Vite root page on port `{port}`.\n", encoding="utf-8")
    print(json.dumps({"decision": decision}, indent=2))
    return 0 if decision.endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
