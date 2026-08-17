from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "deployment-phase3"
CLEAN_SOURCE = OUT / "server-smoke-clean-source"
RUNTIME = OUT / "server-smoke-runtime"
REPORT = OUT / "edgeiq_render_server_smoke_v1.json"
PORT = 18105


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_reset(path: Path) -> None:
    resolved = path.resolve()
    allowed = OUT.resolve()
    if not str(resolved).startswith(str(allowed)):
        raise RuntimeError(f"Unsafe smoke path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def request_json(path: str) -> tuple[int, dict[str, object]]:
    url = f"http://127.0.0.1:{PORT}{path}"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        return error.code, json.loads(body)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    safe_reset(CLEAN_SOURCE)
    safe_reset(RUNTIME)

    env = {
        **os.environ,
        "PORT": str(PORT),
        "EDGEIQ_RUNTIME_ROOT": str(RUNTIME),
        "EDGEIQ_DATA_ROOT": str(RUNTIME / "public" / "data"),
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_ROOT": str(RUNTIME / "public" / "performance-intelligence"),
        "EDGEIQ_PERFORMANCE_DOCS_ROOT": str(RUNTIME / "docs" / "performance-intelligence"),
        "EDGEIQ_MARKET_DATA_ROOT": str(RUNTIME / "data" / "market" / "ladbrokes"),
        "EDGEIQ_HEALTH_PATH": str(RUNTIME / "health" / "edgeiq_production_health_v1.json"),
        "EDGEIQ_REFRESH_ENABLED": "false",
        "EDGEIQ_REFRESH_ON_STARTUP": "false",
    }
    process = subprocess.Popen(
        ["node", str(ROOT / "deployment" / "edgeiq_render_server.mjs")],
        cwd=CLEAN_SOURCE,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout = ""
    stderr = ""
    try:
        healthz_status = 0
        healthz_payload: dict[str, object] = {}
        for _ in range(40):
            time.sleep(0.5)
            try:
                healthz_status, healthz_payload = request_json("/healthz")
                break
            except Exception:
                if process.poll() is not None:
                    break
        api_status = 0
        api_payload: dict[str, object] = {}
        try:
            api_status, api_payload = request_json("/api/health")
        except Exception as exc:
            api_payload = {"error": str(exc)}

        checks = {
            "healthz_200": healthz_status == 200,
            "api_health_fails_visible_without_health_artifact": api_status == 503,
            "public_data_mount_created": (CLEAN_SOURCE / "public" / "data").exists(),
            "public_performance_mount_created": (CLEAN_SOURCE / "public" / "performance-intelligence").exists(),
            "docs_performance_mount_created": (CLEAN_SOURCE / "docs" / "performance-intelligence").exists(),
            "market_mount_created": (CLEAN_SOURCE / "data" / "market" / "ladbrokes").exists(),
            "refresh_disabled": healthz_payload.get("refreshEnabled") is False,
            "startup_refresh_disabled": healthz_payload.get("refreshOnStartup") is False,
        }
        status = "PASS" if all(checks.values()) else "FAIL"
        if process.poll() is not None:
            try:
                stdout, stderr = process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        payload = {
            "schema_version": "EDGEIQ_RENDER_SERVER_SMOKE_V1",
            "generated_at": utc_now(),
            "clean_source_dir": str(CLEAN_SOURCE),
            "runtime_dir": str(RUNTIME),
            "port": PORT,
            "checks": checks,
            "healthz_status": healthz_status,
            "api_health_status_without_health_artifact": api_status,
            "healthz_payload": healthz_payload,
            "api_health_payload": api_payload,
            "process_returncode": process.poll(),
            "stdout_tail": stdout[-2000:],
            "stderr_tail": stderr[-2000:],
            "status": status,
        }
        REPORT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({
            "RENDER_SERVER_SMOKE": status,
            "checks": checks,
            "report": str(REPORT),
        }, indent=2, sort_keys=True))
        return 0 if status == "PASS" else 1
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
