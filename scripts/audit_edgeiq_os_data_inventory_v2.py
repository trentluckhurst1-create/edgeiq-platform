from pathlib import Path
import csv

data = Path("public/data")
out = Path("public/data/edgeiq_os_data_inventory_v2.csv")

keywords = [
    "race_shape",
    "runner_dna",
    "explain",
    "connection",
    "track",
    "weather",
    "sectional",
    "market",
    "live_runner",
    "terminal",
    "feed",
]

rows = []

for path in sorted(data.glob("*.csv")):
    name = path.name.lower()
    if not any(k in name for k in keywords):
        continue

    headers = []
    row_count = 0

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            headers = next(reader, [])
            for _ in reader:
                row_count += 1
    except Exception as exc:
        headers = [f"READ_ERROR: {exc}"]

    rows.append({
        "file": str(path).replace("\\", "/"),
        "name": path.name,
        "rows": row_count,
        "columns": "|".join(headers[:80]),
    })

out.parent.mkdir(parents=True, exist_ok=True)

with out.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["file", "name", "rows", "columns"])
    writer.writeheader()
    writer.writerows(rows)

print("[EDGEIQ_OS_DATA_INVENTORY] wrote", out)
print("matched_files=", len(rows))

for row in rows:
    print(f"{row['name']} :: rows={row['rows']}")
