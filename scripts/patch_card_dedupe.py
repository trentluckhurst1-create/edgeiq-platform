from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_runner_board_v1.py")
text = path.read_text(encoding="utf-8")

anchor = 'card["horse_canon"] = card["horse"].apply(canon)'

inject = '''
card["horse_canon"] = card["horse"].apply(canon)

# ====================================================================================
# HARD DEDUPE ACTIVE CARD
# ====================================================================================

card["race_key"] = (
    card["track"].astype(str).str.upper().str.strip()
    + "_R"
    + card["race_no"].astype(str).str.strip()
)

before = len(card)

card = (
    card
    .sort_values(
        ["race_date"],
        ascending=False,
        na_position="last"
    )
    .drop_duplicates(
        ["race_key", "horse_canon"],
        keep="first"
    )
)

after = len(card)

print("=" * 100)
print("CARD DEDUPE")
print("=" * 100)
print("BEFORE:", before)
print("AFTER :", after)
print("REMOVED:", before - after)
'''

if anchor not in text:
    raise SystemExit("ANCHOR NOT FOUND")

text = text.replace(anchor, inject)

path.write_text(text, encoding="utf-8")

print("HARD CARD DEDUPE PATCHED")
