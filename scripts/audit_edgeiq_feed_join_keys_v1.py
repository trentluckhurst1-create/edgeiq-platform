from pathlib import Path
import csv

feeds = [
    "edgeiq_race_shape_story_v1.csv",
    "edgeiq_runner_dna_drawer_feed_v2.csv",
    "edgeiq_explainability_terminal_feed_v1_2.csv",
]

keys = [
    "meeting",
    "meeting_name",
    "track",
    "track_name",
    "race",
    "race_no",
    "race_number",
    "race_id",
    "runner",
    "runner_name",
]

for feed in feeds:
    path = Path("public/data") / feed

    print("=" * 100)
    print(feed)
    print("=" * 100)

    if not path.exists():
        print("MISSING")
        continue

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        row = next(reader, None)

        if row is None:
            print("EMPTY")
            continue

        for key in keys:
            if key in row:
                print(f"{key}: {row[key]}")
