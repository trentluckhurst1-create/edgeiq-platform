from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")


def main() -> int:
    return subprocess.call([sys.executable, "-u", str(ROOT / "scripts" / "audit_edgeiq_race_entry_projection_forensics_v1.py")], cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
