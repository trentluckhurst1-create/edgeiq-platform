from pathlib import Path
import pandas as pd
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
TAB = DATA / "edgeiq_tab_live_prices_direct_v1.csv"

manual = [
    [1, "DIDN'T MISS MANY", 11.00, 3.40, "Open"],
    [2, "SOUGHT AFTER", "", "", "SCR"],
    [3, "EMMADELLA", 9.00, 3.00, "Open"],
    [4, "LOVELYCUT", 6.00, 2.30, "Open"],
    [5, "BONS TO RICHES", 19.00, 4.80, "Open"],
    [6, "CHANGING COLOURS", "", "", "SCR"],
    [7, "ONE LONG DAY", 23.00, 6.00, "Open"],
    [8, "STORM SEASON", 9.00, 3.00, "Open"],
    [9, "WITHOUT THINKING", 101.00, 22.00, "Open"],
    [10, "COMIC HERO", 19.00, 5.00, "Open"],
]

rows = []
now = datetime.now().isoformat(timespec="seconds")

for no, horse, win, place, status in manual:
    rows.append({
        "scraped_at": now,
        "source": "TAB_MANUAL_VISIBLE_R9",
        "api_url": "manual_visible_tab_page",
        "meeting_date": "2026-06-13",
        "race_date": "2026-06-13",
        "location": "VIC",
        "meeting_name": "SANDOWN",
        "venue_mnemonic": "SAN",
        "race_type": "R",
        "race_no": "9",
        "runner_no": str(no),
        "horse": horse,
        "barrier": "",
        "jockey": "",
        "trainer": "",
        "tab_fixed_win": "" if win == "" else str(win),
        "tab_fixed_place": "" if place == "" else str(place),
        "tab_fixed_open_win": "",
        "tab_fixed_betting_status": status,
        "tab_tote_win": "",
        "tab_tote_place": "",
    })

existing = pd.read_csv(TAB, dtype=str).fillna("") if TAB.exists() else pd.DataFrame()
r9 = pd.DataFrame(rows)

if len(existing):
    existing = existing[~((existing.get("race_no","").astype(str) == "9") & (existing.get("venue_mnemonic","").astype(str).str.upper() == "SAN"))]
    out = pd.concat([existing, r9], ignore_index=True)
else:
    out = r9

out.to_csv(TAB, index=False)

print("[MANUAL_SEED_TAB_R9] COMPLETE")
print(f"rows_total={len(out)}")
print(f"r9_rows={len(r9)}")
print(TAB)
