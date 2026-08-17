from __future__ import annotations

from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from LIVE_PERFORMANCE_BUILDERS.audit_edgeiq_race_entry_horse_performance_snapshot_fact_v1 import main


if __name__ == "__main__":
    main()
