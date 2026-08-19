from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT.parents[1]
DATA = ROOT / "public" / "data"

COVERAGE_AUDIT = DATA / "edgeiq_historical_universe_coverage_audit_v1.csv"
MISSING_HORSES = MODEL_ROOT / "outputs" / "coverage" / "missing_horses.csv"

SCRAPER = MODEL_ROOT / "scrape_ra_horse_career_history.py"

REBUILD_STEPS = [
    ROOT / "scripts" / "build_edgeiq_official_run_context_bridge_v1.py",
    ROOT / "scripts" / "build_edgeiq_historical_performance_rating_v3.py",
    ROOT / "scripts" / "build_edgeiq_historical_performance_rating_v3_3.py",
    ROOT / "scripts" / "build_edgeiq_historical_performance_rating_v5_1.py",
    ROOT / "scripts" / "build_edgeiq_current_field_projection_v5_2.py",
    ROOT / "scripts" / "build_edgeiq_current_field_rated_price_audit_v5_2.py",
    ROOT / "scripts" / "build_edgeiq_current_fair_prices_review_v5_2.py",
    ROOT / "scripts" / "build_edgeiq_live_runner_board_v1.py",
    ROOT / "scripts" / "repair_edgeiq_live_runner_board_fair_price_join_v1.py",
    ROOT / "scripts" / "build_edgeiq_sectional_value_plays_v1.py",
    ROOT / "scripts" / "build_edgeiq_historical_universe_coverage_audit_v1.py",
]

def run(script: Path, cwd: Path) -> None:
    if not script.exists():
        raise FileNotFoundError(script)
    print("=" * 90)
    print(f"RUNNING: {script}")
    print("=" * 90)
    result = subprocess.run([sys.executable, str(script)], cwd=str(cwd), text=True)
    if result.returncode != 0:
        raise SystemExit(result.returncode)

def main() -> None:
    print("=" * 90)
    print("EDGEIQ NO-HISTORY AUTO BACKFILL V1")
    print("=" * 90)

    run(ROOT / "scripts" / "build_edgeiq_historical_universe_coverage_audit_v1.py", ROOT)

    audit = pd.read_csv(COVERAGE_AUDIT, dtype=str, keep_default_na=False)

    targets = (
        audit[audit["coverage_status"].eq("NO_PROJECTION_HISTORY")]
        [["horse"]]
        .drop_duplicates()
        .sort_values("horse")
    )

    MISSING_HORSES.parent.mkdir(parents=True, exist_ok=True)
    targets.to_csv(MISSING_HORSES, index=False)

    print(f"NO_PROJECTION_HISTORY targets: {len(targets)}")
    print(f"wrote: {MISSING_HORSES}")

    if targets.empty:
        print("No missing projection-history horses. Skipping scrape.")
    else:
        run(SCRAPER, MODEL_ROOT)

    for script in REBUILD_STEPS:
        run(script, ROOT)

    summary = DATA / "edgeiq_historical_universe_coverage_audit_v1_summary.csv"
    print("=" * 90)
    print("FINAL COVERAGE SUMMARY")
    print("=" * 90)
    print(summary.read_text(encoding="utf-8"))

if __name__ == "__main__":
    main()
