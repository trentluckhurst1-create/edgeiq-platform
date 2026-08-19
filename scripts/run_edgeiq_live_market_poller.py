import subprocess
import time
from datetime import datetime

SCRIPTS = [
    r".\scripts\capture_sportsbet_live_market_v1.py",
    r".\scripts\build_edgeiq_bookmaker_board_v1.py",
    r".\scripts\build_edgeiq_market_tape_engine_v1.py",
    r".\scripts\build_edgeiq_market_velocity_engine_v1.py"
]

POLL_SECONDS = 60

print("=" * 80)
print("EDGEIQ LIVE MARKET POLLER")
print("=" * 80)
print(f"poll interval: {POLL_SECONDS}s")
print("=" * 80)

while True:
    cycle_start = datetime.now()

    print("")
    print("=" * 80)
    print(f"CYCLE START {cycle_start}")
    print("=" * 80)

    for script in SCRIPTS:
        print(f"RUNNING: {script}")

        result = subprocess.run(
            ["python", script],
            capture_output=True,
            text=True
        )

        print(result.stdout)

        if result.stderr:
            print("ERROR:")
            print(result.stderr)

    print("")
    print(f"SLEEPING {POLL_SECONDS}s")
    print("")

    time.sleep(POLL_SECONDS)

