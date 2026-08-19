from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_runner_board_v1.py")
text = path.read_text(encoding="utf-8")

# Add track/race_no to live_small selected columns
text = text.replace(
'''        "sportsbet_price_num",
        "market_mover",''',
'''        "sportsbet_price_num",
        "track",
        "race_no",
        "market_mover",'''
)

# Replace live dedupe
text = text.replace(
'''.sort_values(["horse_canon", "sportsbet_price_num"], na_position="last")
    .drop_duplicates(["horse_canon", "event_id"], keep="first")''',
'''.sort_values(["track", "race_no", "horse_canon", "sportsbet_price_num"], na_position="last")
    .drop_duplicates(["track", "race_no", "horse_canon"], keep="first")'''
)

# Replace live merge key
text = text.replace(
'''merged = merged.merge(
    live_small,
    on=["horse_canon"],
    how="left",
    suffixes=("", "_live")
)''',
'''card["track"] = card["track"].astype(str).str.upper().str.strip()
live_small["track"] = live_small["track"].astype(str).str.upper().str.strip()
card["race_no"] = card["race_no"].astype(str).str.replace(".0", "", regex=False).str.strip()
live_small["race_no"] = live_small["race_no"].astype(str).str.replace(".0", "", regex=False).str.strip()

print("=" * 100)
print("LIVE MERGE KEYS")
print("=" * 100)
print(["track", "race_no", "horse_canon"])

merged = merged.merge(
    live_small,
    on=["track", "race_no", "horse_canon"],
    how="left",
    suffixes=("", "_live")
)'''
)

path.write_text(text, encoding="utf-8")
print("PATCHED LIVE MERGE TO TRACK + RACE_NO + HORSE")
