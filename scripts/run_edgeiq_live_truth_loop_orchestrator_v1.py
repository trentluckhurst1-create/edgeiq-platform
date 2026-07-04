from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime

ROOT = Path.cwd()
PY = sys.executable

SCRIPTS = [
    # -------------------------------------------------------------------------
    # MARKET / LIVE BASE
    # -------------------------------------------------------------------------
    {
        "name": "LIVE RUNNER BOARD",
        "path": ROOT / "dashboard" / "racing-dashboard" / "scripts" / "build_edgeiq_live_runner_board_v1.py",
        "required": True,
    },

    # -------------------------------------------------------------------------
    # PROBABILITY / CONTEXT
    # -------------------------------------------------------------------------
    {
        "name": "PROBABILITY ENGINE V3",
        "path": ROOT / "dashboard" / "racing-dashboard" / "scripts" / "build_edgeiq_probability_engine_v3.py",
        "required": True,
    },
    {
        "name": "HORSE ENERGY PROFILE V1",
        "path": ROOT / "dashboard" / "racing-dashboard" / "scripts" / "build_edgeiq_horse_energy_profile_engine_v1.py",
        "required": False,
    },
    {
        "name": "RACE SHAPE ENGINE V2",
        "path": ROOT / "dashboard" / "racing-dashboard" / "scripts" / "build_edgeiq_race_shape_engine_v2.py",
        "required": False,
    },
    {
        "name": "UNIVERSAL RACE IDENTITY V2",
        "path": ROOT / "dashboard" / "racing-dashboard" / "scripts" / "build_edgeiq_universal_race_identity_v2.py",
        "required": True,
    },
    {
        "name": "PROBABILITY ENGINE V4.1",
        "path": ROOT / "dashboard" / "racing-dashboard" / "scripts" / "build_edgeiq_probability_engine_v4_1.py",
        "required": True,
    },
    {
        "name": "HORSE ENERGY PROXY V1",
        "path": ROOT / "dashboard" / "racing-dashboard" / "scripts" / "build_edgeiq_horse_energy_proxy_engine_v1.py",
        "required": True,
    },
    {
        "name": "CONTEXTUAL PROBABILITY ENGINE V5",
        "path": ROOT / "dashboard" / "racing-dashboard" / "scripts" / "build_edgeiq_contextual_probability_engine_v5.py",
        "required": True,
    },

    # -------------------------------------------------------------------------
    # EXECUTION / CAPITAL / PORTFOLIO
    # -------------------------------------------------------------------------
    {
        "name": "EXECUTION QUALITY ENGINE V2",
        "path": ROOT / "dashboard" / "racing-dashboard" / "scripts" / "build_edgeiq_execution_quality_engine_v2.py",
        "required": True,
    },
    {
        "name": "CAPITAL ALLOCATION ENGINE V1",
        "path": ROOT / "dashboard" / "racing-dashboard" / "scripts" / "build_edgeiq_capital_allocation_engine_v1.py",
        "required": True,
    },
    {
        "name": "PORTFOLIO RISK ENGINE V1",
        "path": ROOT / "dashboard" / "racing-dashboard" / "scripts" / "build_edgeiq_portfolio_risk_engine_v1.py",
        "required": True,
    },
    {
        "name": "PORTFOLIO THROTTLE ENGINE V1",
        "path": ROOT / "dashboard" / "racing-dashboard" / "scripts" / "build_edgeiq_portfolio_throttle_engine_v1.py",
        "required": True,
    },

    # -------------------------------------------------------------------------
    # RESULTS / LEARNING
    # -------------------------------------------------------------------------
    {
        "name": "LIVE TERMINAL FEED V1",
        "path": ROOT / "dashboard" / "racing-dashboard" / "scripts" / "build_edgeiq_live_terminal_feed_v1.py",
        "required": True,
    },

    {
        "name": "CONTEXTUAL RESULT LINK V1",
        "path": ROOT / "dashboard" / "racing-dashboard" / "scripts" / "build_edgeiq_contextual_result_link_engine_v1.py",
        "required": False,
    },
    {
        "name": "CONTEXTUAL LEARNING ENGINE V1",
        "path": ROOT / "dashboard" / "racing-dashboard" / "scripts" / "build_edgeiq_contextual_learning_engine_v1.py",
        "required": False,
    },
]

OUT = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_truth_loop_orchestrator_v1_status.csv"
LOG = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_truth_loop_orchestrator_v1_log.txt"
SYSTEM_STATE = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_system_state_v1.csv"
LOOP_SECONDS = 60

