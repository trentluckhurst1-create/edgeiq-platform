from pathlib import Path
import csv

files = [
  "edgeiq_race_shape_story_v1.csv",
  "edgeiq_runner_dna_drawer_feed_v2.csv",
  "edgeiq_explainability_terminal_feed_v1_2.csv",
  "edgeiq_connection_intelligence_v2_1.csv",
  "edgeiq_live_track_intelligence_v2_1.csv",
  "edgeiq_live_weather_feed_v1.csv",
  "edgeiq_market_intelligence_v1.csv",
  "edgeiq_live_sectional_intelligence_v1.csv",
]

data = Path("public/data")

for name in files:
    path = data / name
    print("")
    print("=" * 100)
    print(name)
    print("=" * 100)

    if not path.exists():
        print("MISSING")
        continue

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        print("ROWS:", sum(1 for _ in reader))

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        print("COLUMNS:")
        print("|".join(reader.fieldnames or []))

        print("SAMPLE:")
        for i, row in enumerate(reader):
            if i >= 2:
                break
            compact = {k: row.get(k, "") for k in (reader.fieldnames or [])[:30]}
            print(compact)
