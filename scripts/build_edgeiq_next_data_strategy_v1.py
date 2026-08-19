from pathlib import Path
import pandas as pd

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_next_data_strategy_v1.csv"

rows = [
    {
        "priority": 1,
        "problem": "RA HorseFullForm bot-blocked",
        "evidence": "ZenEdge 678-byte interstitial returned for every live profile",
        "wrong_path": "urllib / requests direct scraping",
        "correct_path": "Playwright browser-session capture",
        "expected_impact": "Can backfill active runner form runs from valid live-board RA URLs",
    },
    {
        "priority": 2,
        "problem": "form_card_runs missing active runners",
        "evidence": "0 matches for all 8 Bendigo live runners",
        "wrong_path": "keep trying to match missing rows",
        "correct_path": "build active profile browser backfill",
        "expected_impact": "Live official run count, last3, last5, peak, form confidence become real",
    },
    {
        "priority": 3,
        "problem": "race_fields out of sync with live board",
        "evidence": "live board Bendigo 2026-05-13, race_fields currently 2026-05-15",
        "wrong_path": "using stale race_fields as active truth",
        "correct_path": "active-meeting race_fields refresh before worker",
        "expected_impact": "race_fields matching and class/context fields become reliable",
    },
    {
        "priority": 4,
        "problem": "sectional live linkage low",
        "evidence": "sectional master exists but live runner exact linkage is weak",
        "wrong_path": "treat sectionals as missing globally",
        "correct_path": "use historical horse-only sectionals + active context bridge",
        "expected_impact": "hidden merit, fast finish, sustain signals can inform pricing",
    },
]

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

print(out.to_string(index=False))
print()
print("SAVED:", OUT)
