from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = BASE_DIR / "dashboard" / "racing-dashboard" / "src"


def run_step(title: str, cmd: list[str]) -> None:
    print(f"\n=== {title} ===")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=BASE_DIR)
    if result.returncode != 0:
        raise RuntimeError(f"Step failed: {title}")


def copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        print(f"[MISSING] {src}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"[COPIED] {src} -> {dst}")


def ensure_file(path: Path, message: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{message}\nMissing file: {path}")


def main() -> None:
    py = sys.executable
    public_data = BASE_DIR / "dashboard" / "racing-dashboard" / "public" / "data"

    links_csv = BASE_DIR / "outputs" / "ra_form" / "upcoming_runner_ra_links.csv"
    horse_runs_csv = BASE_DIR / "outputs" / "ra_form" / "horse_runs_ra.csv"
    horses_master_csv = BASE_DIR / "outputs" / "ra_form" / "horses_master.csv"
    runner_snapshot_csv = BASE_DIR / "outputs" / "ra_form" / "upcoming_runner_ra_snapshot.csv"

    rated_runs_csv = BASE_DIR / "outputs" / "ratings" / "all_horse_runs_rated.csv"
    rating_summary_csv = BASE_DIR / "outputs" / "ratings" / "all_horse_rating_summary.csv"
    excluded_csv = BASE_DIR / "outputs" / "ratings" / "all_horse_runs_excluded.csv"

    print("=== FULL RA FORM + RATINGS PIPELINE ===")
    print(f"Base dir: {BASE_DIR}")

    # IMPORTANT:
    # We are intentionally reusing the existing, already-working links file.
    # The local scrape_ra_race_links.py file is currently the wrong script.
    ensure_file(
        links_csv,
        "upcoming_runner_ra_links.csv does not exist.\n"
        "Build it first using your working discovery process, then rerun this pipeline."
    )

    run_step(
        "SCRAPE RA ALL FORM",
        [
            py,
            str(SRC_DIR / "scrape_ra_all_form.py"),
            "--input-csv",
            str(links_csv),
            "--output-dir",
            str(BASE_DIR / "outputs" / "ra_form"),
        ],
    )

    run_step(
        "RATE ALL RUNS",
        [
            py,
            str(SRC_DIR / "all_runs_rating_engine_v2.py"),
            "--input-csv",
            str(horse_runs_csv),
            "--output-dir",
            str(BASE_DIR / "outputs" / "ratings"),
        ],
    )

    copy_if_exists(horse_runs_csv, public_data / "horse_runs_ra.csv")
    copy_if_exists(horses_master_csv, public_data / "horses_master.csv")
    copy_if_exists(runner_snapshot_csv, public_data / "upcoming_runner_ra_snapshot.csv")
    copy_if_exists(rated_runs_csv, public_data / "all_horse_runs_rated.csv")
    copy_if_exists(rating_summary_csv, public_data / "all_horse_rating_summary.csv")
    copy_if_exists(excluded_csv, public_data / "all_horse_runs_excluded.csv")

    print("\n✅ FULL PIPELINE COMPLETE")
    print("Dashboard data updated in dashboard/racing-dashboard/public/data/")


if __name__ == "__main__":
    main()