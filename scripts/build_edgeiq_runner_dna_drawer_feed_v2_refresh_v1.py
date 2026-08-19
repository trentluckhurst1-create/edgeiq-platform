from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SCRIPTS = ROOT / "scripts"

LIVE_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
DRAWER_V2 = DATA / "edgeiq_runner_dna_drawer_feed_v2.csv"
SUMMARY = DATA / "edgeiq_runner_dna_drawer_feed_v2_refresh_v1_summary.csv"

TRUTHY = {"1", "TRUE", "YES", "Y"}


def safe_text(value: object) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_track(value: object) -> str:
    text = safe_text(value).upper()
    text = text.replace("SPORTSBET-", "SPORTSBET ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_horse(value: object) -> str:
    text = safe_text(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def build_key(frame: pd.DataFrame) -> pd.Series:
    horse_key = frame.get("horse_key", pd.Series("", index=frame.index)).map(clean_horse)
    horse = frame.get("horse", pd.Series("", index=frame.index)).map(clean_horse)
    final_horse = horse_key.where(horse_key != "", horse)
    return (
        frame.get("race_date", pd.Series("", index=frame.index)).map(safe_text).str[:10]
        + "|"
        + frame.get("track", pd.Series("", index=frame.index)).map(clean_track)
        + "|"
        + frame.get("race_no", pd.Series("", index=frame.index)).map(safe_text)
        + "|"
        + final_horse
    )


def truthy(value: object) -> bool:
    return safe_text(value).upper() in TRUTHY


def load_active_universe() -> pd.DataFrame:
    frame = pd.read_csv(LIVE_BOARD, dtype=str, keep_default_na=False, low_memory=False)
    if "runner_status" in frame.columns:
        frame = frame[frame["runner_status"].astype(str).str.upper().ne("SCRATCHED")].copy()
    if "is_scratched" in frame.columns:
        frame = frame[~frame["is_scratched"].map(truthy)].copy()
    frame["refresh_key"] = build_key(frame)
    return frame


def run_python(script_name: str) -> None:
    script_path = SCRIPTS / script_name
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    if result.returncode != 0:
        raise RuntimeError(f"Script failed: {script_name}")


def main() -> None:
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    active = load_active_universe()
    active_keys = set(active["refresh_key"])

    run_python("build_edgeiq_runner_dna_contribution_breakdown_v1.py")
    run_python("build_edgeiq_runner_dna_explainability_panel_v1.py")
    run_python("build_edgeiq_runner_dna_drawer_feed_v1.py")
    run_python("build_edgeiq_runner_dna_drawer_feed_v2.py")

    drawer = pd.read_csv(DRAWER_V2, dtype=str, keep_default_na=False, low_memory=False)
    before_rows = len(drawer)
    drawer["refresh_key"] = build_key(drawer)
    filtered = drawer[drawer["refresh_key"].isin(active_keys)].copy()
    filtered = filtered.drop_duplicates(subset=["refresh_key"], keep="first").drop(columns=["refresh_key"], errors="ignore")
    filtered.to_csv(DRAWER_V2, index=False)

    summary_rows = [
        {"metric": "status", "value": "EDGEIQ_RUNNER_DNA_DRAWER_FEED_V2_REFRESH_V1_BUILT"},
        {"metric": "active_universe_rows", "value": len(active)},
        {"metric": "before_rows", "value": before_rows},
        {"metric": "after_rows", "value": len(filtered)},
        {"metric": "removed_rows", "value": before_rows - len(filtered)},
        {"metric": "dna_score_populated", "value": int(filtered.get("dna_v6_2_score", pd.Series("", index=filtered.index)).astype(str).str.strip().ne("").sum())},
        {"metric": "narrative_populated", "value": int(filtered.get("runner_dna_v6_2_narrative", pd.Series("", index=filtered.index)).astype(str).str.strip().ne("").sum())},
        {"metric": "positive_factor_populated", "value": int(filtered.get("positive_1_factor", pd.Series("", index=filtered.index)).astype(str).str.strip().ne("").sum())},
        {"metric": "negative_factor_populated", "value": int(filtered.get("negative_1_factor", pd.Series("", index=filtered.index)).astype(str).str.strip().ne("").sum())},
        {"metric": "built_at", "value": built_at},
    ]
    pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)

    print("[EDGEIQ_RUNNER_DNA_DRAWER_FEED_V2_REFRESH_V1] COMPLETE")
    print(pd.DataFrame(summary_rows).to_string(index=False))
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
