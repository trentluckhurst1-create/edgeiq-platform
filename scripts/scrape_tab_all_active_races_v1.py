from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

from audit_edgeiq_current_day_source_inventory_v1 import (
    TODAY,
    get_display_track,
    get_track_config,
    load_selected_source_rows,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SCRAPER = ROOT / "scripts" / "scrape_tab_single_race_v1.py"
SINGLE_RACE = DATA / "edgeiq_tab_single_race_v1.csv"

OUT = DATA / "edgeiq_tab_live_prices_direct_v1.csv"
AUDIT = DATA / "edgeiq_tab_all_active_races_scrape_audit_v1.csv"


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def norm_track(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\s+", " ", text)
    return text


def canonical_track(value: object) -> str:
    selected_track = get_display_track()
    aliases = {norm_track(alias) for alias in get_track_config(selected_track).get("aliases", set())}
    track = norm_track(value)
    if track in aliases:
        return selected_track
    return track


def horse_key(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\b(NZ|GB|IRE|USA|FR|JPN|SAF|GER|CAN)\b", " ", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def race_no(value: object) -> str:
    return re.sub(r"[^0-9]", "", clean(value))


def build_race_inventory() -> tuple[pd.DataFrame, Path]:
    selected_track = get_display_track()
    source_path, source_rows, choice, _ = load_selected_source_rows(purpose="scrape", write_outputs=True)
    race_col = str(choice.get("race_no_column_used", ""))
    track_col = str(choice.get("track_column_used", ""))

    if not race_col or race_col not in source_rows.columns:
        raise SystemExit(f"Selected source missing race number column: {source_path}")

    inventory = source_rows.copy()
    inventory["source_track_key"] = (
        inventory[track_col].map(canonical_track) if track_col and track_col in inventory.columns else selected_track
    )
    inventory["race_no_key"] = inventory[race_col].map(race_no)

    races = (
        inventory[inventory["race_no_key"] != ""][["source_track_key", "race_no_key"]]
        .drop_duplicates()
        .sort_values(["race_no_key"], key=lambda series: series.astype(int))
        .reset_index(drop=True)
    )
    races["race_date_key"] = TODAY

    if races.empty:
        raise SystemExit(f"Selected source had no valid today races for {selected_track}: {source_path}")

    return races, source_path


def scrape_race(date_value: str, source_track_key: str, race_number: str) -> tuple[str, int, str]:
    selected_track = get_display_track()
    track_config = get_track_config(selected_track)
    venue = clean(track_config.get("tab_venue"))
    slug = clean(track_config.get("tab_slug")) or re.sub(r"[^a-z0-9]+", "-", selected_track.lower()).strip("-")
    race_type = clean(track_config.get("tab_race_type")) or "R"

    if not venue:
        return "NO_VENUE_CODE", 0, f"selected_track={selected_track}"

    url = f"https://www.tab.com.au/racing/{date_value}/{slug}/{venue}/{race_type}/{race_number}"
    try:
        completed = subprocess.run(
            [sys.executable, str(SCRAPER), "--url", url],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return "SCRAPER_TIMEOUT", 0, url

    if completed.returncode != 0:
        note = (completed.stdout or "")[-300:] + (completed.stderr or "")[-300:]
        return "SCRAPER_FAIL", 0, note or url

    if not SINGLE_RACE.exists():
        return "NO_SINGLE_FILE", 0, url

    try:
        race_df = pd.read_csv(SINGLE_RACE, dtype=str, keep_default_na=False, low_memory=False)
    except Exception as exc:
        return "READ_FAIL", 0, repr(exc)

    if race_df.empty:
        return "ZERO_ROWS", 0, url

    return "OK", len(race_df), url


def main() -> None:
    selected_track = get_display_track()
    races, source_path = build_race_inventory()
    all_rows: list[pd.DataFrame] = []
    audit_rows: list[dict[str, object]] = []

    print(f"[TAB_ALL_ACTIVE] source_inventory={source_path.name}")
    print(f"[TAB_ALL_ACTIVE] today={TODAY}")
    print(f"[TAB_ALL_ACTIVE] target_track={selected_track}")
    print(f"[TAB_ALL_ACTIVE] races={len(races)}")

    for row in races.to_dict("records"):
        race_date = row["race_date_key"]
        source_track_key = clean(row["source_track_key"]) or selected_track
        race_number = row["race_no_key"]
        status, count, note = scrape_race(race_date, source_track_key, race_number)

        audit_rows.append(
            {
                "race_date": race_date,
                "track": selected_track,
                "source_inventory_file": source_path.name,
                "source_track": source_track_key,
                "race_no": race_number,
                "status": status,
                "rows": count,
                "url_or_note": note,
            }
        )

        if status != "OK":
            print(f"[TAB_ALL_ACTIVE] {source_track_key} R{race_number} {status}")
            continue

        race_df = pd.read_csv(SINGLE_RACE, dtype=str, keep_default_na=False, low_memory=False)
        race_df["race_date"] = race_date
        race_df["meeting_date"] = race_date
        race_df["track"] = selected_track
        race_df["track_source_tab"] = source_track_key
        race_df["race_no"] = race_number
        race_df["horse_key"] = race_df["horse"].map(horse_key)
        all_rows.append(race_df)
        print(f"[TAB_ALL_ACTIVE] {source_track_key} R{race_number} OK rows={len(race_df)}")
        time.sleep(0.2)

    if all_rows:
        out = pd.concat(all_rows, ignore_index=True)
        out = out.drop_duplicates(["meeting_date", "track", "race_no", "horse_key"], keep="first")
        out.to_csv(OUT, index=False)
    else:
        pd.DataFrame().to_csv(OUT, index=False)

    audit_df = pd.DataFrame(audit_rows)
    audit_df.to_csv(AUDIT, index=False)

    ok_rows = int(audit_df.loc[audit_df["status"] == "OK", "rows"].sum()) if not audit_df.empty else 0
    failed = audit_df[audit_df["status"] != "OK"]

    print("[TAB_ALL_ACTIVE] COMPLETE")
    print(f"today={TODAY}")
    print(f"target_track={selected_track}")
    print(f"source_inventory={source_path.name}")
    print(f"races_scraped={len(audit_df)}")
    print(f"rows={ok_rows}")
    print(f"out={OUT}")
    print(f"audit={AUDIT}")

    if not failed.empty:
        print("[TAB_ALL_ACTIVE] FAILURES")
        print(failed.to_string(index=False))


if __name__ == "__main__":
    main()
