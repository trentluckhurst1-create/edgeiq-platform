from pathlib import Path
from datetime import datetime
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OVERRIDE = DATA / "edgeiq_official_scratchings_override_v1.csv"

TARGET_FILES = [
    DATA / "edgeiq_vic_three_day_meeting_universe.csv",
    DATA / "edgeiq_vic_three_day_race_fields.csv",
    DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
    DATA / "edgeiq_current_field_projection_v5_2.csv",
    DATA / "edgeiq_current_fair_prices_review_v5_2.csv",
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "edgeiq_sectional_value_plays_v1.csv",
]

REMOVED_AUDIT = DATA / "edgeiq_scratching_governance_removed_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_scratching_governance_summary_v1.csv"


def norm(v):
    return re.sub(r"[^A-Z0-9]", "", str(v or "").upper())


def clean(v):
    return str(v or "").strip()


def first_existing(df, names):
    for n in names:
        if n in df.columns:
            return n
    return None


def read_csv(path):
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False).fillna("")


def write_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")


def make_key_parts(df):
    track_col = first_existing(df, ["track", "meeting_track", "venue"])
    race_col = first_existing(df, ["race_no", "race_number", "race"])
    horse_col = first_existing(df, ["horse", "runner", "runner_name", "horse_name", "horse_rated"])

    if not track_col or not race_col or not horse_col:
        return None, None, None

    track = df[track_col].map(norm)
    race = df[race_col].map(lambda x: str(x or "").strip().replace(".0", ""))
    horse = df[horse_col].map(norm)
    return track, race, horse


def main():
    built_at = datetime.now().isoformat(timespec="seconds")

    override = read_csv(OVERRIDE)
    if override.empty:
        print("NO OVERRIDE FILE FOUND:", OVERRIDE)
        return

    o_track, o_race, o_horse = make_key_parts(override)
    override["_scratch_key"] = o_track + "|" + o_race + "|" + o_horse
    scratch_keys = set(override["_scratch_key"].dropna().astype(str))

    removed_rows = []
    summary_rows = []

    for path in TARGET_FILES:
        df = read_csv(path)

        if df.empty:
            summary_rows.append({
                "built_at": built_at,
                "file": path.name,
                "status": "SKIPPED_EMPTY_OR_MISSING",
                "input_rows": 0,
                "removed_rows": 0,
                "output_rows": 0,
            })
            continue

        key_parts = make_key_parts(df)
        if key_parts[0] is None:
            summary_rows.append({
                "built_at": built_at,
                "file": path.name,
                "status": "SKIPPED_NO_KEYS",
                "input_rows": len(df),
                "removed_rows": 0,
                "output_rows": len(df),
            })
            continue

        track, race, horse = key_parts
        df["_scratch_key"] = track + "|" + race + "|" + horse

        mask = df["_scratch_key"].isin(scratch_keys)
        removed = df.loc[mask].copy()
        kept = df.loc[~mask].copy()

        if not removed.empty:
            removed.insert(0, "governance_removed_at", built_at)
            removed.insert(1, "source_file", path.name)
            removed_rows.append(removed)

        kept = kept.drop(columns=["_scratch_key"], errors="ignore")
        write_csv(kept, path)

        summary_rows.append({
            "built_at": built_at,
            "file": path.name,
            "status": "UPDATED",
            "input_rows": len(df),
            "removed_rows": int(mask.sum()),
            "output_rows": len(kept),
        })

    removed_out = pd.concat(removed_rows, ignore_index=True) if removed_rows else pd.DataFrame()
    if not removed_out.empty:
        removed_out = removed_out.drop(columns=["_scratch_key"], errors="ignore")

    write_csv(removed_out, REMOVED_AUDIT)
    write_csv(pd.DataFrame(summary_rows), SUMMARY_OUT)

    print("=" * 90)
    print("EDGEIQ SCRATCHING GOVERNANCE V1")
    print("=" * 90)
    print("override rows:", len(override))
    print("scratch keys:", len(scratch_keys))
    print("removed rows:", len(removed_out))
    print("audit:", REMOVED_AUDIT)
    print("summary:", SUMMARY_OUT)
    print("=" * 90)
    print(pd.DataFrame(summary_rows).to_string(index=False))


if __name__ == "__main__":
    main()
