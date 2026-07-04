from pathlib import Path
import pandas as pd

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

rows = []

for path in sorted(DATA.glob("*.csv")):
    try:
        df = pd.read_csv(path, nrows=1, low_memory=False)

        for c in df.columns:
            rows.append({
                "source_file": path.name,
                "column_name": str(c)
            })

    except:
        pass

out = DATA / "edgeiq_all_csv_column_inventory_v1.csv"
pd.DataFrame(rows).to_csv(out, index=False)

print("[EDGEIQ_ALL_CSV_COLUMN_INVENTORY_V1] COMPLETE")
print(f"out={out}")
