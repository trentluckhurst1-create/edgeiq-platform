from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_tab_vic_thoroughbred_urls_v1.csv"

rows = []

meetings = [
    ("2026-06-06", "FLEMINGTON", "FLEMINGTON", "FLM", range(1, 10)),
    ("2026-06-06", "SWAN HILL", "SWAN-HILL", "SWN", range(1, 10)),
]

for date, meeting, slug, venue, races in meetings:
    for rn in races:
        rows.append({
            "meeting_date": date,
            "meeting_name": meeting,
            "location": "VIC",
            "race_type": "R",
            "venue_mnemonic": venue,
            "race_no": rn,
            "tab_frontend_url": f"https://www.tab.com.au/racing/{date}/{slug}/{venue}/R/{rn}",
        })

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)

print("[tab_vic_urls] rows", len(df))
print(df.to_string(index=False))
