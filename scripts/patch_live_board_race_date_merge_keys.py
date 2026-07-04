from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_runner_board_v1.py")
text = path.read_text(encoding="utf-8")

replacements = {
    '.sort_values(["track", "race_no", "horse_canon", "sportsbet_price_num"], na_position="last")':
    '.sort_values(["race_date", "track", "race_no", "horse_canon", "sportsbet_price_num"], na_position="last")',

    '.drop_duplicates(["track", "race_no", "horse_canon"], keep="first")':
    '.drop_duplicates(["race_date", "track", "race_no", "horse_canon"], keep="first")',

    'print(["track", "race_no", "horse_canon"])':
    'print(["race_date", "track", "race_no", "horse_canon"])',

    'on=["track", "race_no", "horse_canon"],':
    'on=["race_date", "track", "race_no", "horse_canon"],',

    '["track", "race_no", "horse_canon", "v3_fair_price_num", "v3_overlay_pct_num"],':
    '["race_date", "track", "race_no", "horse_canon", "v3_fair_price_num", "v3_overlay_pct_num"],',

    'out.groupby(["track", "race_no"])["live_price"]':
    'out.groupby(["race_date", "track", "race_no"])["live_price"]',

    'out.groupby(["track", "race_no"])["fair_price"]':
    'out.groupby(["race_date", "track", "race_no"])["fair_price"]',

    'out.groupby(["track", "race_no"])["edge_pct"]':
    'out.groupby(["race_date", "track", "race_no"])["edge_pct"]',
}

for old, new in replacements.items():
    if old in text:
        text = text.replace(old, new)

text = text.replace(
    '# Live merge is now strict on track + race_no + horse_canon, so no blanking block is required.',
    '# Live merge is now strict on race_date + track + race_no + horse_canon, so no blanking block is required.'
)

path.write_text(text, encoding="utf-8")
print("Live board merge keys patched to include race_date")