def run_script(item):
    name = item["name"]
    path = item["path"]
    required = item["required"]

    started = datetime.now()
    status = "OK"
    return_code = 0
    message = ""

    if not path.exists():
        status = "MISSING_REQUIRED" if required else "MISSING_OPTIONAL"
        return_code = -1
        message = f"Missing script: {path}"
        return {
            "timestamp": started.isoformat(timespec="seconds"),
            "engine": name,
            "script": str(path),
            "required": required,
            "status": status,
            "return_code": return_code,
            "seconds": 0,
            "message": message,
        }

    print()
    print("=" * 100)
    print(f"RUNNING: {name}")
    print(path)
    print("=" * 100)

    try:
        proc = subprocess.run(
            [PY, str(path)],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=240,
        )

        return_code = proc.returncode

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""

        if stdout.strip():
            print(stdout)

        if stderr.strip():
            print("STDERR:")
            print(stderr)

        if proc.returncode != 0:
            status = "FAILED_REQUIRED" if required else "FAILED_OPTIONAL"
            message = stderr.strip()[:1000] or stdout.strip()[-1000:]
        else:
            status = "OK"
            message = stdout.strip().splitlines()[-1] if stdout.strip() else "completed"

    except subprocess.TimeoutExpired:
        status = "TIMEOUT_REQUIRED" if required else "TIMEOUT_OPTIONAL"
        return_code = -2
        message = "Timed out after 240 seconds"

    except Exception as e:
        status = "ERROR_REQUIRED" if required else "ERROR_OPTIONAL"
        return_code = -3
        message = repr(e)

    finished = datetime.now()
    seconds = round((finished - started).total_seconds(), 2)

    return {
        "timestamp": finished.isoformat(timespec="seconds"),
        "engine": name,
        "script": str(path),
        "required": required,
        "status": status,
        "return_code": return_code,
        "seconds": seconds,
        "message": message,
    }

def run_once():
    print("=" * 100)
    print("EDGEIQ LIVE TRUTH LOOP ORCHESTRATOR V1.1")
    print("=" * 100)
    print("ROOT:", ROOT)
    print("PYTHON:", PY)
    print("START:", datetime.now().isoformat(timespec="seconds"))

    rows = []
    hard_fail = False

    LOG.parent.mkdir(parents=True, exist_ok=True)

    with LOG.open("a", encoding="utf-8") as log:
        log.write("\n" + "=" * 100 + "\n")
        log.write(f"EDGEIQ LIVE TRUTH LOOP ORCHESTRATOR V1 START {datetime.now().isoformat(timespec='seconds')}\n")
        log.write("=" * 100 + "\n")

    for item in SCRIPTS:
        result = run_script(item)
        rows.append(result)

        with LOG.open("a", encoding="utf-8") as log:
            log.write(
                f"{result['timestamp']} | {result['engine']} | "
                f"{result['status']} | {result['seconds']}s | {result['message']}\n"
            )

        if item["required"] and not str(result["status"]).upper().startswith("OK"):
            hard_fail = True
            print()
            print("=" * 100)
            print("HARD STOP — REQUIRED ENGINE FAILED")
            print(result["engine"])
            print(result["status"])
            print(result["message"])
            print("=" * 100)
            break

        time.sleep(0.5)

    import pandas as pd

    status_df = pd.DataFrame(rows)
    status_df.to_csv(OUT, index=False)

    print()
    print("=" * 100)
    print("ORCHESTRATOR SUMMARY")
    print("=" * 100)

    print(status_df[["engine", "required", "status", "seconds"]].to_string(index=False))

    print()
    print("SAVED:")
    print(OUT)
    print(LOG)

    if hard_fail:
        print()
        print("ORCHESTRATOR RESULT: FAILED")
        sys.exit(1)

    system_rows = [{
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "orchestrator": "EDGEIQ_LIVE_TRUTH_LOOP_V1_1",
        "required_failures": int(status_df[status_df["status"].astype(str).str.contains("FAILED|ERROR|TIMEOUT|MISSING_REQUIRED", case=False, regex=True)].shape[0]),
        "engines_run": int(len(status_df)),
        "engines_ok": int((status_df["status"] == "OK").sum()),
        "system_status": "FAILED" if hard_fail else "OK",
        "last_completed_engine": status_df["engine"].iloc[-1] if len(status_df) else "",
    }]

    pd.DataFrame(system_rows).to_csv(SYSTEM_STATE, index=False)

    print()
    print("SYSTEM STATE SAVED:")
    print(SYSTEM_STATE)

    print()
    print("ORCHESTRATOR RESULT: OK")

def main():
    while True:
        run_once()
        print()
        print("=" * 100)
        print(f"NEXT EDGEIQ TRUTH LOOP RUN IN {LOOP_SECONDS} SECONDS")
        print("=" * 100)
        time.sleep(LOOP_SECONDS)

if __name__ == "__main__":
    main()
