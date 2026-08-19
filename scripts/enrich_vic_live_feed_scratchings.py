from pathlib import Path
import pandas as pd
import re
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_PATH = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
SYNCED_FIELDS_PATH = DATA / "edgeiq_vic_live_fields_synced.csv"
FIELDS_PATH = DATA / "race_fields.csv"
OUT_PATH = LIVE_PATH
DIAG_PATH = DATA / "edgeiq_vic_scratchings_diagnostics.csv"

def norm(v):
    s = str(v or "").upper().strip()
    s = s.replace("’", "'")
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def clean_race_no(v):
    s = str(v or "").upper().strip()
    s = s.replace("RACE", "").replace("R", "").strip()
    s = re.sub(r"[^0-9]", "", s)
    return s

def as_bool(v):
    s = str(v or "").strip().upper()
    return s in {"1", "Y", "YES", "TRUE", "SCR", "SCRATCHED", "LATE SCR", "LATE SCRATCHING", "WITHDRAWN"}

def load(path):
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False).fillna("")

def make_maps(fields):
    by_full = {}
    by_track_race_horse = {}
    by_track_horse = {}
    by_horse = {}
    source_scratched = 0

    for _, r in fields.iterrows():
        race_date = str(r.get("race_date", r.get("date", ""))).strip()
        track = norm(r.get("track", ""))
        race_no = clean_race_no(r.get("race_no", r.get("race", "")))
        horse = norm(r.get("horse_key", "") or r.get("horse", ""))

        scratched = (
            as_bool(r.get("is_scratched", "")) or
            as_bool(r.get("scratched", "")) or
            as_bool(r.get("scratch_status", "")) or
            as_bool(r.get("runner_status", "")) or
            as_bool(r.get("status", "")) or
            as_bool(r.get("ui_action", "")) or
            as_bool(r.get("execution_action", ""))
        )

        if scratched:
            source_scratched += 1

        if not horse:
            continue

        by_full["|".join([race_date, track, race_no, horse])] = scratched
        by_track_race_horse["|".join([track, race_no, horse])] = scratched
        by_track_horse["|".join([track, horse])] = scratched
        by_horse[horse] = scratched

    return by_full, by_track_race_horse, by_track_horse, by_horse, source_scratched

def main():
    live = load(LIVE_PATH)
    synced = load(SYNCED_FIELDS_PATH)
    fields = load(FIELDS_PATH)

    if live.empty:
        raise SystemExit(f"Missing live feed: {LIVE_PATH}")

    field_source = synced if not synced.empty else fields
    source_name = "edgeiq_vic_live_fields_synced.csv" if not synced.empty else "race_fields.csv"

    by_full, by_track_race_horse, by_track_horse, by_horse, source_scratched = make_maps(field_source)

    for col in [
        "is_scratched",
        "scratch_status",
        "runner_status",
        "ui_action",
        "execution_action",
        "ui_price",
        "sportsbet_price",
        "live_price",
        "market_price",
        "fixed_win",
        "ui_edge_pct",
        "edge_pct",
        "overlay_pct",
    ]:
        if col not in live.columns:
            live[col] = ""

    rows = []
    matched = 0
    scratched_live = 0

    for idx, r in live.iterrows():
        race_date = str(r.get("race_date", r.get("date", ""))).strip()
        track = norm(r.get("track", ""))
        race_no = clean_race_no(r.get("race_no", r.get("race", "")))
        horse = norm(r.get("horse_key", "") or r.get("horse", ""))

        candidates = [
            ("FULL", "|".join([race_date, track, race_no, horse]), by_full),
            ("TRACK_RACE_HORSE", "|".join([track, race_no, horse]), by_track_race_horse),
            ("TRACK_HORSE", "|".join([track, horse]), by_track_horse),
            ("HORSE_ONLY", horse, by_horse),
        ]

        match_type = ""
        scratched = False

        for label, k, mapping in candidates:
            if k in mapping:
                match_type = label
                scratched = mapping[k]
                break

        if match_type:
            matched += 1

        if scratched:
            scratched_live += 1
            live.at[idx, "is_scratched"] = "1"
            live.at[idx, "scratch_status"] = "SCRATCHED"
            live.at[idx, "runner_status"] = "SCRATCHED"
            live.at[idx, "ui_action"] = "SCRATCHED"
            live.at[idx, "execution_action"] = "SCRATCHED"

            for price_col in ["ui_price", "sportsbet_price", "live_price", "market_price", "fixed_win"]:
                live.at[idx, price_col] = ""

            for edge_col in ["ui_edge_pct", "edge_pct", "overlay_pct"]:
                live.at[idx, edge_col] = ""

        rows.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "field_source": source_name,
            "horse": r.get("horse", ""),
            "track": r.get("track", ""),
            "race_no": r.get("race_no", ""),
            "race_date": race_date,
            "horse_key": horse,
            "match_type": match_type or "NO_MATCH",
            "matched_field": "YES" if match_type else "NO",
            "scratched": "YES" if scratched else "NO",
        })

    live.to_csv(OUT_PATH, index=False, encoding="utf-8")
    pd.DataFrame(rows).to_csv(DIAG_PATH, index=False, encoding="utf-8")

    print("=" * 90)
    print("EDGEIQ VIC SCRATCHINGS ENRICHMENT V3")
    print("=" * 90)
    print("FIELD SOURCE:", source_name)
    print("FIELD ROWS:", len(field_source))
    print("SOURCE SCRATCHINGS:", source_scratched)
    print("LIVE ROWS:", len(live))
    print("MATCHED LIVE TO FIELD:", matched)
    print("SCRATCHED LIVE:", scratched_live)
    print("UPDATED:", OUT_PATH)
    print("DIAG:", DIAG_PATH)

if __name__ == "__main__":
    main()
