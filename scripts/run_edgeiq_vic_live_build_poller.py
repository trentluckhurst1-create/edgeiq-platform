from pathlib import Path
import subprocess
import time
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]

STEPS = [
    ["python", str(ROOT / "scripts" / "enrich_vic_live_feed_scratchings.py")],
    ["python", str(ROOT / "scripts" / "enrich_vic_live_feed_silks.py")],
]

POLL_SECONDS = 60

def run_step(cmd):
    print("=" * 90)
    print(datetime.now().isoformat(timespec="seconds"), "RUNNING:", " ".join(cmd))
    print("=" * 90)

    result = subprocess.run(cmd, cwd=ROOT, text=True)

    if result.returncode != 0:
        print("FAILED:", " ".join(cmd), "CODE:", result.returncode)
        return False

    return True

def main():
    print("=" * 90)
    print("EDGEIQ VIC LIVE BUILD POLLER")
    print("=" * 90)
    print("VIC ONLY")
    print("POLL RATE:", POLL_SECONDS, "seconds")
    print("ROOT:", ROOT)
    print("=" * 90)

    while True:
        ok = True

        for cmd in STEPS:
            if not run_step(cmd):
                ok = False
                break

        print("=" * 90)
        print(datetime.now().isoformat(timespec="seconds"), "CYCLE COMPLETE", "OK" if ok else "FAILED")
        print("NEXT RUN IN", POLL_SECONDS, "SECONDS")
        print("=" * 90)

        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()

