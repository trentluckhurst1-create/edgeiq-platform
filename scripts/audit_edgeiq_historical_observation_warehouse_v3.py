from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path.cwd().absolute()

BUILDER = (
    ROOT
    / "scripts"
    / "rebuild_edgeiq_historical_observation_warehouse_v3.py"
)


def main() -> int:
    if not BUILDER.exists():
        raise FileNotFoundError(
            BUILDER.as_posix()
        )

    result = subprocess.run(
        [
            sys.executable,
            "-u",
            str(BUILDER),
            "--audit-only",
        ],
        cwd=ROOT,
        check=False,
    )

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
