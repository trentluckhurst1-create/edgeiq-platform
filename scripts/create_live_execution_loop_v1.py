from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboard" / "racing-dashboard"

poller = ROOT / "run_edgeiq_live_execution_loop_v1.py"

poller.write_text(r'''
import subprocess
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboard" / "racing-dashboard"
LOG = ROOT / "outputs" / "live_execution_loop"
LOG.mkdir(parents=True, exist_ok=True)

PY = "python"

COMMANDS = [
    [PY, str(ROOT / "capture_real_race_page.py")],
    [PY, str(ROOT / "final_restore_sportsbet_market.py")],
    [PY, str(ROOT / "derive_sportsbet_track_names.py")],
    [PY, str(DASH / "scripts" / "build_edgeiq_live_runner_board_v1.py")],
    [PY, str(DASH / "scripts" / "build_edgeiq_price_truth_execution_v1.py")],
    [PY, str(DASH / "scripts" / "build_edgeiq_execution_explainability_v1.py")],
]

POLL_SECONDS = 60

def run_cmd(cmd):
    print()
    print("=" * 100)
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "RUNNING:")
    print(" ".join(cmd))
    print("=" * 100)

    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        shell=False
    )

    print(result.stdout)

    if result.stderr.strip():
        print("STDERR:")
        print(result.stderr)

    if result.returncode != 0:
        print("FAILED:", result.returncode)
        return False

    return True

print("=" * 100)
print("EDGEIQ LIVE EXECUTION LOOP V1")
print("=" * 100)
print("POLL SECONDS:", POLL_SECONDS)
print("CTRL+C TO STOP")
print("=" * 100)

while True:
    cycle_start = datetime.now()

    print()
    print("#" * 100)
    print("LIVE EXECUTION CYCLE:", cycle_start.strftime("%Y-%m-%d %H:%M:%S"))
    print("#" * 100)

    ok = True

    for cmd in COMMANDS:
        if not run_cmd(cmd):
            ok = False
            break

    status = "OK" if ok else "FAILED"

    heartbeat = LOG / "heartbeat.txt"
    heartbeat.write_text(
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {status}\n",
        encoding="utf-8"
    )

    print()
    print("=" * 100)
    print("CYCLE COMPLETE:", status)
    print("NEXT RUN IN", POLL_SECONDS, "SECONDS")
    print("=" * 100)

    time.sleep(POLL_SECONDS)
''', encoding="utf-8")

print("LIVE EXECUTION LOOP CREATED:")
print(poller)
