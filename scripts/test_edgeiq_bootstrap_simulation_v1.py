from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "deployment-phase3"
RUNTIME = OUT / "bootstrap-simulation-runtime"
CLEAN_SOURCE = OUT / "bootstrap-simulation-clean-source"
SEED = Path("C:/EDGEIQ_DEPLOYMENT_SEED_V1")
REPORT = OUT / "edgeiq_bootstrap_simulation_v1.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run(
    command: list[str],
    env: dict[str, str] | None = None,
    cwd: Path = ROOT,
) -> dict[str, object]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        env={**os.environ, **(env or {})},
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
        "status": "PASS" if completed.returncode == 0 else "FAIL",
    }


def safe_reset_runtime() -> None:
    resolved = RUNTIME.resolve()
    allowed = (ROOT / "outputs" / "deployment-phase3").resolve()
    if not str(resolved).startswith(str(allowed)):
        raise RuntimeError(f"Unsafe bootstrap simulation path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved, onexc=force_remove)
    resolved.mkdir(parents=True, exist_ok=True)


def safe_reset_clean_source() -> None:
    resolved = CLEAN_SOURCE.resolve()
    allowed = (ROOT / "outputs" / "deployment-phase3").resolve()
    if not str(resolved).startswith(str(allowed)):
        raise RuntimeError(f"Unsafe clean source simulation path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved, onexc=force_remove)
    (resolved / "scripts").mkdir(parents=True, exist_ok=True)
    for script_name in [
        "bootstrap_edgeiq_production_data_v1.py",
        "edgeiq_production_refresh_launcher_v1.py",
    ]:
        shutil.copy2(ROOT / "scripts" / script_name, resolved / "scripts" / script_name)


def force_remove(function, path, exc_info) -> None:
    Path(path).chmod(stat.S_IWRITE)
    function(path)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if not SEED.exists():
        raise RuntimeError(f"Exported seed does not exist: {SEED}")
    safe_reset_runtime()
    safe_reset_clean_source()
    bootstrap = run([
        sys.executable,
        "scripts/bootstrap_edgeiq_production_data_v1.py",
        "--seed-dir",
        str(SEED),
        "--data-root",
        str(RUNTIME),
    ])
    validate = run([
        sys.executable,
        "scripts/bootstrap_edgeiq_production_data_v1.py",
        "--seed-dir",
        str(SEED),
        "--validate-seed-only",
    ])
    audit = run([
        sys.executable,
        "scripts/bootstrap_edgeiq_production_data_v1.py",
        "--data-root",
        str(RUNTIME),
        "--audit-only",
    ])
    health_env = {
        "EDGEIQ_RUNTIME_ROOT": str(RUNTIME),
        "EDGEIQ_DATA_ROOT": str(RUNTIME / "public" / "data"),
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_ROOT": str(RUNTIME / "public" / "performance-intelligence"),
        "EDGEIQ_PERFORMANCE_DOCS_ROOT": str(RUNTIME / "docs" / "performance-intelligence"),
        "EDGEIQ_MARKET_DATA_ROOT": str(RUNTIME / "data" / "market" / "ladbrokes"),
        "EDGEIQ_HEALTH_PATH": str(RUNTIME / "health" / "edgeiq_production_health_v1.json"),
        "EDGEIQ_BOOTSTRAP_ENABLED": "false",
    }
    health = run([
        sys.executable,
        "scripts/edgeiq_production_refresh_launcher_v1.py",
        "--audit-only",
        "--trigger",
        "bootstrap-simulation",
    ], env=health_env, cwd=CLEAN_SOURCE)
    state = RUNTIME / "state" / "edgeiq_seed_state_v1.json"
    checks = {
        "seed_exists": SEED.exists(),
        "bootstrap_pass": bootstrap["returncode"] == 0,
        "validate_pass": validate["returncode"] == 0,
        "audit_pass": audit["returncode"] == 0,
        "seed_state_written": state.exists(),
        "public_data_seeded": (RUNTIME / "public" / "data").exists(),
        "performance_docs_seeded": (RUNTIME / "docs" / "performance-intelligence").exists(),
        "market_data_seeded": (RUNTIME / "data" / "market" / "ladbrokes").exists(),
        "health_audit_executed": health["returncode"] in {0, 1},
    }
    payload = {
        "schema_version": "EDGEIQ_BOOTSTRAP_SIMULATION_V1",
        "generated_at": utc_now(),
        "seed_dir": str(SEED),
        "runtime_dir": str(RUNTIME),
        "clean_source_dir": str(CLEAN_SOURCE),
        "checks": checks,
        "bootstrap": bootstrap,
        "validate": validate,
        "audit": audit,
        "health": health,
        "BOOTSTRAP_SIMULATION": "PASS" if all(checks.values()) else "FAIL",
    }
    REPORT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "BOOTSTRAP_SIMULATION": payload["BOOTSTRAP_SIMULATION"],
        "runtime_dir": str(RUNTIME),
        "checks": checks,
    }, indent=2, sort_keys=True))
    return 0 if payload["BOOTSTRAP_SIMULATION"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
